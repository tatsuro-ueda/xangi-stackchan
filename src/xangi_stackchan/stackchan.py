import glob
import json
import os
import platform
import threading
import time
from dataclasses import dataclass

import requests
import serial
import serial.tools.list_ports


DEFAULT_BAUD = 921600
DEFAULT_WIFI_HOST = os.environ.get("STACKCHAN_IP", "192.168.1.100")


def detect_serial_port() -> str:
    env_port = os.environ.get("STACKCHAN_PORT")
    if env_port:
        return env_port

    esp_vid = 0x303A
    bridge_vids = {0x10C4, 0x1A86}
    ports = list(serial.tools.list_ports.comports())
    for port in ports:
        if port.vid == esp_vid:
            return port.device
    for port in ports:
        if port.vid in bridge_vids:
            return port.device

    if platform.system() == "Darwin":
        candidates = glob.glob("/dev/cu.usbmodem*") + glob.glob("/dev/cu.usbserial*")
    else:
        candidates = glob.glob("/dev/ttyACM*") + glob.glob("/dev/ttyUSB*")
    return candidates[0] if candidates else "/dev/ttyACM0"


class StackchanSerial:
    """USB serial backend for stackchan family devices (K151 / stackchan-atama)."""

    def __init__(self, port: str, baud: int = DEFAULT_BAUD):
        self.port = port
        self.baud = baud
        self.ser = None
        # シリアルバスは USB 1 本の共有資源。WAV 転送中に MOVE/FACE/VOLUME などの
        # テキストコマンドが割り込むと WAV データに ASCII バイト列が混入し、
        # playWav 失敗・no READY response・ノイズ再生を引き起こす。RLock で
        # send_command / send_wav 全体を直列化する。
        self._lock = threading.RLock()

    def open(self):
        self.ser = serial.Serial(self.port, self.baud, timeout=5)
        time.sleep(0.5)
        self.drain()

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()

    def drain(self):
        while self.ser and self.ser.in_waiting:
            self.ser.read(self.ser.in_waiting)

    def send_command(self, cmd: str) -> dict:
        with self._lock:
            self.ser.write(f"{cmd}\n".encode())
            self.ser.flush()
            time.sleep(0.2)
            response = ""
            while self.ser.in_waiting:
                line = self.ser.readline().decode("utf-8", errors="replace").strip()
                if line:
                    response = line
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                return {"raw": response}

    def send_wav(self, wav_data: bytes, chunk_size: int = 1024, chunk_delay: float = 0.005) -> dict:
        if not wav_data:
            return {"status": "error", "error": "empty WAV"}

        # Step G: ファーム (xangi-bridge-0.4+) は WAV キューが満杯なら受信前に
        # `{"status":"error","error":"queue full"}` を返す。再生中のスロットが
        # 空くまで短く sleep + retry する (キュー 4 slot なので最悪でも 1 chunk
        # 分の再生時間 = 数秒待てば必ず空く)。リトライ中もシリアル排他は維持。
        for attempt in range(8):
            with self._lock:
                result = self._send_wav_locked(wav_data, chunk_size, chunk_delay)
            if result.get("status") == "error" and result.get("error") == "queue full":
                time.sleep(0.5)
                continue
            return result
        return result

    def _send_wav_locked(self, wav_data: bytes, chunk_size: int, chunk_delay: float) -> dict:
        self.drain()
        self.ser.write(f"WAV:{len(wav_data)}\n".encode())
        self.ser.flush()

        # READY 待ち。READY が来ればバイナリ送信フェーズに進む。`{` で始まる行が
        # 来た場合はファームが事前エラー (queue full / size=0 / size exceeds /
        # ps_malloc failed) を返したと見なして JSON を即返す (Step G で追加された
        # 早期エラーパス)。
        deadline = time.time() + 3
        ready = False
        while time.time() < deadline:
            if self.ser.in_waiting:
                line = self.ser.readline().decode("utf-8", errors="replace").strip()
                if line == "READY":
                    ready = True
                    break
                if line.startswith("{"):
                    try:
                        return json.loads(line)
                    except json.JSONDecodeError:
                        pass
            time.sleep(0.05)
        if not ready:
            return {"status": "error", "error": "no READY response"}

        sent = 0
        while sent < len(wav_data):
            end = min(sent + chunk_size, len(wav_data))
            self.ser.write(wav_data[sent:end])
            self.ser.flush()
            sent = end
            time.sleep(chunk_delay)

        # ack 待ち。`readline()` は self.ser のグローバル timeout (=5s) で
        # \n まで block するので、in_waiting で来た分だけ読んで自前で行分割
        # する (デバイス側が大量のデバッグログを流す場合に readline ブロックで
        # deadline を越えてしまう問題への対策)。
        deadline = time.time() + 10
        buf = b""
        while time.time() < deadline:
            avail = self.ser.in_waiting
            if avail > 0:
                buf += self.ser.read(avail)
                while b"\n" in buf:
                    raw_line, buf = buf.split(b"\n", 1)
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if not line.startswith("{"):
                        continue
                    try:
                        parsed = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    # WAV ack のシグネチャ: ファーム xangi-bridge-0.4+ は
                    # `{"status":"ok","size":N,"queued":n}` を返す。前 MOVE
                    # ack や FACE ack (yaw/pitch/face フィールドを持つ) が
                    # シリアル TX の遅延ではぐれてここに紛れ込むことがある
                    # ので、`size` キーが無い ack は捨てて次の行を読む。
                    # エラー ack (`error` キー有り) は WAV 起因なのでそのまま
                    # 返す (size 無くても識別可能)。
                    if "size" in parsed or "error" in parsed:
                        return parsed
                    # それ以外 (他コマンドの ack のはぐれ) は捨てて継続
                    continue
            else:
                time.sleep(0.05)
        return {"status": "ok", "size": len(wav_data), "note": "no confirmation received"}


class StackchanWifi:
    """WiFi HTTP API backend for stackchan family devices (K151 / stackchan-atama)."""

    def __init__(self, host: str = DEFAULT_WIFI_HOST):
        self.base_url = f"http://{host}"

    def open(self):
        return None

    def close(self):
        return None

    def send_command(self, cmd: str) -> dict:
        if cmd == "STATUS":
            response = requests.get(f"{self.base_url}/status", timeout=5)
        elif cmd.startswith("FACE:"):
            expression = cmd.split(":", 1)[1]
            response = requests.get(f"{self.base_url}/face", params={"expression": expression}, timeout=5)
        elif cmd.startswith("VOLUME:"):
            level = cmd.split(":", 1)[1]
            response = requests.get(f"{self.base_url}/setting", params={"volume": level}, timeout=5)
        else:
            return {"status": "error", "error": f"unsupported WiFi command: {cmd}"}
        response.raise_for_status()
        return response.json()

    def send_wav(self, wav_data: bytes, chunk_size: int = 1024, chunk_delay: float = 0.005) -> dict:
        if not wav_data:
            return {"status": "error", "error": "empty WAV"}
        response = requests.post(
            f"{self.base_url}/play",
            data=wav_data,
            headers={"Content-Type": "application/octet-stream"},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()


@dataclass
class StackchanConfig:
    wifi: bool = False
    host: str = DEFAULT_WIFI_HOST
    port: str = ""
    baud: int = DEFAULT_BAUD


def create_backend(config: StackchanConfig):
    if config.wifi:
        return StackchanWifi(config.host)
    return StackchanSerial(config.port or detect_serial_port(), config.baud)

