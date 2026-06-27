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

# Enable ALS with bit7=1, ALS0 x128 gain
wreg(0x40, 0xC0)
time.sleep_ms(50)
wreg(0x41, 0xE6)
wreg(0x42, 0xC3)  # ALS0 x128, ALS1 x1, LED 25mA, PS x4

sys.stdout.write("MODE=0x{:02X} APC=0x{:02X}\r\n".format(rreg(0x41), rreg(0x42)))
sys.stdout.write("ALS0 x128 gain. Steps:\r\n")
sys.stdout.write(" t=0-5s: normal (open sensor)\r\n")
sys.stdout.write(" t=5-10s: cover sensor COMPLETELY with finger/tape\r\n")
sys.stdout.write(" t=10-15s: flashlight directly on sensor\r\n")
sys.stdout.write(" t=15s+: open again\r\n")

for i in range(40):
    ps, a0, a1 = read_all()
    sys.stdout.write("t={:2d}s PS:{:4d} ALS0:{:6d} ALS1:{:5d}\r\n".format(
        i // 2, ps, a0, a1))
    time.sleep_ms(500)

# Dump full 0x44-0x4F to see raw bytes
sys.stdout.write("\r\nRaw regs 0x44-0x4F:\r\n")
d = rburst(0x44, 12)
for i in range(12):
    sys.stdout.write("  [0x{:02X}]=0x{:02X} ({})\r\n".format(0x44+i, d[i], d[i]))
