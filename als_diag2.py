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

def read_all():
    d = rburst(0x44, 6)
    ps   = ((d[1] & 0x0F) << 8) | d[0]
    als0 = (d[3] << 8) | d[2]
    als1 = (d[5] << 8) | d[4]
    return ps, als0, als1

# --- Step 1: ONE soft reset, then try values WITHOUT resetting between ---
sys.stdout.write("=== ONE-TIME reset, then mode scan ===\r\n")
wreg(0x40, 0xC0)  # soft reset
time.sleep_ms(50)
sys.stdout.write("After reset: SC=0x{:02X}\r\n".format(rreg(0x40)))

# ALS_PS_CONTROL stays at 0x03 throughout
wreg(0x42, 0x03)

# Try each MEAS_TIME without intermediate resets
for mv in [0x01, 0x06, 0x46, 0x66, 0x16, 0x26, 0x36, 0x56, 0x76, 0xE6]:
    wreg(0x41, mv)
    time.sleep_ms(400)  # wait 4 measurement cycles
    ps, a0, a1 = read_all()
    mc = rreg(0x41)
    sys.stdout.write("SET=0x{:02X} READ=0x{:02X} PS={:4d} ALS0={:5d} ALS1={:5d}\r\n".format(mv, mc, ps, a0, a1))

# --- Step 2: Find which value restores PS (confirms 0x66 still works) ---
sys.stdout.write("\r\n=== Restore 0x66+0x03, 10 readings ===\r\n")
wreg(0x41, 0x66)
wreg(0x42, 0x03)
time.sleep_ms(200)
for _ in range(10):
    ps, a0, a1 = read_all()
    sys.stdout.write("PS:{:4d} ALS0:{:5d} ALS1:{:5d}\r\n".format(ps, a0, a1))
    time.sleep_ms(500)

# --- Step 3: ALS-specific register check ---
sys.stdout.write("\r\n=== Reg dump while 0x66 active ===\r\n")
for reg in range(0x40, 0x50):
    v = rreg(reg)
    sys.stdout.write("  [0x{:02X}]=0x{:02X} {:3d}\r\n".format(reg, v, v))
