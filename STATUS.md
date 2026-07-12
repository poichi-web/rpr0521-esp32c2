# rpr0521_test — STATUS

**状態**: 稼働中
**最終更新**: 2026-07-12
**Notion仕様**: https://app.notion.com/p/391d22fa628b819da4d7f83221193fc2

## 概要
ESP8684(ESP32-C2) + RPR-0521RS(照度・近接センサー)で室内照度を1時間おきにロギングし、植物育成に十分な光量があるかを評価する。

## 現状
- `overnight_logger.py` をデバイス上の `main.py` として書き込み済み。1時間おきに `/log.csv` へローカル記録 **かつ** WiFi経由でVercel Function（[rpr0521-ingest](https://github.com/poichi-web/rpr0521-ingest)）へ送信し、Notion DB「[📈 照度ログ](https://app.notion.com/p/429b13a196314247ab95317e0dc5ced6)」へ1行ずつリアルタイム反映
- **WiFi + NTP時刻同期を実装済み**（2026-07-12）。起動時にWiFi接続→`ntp.nict.jp`で時刻取得→JSTに変換してRTCへ反映。電源断でデバイスを移動・再起動しても正しい時刻でロギングを継続できる（WiFi接続情報は`wifi_secrets.py`、`.gitignore`済みでローカル/デバイスのみに保持）
- **常時WiFi送信を実装済み**（2026-07-12）。`urequests`でVercel Function `POST /api/log` へ送信（共有トークン認証）。送信失敗時もローカル`/log.csv`への記録は継続するため、データは失われない。認証情報は`ingest_secrets.py`（`.gitignore`済み）
- ホストPC（COM3・mpremote）でロギング継続中（バックグラウンドプロセス、USB回収経路も併存）
- リポジトリの [log.csv](log.csv) は2026-07-12にデバイスから回収した510件（信頼できるタイムスタンプのみ。詳細は下記「既知の問題」参照）
- [analyze.py](analyze.py) で日別サマリ・時間帯別・植物育成評価、[assess_with_weather.py](assess_with_weather.py) で東京の気象実況（Open-Meteo）との突き合わせが可能
- 毎週月曜08:00にWindows Task Scheduler（`rpr0521_WeeklyLogSync`タスク）が[sync_log.py](sync_log.py)を実行し、log.csvをGitHubへpush。毎週月曜09:00 JSTにクラウドルーティン（`rpr0521 Weekly Lux Assessment`）がNotionページへ週次サマリを追記（WiFi送信経路と並行稼働、どちらかが壊れても他方でカバー）

## 既知の問題
- **2026-07-02 21:12〜2026-07-12 17:54の約10日間、記録はあるがタイムスタンプが信頼できない**：WiFi/NTP実装前の`overnight_logger.py`が、電源断以外のリセットのたびにRTCを固定日時（2026-07-02 22:03）へ巻き戻すバグを持っていたため。この期間中の生データ（237件、値そのものは正常）はデバイス上に残っているが、実際の計測日時を正確に特定できないため`log.csv`からは除外した。**再発防止済み**（下記参照）なので今後は起きない
- **RTC強制上書きバグ**（2026-07-02発見・修正）: 起動のたびにRTCを固定日時へ上書きしていた。`if rtc.datetime()[0] < 2026` のガードを追加し、電源断時のみRTCを初期化するよう修正
- **NTPデフォルトサーバー(`pool.ntp.org`)がこのネットワークからタイムアウト**（2026-07-12発見・修正）: `ntp.nict.jp`（NICT・日本の公式NTPサーバー）に切り替えて解決。診断用に[wifi_diag.py](wifi_diag.py)を追加

## 残タスク
- [ ] 長期運用でWiFi送信・NTP同期が安定して動くか確認（電波状況が悪い設置場所での動作含む）

## 次のアクション
- 特になし。継続監視のみ
