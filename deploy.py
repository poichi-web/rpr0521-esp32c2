#!/usr/bin/env python3
"""
ESP32 デプロイヘルパー - RTC設定 + ロガー書き込み

使用方法:
  python deploy.py [COMポート]   # 省略時 COM3

実行すると:
  1. PCの現在時刻(JST)を ESP32 RTC に設定
  2. main_logger.py を main.py として書き込み
  3. デバイスをリセット → 10分間隔ログ開始
"""
import subprocess, sys
from datetime import datetime, timezone, timedelta

COM_PORT = sys.argv[1] if len(sys.argv) > 1 else "COM3"
JST      = timezone(timedelta(hours=9))


def mpremote(*args):
    cmd = ["python", "-m", "mpremote", "connect", COM_PORT] + list(args)
    r   = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("  [ERROR]", r.stderr.strip() or r.stdout.strip())
        sys.exit(1)
    return r.stdout.strip()


def main():
    now = datetime.now(JST)
    print("=== 書斎照度ロガー デプロイ ===")
    print(f"ポート     : {COM_PORT}")
    print(f"現在時刻   : {now.strftime('%Y-%m-%d %H:%M:%S')} JST")
    print()

    # 1. RTC 設定
    # rtc.datetime(year, month, day, weekday, hour, minute, second, subseconds)
    # weekday: 0=月 … 6=日（MicroPython は Python と同じ）
    rtc_expr = (
        "import machine,sys;"
        "rtc=machine.RTC();"
        "rtc.datetime(({y},{mo},{d},{wd},{h},{mi},{s},0));"
        "t=rtc.datetime();"
        "sys.stdout.write('{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}\\r\\n'"
        ".format(t[0],t[1],t[2],t[4],t[5],t[6]))"
    ).format(
        y=now.year, mo=now.month, d=now.day,
        wd=now.weekday(), h=now.hour, mi=now.minute, s=now.second
    )
    print("[1/3] RTC 設定中...")
    result = mpremote("exec", rtc_expr)
    print(f"  RTC = {result}")

    # 2. ファームウェア書き込み
    print("[2/3] main_logger.py → :main.py 書き込み中...")
    mpremote("fs", "cp", "main_logger.py", ":main.py")
    print("  完了")

    # 3. リセット（ソフトリセット）
    print("[3/3] デバイスリセット中...")
    mpremote("exec", "import machine; machine.reset()")

    print()
    print("✅ デプロイ完了！")
    print("   10分ごとに /log.csv へ記録されます。")
    print("   3日後にデータを回収するには:")
    print("     python collect_and_report.py")
    print()
    print("   ⚠️  電源を切ると RTC がリセットされます。")
    print("      その場合は再度 deploy.py を実行してください。")


if __name__ == "__main__":
    main()
