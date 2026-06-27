import machine, time

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

# Reset
wreg(0x40, 0xC0)
time.sleep_ms(20)

print("=== ALS only test (PS off) ===")
# 0x64 = 0b01100100: ALS enabled, PS disabled
wreg(0x41, 0x64)
wreg(0x42, 0x02)  # gain x1, LED off (PS off)
time.sleep_ms(200)
print(f"MODE=0x{rreg(0x41):02X}")
for i in range(5):
    d = rburst(0x46, 4)  # ALS0+ALS1
    als0 = (d[1] << 8) | d[0]
    als1 = (d[3] << 8) | d[2]
    print(f"  ALS0={als0} ALS1={als1}")
    time.sleep_ms(200)

print("\n=== Full scan: 0x41 values 0x00-0x6F ===")
for mv in [0x60, 0x61, 0x62, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68, 0x69, 0x6A, 0x6B]:
    wreg(0x41, mv)
    time.sleep_ms(150)
    d = rburst(0x44, 6)
    ps   = ((d[1] & 0x0F) << 8) | d[0]
    als0 = (d[3] << 8) | d[2]
    als1 = (d[5] << 8) | d[4]
    print(f"  0x41=0x{mv:02X} → PS={ps} ALS0={als0} ALS1={als1}")
