import csv
import json
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")

LOG_FILE = "log_device_20260702.csv"
WEATHER_FILE = r"C:/Users/highm/AppData/Local/Temp/claude/c--dev-rpr0521-test/324ca9ae-0441-4a8e-9523-8454d7baeb72/scratchpad/tokyo_weather.json"

WMO_JA = {
    0: "快晴", 1: "晴れ", 2: "薄曇り", 3: "曇り",
    45: "霧", 48: "霧氷",
    51: "小雨(霧雨)", 53: "霧雨", 55: "強い霧雨",
    61: "小雨", 63: "雨", 65: "大雨",
    80: "にわか雨", 81: "強いにわか雨", 82: "非常に強いにわか雨",
}

# --- 照度ログ読み込み（RTCリセットで生じた異常行を除外） ---
rows = list(csv.reader(open(LOG_FILE, encoding="utf-8")))
header, rows = rows[0], rows[1:]

clean = []
prev_ts = None
for r in rows:
    ts = r[0]
    if prev_ts and ts < prev_ts:
        continue  # RTCリセットによる巻き戻り行をスキップ
    clean.append(r)
    prev_ts = ts

print(f"有効レコード数: {len(clean)} / 全 {len(rows)}")
print(f"期間: {clean[0][0]} 〜 {clean[-1][0]}")

# --- 天気データ読み込み ---
weather = json.load(open(WEATHER_FILE, encoding="utf-8"))
w_time = weather["hourly"]["time"]
w_cloud = weather["hourly"]["cloud_cover"]
w_precip = weather["hourly"]["precipitation"]
w_code = weather["hourly"]["weather_code"]
w_rad = weather["hourly"]["shortwave_radiation"]

w_by_hour = {}
for i, t in enumerate(w_time):
    w_by_hour[t] = {
        "cloud": w_cloud[i],
        "precip": w_precip[i],
        "code": w_code[i],
        "rad": w_rad[i],
    }

# --- 時間単位（1時間おきレコードのみ）でマージ ---
merged = []
for r in clean:
    ts, lux, ps, als0, als1 = r
    dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
    # 分・秒を切り捨てて時間キーに変換
    hour_key = dt.strftime("%Y-%m-%dT%H:00")
    w = w_by_hour.get(hour_key)
    merged.append((dt, float(lux), w))

# --- 日別サマリ ---
from collections import defaultdict
daily = defaultdict(list)
for dt, lux, w in merged:
    daily[dt.date()].append((dt, lux, w))

DAY_START, DAY_END = 6, 18  # 日中帯（サンプリング密度の違いによる夜間バイアスを避けるため昼間のみで比較）

print("\n=== 日別サマリ（昼6-18時のみ・照度 x 天気）===")
print(f"{'日付':<12}{'平均lux':>9}{'最大lux':>9}{'平均雲量%':>10}{'降水量mm':>9}  天候")
for day, items in sorted(daily.items()):
    day_items = [x for x in items if DAY_START <= x[0].hour <= DAY_END]
    if not day_items:
        continue
    luxes = [x[1] for x in day_items]
    clouds = [x[2]["cloud"] for x in day_items if x[2]]
    precips = [x[2]["precip"] for x in day_items if x[2]]
    codes = [x[2]["code"] for x in day_items if x[2]]
    avg_lux = sum(luxes) / len(luxes)
    max_lux = max(luxes)
    avg_cloud = sum(clouds) / len(clouds) if clouds else float("nan")
    total_precip = sum(precips) if precips else 0.0
    label = WMO_JA.get(max(set(codes), key=codes.count), "?") if codes else "?"
    print(f"{str(day):<12}{avg_lux:>9.1f}{max_lux:>9.1f}{avg_cloud:>10.1f}{total_precip:>9.1f}  {label} (n={len(day_items)})")

# --- 相関確認: 昼間帯のみで 雲量/日射量 と luxの相関係数 ---
day_pairs = [(lux, w["cloud"], w["rad"]) for dt, lux, w in merged if w and DAY_START <= dt.hour <= DAY_END]

def corr_of(pairs, xi, yi):
    n = len(pairs)
    xs = [p[xi] for p in pairs]
    ys = [p[yi] for p in pairs]
    mx, my = sum(xs)/n, sum(ys)/n
    cov = sum((x-mx)*(y-my) for x, y in zip(xs, ys)) / n
    sx = (sum((x-mx)**2 for x in xs)/n) ** 0.5
    sy = (sum((y-my)**2 for y in ys)/n) ** 0.5
    return cov / (sx*sy) if sx and sy else float("nan")

if len(day_pairs) > 1:
    c_cloud = corr_of(day_pairs, 0, 1)
    c_rad = corr_of(day_pairs, 0, 2)
    print(f"\n[昼間帯 n={len(day_pairs)}] 照度 x 雲量 相関係数: {c_cloud:.3f}（負＝曇るとluxが下がる、が期待される符号）")
    print(f"[昼間帯 n={len(day_pairs)}] 照度 x 日射量 相関係数: {c_rad:.3f}（正＝日射が強いとluxが上がる、が期待される符号）")
