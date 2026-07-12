import machine, time, sys

i2c = machine.I2C(0, sda=machine.Pin(5), scl=machine.Pin(6), freq=100000)
ADDR = 0x38

def wreg(reg, val):
    i2c.writeto(ADDR, bytes([reg, val]))

def rburst(reg, n):
    i2c.writeto(ADDR, bytes([reg]), False)
    return i2c.readfrom(ADDR, n)

def read_sensor():
    d = rburst(0x44, 6)
    ps   = ((d[1] & 0x0F) << 8) | d[0]
    als0 = (d[3] << 8) | d[2]
    als1 = (d[5] << 8) | d[4]
    return ps, als0, als1

def to_lux(als0, als1):
    if als0 == 0:
        return 0.0
    d = als1 / als0
    cf = 2.0
    if d < 0.595:
        lux = cf * (1.682 * als0 - 1.877 * als1)
    elif d < 1.015:
        lux = cf * (0.644 * als0 - 0.132 * als1)
    elif d < 1.352:
        lux = cf * (0.756 * als0 - 0.243 * als1)
    else:
        lux = cf * 0.766 * als0
    return max(0.0, lux)

wreg(0x40, 0xC0)
time.sleep_ms(50)
wreg(0x41, 0xE6)
wreg(0x42, 0x03)
time.sleep_ms(200)

sys.stdout.write("live lux start\r\n")

for _ in range(60):
    ps, a0, a1 = read_sensor()
    lux = to_lux(a0, a1)
    sys.stdout.write("lux={:.1f} ps={} als0={} als1={}\r\n".format(lux, ps, a0, a1))
    time.sleep_ms(500)
