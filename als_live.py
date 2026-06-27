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

# ONE reset then set 0xE6 (bit7=1 required for ALS)
wreg(0x40, 0xC0)
time.sleep_ms(50)
wreg(0x41, 0xE6)   # ALS+PS continuous
wreg(0x42, 0x03)   # gain x1, LED 25mA
time.sleep_ms(200)

sys.stdout.write("MODE=0x{:02X} APC=0x{:02X}\r\n".format(
    rburst(0x41,1)[0], rburst(0x42,1)[0]))
sys.stdout.write("Live: shine flashlight at sensor, wave hand nearby\r\n")
sys.stdout.write("PS=proximity  ALS0=visible  ALS1=IR\r\n")

while True:
    try:
        ps, a0, a1 = read_all()
        sys.stdout.write("PS:{:4d}  ALS0:{:6d}  ALS1:{:6d}\r\n".format(ps, a0, a1))
    except Exception as e:
        sys.stdout.write("ERR:{}\r\n".format(e))
    time.sleep_ms(500)
