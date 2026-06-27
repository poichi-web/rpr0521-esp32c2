import machine, time, sys

i2c = machine.I2C(0, sda=machine.Pin(5), scl=machine.Pin(6), freq=100000)
ADDR = 0x38

def wreg(reg, val):
    i2c.writeto(ADDR, bytes([reg, val]))

def rreg(reg):
    i2c.writeto(ADDR, bytes([reg]), False)
    return i2c.readfrom(ADDR, 1)[0]

def rburst(reg, n):
    i2c.writeto(ADDR, bytes([reg]), False)
    return i2c.readfrom(ADDR, n)

def reset():
    wreg(0x40, 0xC0)
    time.sleep_ms(20)

def read_als():
    d = rburst(0x46, 4)
    return (d[1] << 8) | d[0], (d[3] << 8) | d[2]

def read_ps():
    d = rburst(0x44, 2)
    return ((d[1] & 0x0F) << 8) | d[0]

reset()
# Read SYSTEM_CONTROL (part/manufacturer ID)
sc = rreg(0x40)
sys.stdout.write("SYSTEM_CONTROL=0x{:02X} (expect 0x0A=ROHM RPR-0521RS)\r\n".format(sc))

# --- Phase 1: Try MEAS_TIME 0x00-0x09 with bits[7:4]=0 (ALS+PS modes only) ---
sys.stdout.write("\r\n=== Phase 1: MEAS_TIME 0x00-0x09, APC=0x03 ===\r\n")
for mv in range(0x00, 0x0A):
    reset()
    wreg(0x41, mv)
    wreg(0x42, 0x03)
    time.sleep_ms(300)
    ps = read_ps()
    a0, a1 = read_als()
    sys.stdout.write("0x41={:02X} PS={:4d} ALS0={:5d} ALS1={:5d}\r\n".format(mv, ps, a0, a1))

# --- Phase 2: High ALS gain test ---
sys.stdout.write("\r\n=== Phase 2: ALS gain sweep, MODE=0x06 (ALS50ms+PS50ms) ===\r\n")
# ALS_PS_CONTROL bits[7:6]=ALS0gain, bits[5:4]=ALS1gain, bits[3:2]=LED, bits[1:0]=PSgain
# gains: 00=x1, 01=x2, 10=x64, 11=x128
for apc in [0x03, 0x43, 0x83, 0xC3, 0xC7, 0xFF]:
    reset()
    wreg(0x41, 0x06)
    wreg(0x42, apc)
    time.sleep_ms(300)
    a0, a1 = read_als()
    ps = read_ps()
    sys.stdout.write("APC=0x{:02X} PS={:4d} ALS0={:5d} ALS1={:5d}\r\n".format(apc, ps, a0, a1))

# --- Phase 3: Individual register reads (not burst) ---
sys.stdout.write("\r\n=== Phase 3: Single-reg reads after 0x06+0x03 ===\r\n")
reset()
wreg(0x41, 0x06)
wreg(0x42, 0xC3)   # x128 ALS0 gain, 25mA LED
time.sleep_ms(300)
for reg in [0x44, 0x45, 0x46, 0x47, 0x48, 0x49, 0x4A]:
    v = rreg(reg)
    sys.stdout.write("  reg[0x{:02X}]=0x{:02X} ({})\r\n".format(reg, v, v))

# --- Phase 4: Continuous ALS monitoring with x128 gain ---
sys.stdout.write("\r\n=== Phase 4: Live (wave hand AND shine light) ===\r\n")
reset()
wreg(0x41, 0x06)   # ALS 50ms + PS 50ms, 1 pulse
wreg(0x42, 0xC3)   # ALS0 x128 gain, ALS1 x1, LED 25mA, PS x4
time.sleep_ms(150)
for _ in range(20):
    ps = read_ps()
    a0, a1 = read_als()
    sys.stdout.write("PS:{:4d} ALS0:{:6d} ALS1:{:6d}\r\n".format(ps, a0, a1))
    time.sleep_ms(500)
