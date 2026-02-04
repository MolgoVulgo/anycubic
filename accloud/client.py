from typing import Any, Dict, Optional
import hashlib
import json
import os
import time
import uuid

try:
    import httpx
except ModuleNotFoundError as exc:  # pragma: no cover - user environment dependency
    raise ModuleNotFoundError(
        "Missing dependency 'httpx'. Install with: pip install httpx"
    ) from exc

from endpoints import BASE_URL
from .utils import append_log_line, get_logger, redact_payload, redacted_headers, truncate_text


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
        self.http_log_path = os.path.join(os.getcwd(), "accloud_http.log")

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
        redacted = redacted_headers(headers)
        payload = None
        if "json" in kwargs:
            payload = redact_payload(kwargs.get("json"))
        elif "data" in kwargs:
            payload = kwargs.get("data")
        self.logger.debug('HTTP %s %s headers=%s', method, url, redacted)
        if payload is not None:
            append_log_line(self.http_log_path, f"{method} {url} headers={redacted} payload={payload}")
        else:
            append_log_line(self.http_log_path, f"{method} {url} headers={redacted}")
        resp = self._client.request(method, url, **kwargs)
        response_body: Any = None
        try:
            response_body = resp.json()
            response_body = redact_payload(response_body)
        except Exception:
            response_body = truncate_text(resp.text or "")
        append_log_line(
            self.http_log_path,
            f"{method} {url} status={resp.status_code} response={json.dumps(response_body, ensure_ascii=True)}",
        )
        resp.raise_for_status()
        return resp

    def close(self) -> None:
        self._client.close()
