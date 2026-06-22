import json
import time
from collections.abc import Iterator
from urllib.parse import urlparse

import requests

from .auth import build_xangi_basic_auth


def normalize_xangi_stream_url(url: str) -> str:
    """Accept either a xangi base URL or a full /api/events/stream URL."""
    trimmed = (url or "").strip().rstrip("/")
    if not trimmed:
        raise ValueError("xangi URL is required")
    parsed = urlparse(trimmed)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"invalid xangi URL: {url}")
    if trimmed.endswith("/api/events/stream"):
        return trimmed
    return f"{trimmed}/api/events/stream"


def iter_sse_messages(url: str, timeout: int = 65) -> Iterator[dict[str, str]]:
    """Yield raw SSE messages as {event, data} dictionaries."""
    with requests.get(
        url,
        stream=True,
        headers={"Accept": "text/event-stream"},
        auth=build_xangi_basic_auth(),
        timeout=(5, timeout),
    ) as resp:
        resp.raise_for_status()
        event = "message"
        data_lines: list[str] = []
        for raw_line in resp.iter_lines(decode_unicode=True):
            if raw_line is None:
                continue
            line = raw_line.rstrip("\r")
            if line == "":
                if data_lines:
                    yield {"event": event, "data": "\n".join(data_lines)}
                event = "message"
                data_lines = []
                continue
            if line.startswith(":"):
                continue
            if line.startswith("event:"):
                event = line[6:].strip() or "message"
                continue
            if line.startswith("data:"):
                data_lines.append(line[5:].lstrip())


def iter_xangi_events(url: str, timeout: int = 65) -> Iterator[dict]:
    """Yield parsed xangi event payloads from the pull-mode SSE stream."""
    for msg in iter_sse_messages(url, timeout=timeout):
        payload = json.loads(msg["data"])
        payload["_sse_event"] = msg["event"]
        yield payload


def reconnecting_xangi_events(
    stream_url: str,
    timeout: int = 65,
    retry_seconds: float = 1.0,
    max_retry_seconds: float = 30.0,
) -> Iterator[dict]:
    """Yield xangi events forever, reconnecting with exponential backoff."""
    backoff = max(retry_seconds, 1.0)
    max_backoff = max(backoff, max_retry_seconds)
    while True:
        try:
            yield {"_bridge_event": "connecting", "url": stream_url}
            for event in iter_xangi_events(stream_url, timeout=timeout):
                yield event
            backoff = max(retry_seconds, 1.0)
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            yield {
                "_bridge_event": "stream_error",
                "error": str(exc),
                "retry_seconds": backoff,
            }
            time.sleep(backoff)
            backoff = min(backoff * 2, max_backoff)
