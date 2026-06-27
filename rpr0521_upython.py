import machine, time, sys

i2c = machine.I2C(0, sda=machine.Pin(5), scl=machine.Pin(6), freq=100000)
ADDR = 0x38

def wreg(reg, val):
    i2c.writeto(ADDR, bytes([reg, val]))

def rburst(reg, n):
    i2c.writeto(ADDR, bytes([reg]), False)
    return i2c.readfrom(ADDR, n)

wreg(0x40, 0xC0)
time.sleep_ms(50)
# 0xE6: bit7 must be 1 for ALS to activate; bits[7:6]=11=8 PS pulses; MEAS_TIME=6
wreg(0x41, 0xE6)
wreg(0x42, 0x03)
time.sleep_ms(200)

mc  = rburst(0x41, 1)[0]
apc = rburst(0x42, 1)[0]
sys.stdout.write("MODE=0x{:02X} APC=0x{:02X}\r\n".format(mc, apc))
sys.stdout.write("Reading (wave hand=PS up, flashlight=ALS up)\r\n")

while True:
    try:
        d = rburst(0x44, 6)
        ps   = ((d[1] & 0x0F) << 8) | d[0]
        als0 = (d[3] << 8) | d[2]
        als1 = (d[5] << 8) | d[4]
        sys.stdout.write("PS:{:4d}  ALS0:{:5d}  ALS1:{:5d}\r\n".format(ps, als0, als1))
    except Exception as e:
        sys.stdout.write("ERR: {}\r\n".format(e))
    time.sleep_ms(500)
