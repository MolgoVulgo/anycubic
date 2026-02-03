from typing import Any, Dict, Optional
import hashlib
import time
import uuid

try:
    import httpx
except ModuleNotFoundError as exc:  # pragma: no cover - user environment dependency
    raise ModuleNotFoundError(
        "Missing dependency 'httpx'. Install with: pip install httpx"
    ) from exc

from endpoints import BASE_URL
from .utils import get_logger, redacted_headers


class CloudClient:
    def __init__(
        self,
        base_url: str = BASE_URL,
        cookies: Optional[httpx.Cookies] = None,
        tokens: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0,
    ):
        self.base_url = base_url.rstrip('/')
        self.cookies = cookies or httpx.Cookies()
        self.tokens = tokens or {}
        self.timeout = timeout
        self.logger = get_logger('accloud')
        self._client = httpx.Client(base_url=self.base_url, cookies=self.cookies, timeout=self.timeout)

        # Constants extracted from web app bundle (HAR)
        self._app_id = "f9b3528877c94d5c9c5af32245db46ef"
        self._app_secret = "0cf75926606049a3937f56b0373b99fb"
        self._app_version = "1.0.0"

    def _signature(self, nonce: str, timestamp_ms: str) -> str:
        # JS formula: md5(appid + timestamp + version + appSecret + nonce + appid)
        raw = f"{self._app_id}{timestamp_ms}{self._app_version}{self._app_secret}{nonce}{self._app_id}"
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    def _default_headers(self) -> Dict[str, str]:
        nonce = str(uuid.uuid1())
        timestamp = str(int(time.time() * 1000))
        signature = self._signature(nonce, timestamp)
        headers: Dict[str, str] = {
            "XX-Device-Type": "web",
            "XX-IS-CN": "2",
            "XX-Version": self._app_version,
            "XX-Nonce": nonce,
            "XX-Timestamp": timestamp,
            "XX-Signature": signature,
        }
        token = self.tokens.get("token")
        if token:
            headers["XX-Token"] = str(token)
        return headers

    def request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        url = path if path.startswith('http') else f"{self.base_url}{path}"
        headers = dict(self._default_headers())
        headers.update(kwargs.get('headers', {}) or {})
        kwargs['headers'] = headers
        self.logger.debug('HTTP %s %s headers=%s', method, url, redacted_headers(headers))
        resp = self._client.request(method, url, **kwargs)
        resp.raise_for_status()
        return resp

    def close(self) -> None:
        self._client.close()
