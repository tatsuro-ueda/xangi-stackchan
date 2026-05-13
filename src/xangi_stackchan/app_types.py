from dataclasses import dataclass

from .stackchan import StackchanConfig


@dataclass
class BridgeConfig:
    xangi_url: str
    thread_id: str | None
    stackchan: StackchanConfig
    volume: int
    tts: str
    piper_bin: str
    piper_model: str
    piper_speaker: int
    voicevox_url: str
    voicevox_speaker: int
    serial_chunk: int
    serial_delay: float
    stackchan_retry_seconds: float
    face_idle: str
    face_thinking: str
    face_talking: str
    face_error: str
    stream_timeout: int
    retry_seconds: float
    max_retry_seconds: float
    move_enabled: bool = True
    move_idle_yaw: float = 0.0
    move_idle_pitch: float = 5.0
    move_thinking_yaw: float = -8.0
    move_thinking_pitch: float = 5.0
    move_error_yaw: float = 0.0
    move_error_pitch: float = -10.0
    move_talking_sway_yaw: float = 4.0
    move_talking_sway_pitch: float = 2.0
    move_talking_sway_interval: float = 1.5
