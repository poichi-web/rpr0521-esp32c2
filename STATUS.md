# rpr0521_test — STATUS

**状態**: 稼働中
**最終更新**: 2026-07-12
**Notion仕様**: https://app.notion.com/p/391d22fa628b819da4d7f83221193fc2

## 概要
ESP8684(ESP32-C2) + RPR-0521RS(照度・近接センサー)で室内照度を1時間おきにロギングし、植物育成に十分な光量があるかを評価する。

## 現状
- `overnight_logger.py` をデバイス上の `main.py` として書き込み済み。USB接続時に自動起動し、1時間おきに `/log.csv` へ `time,lux,ps,als0,als1` を追記
- **WiFi + NTP時刻同期を実装済み**（2026-07-12）。起動時にWiFi接続→`ntp.nict.jp`で時刻取得→JSTに変換してRTCへ反映。電源断でデバイスを移動・再起動しても正しい時刻でロギングを継続できる（WiFi接続情報は`wifi_secrets.py`、`.gitignore`済みでローカル/デバイスのみに保持）
- ホストPC（COM3・mpremote）でロギング継続中（バックグラウンドプロセス）
- リポジトリの [log.csv](log.csv) は2026-07-02にデバイスから回収した499件（2026-06-27 23:32〜2026-07-02 21:12）で最新化済み
- [analyze.py](analyze.py) で日別サマリ・時間帯別・植物育成評価、[assess_with_weather.py](assess_with_weather.py) で東京の気象実況（Open-Meteo）との突き合わせが可能
- 毎週月曜08:00にWindows Task Scheduler（`rpr0521_WeeklyLogSync`タスク）が[sync_log.py](sync_log.py)を実行し、log.csvをGitHubへpush。毎週月曜09:00 JSTにクラウドルーティン（`rpr0521 Weekly Lux Assessment`）がNotionページへ週次サマリを追記

## 既知の問題（修正済み）
- **RTC強制上書きバグ**（2026-07-02発見・修正）: `overnight_logger.py` が起動のたびにRTCを固定日時（2026-06-28 07:12）へ上書きしていたため、電源断以外のリセットでもタイムスタンプが巻き戻っていた。`if rtc.datetime()[0] < 2026` のガードを追加し、電源断時のみRTCを初期化するよう修正・再デプロイ済み（現在はWiFi/NTPが最優先、このガードはWiFi不通時の最終手段）
- **NTPデフォルトサーバー(`pool.ntp.org`)がこのネットワークからタイムアウト**（2026-07-12発見・修正）: `ntp.nict.jp`（NICT・日本の公式NTPサーバー）に切り替えて解決。診断用に[wifi_diag.py](wifi_diag.py)を追加

## 残タスク
- なし（デバイス移動時の時刻ズレ問題はNTP同期で解消）

## 次のアクション
- 実際に別の場所へ移動させて長期観測し、WiFi/NTPが安定して動くか確認する
