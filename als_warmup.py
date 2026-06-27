import machine, time, sys

i2c = machine.I2C(0, sda=machine.Pin(5), scl=machine.Pin(6), freq=100000)
ADDR = 0x38

def wreg(reg, val):
    i2c.writeto(ADDR, bytes([reg, val]))

def rburst(reg, n):
    i2c.writeto(ADDR, bytes([reg]), False)
    return i2c.readfrom(ADDR, n)

def read_all():
    d = rburst(0x44, 6)
    ps   = ((d[1] & 0x0F) << 8) | d[0]
    als0 = (d[3] << 8) | d[2]
    als1 = (d[5] << 8) | d[4]
    return ps, als0, als1

# Fresh reset, then 0x66 (same as original script) — watch for ALS to appear
wreg(0x40, 0xC0)
time.sleep_ms(50)
wreg(0x41, 0x66)
wreg(0x42, 0x03)

sys.stdout.write("=== Warm-up test with 0x66 (60 readings x 500ms = 30s) ===\r\n")
sys.stdout.write("Watch ALS0 — shine flashlight at t~15s mark\r\n")
for i in range(60):
    ps, a0, a1 = read_all()
    sys.stdout.write("t={:2d}s PS:{:4d} ALS0:{:5d} ALS1:{:5d}\r\n".format(
        i // 2, ps, a0, a1))
    time.sleep_ms(500)

# Now force PS-off to check if ALS0/ALS1 are from PS LED reflection
sys.stdout.write("\r\n=== PS LED off (MEAS_TIME=5 → ALS100ms PS-off), 0x66→0x65 ===\r\n")
wreg(0x41, 0x65)   # MEAS_TIME=5 = ALS 100ms, PS off (if same bit layout as 0x66)
time.sleep_ms(300)
for _ in range(10):
    ps, a0, a1 = read_all()
    sys.stdout.write("PS:{:4d} ALS0:{:5d} ALS1:{:5d}\r\n".format(ps, a0, a1))
    time.sleep_ms(500)

sys.stdout.write("\r\n=== PS LED off with 0xE5 ===\r\n")
wreg(0x41, 0xE5)
time.sleep_ms(300)
for _ in range(10):
    ps, a0, a1 = read_all()
    sys.stdout.write("PS:{:4d} ALS0:{:5d} ALS1:{:5d}\r\n".format(ps, a0, a1))
    time.sleep_ms(500)

sys.stdout.write("\r\n=== ALS-only x128 gain (0xE5 + APC=0xC0) ===\r\n")
wreg(0x41, 0xE5)
wreg(0x42, 0xC0)   # ALS0 x128, ALS1 x1, LED off
time.sleep_ms(300)
for _ in range(10):
    ps, a0, a1 = read_all()
    sys.stdout.write("PS:{:4d} ALS0:{:5d} ALS1:{:5d}\r\n".format(ps, a0, a1))
    time.sleep_ms(500)
