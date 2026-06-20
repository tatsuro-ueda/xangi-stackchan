from datetime import datetime

from xangi_stackchan import app


def test_format_hourly_chime_text_uses_japanese_am_pm():
    assert app.format_hourly_chime_text(7) == "午前7時です"
    assert app.format_hourly_chime_text(12) == "正午です"
    assert app.format_hourly_chime_text(15) == "午後3時です"
    assert app.format_hourly_chime_text(21) == "午後9時です"


def test_format_hourly_chime_text_returns_none_outside_7_to_21():
    assert app.format_hourly_chime_text(6) is None
    assert app.format_hourly_chime_text(22) is None


def test_hourly_chime_loop_speaks_once_at_top_of_allowed_hour():
    spoken = []
    loop = app.HourlyChimeLoop(
        backend=object(),
        config=object(),
        piper_process=None,
        now_fn=lambda: datetime(2026, 6, 20, 15, 0),
        speak_fn=lambda _backend, text, _config, _piper_process: spoken.append(text),
    )

    assert loop._send_once() is True
    assert loop._send_once() is False
    assert spoken == ["午後3時です"]


def test_hourly_chime_loop_does_not_speak_outside_top_of_hour():
    spoken = []
    loop = app.HourlyChimeLoop(
        backend=object(),
        config=object(),
        piper_process=None,
        now_fn=lambda: datetime(2026, 6, 20, 15, 1),
        speak_fn=lambda _backend, text, _config, _piper_process: spoken.append(text),
    )

    assert loop._send_once() is False
    assert spoken == []


def test_hourly_chime_loop_skips_when_busy():
    spoken = []
    loop = app.HourlyChimeLoop(
        backend=object(),
        config=object(),
        piper_process=None,
        now_fn=lambda: datetime(2026, 6, 20, 15, 0),
        can_speak_fn=lambda: False,
        speak_fn=lambda _backend, text, _config, _piper_process: spoken.append(text),
    )

    assert loop._send_once() is False
    assert spoken == []


def test_hourly_chime_loop_skips_during_mic_recording_or_wav_playback():
    spoken = []

    class BusyBackend:
        _mic_recording = True
        _wav_active = False

    mic_loop = app.HourlyChimeLoop(
        backend=BusyBackend(),
        config=object(),
        piper_process=None,
        now_fn=lambda: datetime(2026, 6, 20, 15, 0),
        speak_fn=lambda _backend, text, _config, _piper_process: spoken.append(text),
    )
    assert mic_loop._send_once() is False

    BusyBackend._mic_recording = False
    BusyBackend._wav_active = True
    wav_loop = app.HourlyChimeLoop(
        backend=BusyBackend(),
        config=object(),
        piper_process=None,
        now_fn=lambda: datetime(2026, 6, 20, 16, 0),
        speak_fn=lambda _backend, text, _config, _piper_process: spoken.append(text),
    )
    assert wav_loop._send_once() is False

    assert spoken == []
