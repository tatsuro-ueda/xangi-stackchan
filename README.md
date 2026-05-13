# xangi-stackchan

![xangi-stackchan](docs/images/cover.jpg)

[xangi](https://github.com/karaage0703/xangi)（AI アシスタントフレームワーク）の `GET /api/events/stream` を購読してスタックチャン系デバイスを物理ペットのように動かす、常駐ブリッジ + Arduino ファームウェア。xangi の応答に合わせて表情・首振り・音声合成を実機側で再生する。

## できること

- xangi が考え始めるとデバイスが `doubt` 顔 + 首をかしげる
- xangi が話し始めると `happy` 顔になる
- `turn.complete` の最終テキストを piper-plus / VOICEVOX で音声化して再生。再生中は首がささやかに揺れる
- 完了後は `neutral` 顔 + idle ポーズに戻る
- `agent.error` では `sad` 顔 + 首を下げる

表示 UI は持たず、デバイスの表情変更と音声再生に集中する。サーボ動作は K151 / K151-R 用 (atama 機はサーボ無しなので MOVE はファーム側エラー応答が返るだけ)。

## 対応デバイス

- **stackchan-atama** (M5Stack 単体版、サーボなし) — Python ホストブリッジ経由で USB / WiFi 制御
  - M5Stack 側のファームは別リポ [`karaage0703/stackchan-atama`](https://github.com/karaage0703/stackchan-atama) を焼く
- **M5Stack 公式 K151 / K151-R** (CoreS3 + サーボ + Remote) — `firmware/k151/` 配下に Arduino (PlatformIO) ファームを焼いて USB シリアル経由で制御

## 構成

```
xangi (:18888)
  └─ GET /api/events/stream (SSE)
      └─ xangi-stackchan (host bridge, Python)
          ├─ thread_id filter
          ├─ piper-plus persistent process
          └─ device (USB serial 共通プロトコル: STATUS / FACE: / WAV:<size> / VOLUME: / MOVE:)
              ├─ K151 / K151-R    (firmware/k151/、サーボあり)
              └─ stackchan-atama  (karaage0703/stackchan-atama のファームを焼いた M5Stack 単体機)
```

## クイックスタート

```bash
git clone https://github.com/karaage0703/xangi-stackchan.git
cd xangi-stackchan
uv sync
./scripts/setup_piper.sh

uv run xangi-stackchan \
  --xangi-url http://127.0.0.1:18888 \
  --port /dev/stackchan \
  --tts piper
```

起動すると設定 UI が `http://127.0.0.1:7897/` で立ち上がる。xangi URL / 接続先 / 音量 / TTS / 表情をブラウザから変更でき、保存すると `~/.xangi/xangi-stackchan/config.json` に永続化される。

詳細なセットアップ・オプション・常駐起動・トラブルシュートは [`docs/usage.md`](./docs/usage.md) を参照。

## AI エージェント連携

[`SKILL.md`](./SKILL.md) を参照。Claude Code や borot 等の AI エージェントから本ブリッジを起動・操作してスタックチャンを動かすための手順を集約してある。

## ドキュメント

- [`docs/usage.md`](./docs/usage.md): セットアップ・オプション・常駐起動・デモ・トラブルシュート
- [`docs/xangi_bridge_protocol.md`](./docs/xangi_bridge_protocol.md): USB シリアル共通プロトコル仕様
- [`docs/scservo_protocol.md`](./docs/scservo_protocol.md): Feetech SCS シリアルサーボのプロトコル仕様
- [`firmware/k151/README.md`](./firmware/k151/README.md): K151 / K151-R 用 Arduino ファームの開発ガイド

## 参考

- [karaage0703/stackchan-atama](https://github.com/karaage0703/stackchan-atama): stackchan-atama (M5Stack 単体版) 用の M5Stack 側ファーム — atama 機を使う場合はこのリポを焼く
- [m5stack/StackChan](https://github.com/m5stack/StackChan): M5Stack 公式 K151 のリポ (xiaozhi-esp32 ベース、本リポでは仕様情報のみ参照)
- [stack-chan/stack-chan](https://github.com/stack-chan/stack-chan): 元祖スタックチャン (Apache-2.0、`firmware/k151/` のサーボ制御ロジックの仕様参照元)

## ライセンス

MIT License
