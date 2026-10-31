import getpass
import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from ascend.storage import default_home


def client_settings():
    path = default_home() / "client.json"
    return json.loads(path.read_text()) if path.exists() else {}


def server_url(explicit=None):
    return (
        explicit or os.environ.get("ASCEND_SERVER") or client_settings().get("server")
    )


def configure_server(url):
    path = default_home() / "client.json"
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    settings = client_settings()
    if url in {"off", "none"}:
        settings.pop("server", None)
    else:
        if urlparse(url).scheme not in {"http", "https"} or not urlparse(url).netloc:
            raise ValueError("Server URL must use http or https")
        settings["server"] = url.rstrip("/")
    path.write_text(json.dumps(settings))
    return settings


def request(server, path, data=None):
    token_file = default_home() / "token"
    tokens = json.loads(token_file.read_text()) if token_file.exists() else {}
    headers = {"Content-Type": "application/json"}
    if tokens.get(server):
        headers["Authorization"] = "Bearer " + tokens[server]
    req = Request(
        server.rstrip("/") + path,
        data=json.dumps(data).encode() if data is not None else None,
        headers=headers,
    )
    try:
        with urlopen(req, timeout=30) as response:
            return json.load(response)
    except HTTPError as error:
        try:
            detail = json.load(error).get("detail", str(error.code))
        except (ValueError, OSError):
            detail = str(error.code)
        raise ValueError(f"Server: {detail}") from None
    except (URLError, OSError):
        raise ValueError("Cannot reach the Ascend server") from None


def login(server):
    result = request(
        server,
        "/api/login",
        {"username": input("Username: "), "password": getpass.getpass("Password: ")},
    )
    path = default_home() / "token"
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    tokens = json.loads(path.read_text()) if path.exists() else {}
    tokens[server] = result["token"]
    fd = os.open(path, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(tokens, stream)
    configure_server(server)
    return {"logged_in": server}
