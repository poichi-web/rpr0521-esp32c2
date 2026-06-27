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
    return ((d[1]&0xF)<<8)|d[0], (d[3]<<8)|d[2], (d[5]<<8)|d[4]

wreg(0x40, 0xC0)
time.sleep_ms(50)
wreg(0x41, 0xE6)
wreg(0x42, 0x03)   # same as before but MODE=0xE6
time.sleep_ms(200)

sys.stdout.write("APC=0x03 (x1 gain). Cover at t=5s, flashlight at t=10s\r\n")
for i in range(40):
    ps, a0, a1 = read_all()
    sys.stdout.write("t={:2d}s PS:{:4d} ALS0:{:5d} ALS1:{:4d}\r\n".format(i//2, ps, a0, a1))
    time.sleep_ms(500)
