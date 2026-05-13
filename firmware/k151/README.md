# firmware/k151

M5Stack 公式 StackChan **K151 / K151-R** 用 Arduino (PlatformIO) ファーム。
xangi の SSE イベントを購読する USB シリアルブリッジと連携する。

## 依存ライブラリ

- [m5stack/M5Unified](https://github.com/m5stack/M5Unified) (MIT)
- `meganetaaan/M5Stack-Avatar` (PIO Registry 名、リポは [stack-chan/m5stack-avatar](https://github.com/stack-chan/m5stack-avatar)) (MIT)

## ビルド

```bash
cd firmware/k151
pio run                      # ビルドのみ
pio run -t upload            # K151 を USB 接続してから書き込み
pio device monitor           # 115200bps でシリアルログ確認
```

## examples

`examples/<Name>/` 以下に独立ファーム を置き、別 PIO env で焼く。

### HomeCalibration (中央位置を NVS に保存)

K151 の組み付け公差で「サーボの中央 = 真正面・水平」になっていない個体向け。
SCSCL シリーズはサーボ側に「物理現在位置を中央として永続記録」するキャリブ
機能を持たない (元祖 stack-chan/scservo.ts の `@note SCS series does not have
zero position calibration function` 参照) ため、ホスト側 (ESP32 NVS) で
zero raw を保持する D 案で実装している。

```bash
pio run -e m5stack-cores3-homecal -t upload
pio device monitor
```

操作:
1. 起動すると torque OFF。LCD に yaw / pitch の現在角度 (raw 値も併記) が
   200ms ごと表示される。
2. **手で「真正面・水平」の姿勢に物理的に向ける。**
3. 以下のいずれかでトリガ (CoreS3 では BtnA が動かないため 3 系統用意):
   - 画面 LCD タップ
   - BtnA 押下 (効くデバイス向け)
   - USB シリアルに `c` (or `C`) を送信
4. 完了すると "saved to NVS!" が表示され、現在の raw が NVS namespace
   `xstackchan` の `yaw_zero` / `pitch_zero` に保存される。
5. 通常運用ファーム / SetAngleDemo はこの値を読み込んで `setAngle*()` の
   zero ベース計算に使う。

NVS 書き込みは電源 OFF 後も残るが、別の物理位置で再トリガすれば上書き
される。再キャリブには「水平にし直してタップ」だけで良い。

### SpeakerDemo (CoreS3 内蔵スピーカーで WAV 再生)

CoreS3 内蔵スピーカー (NS4150 アンプ + I2S) から 440Hz 0.5 秒のサイン波を
`M5.Speaker.playWav()` で再生する最小ファーム。サーボ・PY32 VM_EN には
触らないので HomeCalibration の前後どちらでも単独で焼ける。

将来 Step D で xangi SSE bridge から `WAV:<size>\n` + バイナリで受信する
音声をそのまま `playWav` に流す経路の **前段検証用**。setup 時に WAV ヘッダ
(44 byte RIFF/PCM/16bit/mono/16kHz) + PCM 8000 サンプルを `.bss` 上の
`g_wavBuf` に組み立て、トリガごとに同バッファを再生する。

```bash
pio run -e m5stack-cores3-speaker-demo -t upload
pio device monitor
```

操作:
1. 起動すると `ready` 表示、音量 128/255。
2. 以下のいずれかで再生トリガ:
   - 画面 LCD タップ
   - USB シリアルに `p` (or `P`) を送信
3. `playing...` 表示中、内蔵スピーカーから 440Hz 0.5 秒のビープが流れる。
4. 完了で自動的に `ready` に戻る。
5. 音量調整: serial `-` で −16、serial `+` で +16 (0..255)。
6. 緊急停止: serial `s` で再生中の WAV を中断。

> **CoreS3 のボタン事情**: CoreS3 にはハード BtnA/B/C が無い (BtnPWR のみ)。
> M5Unified の `setTouchButtonHeight()` で画面下端タッチ 3 分割を仮想 BtnA/B/C
> に割り当てる仕様はあるが、SpeakerDemo は最小ファームとして UI を作り込ま
> ず、画面全体タップ + シリアルだけで完結する。

> **注**: `M5.Speaker.playWav` は `M5Unified` 内部で WAV ヘッダを parse する。
> 16bit / mono / 16kHz は piper / VOICEVOX 出力と同じ形式で、旧 stackchan-atama
> 試作で実機再生実績がある最も保守的な組合せ。Step D で外部受信した WAV も
> この形式で揃える前提。

### XangiBridge (xangi シリアル経由 WAV 再生 + Avatar + サーボ)

xangi (or 任意ホスト) のシリアル経由音声出力 + 表情 + 首振りデバイスとして
K151 を動かす受信ファーム。Step D-1 / D-2 / Step E をまとめた本番ファーム
位置づけ。プロトコルは `docs/xangi_bridge_protocol.md` 参照。

- **Step D-1**: WAV シリアル受信 + `playWav`
- **Step D-2**: Avatar 統合、`FACE:<expr>` 表情切替 + 再生中の口パク
- **Step E**: SCServo 統合、`MOVE:<yaw,pitch>` で首振り、PY32 VM_EN ON
  + NVS zero load + SAFE clamp 透明 ack (`clamped:true` + `requested_*` 併記)

サーボ初期化失敗時は graceful degradation で `MOVE:` だけ無効化、WAV/FACE は
継続動作。**HomeCalibration を先に焼く前提** (NVS の `yaw_zero` / `pitch_zero` 必須)。

```bash
pio run -e m5stack-cores3-xangi-bridge -t upload
# Python 側からテスト (FACE 巡回 → WAV 再生):
uv run python scripts/test_xangi_bridge.py --port /dev/ttyACM0
```

対応コマンド (\n 終端):
- `STATUS` → `{"state":"...","volume":N,"version":"xangi-bridge-0.3","servo":bool,"torque":bool}`
- `VOLUME:<0-255>` → 音量設定、`{"status":"ok","volume":N}`
- `WAV:<size>` → `READY\n` 返してバイナリモード、`<size>` byte 受信して
  `M5.Speaker.playWav` 再生 (再生中は口パク連動)、完了後
  `{"status":"ok","size":N,"played":true}`
- `FACE:<expr>` → `setExpression` (`neutral`/`happy`/`sad`/`doubt`/`sleepy`/`angry`)、
  `{"status":"ok","face":"..."}`
- `MOVE:<yaw_deg>,<pitch_deg>` → zero ベース角度 (yaw ±100° / pitch ±30° SAFE)、
  `{"status":"ok","yaw":N,"pitch":N}` (clamp 時は `requested_*` + `clamped:true` 併記)

Python 側は `src/xangi_stackchan/stackchan.py` の `StackchanSerial` がそのまま
使える (ボーレート 921600 一致、`send_wav` のチャンク 1024B / chunk_delay 5ms
シーケンスと整合)。

### SetAngleDemo (yaw 中央移動 + ±30° スイープ)

NVS に保存した zero raw を使って `servo.setAngleYaw()` を呼ぶ初の torque ON
系デモ。**HomeCalibration を先に焼いて zero を保存しておくこと** (未保存だと
zero=512 デフォルトで動き、物理姿勢によっては大きく回転して機械干渉する)。
pitch は触らない (SAFE 範囲の意味論修正は次 PR で対応)。

```bash
pio run -e m5stack-cores3-setangle-demo -t upload
pio device monitor
```

操作:
1. 起動すると **両軸 torque OFF**、LCD に yaw の現在角度を 200ms ごと表示。
2. 以下のいずれかでデモ起動:
   - 画面 LCD タップ
   - BtnA 押下
   - USB シリアルに `g` (or `G`) を送信
3. yaw torque ON →  `0° → -30° → 0° → +30° → 0°` を 1.5 秒ずつ移動。
4. 完了後は torque ON のまま放置 (再トリガで再実行)。
5. **緊急停止 / yaw torque OFF**: BtnB / シリアル `s`。完了後の手動戻しに使う。
