import csv, sys
sys.stdout.reconfigure(encoding='utf-8')

LOG_FILE = 'c:/dev/rpr0521_test/log.csv'

with open(LOG_FILE, newline='') as f:
    rows = list(csv.DictReader(f))

if not rows:
    print('No data.')
    sys.exit(0)

lux   = [float(r['lux']) for r in rows]
times = [r['time'] for r in rows]

print('=== 照度ログ集計 ===')
print('期間: {} ~ {}'.format(times[0], times[-1]))
print('記録件数: {} 件'.format(len(rows)))
print()
print('最大: {:7.1f} lux  at {}'.format(max(lux), times[lux.index(max(lux))]))
print('最小: {:7.1f} lux  at {}'.format(min(lux), times[lux.index(min(lux))]))
print('平均: {:7.1f} lux'.format(sum(lux) / len(lux)))
print()

# 日別サマリ
from collections import defaultdict
daily = defaultdict(list)
for r in rows:
    day = r['time'][:10]
    daily[day].append(float(r['lux']))

print('=== 日別サマリ ===')
for day in sorted(daily):
    vals = daily[day]
    daytime = [v for v in vals if v > 10]
    avg_day = sum(daytime)/len(daytime) if daytime else 0
    print('{} | max={:6.1f} avg(明)={:6.1f} dark={}h'.format(
        day, max(vals), avg_day,
        sum(1 for v in vals if v < 5)))

print()

# 時間帯別（全日共通）
hourly = defaultdict(list)
for r in rows:
    h = int(r['time'][11:13])
    hourly[h].append(float(r['lux']))

print('=== 時間帯別 lux（全日平均） ===')
for h in sorted(hourly):
    vals = hourly[h]
    bar = '#' * int(sum(vals)/len(vals)/20)
    print('  {:02d}:xx {:5.1f} lux  {}'.format(h, sum(vals)/len(vals), bar))

print()

# 植物育成評価
peak = max(lux)
avg_bright = sum(v for v in lux if v > 10) / max(1, sum(1 for v in lux if v > 10))
print('=== 植物育成評価 ===')
print('ピーク照度: {:.0f} lux'.format(peak))
print('明時平均:   {:.0f} lux'.format(avg_bright))

if peak >= 5000:
    plant = 'ほとんどの植物に十分（野菜・ハーブも可）'
elif peak >= 2000:
    plant = '多くの観葉植物に適切（モンステラ・ゴムの木等）'
elif peak >= 1000:
    plant = '耐陰性植物向き（ポトス・アスプレニウム等）'
elif peak >= 300:
    plant = '暗所向き植物のみ（サンセベリア等）'
else:
    plant = '植物育成には光量不足（人工照明の追加を検討）'

print('育成適性:   {}'.format(plant))
