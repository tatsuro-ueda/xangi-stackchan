from __future__ import annotations

import time
from unittest.mock import MagicMock

from xangi_stackchan.voice_conversation import VoiceConversation


def _wait_until(predicate, timeout: float = 3.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return predicate()


def test_mac_input_records_without_mic_start(monkeypatch):
    backend = MagicMock()
    on_stop = MagicMock()
    on_transcribed = MagicMock()

    def fake_record_mac_microphone(seconds):
        return {
            "status": "ok",
            "input_source": "mac",
            "wav": b"RIFF1234",
            "pcm": b"\x01\x00" * 5000,
            "frames": 5000,
            "duration_seconds": seconds,
        }

    monkeypatch.setattr(
        "xangi_stackchan.voice_conversation.mac_mic.record_mac_microphone",
        fake_record_mac_microphone,
    )
    monkeypatch.setattr(
        "xangi_stackchan.voice_conversation.stt_module.transcribe",
        lambda wav, language: {
            "status": "ok",
            "text": "こんにちは",
            "language": language,
            "elapsed_seconds": 0.01,
        },
    )

    vc = VoiceConversation(
        backend=backend,
        xangi_base_url="",
        input_source="mac",
        mac_mic_seconds=0.1,
        min_pcm_bytes=1,
        on_stop=on_stop,
        on_transcribed=on_transcribed,
        trigger_head_touch=False,
        trigger_mic_button=True,
    )

    vc._on_mic_button({"action": "down"})

    assert _wait_until(lambda: vc._recording is False)
    backend.start_mic_recording.assert_not_called()
    backend.stop_mic_recording.assert_not_called()
    on_stop.assert_called_once()
    assert on_stop.call_args.args[0]["input_source"] == "mac"
    on_transcribed.assert_called_once()
    assert vc.history[-1]["text"] == "こんにちは"
    assert vc.history[-1]["input_source"] == "mac"
