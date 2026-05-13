import pytest

from xangi_stackchan.events import normalize_xangi_stream_url


def test_normalize_base_url():
    assert (
        normalize_xangi_stream_url("http://127.0.0.1:18890")
        == "http://127.0.0.1:18890/api/events/stream"
    )


def test_normalize_stream_url():
    assert (
        normalize_xangi_stream_url("http://127.0.0.1:18890/api/events/stream")
        == "http://127.0.0.1:18890/api/events/stream"
    )


def test_normalize_rejects_empty():
    with pytest.raises(ValueError):
        normalize_xangi_stream_url("")

