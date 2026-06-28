#!/usr/bin/env python3
"""
書斎照度プロジェクト - データ収集 & Notion レポート生成

必要パッケージ:
  pip install requests

Notion 設定（環境変数）:
  set NOTION_TOKEN=secret_xxxxx          # インテグレーションシークレット
  set NOTION_PAGE_ID=xxxxxxxxxxxxxxxx    # 投稿先ページ ID

使用方法:
  python collect_and_report.py           # ESP32 から取得して Notion へ
  python collect_and_report.py --no-pull # 既存 log_pulled.csv のみ使用
"""
import subprocess, csv, json, os, sys
from datetime import datetime, timedelta, timezone, date
from collections import defaultdict, Counter

try:
    import requests
except ImportError:
    print("pip install requests が必要です")
    sys.exit(1)

# ===== 設定 =====
COM_PORT       = "COM3"
LOCAL_CSV      = "log_pulled.csv"
LAT            = 35.68        # 緯度（東京）→ 実際の場所に変更
LON            = 139.69       # 経度（東京）
TZ_NAME        = "Asia/Tokyo"
NOTION_TOKEN   = os.environ.get("NOTION_TOKEN", "")
NOTION_PAGE_ID = os.environ.get("NOTION_PAGE_ID", "")
# ================

JST   = timezone(timedelta(hours=9))
NO_PULL = "--no-pull" in sys.argv


# ─── データ取得 ───────────────────────────────────────────────────────────────

def pull_csv():
    print(f"[1/5] ESP32 ({COM_PORT}) からデータ取得中...")
    r = subprocess.run(
        ["python", "-m", "mpremote", "connect", COM_PORT,
         "fs", "cp", ":log.csv", LOCAL_CSV],
        capture_output=True, text=True
    )
    if r.returncode != 0:
        print(f"  警告: {r.stderr.strip()}")
        if os.path.exists(LOCAL_CSV):
            print(f"  既存の {LOCAL_CSV} を使用します")
            return True
        return False
    print(f"  → {LOCAL_CSV} 保存完了")
    return True


def load_csv(path):
    rows = []
    with open(path, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            try:
                row['lux'] = float(row['lux'])
                row['dt']  = datetime.strptime(row['time'], '%Y-%m-%d %H:%M:%S').replace(tzinfo=JST)
                rows.append(row)
            except (ValueError, KeyError):
                pass
    return rows


# ─── 天気取得（Open-Meteo / 無料・認証不要）─────────────────────────────────

def fetch_weather(start_dt, end_dt):
    print("[3/5] 天気データ取得中 (Open-Meteo)...")
    today     = datetime.now(JST).date()
    past_days = max(0, (today - start_dt.date()).days + 1)
    fcast_days = max(1, (end_dt.date() - today).days + 2)
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={LAT}&longitude={LON}"
        f"&hourly=temperature_2m,precipitation,weather_code,cloud_cover"
        f"&timezone={TZ_NAME}"
        f"&past_days={past_days}&forecast_days={fcast_days}"
    )
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    h = resp.json()['hourly']
    result = {}
    for i, t in enumerate(h['time']):
        dt = datetime.strptime(t, '%Y-%m-%dT%H:%M').replace(tzinfo=JST)
        result[dt.strftime('%Y-%m-%d %H')] = {
            'temp':   h['temperature_2m'][i],
            'code':   h['weather_code'][i],
            'cloud':  h['cloud_cover'][i],
            'precip': h['precipitation'][i],
        }
    print(f"  → {len(result)} 時間分取得")
    return result


WMO = {
    0: '快晴',  1: '晴れ',    2: '一部曇', 3: '曇り',
    45: '霧',   48: '霧',
    51: '霧雨', 53: '霧雨',   55: '霧雨',
    61: '小雨', 63: '雨',     65: '大雨',
    71: '小雪', 73: '雪',     75: '大雪',
    80: 'にわか雨', 81: 'にわか雨', 82: '強にわか雨',
    95: '雷雨', 96: '雷雨',   99: '雷雨',
}

def wmo(code):
    return WMO.get(int(code), f'#{code}') if code is not None else '-'


# ─── 分析 ─────────────────────────────────────────────────────────────────────

def analyze(rows, weather):
    print("[4/5] データ分析中...")
    by_hour = defaultdict(list)
    by_day  = defaultdict(list)
    for r in rows:
        by_hour[r['dt'].strftime('%Y-%m-%d %H')].append(r['lux'])
        by_day[r['dt'].strftime('%Y-%m-%d')].append(r['lux'])

    hourly = []
    for h_key in sorted(by_hour):
        luxes = by_hour[h_key]
        w = weather.get(h_key, {})
        hourly.append({
            'hour':    h_key,
            'avg_lux': sum(luxes) / len(luxes),
            'max_lux': max(luxes),
            'count':   len(luxes),
            'temp':    w.get('temp'),
            'code':    w.get('code'),
            'weather': wmo(w.get('code')),
            'cloud':   w.get('cloud'),
        })

    daily = {}
    for d_key in sorted(by_day):
        luxes   = by_day[d_key]
        d_hours = [h for h in hourly if h['hour'].startswith(d_key)]
        peak    = max(d_hours, key=lambda h: h['avg_lux'], default=None)
        codes   = [h['code'] for h in d_hours if h['code'] is not None]
        daily[d_key] = {
            'max':      max(luxes),
            'min':      min(luxes),
            'avg':      sum(luxes) / len(luxes),
            'count':    len(luxes),
            'peak_h':   peak['hour'][11:13] + '時台' if peak else '-',
            'peak_lux': peak['avg_lux'] if peak else 0,
            'weather':  wmo(Counter(codes).most_common(1)[0][0] if codes else None),
        }
    return hourly, daily


# ─── テキスト生成 ──────────────────────────────────────────────────────────────

def ascii_chart(hourly, bar_width=48):
    if not hourly:
        return "データなし"
    max_val = max(h['avg_lux'] for h in hourly) or 1.0
    lines = [f"  照度推移チャート  ( ■ max = {max_val:.0f} lux )"]
    lines.append("  日時            avg lux  " + "─" * bar_width)
    prev_day = None
    for h in hourly:
        day = h['hour'][:10]
        if day != prev_day:
            lines.append(f"  ── {day} ──")
            prev_day = day
        bar = '█' * int(h['avg_lux'] / max_val * bar_width)
        lines.append(f"  {h['hour'][5:]}h  {h['avg_lux']:7.1f}  {bar}")
    return '\n'.join(lines)


def data_table(hourly):
    hdr = "{:<16}  {:>8}  {:>8}  {:<8}  {:>6}  {:>5}".format(
        "日時", "avg lux", "max lux", "天気", "気温", "雲量")
    sep = "─" * 62
    lines = [hdr, sep]
    prev_day = None
    for h in hourly:
        day = h['hour'][:10]
        if day != prev_day:
            if prev_day:
                lines.append("")
            prev_day = day
        t   = f"{h['temp']:.1f}°C" if h['temp'] is not None else "  -  "
        cld = f"{h['cloud']:.0f}%"  if h['cloud'] is not None else " -"
        lines.append("{:<16}  {:>8.1f}  {:>8.1f}  {:<8}  {:>6}  {:>5}".format(
            h['hour'][5:] + "h",
            h['avg_lux'], h['max_lux'],
            h['weather'], t, cld
        ))
    return '\n'.join(lines)


def analysis_text(hourly, daily):
    lines = []

    # 作業照度 (300 lux 以上)
    bright = [h for h in hourly if h['avg_lux'] >= 300]
    if bright:
        h_set = sorted(set(h['hour'][11:13] for h in bright))
        lines.append(f"• 作業照度（300 lux 以上）が期待できる時間帯: {', '.join(h_set)} 時台")
    else:
        peak = max(hourly, key=lambda h: h['avg_lux'])
        lines.append(f"• 300 lux 以上の時間帯なし（最大: {peak['avg_lux']:.0f} lux @ {peak['hour'][5:]}h）")

    # 瞬間最大
    peak_h = max(hourly, key=lambda h: h['max_lux'])
    lines.append(f"• 瞬間最大照度: {peak_h['max_lux']:.0f} lux（{peak_h['hour'][5:]}h, {peak_h['weather']}）")

    # 有効採光時間帯推定（> 20 lux）
    daylight = [h for h in hourly if h['avg_lux'] > 20]
    if daylight:
        dawn = min(daylight, key=lambda h: h['hour'])
        dusk = max(daylight, key=lambda h: h['hour'])
        lines.append(f"• 有効採光時間帯（推定 > 20 lux）: {dawn['hour'][11:]}h ～ {dusk['hour'][11:]}h")

    # 天気別平均照度
    by_wx = defaultdict(list)
    for h in hourly:
        if h['weather'] != '-':
            by_wx[h['weather']].append(h['avg_lux'])
    for wx, luxes in sorted(by_wx.items(), key=lambda x: -sum(x[1]) / len(x[1])):
        lines.append(f"• {wx}時の平均照度: {sum(luxes)/len(luxes):.0f} lux（{len(luxes)} 時間）")

    return '\n'.join(lines)


# ─── Notion ブロックビルダー ──────────────────────────────────────────────────

def _rt(text):
    return {"type": "text", "text": {"content": text}}

def _h2(text):
    return {"object": "block", "type": "heading_2",
            "heading_2": {"rich_text": [_rt(text)]}}

def _para(text):
    return {"object": "block", "type": "paragraph",
            "paragraph": {"rich_text": [_rt(text)]}}

def _callout(text, emoji):
    return {"object": "block", "type": "callout",
            "callout": {"rich_text": [_rt(text)],
                        "icon": {"type": "emoji", "emoji": emoji}}}

def _code(text):
    return {"object": "block", "type": "code",
            "code": {"rich_text": [_rt(text)], "language": "plain text"}}

def _divider():
    return {"object": "block", "type": "divider", "divider": {}}


DAY_EMOJI = {
    '快晴': '☀️', '晴れ': '🌤', '一部曇': '⛅', '曇り': '☁️',
    '小雨': '🌧', '雨': '🌧', '大雨': '⛈', '強にわか雨': '⛈',
    '霧雨': '🌦', 'にわか雨': '🌦',
    '雪': '❄️', '小雪': '❄️', '大雪': '❄️', '霧': '🌫', '雷雨': '⛈',
}


def build_notion_blocks(hourly, daily, rows, chart, table, analysis):
    all_lux    = [r['lux'] for r in rows]
    date_start = min(r['dt'] for r in rows).strftime('%Y-%m-%d')
    date_end   = max(r['dt'] for r in rows).strftime('%Y-%m-%d')

    blocks = [
        _callout(
            f"測定期間: {date_start} ～ {date_end}  |  データ数: {len(rows)} 件\n"
            f"最大: {max(all_lux):.1f} lux  |  最小: {min(all_lux):.1f} lux  "
            f"|  平均: {sum(all_lux)/len(all_lux):.1f} lux",
            "📊"
        ),
        _divider(),
        _h2("日別サマリー"),
    ]
    for d, s in daily.items():
        emoji = DAY_EMOJI.get(s['weather'], '🌡')
        blocks.append(_callout(
            f"{d}  |  {s['weather']}  |  "
            f"最大 {s['max']:.0f} lux  最小 {s['min']:.0f} lux  平均 {s['avg']:.0f} lux  "
            f"ピーク {s['peak_h']}  ({s['count']} 件)",
            emoji
        ))

    blocks += [
        _divider(),
        _h2("照度推移チャート（時間別）"),
        _code(chart),
        _divider(),
        _h2("時間別詳細データ"),
        _code(table),
        _divider(),
        _h2("分析まとめ"),
        _para(analysis),
    ]
    return blocks


# ─── Notion 投稿 ──────────────────────────────────────────────────────────────

def post_to_notion(blocks, title):
    print("[5/5] Notion ページ投稿中...")
    headers = {
        "Authorization":  f"Bearer {NOTION_TOKEN}",
        "Content-Type":   "application/json",
        "Notion-Version": "2022-06-28",
    }
    payload = {
        "parent":     {"page_id": NOTION_PAGE_ID},
        "properties": {"title": {"title": [_rt(title)]}},
        "children":   blocks[:100],
    }
    resp = requests.post("https://api.notion.com/v1/pages",
                         headers=headers, json=payload, timeout=20)
    if not resp.ok:
        print(f"  エラー {resp.status_code}: {resp.text[:300]}")
        return None

    page    = resp.json()
    page_id = page["id"]
    page_url = page.get("url", "")

    # 100 件超の場合は追記
    for i in range(100, len(blocks), 100):
        r2 = requests.patch(
            f"https://api.notion.com/v1/blocks/{page_id}/children",
            headers=headers,
            json={"children": blocks[i:i+100]},
            timeout=20
        )
        if not r2.ok:
            print(f"  追記エラー {r2.status_code}: {r2.text[:200]}")

    return page_url


# ─── メイン ───────────────────────────────────────────────────────────────────

def main():
    print("=== 書斎照度プロジェクト - レポート生成 ===\n")

    # 1. データ取得
    if NO_PULL:
        print("[1/5] --no-pull: ESP32取得をスキップ")
    elif not pull_csv():
        print("ESP32 からデータを取得できませんでした。")
        sys.exit(1)

    # 2. CSV 読み込み
    print("[2/5] CSV 解析中...")
    if not os.path.exists(LOCAL_CSV):
        print(f"  {LOCAL_CSV} が見つかりません。先に deploy.py で測定を開始してください。")
        sys.exit(1)
    rows = load_csv(LOCAL_CSV)
    if not rows:
        print("  データが空です。ログが正常に記録されているか確認してください。")
        sys.exit(1)
    print(f"  → {len(rows)} 件  ({rows[0]['time']} ～ {rows[-1]['time']})")

    # 3. 天気取得
    weather = {}
    try:
        weather = fetch_weather(rows[0]['dt'], rows[-1]['dt'])
    except Exception as e:
        print(f"  天気データ取得失敗（天気なしで続行）: {e}")

    # 4. 分析
    hourly, daily = analyze(rows, weather)

    # 5. テキスト生成
    chart    = ascii_chart(hourly)
    table    = data_table(hourly)
    analysis = analysis_text(hourly, daily)

    # ターミナルプレビュー
    print("\n" + "=" * 64)
    print(chart)
    print()
    print(analysis)
    print("=" * 64 + "\n")

    # 6. Notion 投稿
    if NOTION_TOKEN and NOTION_PAGE_ID:
        date_start = rows[0]['dt'].strftime('%Y-%m-%d')
        date_end   = rows[-1]['dt'].strftime('%Y-%m-%d')
        title  = f"書斎窓側 照度記録 {date_start} ～ {date_end}"
        blocks = build_notion_blocks(hourly, daily, rows, chart, table, analysis)
        url    = post_to_notion(blocks, title)
        if url:
            print(f"✅ Notion ページ作成完了: {url}")
    else:
        print("NOTION_TOKEN / NOTION_PAGE_ID が未設定のため Notion 投稿をスキップしました。")
        print()
        print("設定方法 (PowerShell):")
        print("  $env:NOTION_TOKEN   = 'secret_xxxx'")
        print("  $env:NOTION_PAGE_ID = 'xxxxxxxxxxxxxxxxxxxxxxxxxx'")
        print()
        print("Notion インテグレーション作成:")
        print("  https://www.notion.so/my-integrations")


if __name__ == "__main__":
    main()
