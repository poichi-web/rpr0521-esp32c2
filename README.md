# rpr0521_test — ESP8684 + RPR-0521RS センサーテスト

## 環境
- ボード: ESP8684-WROOM-02C (ESP32-C2, 26MHz crystal, 4MB flash)
- センサー: RPR-0521RS (Switch Science SSCI-027700)
- ファームウェア: MicroPython v1.28.0

## 配線
| センサー | ESP8684 |
|---------|---------|
| 3.3V | 3V3 |
| GND | GND |
| SDA | GPIO5 |
| SCL | GPIO6 |

## 実行方法
```powershell
python -m mpremote connect COM3 run c:\dev\rpr0521_test\rpr0521_upython.py
```

main.py として書き込み済みなので USB 接続するだけで自動起動もする。

## 動作確認済み
- PS（近接）: 背景ノイズ6〜7、手を近づけると300+ ✅
- ALS（照度）: 室内=35、遮光時=5、スマホライト=500+ ✅

## 重要: MODE_CONTROL レジスタ

**bit 7 = 1 が必須** (0xE6、0x66 ではない)

- 0x66: bit7=0 → ALS が有効化されず常に 0
- 0xE6: bit7=1, bits[7:6]=11（PS 8パルス）, MEAS_TIME=6 (ALS 50ms + PS 100ms) → ALS/PS 両方動作

```python
wreg(0x41, 0xE6)  # ← 正しい（0x66 は誤り）
wreg(0x42, 0x03)  # ALS x1 gain, LED 25mA, PS x4 gain
```

## セットアップ経緯とつまずき

### Arduino ESP32 / PlatformIO は ESP32-C2 未対応（2026-06時点）
- espressif32 v7.0.1 に esp8684-devkitm-1 ボードなし
- arduino-esp32 3.3.10 に esp32c2-libs パッケージなし（boards.txt に hide=true）
- C3 libs で代替しても Illegal instruction（アーキテクチャ非互換）

### MicroPython で解決
- https://micropython.org/download/ESP32_GENERIC_C2/ から v1.28.0 をダウンロード
- esptool で DIO モード・60MHz で書き込み

### フラッシュモードの注意
ESP8684-WROOM-02C は DIO モードのみ対応。QIO で書くと SHA-256 mismatch エラー。
```
esptool --chip esp32c2 --port COM3 --baud 921600 write-flash \
  --flash-mode dio --flash-freq 60m --flash-size 4MB \
  0x0 ESP32_GENERIC_C2-v1.28.0.bin
```

### RPR-0521RS 初期化（重要！）
MODE_CONTROL (0x41) = **0xE6** で ALS+PS 同時測定（bit 7 = 1 必須）
- 0x66 は誤り（ALS が全く動かない）
- ALS_PS_CONTROL (0x42) = 0x03: ALS x1 gain, LED 25mA, PS x4

### mpremote での出力
日本語文字列は mpremote 経由の Windows コンソールで文字化けする。
`sys.stdout.write()` + ASCII 文字のみで出力すること。

### ALS が 0 になる診断方法
1. ALS が 0 → MODE_CONTROL 0x41 の bit 7 が 0 になっている。0xE6 に変更。
2. 全データが 0 → ソフトリセット後に MEAS_TIME=0 に設定してしまった（スタンバイ）。0xE6 に設定し直す。
3. ALS が変化しない → 部屋が暗い場合 x1 gain では値が低い。カバーテストで 1〜35 の変化を確認する。
