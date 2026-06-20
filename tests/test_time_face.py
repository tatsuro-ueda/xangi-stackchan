from datetime import datetime

from xangi_stackchan import app


def test_select_time_face_prioritizes_minute_rule():
    assert app.select_time_face(20, 44) == "angry"
    assert app.select_time_face(20, 45) == "doubt"
    assert app.select_time_face(20, 49) == "doubt"
    assert app.select_time_face(20, 50) == "sleepy"
    assert app.select_time_face(20, 54) == "sleepy"
    assert app.select_time_face(20, 55) == "happy"
    assert app.select_time_face(20, 59) == "happy"


def test_select_time_face_uses_hour_bands_before_45_minutes():
    assert app.select_time_face(6, 44) == "sleepy"
    assert app.select_time_face(7, 0) == "neutral"
    assert app.select_time_face(11, 44) == "neutral"
    assert app.select_time_face(12, 0) == "happy"
    assert app.select_time_face(13, 0) == "neutral"
    assert app.select_time_face(16, 44) == "neutral"
    assert app.select_time_face(17, 0) == "sad"
    assert app.select_time_face(18, 44) == "sad"
    assert app.select_time_face(19, 0) == "sleepy"
    assert app.select_time_face(20, 0) == "angry"
    assert app.select_time_face(21, 0) == "sleepy"
    assert app.select_time_face(23, 44) == "sleepy"


def test_get_current_time_face_accepts_datetime_or_struct_time_style():
    assert app.get_current_time_face(lambda: datetime(2026, 6, 20, 17, 30)) == "sad"


class FakeBackend:
    def __init__(self):
        self.commands = []

    def send_command(self, command):
        self.commands.append(command)
        return {"status": "ok", "face": command.split(":", 1)[1]}


def test_set_idle_visual_face_uses_current_time_face_for_avatar_mode():
    backend = FakeBackend()
    current_face = [None]
    config = type("Config", (), {"face_mode": "avatar", "face_idle": "neutral"})()

    assert app.set_idle_visual_face(
        backend,
        config,
        current_face,
        sprite_renderer=[None],
        sprite_animator=None,
        now_fn=lambda: datetime(2026, 6, 20, 20, 0),
    ) is True

    assert backend.commands == ["FACE:angry"]
    assert current_face == ["angry"]
