import csv, sys
sys.stdout.reconfigure(encoding='utf-8')

with open('c:/dev/rpr0521_test/log.csv', newline='') as f:
    rows = list(csv.DictReader(f))

lux   = [float(r['lux']) for r in rows]
times = [r['time'] for r in rows]

print('=== Stats ===')
print('Total records:', len(rows))
print('Min lux: {:.1f}  at {}'.format(min(lux), times[lux.index(min(lux))]))
print('Max lux: {:.1f}  at {}'.format(max(lux), times[lux.index(max(lux))]))

lights_off = next((times[i] for i,v in enumerate(lux) if v < 10), None)
dawn = next((times[i] for i,v in enumerate(lux) if times[i] >= '2026-06-28 03:00' and v > 50), None)
print('Lights off (< 10 lux):', lights_off)
print('Dawn     (> 50 lux)  :', dawn)

from collections import defaultdict
hourly = defaultdict(list)
for r in rows:
    h = r['time'][11:13]
    hourly[h].append(float(r['lux']))

print()
print('=== Hourly average lux ===')
for h in sorted(hourly):
    vals = hourly[h]
    print('  {}:xx  avg={:6.1f}  min={:6.1f}  max={:6.1f}'.format(
        h, sum(vals)/len(vals), min(vals), max(vals)))

print()
print('=== 30min interval samples ===')
for r in rows:
    mm = int(r['time'][14:16])
    if mm == 0 or mm == 30:
        print('  {}  {:7.1f} lux  ALS0={}'.format(
            r['time'][11:], float(r['lux']), r['als0']))
