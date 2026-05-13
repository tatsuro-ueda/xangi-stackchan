# xangi events

`xangi-stackchan` は xangi の pull 型 SSE を購読する。

## Endpoint

```
GET <xangi-url>/api/events/stream
```

最初に `event: ready` が届く。

```json
{"instance_id":"xangi-a","host_hint":"hostname"}
```

以後は通常の `message` イベントとして turn lifecycle が届く。

## Event types

- `turn.started`: ユーザー入力を受けた。デバイスを `thinking` 顔にする
- `message.delta`: 応答が流れ始めた。デバイスを `talking` 顔にする
- `turn.complete`: 最終応答が確定した。`text` をTTSして再生する
- `turn.aborted`: 中断。`idle` 顔に戻す
- `agent.error`: エラー。`error` 顔にする

## Filtering

接続先の xangi は `--xangi-url` で選ぶ。必要ならブリッジ側で以下を self-filter する。

- `--thread-id`: 特定 Discord / Slack / web thread だけ処理

xangi 側の設定変更は不要。
