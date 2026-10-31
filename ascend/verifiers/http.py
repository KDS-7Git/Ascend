from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import urlparse

from ascend.engine.packs import substitute
from ascend.engine.verifiers import VerifyResult


def verify(spec, vars):
    spec = substitute(spec, vars)
    url = spec.get("url", "")
    if urlparse(url).scheme not in {"http", "https"}: return VerifyResult(False, "HTTP verifier needs an http(s) URL")
    try:
        with urlopen(Request(url, headers={"User-Agent": "Ascend/0.1"}), timeout=10) as response:
            status = response.status
    except HTTPError as error: status = error.code
    except (URLError, OSError, ValueError): return VerifyResult(False, "HTTP endpoint could not be reached")
    return VerifyResult(status == spec.get("status", 200), f"HTTP endpoint returned {status}")
