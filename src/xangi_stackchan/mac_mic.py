"""macOS local microphone recorder used by voice conversation.

The bridge normally records PCM from StackChan firmware.  For demos where the
CoreS3 built-in microphone is too noisy, this module records from the Mac's
default input device and returns the same shape as StackchanSerial.stop_mic_recording().
"""

from __future__ import annotations

import io
import os
import shutil
import subprocess
import tempfile
import time
import wave
from pathlib import Path


HELPER_VERSION = "1"
DEFAULT_SAMPLE_RATE = 16000
DEFAULT_CHANNELS = 1

_SWIFT_SOURCE = r'''
import Foundation
import AVFoundation

if CommandLine.arguments.count < 3 {
    fputs("usage: mac_mic_recorder <seconds> <output.wav>\n", stderr)
    exit(2)
}

let seconds = Double(CommandLine.arguments[1]) ?? 0.0
let outputPath = CommandLine.arguments[2]
if seconds <= 0 {
    fputs("seconds must be positive\n", stderr)
    exit(2)
}

let url = URL(fileURLWithPath: outputPath)
try? FileManager.default.removeItem(at: url)

let settings: [String: Any] = [
    AVFormatIDKey: Int(kAudioFormatLinearPCM),
    AVSampleRateKey: 16000.0,
    AVNumberOfChannelsKey: 1,
    AVLinearPCMBitDepthKey: 16,
    AVLinearPCMIsFloatKey: false,
    AVLinearPCMIsBigEndianKey: false
]

do {
    let recorder = try AVAudioRecorder(url: url, settings: settings)
    recorder.prepareToRecord()
    if !recorder.record() {
        fputs("failed to start recording\n", stderr)
        exit(1)
    }
    Thread.sleep(forTimeInterval: seconds)
    recorder.stop()
    print(outputPath)
} catch {
    fputs("recording error: \(error)\n", stderr)
    exit(1)
}
'''


def _cache_dir() -> Path:
    return Path(
        os.environ.get(
            "XANGI_STACKCHAN_CACHE_DIR",
            str(Path.home() / ".cache" / "xangi-stackchan"),
        )
    )


def _helper_paths() -> tuple[Path, Path]:
    cache = _cache_dir()
    return (
        cache / f"mac_mic_recorder_v{HELPER_VERSION}.swift",
        cache / f"mac_mic_recorder_v{HELPER_VERSION}",
    )


def ensure_helper() -> Path:
    source_path, binary_path = _helper_paths()
    source_path.parent.mkdir(parents=True, exist_ok=True)
    if not source_path.exists() or source_path.read_text() != _SWIFT_SOURCE:
        source_path.write_text(_SWIFT_SOURCE)
        if binary_path.exists():
            binary_path.unlink()
    if binary_path.exists():
        return binary_path

    xcrun = shutil.which("xcrun")
    swiftc = shutil.which("swiftc")
    if xcrun:
        cmd = [xcrun, "swiftc", str(source_path), "-o", str(binary_path)]
    elif swiftc:
        cmd = [swiftc, str(source_path), "-o", str(binary_path)]
    else:
        raise RuntimeError("swiftc not found; install Xcode Command Line Tools")

    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(f"failed to build mac microphone helper: {detail}")
    return binary_path


def _read_wav(path: Path) -> tuple[bytes, bytes, int, float]:
    wav_bytes = path.read_bytes()
    with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
        frames = wf.getnframes()
        framerate = wf.getframerate()
        pcm = wf.readframes(frames)
    duration = frames / float(framerate) if framerate else 0.0
    return wav_bytes, pcm, frames, duration


def record_mac_microphone(seconds: float, path: str | None = None) -> dict:
    """Record a fixed-length WAV from macOS default input device."""
    seconds = float(seconds)
    if seconds <= 0:
        raise ValueError("seconds must be positive")

    output_path: Path
    if path:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        output_path = Path(tempfile.gettempdir()) / f"xangi_stackchan_mac_mic_{int(time.time())}.wav"

    helper = ensure_helper()
    started = time.time()
    proc = subprocess.run(
        [str(helper), f"{seconds:.3f}", str(output_path)],
        capture_output=True,
        text=True,
        timeout=max(10.0, seconds + 10.0),
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(f"mac microphone recording failed: {detail}")
    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError("mac microphone recording produced no wav")

    wav_bytes, pcm, frames, duration = _read_wav(output_path)
    return {
        "status": "ok",
        "input_source": "mac",
        "path": str(output_path),
        "wav": wav_bytes,
        "pcm": pcm,
        "frames": frames,
        "duration_seconds": duration,
        "elapsed_seconds": time.time() - started,
        "sample_rate": DEFAULT_SAMPLE_RATE,
        "channels": DEFAULT_CHANNELS,
    }
