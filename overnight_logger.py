import machine, time, sys, os

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

# RTC: 起動のたびに上書きしない（電源断以外のリセットで時刻が過去に巻き戻るバグを回避）
# 電源断でRTCが失われた場合のみ、下の日時で初期化する
rtc = machine.RTC()
if rtc.datetime()[0] < 2026:
    rtc.datetime((2026, 7, 2, 3, 22, 3, 0, 0))  # 電源断復旧時のフォールバック

# センサー初期化
wreg(0x40, 0xC0)
time.sleep_ms(50)
wreg(0x41, 0xE6)
wreg(0x42, 0x03)
time.sleep_ms(200)

LOG_FILE = '/log.csv'
INTERVAL_S = 3600  # 1時間ごと

write_header = True
try:
    os.stat(LOG_FILE)
    write_header = False
except:
    pass

with open(LOG_FILE, 'a') as f:
    if write_header:
        f.write('time,lux,ps,als0,als1\r\n')

sys.stdout.write("Logging 1h interval. Appending to {}\r\n".format(LOG_FILE))

# 最初の1件を即時記録してから1時間待機
next_tick = time.ticks_ms()

while True:
    now = rtc.datetime()
    h, m, s = now[4], now[5], now[6]

    ps, als0, als1 = read_sensor()
    lux = to_lux(als0, als1)

    ts = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
        now[0], now[1], now[2], h, m, s)
    line = "{},{:.1f},{},{},{}\r\n".format(ts, lux, ps, als0, als1)

    with open(LOG_FILE, 'a') as f:
        f.write(line)

    sys.stdout.write(line)

    next_tick = time.ticks_add(next_tick, INTERVAL_S * 1000)
    wait = time.ticks_diff(next_tick, time.ticks_ms())
    if wait > 0:
        time.sleep_ms(wait)
    else:
        next_tick = time.ticks_ms()
