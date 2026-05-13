#!/usr/bin/env python3
"""Stackchan ダンスデモ CLI: piper TTS で喋らせつつ BPM 駆動の首振りを流す。

2 モード:

- `--via-bridge URL`: 動作中の xangi-stackchan の settings server に
  `POST /api/demo` する。USB シリアルは xangi-stackchan が掴んだまま、
  TTS / 再生 / ダンスを内部で実行する (デバイス取り合いなし)。
- 直接モード (デフォルト): xangi-stackchan を起動せず、このスクリプトが
  シリアルを直接掴んで TTS → 再生 → ダンスする単発実行。

例:
    # 動作中の xangi-stackchan 経由 (推奨)
    uv run python scripts/dance_demo.py --text "踊るよ" --preset happy \\
        --via-bridge http://127.0.0.1:7897

    # 直接 (xangi-stackchan 停止時のスタンドアロン)
    uv run python scripts/dance_demo.py --text "踊るよ" --preset happy

    # TTS だけ確認 (シリアル不要)
    uv run python scripts/dance_demo.py --text "テスト" --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request

try:
    from xangi_stackchan.dance import (
        PRESETS,
        DanceLoop,
        resolve_pattern,
        wav_duration_seconds,
    )
    from xangi_stackchan.stackchan import (
        DEFAULT_BAUD,
        StackchanSerial,
        detect_serial_port,
    )
    from xangi_stackchan.tts import DEFAULT_PIPER_BIN, DEFAULT_PIPER_MODEL, PiperProcess, split_text
except ImportError:
    print("ERROR: xangi_stackchan を import できない。`uv sync` 済みか確認。", file=sys.stderr)
    sys.exit(1)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--text", required=True, help="喋らせるテキスト")
    parser.add_argument(
        "--preset",
        default="happy",
        choices=sorted(PRESETS.keys()),
        help="ダンスプリセット (デフォルト happy)",
    )
    parser.add_argument("--bpm", type=float, default=None, help="BPM をプリセット既定から上書き")
    parser.add_argument(
        "--via-bridge",
        default=None,
        metavar="URL",
        help="動作中の xangi-stackchan の settings URL (例 http://127.0.0.1:7897)",
    )
    parser.add_argument("--port", default=None, help="直接モード: シリアルポート (省略時自動検出)")
    parser.add_argument("--baud", type=int, default=DEFAULT_BAUD)
    parser.add_argument("--piper-bin", default=DEFAULT_PIPER_BIN)
    parser.add_argument("--piper-model", default=DEFAULT_PIPER_MODEL)
    parser.add_argument("--piper-speaker", type=int, default=0)
    parser.add_argument("--volume", type=int, default=160, help="直接モード: 音量 0..255")
    parser.add_argument("--face", default="happy", help="直接モード: 再生中の表情")
    parser.add_argument("--idle-yaw", type=float, default=0.0)
    parser.add_argument("--idle-pitch", type=float, default=5.0)
    parser.add_argument("--dry-run", action="store_true", help="TTS のみ実行、シリアル不使用")
    return parser.parse_args(argv)


def run_via_bridge(args: argparse.Namespace) -> int:
    url = args.via_bridge.rstrip("/") + "/api/demo"
    payload = {"text": args.text, "preset": args.preset}
    if args.bpm is not None:
        payload["bpm"] = args.bpm
    data = json.dumps(payload, ensure_ascii=False).encode()
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json; charset=utf-8"}, method="POST"
    )
    print(f"[dance] POST {url} payload={payload}")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = resp.read().decode("utf-8")
            print(f"[dance] <- {resp.status} {body}")
            return 0
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8") if exc.fp else ""
        print(f"[dance] HTTP {exc.code}: {body}", file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print(f"[dance] connection error: {exc}", file=sys.stderr)
        return 1


def run_direct(args: argparse.Namespace) -> int:
    pattern = resolve_pattern(args.preset, args.bpm)
    volume = max(0, min(255, args.volume))

    print(f"[dance] preset={args.preset} bpm={pattern['bpm']} text={args.text}")
    print("[dance] synthesizing with piper ...")
    piper = PiperProcess(args.piper_bin, args.piper_model, args.piper_speaker)
    try:
        chunks = split_text(args.text)
        wavs = piper.synthesize_many(chunks)
        synthesized = list(zip(chunks, wavs))
        total_audio = sum(wav_duration_seconds(wav) for _, wav in synthesized)
        total_bytes = sum(len(wav) for _, wav in synthesized)
        print(f"[dance] tts: chunks={len(synthesized)} bytes={total_bytes} audio={total_audio:.2f}s")

        if args.dry_run:
            print("[dance] dry-run: skipping serial / playback")
            for idx, (chunk, wav) in enumerate(synthesized, start=1):
                print(f"  chunk {idx}: '{chunk}' ({len(wav)} bytes, {wav_duration_seconds(wav):.2f}s)")
            return 0

        port = args.port or detect_serial_port()
        print(f"[dance] port={port} baud={args.baud}")
        backend = StackchanSerial(port, args.baud)
        backend.open()
        try:
            backend.send_command(f"VOLUME:{volume}")
            backend.send_command(f"FACE:{args.face}")
            backend.send_command(f"MOVE:{args.idle_yaw:.1f},{args.idle_pitch:.1f}")
            time.sleep(0.2)

            send_seconds_last = 0.0
            with DanceLoop(backend, pattern, args.idle_yaw, args.idle_pitch):
                for idx, (chunk, wav) in enumerate(synthesized, start=1):
                    started = time.time()
                    result = backend.send_wav(wav)
                    send_seconds_last = time.time() - started
                    print(
                        f"[dance] chunk {idx}/{len(synthesized)}: "
                        f"bytes={len(wav)} audio={wav_duration_seconds(wav):.2f}s "
                        f"send={send_seconds_last:.2f}s result={result}"
                    )
                remaining = max(0.0, total_audio - send_seconds_last)
                time.sleep(remaining + 0.3)

            backend.send_command("FACE:neutral")
        finally:
            backend.close()
    finally:
        piper.close()

    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.via_bridge:
        return run_via_bridge(args)
    return run_direct(args)


if __name__ == "__main__":
    sys.exit(main())
