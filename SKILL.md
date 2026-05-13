---
name: xs:xangi-stackchan
description: xangi の SSE イベントを購読してスタックチャン (M5Stack atama / K151 / K151-R) に喋らせ・表情変更・首振りさせる常駐ブリッジを起動・操作するスキル。TTS は piper-plus / VOICEVOX を選択可。設定 UI 経由でランタイム設定変更、ダンスデモ実行、ファーム単体テストにも対応。「xangi の返答をスタックチャンで読ませて」「xangi-stackchan を立ち上げて」「スタックチャン踊らせて」「xangi-stackchan」で使用。
---

# xangi-stackchan 制御スキル

xangi の `GET /api/events/stream` を購読して、`turn.started` / `message.delta` / `turn.complete` / `agent.error` に応じてスタックチャンに表情・首振り・音声再生をさせる常駐ブリッジ。

USB シリアルまたは WiFi HTTP API でデバイス側 (atama 機 / K151 機) と通信する。
表示 UI は持たず、デバイスの表情変更と音声再生に集中する。

## 対応デバイス

- **stackchan-atama** (M5Stack 単体版、サーボなし) — USB / WiFi、ファームは別リポ [`karaage0703/stackchan-atama`](https://github.com/karaage0703/stackchan-atama)
- **M5Stack 公式 K151 / K151-R** — CoreS3 + サーボ + Remote、`firmware/k151/` の Arduino (PlatformIO) ファームを焼く

K151 系のみ MOVE (首振り) コマンドが効く。atama 機では MOVE はファーム側でエラー応答が返るだけ。

## Step 0: 初回セットアップ (piper-plus のバイナリ・モデルが無い場合のみ)

```bash
cd [SKILL_DIR] && uv sync && ./scripts/setup_piper.sh
```

OS/ARCH を自動判定し、piper-plus CLI (macOS/Linux arm64/x64) と、つくよみちゃん 6-language モデルをダウンロード、`tools/piper` ラッパーを生成する。

`tools/piper` はモデルカードの推奨どおり `--language ja-en-zh-es-fr-pt` と `--length-scale 1.5` を既定で使う。上書きする場合は `PIPER_LANGUAGE` / `PIPER_LENGTH_SCALE` / `PIPER_NOISE_SCALE` を指定する。

**`piper failed: ... Opset 5 ... opset 3 only` エラーが出たら:** 初回実行で生成された最適化キャッシュが onnxruntime と互換性が無い状態。`rm [SKILL_DIR]/models/*.cpu.opt.onnx*` で解消。

## Step 1: 起動状態の確認

設定 UI が立ち上がっているかで判断するのが速い (常駐起動済みなら `7897` で listen している)。

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:7897/api/config
# 200 が返れば常駐中
```

プロセス単位で確認:

```bash
pgrep -fa xangi-stackchan
```

## Step 2: 立ち上げ (常駐起動)

ターミナル終了で落ちないように `setsid -f` で常駐起動する。

```bash
cd [SKILL_DIR]
setsid -f bash -c 'cd '"$PWD"' && exec uv run xangi-stackchan \
  --xangi-url http://127.0.0.1:18888 \
  --port /dev/stackchan \
  --baud 115200 \
  --volume 200 \
  --tts piper \
  --stackchan-retry-seconds 3 \
  --settings-port 7897' </dev/null >>/tmp/xangi-stackchan.log 2>&1
```

オプション要点:

- `--xangi-url`: 接続先 xangi (既定 `http://127.0.0.1:18888`)
- `--port`: USB シリアル (udev で `/dev/stackchan` 固定推奨)
- `--baud`: 115200 (atama) / 921600 (K151 XangiBridge)
- `--volume`: 0〜255 (既定 255)
- `--tts`: `piper` / `voicevox` / `none`
- `--settings-port`: 設定 UI の port (既定 7897)
- `--settings-bind`: LAN/Tailscale 公開時は `0.0.0.0`

WiFi モード (atama 機向け):

```bash
setsid -f bash -c '... uv run xangi-stackchan \
  --xangi-url http://127.0.0.1:18888 \
  --wifi --host 192.168.1.6 --volume 200 --tts piper' </dev/null >>/tmp/xangi-stackchan.log 2>&1
```

ログ確認:

```bash
tail -f /tmp/xangi-stackchan.log
```

## Step 3: 設定 UI 経由でランタイム設定変更

ブラウザで <http://127.0.0.1:7897/> を開くと以下を変更できる。

- xangi URL / thread filter
- USB / WiFi 接続先・音量
- TTS 設定 (piper / voicevox / none)
- 状態ごとの表情 (idle / thinking / talking / error)
- 首振り (MOVE) 設定 (K151 機のみ)

保存すると `~/.xangi/xangi-stackchan/config.json` に永続化し、実行中デーモンにも反映する。xangi URL を変更した場合はストリームを張り直す。

API 経由で叩く場合:

```bash
# 現在の設定取得
curl -s http://127.0.0.1:7897/api/config | jq

# 一部更新 (例: 音量)
curl -s -X POST http://127.0.0.1:7897/api/config \
  -H 'Content-Type: application/json' \
  -d '{"volume":180}'
```

## Step 4: ダンスデモ (K151 サーボ機のみ)

テキストを piper TTS で喋らせつつ BPM 駆動で首を振る単発デモ。

プリセット:

- `happy` — BPM 120 / yaw ±20° / pitch ±5° (元気)
- `chill` — BPM 70 / yaw ±10° / pitch ±2° (ゆっくり)
- `wave`  — BPM 100 / yaw ±15° / pitch ±5° (8 の字)

### A. 動作中の xangi-stackchan に POST (推奨、シリアル取り合いなし)

```bash
curl -s -X POST http://127.0.0.1:7897/api/demo \
  -H 'Content-Type: application/json' \
  -d '{"text":"踊るよ","preset":"happy"}'
```

CLI ラッパー版:

```bash
cd [SKILL_DIR]
uv run python scripts/dance_demo.py --text "踊るよ" --preset happy \
    --via-bridge http://127.0.0.1:7897
```

### B. xangi-stackchan 停止時のスタンドアロン

```bash
cd [SKILL_DIR]
uv run python scripts/dance_demo.py --text "踊るよ" --preset happy
uv run python scripts/dance_demo.py --text "TTS だけ確認" --dry-run    # シリアル不要
```

シリアルを直接掴むので、常駐ブリッジが動いていると競合する。先に `pkill -f xangi-stackchan` で停止してから実行する。

## Step 5: ファーム単体テスト (K151 XangiBridge)

STATUS / VOLUME / FACE / MOVE / WAV (440Hz トーン) の往復を 1 ショットで確認する。

```bash
cd [SKILL_DIR]
uv run python scripts/test_xangi_bridge.py --port /dev/stackchan
```

ファーム書き込み直後の動作確認に使う。常駐ブリッジが動いていると競合するので停止してから。

## Step 6: 停止

```bash
pkill -f xangi-stackchan
```

`setsid -f` で起動しているので、Ctrl-C ではなく `pkill` で落とす。

## イベントごとの既定動作

xangi 側から流れてくる SSE イベントに対する振る舞い:

| イベント | 表情 | サーボ (K151) |
|----------|------|---------------|
| `turn.started`  | `doubt`   | thinking ポーズ (yaw -8° / pitch +5°) |
| `message.delta` | `happy`   | (継続) |
| `turn.complete` | 発話中 `happy` → 発話後 `neutral` | 発話中は sway (±4° / ±2° を 1.5 秒間隔)、発話後 idle ポーズ |
| `agent.error`   | `sad`     | エラーポーズ (pitch -10°) |

設定 UI または CLI オプション (`--face-*`, `--move-*`) で個別に変更できる。

## 動作確認・実機テスト

xangi 経由で会話を投げてリアクションを確認:

```bash
curl -sN -X POST http://127.0.0.1:18888/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"接続テストです。「接続テスト成功」とだけ返してください。"}'
```

xangi-stackchan 側のログで `turn.started` → `turn.complete` の流れと `send_wav: queued` が出ていれば OK。

## トラブルシュート

- **常駐ブリッジが xangi に繋がらない**: `--xangi-url` で指定した port が xangi のデフォルト (`18888`) と合っているか / xangi が起動しているか確認
- **デバイスに音声が届かない**: `pgrep -fa xangi-stackchan` で生きているか、`tail -f /tmp/xangi-stackchan.log` で `send_wav` エラーが出ていないか確認
- **シリアルポートが掴まれている**: 常駐ブリッジ自身が掴んでいるケース。`pkill -f xangi-stackchan` で落としてから再起動
- **MOVE が効かない**: atama 機ではサーボ無しなので無効。K151 機の場合は `--no-move-enabled` で OFF にしていないか / 設定 UI で MOVE が有効か確認
- **発話が遅い**: piper-plus は常駐プロセスなので、初回だけモデルロード。それ以降は低遅延

## 使用例

```
xangi の返答をスタックチャンで読ませて
xangi-stackchan を立ち上げて
スタックチャンを happy preset で踊らせて
xangi-stackchan の状態確認して
xangi-stackchan を止めて
ファームの単体テストやって
```
