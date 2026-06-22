import os

from requests.auth import HTTPBasicAuth


def build_xangi_basic_auth() -> HTTPBasicAuth | None:
    """Return Basic auth credentials for xangi HTTP requests, if configured."""
    username = os.environ.get("XANGI_BASIC_AUTH_USER", "").strip()
    password = os.environ.get("XANGI_BASIC_AUTH_PASSWORD", "")
    if not username and not password:
        return None
    if not username or not password:
        raise ValueError(
            "both XANGI_BASIC_AUTH_USER and XANGI_BASIC_AUTH_PASSWORD are required"
        )
    return HTTPBasicAuth(username, password)
