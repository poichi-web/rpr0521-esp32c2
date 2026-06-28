"""
書斎照度プロジェクト - 10分間隔ロガー (ESP32-C2 / RPR-0521RS)

deploy.py でデプロイすると RTC 設定済みの状態で main.py として動作する。
ログは /log.csv に蓄積される（3日間 = 約432件 / ~15KB）。
"""
import machine, time, sys, os

i2c  = machine.I2C(0, sda=machine.Pin(5), scl=machine.Pin(6), freq=100000)
ADDR = 0x38

def wreg(reg, val):
    i2c.writeto(ADDR, bytes([reg, val]))

def rburst(reg, n):
    i2c.writeto(ADDR, bytes([reg]), False)
    return i2c.readfrom(ADDR, n)

def read_sensor():
    d    = rburst(0x44, 6)
    ps   = ((d[1] & 0x0F) << 8) | d[0]
    als0 = (d[3] << 8) | d[2]
    als1 = (d[5] << 8) | d[4]
    return ps, als0, als1

def to_lux(als0, als1):
    if als0 == 0:
        return 0.0
    d  = als1 / als0
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

# センサー初期化
wreg(0x40, 0xC0)
time.sleep_ms(50)
wreg(0x41, 0xE6)   # bit7=1 必須、ALS+PS 同時測定
wreg(0x42, 0x03)   # ALS x1 gain, LED 25mA
time.sleep_ms(200)

LOG_FILE   = '/log.csv'
INTERVAL_S = 600   # 10分 = 3日で 432 件

rtc = machine.RTC()

# ヘッダー書き込み（新規ファイルの場合のみ）
try:
    os.stat(LOG_FILE)
    write_header = False
except OSError:
    write_header = True

with open(LOG_FILE, 'a') as f:
    if write_header:
        f.write('time,lux,ps,als0,als1\r\n')

t = rtc.datetime()
sys.stdout.write("=== Logger started ({:04d}-{:02d}-{:02d} {:02d}:{:02d}) ===\r\n".format(
    t[0], t[1], t[2], t[4], t[5]))
sys.stdout.write("Interval: {}min  Log: {}\r\n".format(INTERVAL_S // 60, LOG_FILE))

next_tick = time.ticks_ms()

while True:
    now = rtc.datetime()
    ts  = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
        now[0], now[1], now[2], now[4], now[5], now[6])

    try:
        ps, als0, als1 = read_sensor()
        lux = to_lux(als0, als1)
    except Exception as e:
        sys.stdout.write("READ_ERR:{}\r\n".format(e))
        ps, als0, als1, lux = 0, 0, 0, 0.0

    line = "{},{:.1f},{},{},{}\r\n".format(ts, lux, ps, als0, als1)
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(line)
    except OSError as e:
        sys.stdout.write("WRITE_ERR:{}\r\n".format(e))

    sys.stdout.write(line)

    next_tick = time.ticks_add(next_tick, INTERVAL_S * 1000)
    wait = time.ticks_diff(next_tick, time.ticks_ms())
    if wait > 0:
        time.sleep_ms(wait)
    else:
        next_tick = time.ticks_ms()
