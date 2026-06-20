from datetime import datetime
from threading import Event

from xangi_stackchan.app import ClockSyncLoop, format_clock_command


def test_format_clock_command_uses_two_digit_hhmm():
    assert format_clock_command(9, 42) == "TIME:09:42"
    assert format_clock_command(23, 59) == "TIME:23:59"


class FakeBackend:
    def __init__(self, result=None):
        self.result = result if result is not None else {"status": "ok", "time": "09:42"}
        self.commands = []
        self.sent = Event()

    def send_command(self, command):
        self.commands.append(command)
        self.sent.set()
        return self.result


def test_clock_sync_loop_sends_time_immediately_when_started():
    backend = FakeBackend()
    loop = ClockSyncLoop(
        backend,
        now_fn=lambda: datetime(2026, 6, 20, 9, 42),
        interval_seconds=60.0,
    )

    loop.start()
    try:
        assert backend.sent.wait(timeout=1.0)
        assert backend.commands == ["TIME:09:42"]
    finally:
        loop.stop()


def test_clock_sync_loop_ignores_error_result():
    backend = FakeBackend({"status": "error", "error": "TIME syntax: HH:MM"})
    loop = ClockSyncLoop(
        backend,
        now_fn=lambda: datetime(2026, 6, 20, 9, 42),
        interval_seconds=60.0,
    )

    loop._send_once()

    assert backend.commands == ["TIME:09:42"]


def test_clock_sync_loop_calls_success_callback_after_time_sync():
    backend = FakeBackend()
    callbacks = []
    loop = ClockSyncLoop(
        backend,
        now_fn=lambda: datetime(2026, 6, 21, 0, 1),
        interval_seconds=60.0,
        on_sync=lambda hour, minute: callbacks.append((hour, minute)),
    )

    assert loop._send_once() is True

    assert backend.commands == ["TIME:00:01"]
    assert callbacks == [(0, 1)]
