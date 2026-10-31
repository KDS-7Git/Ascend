import os
import re
from urllib.request import Request, urlopen
from urllib.error import URLError


def send(message, topic=None, server=None, **config):
    topic = topic or os.environ.get("NTFY_TOPIC")
    server = (server or os.environ.get("NTFY_SERVER", "https://ntfy.sh")).rstrip("/")
    if not topic or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", topic):
        raise ValueError("Set a private ntfy topic before sending reminders")
    if not server.startswith(("http://", "https://")):
        raise ValueError("ntfy server must be an http(s) URL")
    headers = {"Title": "Ascend", "Content-Type": "text/plain; charset=utf-8"}
    if os.environ.get("NTFY_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["NTFY_TOKEN"]
    try:
        with urlopen(
            Request(f"{server}/{topic}", data=message.encode(), headers=headers),
            timeout=10,
        ):
            pass
    except (URLError, OSError):
        raise ValueError(
            "ntfy delivery failed; check the server and topic configuration"
        ) from None
