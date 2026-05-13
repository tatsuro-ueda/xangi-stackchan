from xangi_stackchan.app_types import BridgeConfig
from xangi_stackchan.settings import merge_config
from xangi_stackchan.stackchan import StackchanConfig


def _base_config() -> BridgeConfig:
    return BridgeConfig(
        xangi_url="http://127.0.0.1:18890",
        thread_id=None,
        stackchan=StackchanConfig(wifi=False, host="192.168.1.100", port="/dev/stackchan", baud=115200),
        volume=255,
        tts="piper",
        piper_bin="piper",
        piper_model="model.onnx",
        piper_speaker=0,
        voicevox_url="http://127.0.0.1:50021",
        voicevox_speaker=1,
        serial_chunk=1024,
        serial_delay=0.005,
        stackchan_retry_seconds=3.0,
        face_idle="neutral",
        face_thinking="doubt",
        face_talking="happy",
        face_error="sad",
        stream_timeout=65,
        retry_seconds=1.0,
        max_retry_seconds=30.0,
    )


def test_merge_config_keeps_numeric_defaults_for_blank_form_values():
    config = merge_config(
        _base_config(),
        {
            "baud": "",
            "volume": "",
            "piper_speaker": "",
            "voicevox_speaker": "",
            "serial_chunk": "",
            "serial_delay": "",
            "stackchan_retry_seconds": "",
            "stream_timeout": "",
            "retry_seconds": "",
            "max_retry_seconds": "",
        },
    )

    assert config.stackchan.baud == 115200
    assert config.volume == 255
    assert config.piper_speaker == 0
    assert config.voicevox_speaker == 1
    assert config.serial_chunk == 1024
    assert config.serial_delay == 0.005
    assert config.stackchan_retry_seconds == 3.0
    assert config.stream_timeout == 65
    assert config.retry_seconds == 1.0
    assert config.max_retry_seconds == 30.0


def test_merge_config_clamps_volume():
    assert merge_config(_base_config(), {"volume": "-1"}).volume == 0
    assert merge_config(_base_config(), {"volume": "999"}).volume == 255
    assert merge_config(_base_config(), {"volume": "128"}).volume == 128


def test_merge_config_keeps_move_defaults_for_blank_form_values():
    config = merge_config(
        _base_config(),
        {
            "move_idle_yaw": "",
            "move_idle_pitch": "",
            "move_thinking_yaw": "",
            "move_thinking_pitch": "",
            "move_error_yaw": "",
            "move_error_pitch": "",
            "move_talking_sway_yaw": "",
            "move_talking_sway_pitch": "",
            "move_talking_sway_interval": "",
        },
    )

    assert config.move_enabled is True
    assert config.move_idle_pitch == 5.0
    assert config.move_thinking_yaw == -8.0
    assert config.move_error_pitch == -10.0
    assert config.move_talking_sway_yaw == 4.0
    assert config.move_talking_sway_interval == 1.5


def test_merge_config_disables_move_with_form_checkbox_off():
    # HTML form checkbox: not sent when off, so _flatten_form sets move_enabled=False
    config = merge_config(_base_config(), {"move_enabled": False})
    assert config.move_enabled is False


def test_merge_config_accepts_move_overrides():
    config = merge_config(
        _base_config(),
        {
            "move_idle_pitch": "10",
            "move_talking_sway_yaw": "2.5",
            "move_talking_sway_interval": "0.8",
        },
    )
    assert config.move_idle_pitch == 10.0
    assert config.move_talking_sway_yaw == 2.5
    assert config.move_talking_sway_interval == 0.8
