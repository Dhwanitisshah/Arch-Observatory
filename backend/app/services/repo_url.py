import re
from urllib.parse import urlsplit

from app.config import settings

_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


def parse_github_url(url: str) -> tuple[str, str]:
    """Validate and parse a GitHub repo URL, returning (owner, name).

    Raises ValueError for anything not a plain https://<allowed-host>/owner/name URL.
    """
    parts = urlsplit(url)

    if parts.scheme != "https":
        raise ValueError("URL must use the https scheme")

    if "@" in parts.netloc:
        raise ValueError("URL must not contain credentials")

    if parts.hostname not in settings.ALLOWED_GIT_HOSTS:
        raise ValueError(f"Host must be one of {settings.ALLOWED_GIT_HOSTS}")

    if parts.query:
        raise ValueError("URL must not contain a query string")

    if parts.fragment:
        raise ValueError("URL must not contain a fragment")

    path = parts.path.rstrip("/")
    if path.endswith(".git"):
        path = path[: -len(".git")]

    segments = [s for s in path.split("/") if s]
    if len(segments) != 2:
        raise ValueError("URL path must be exactly /owner/name")

    owner, name = segments
    if not _NAME_RE.match(owner) or not _NAME_RE.match(name):
        raise ValueError("Owner and name must match ^[A-Za-z0-9_.-]+$")

    return owner, name
