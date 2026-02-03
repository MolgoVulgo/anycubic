import json
import os
from pathlib import Path
from typing import Any, Dict, List

import httpx

DEFAULT_SESSION_PATH = ".accloud/session.json"


def load_cookies_from_json(path: str) -> httpx.Cookies:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    cookies = httpx.Cookies()

    # Common browser export format: list of cookie dicts
    if isinstance(data, list):
        for item in data:
            name = item.get("name")
            value = item.get("value")
            domain = item.get("domain")
            cookie_path = item.get("path", "/")
            if name and value:
                cookies.set(name, value, domain=domain, path=cookie_path)
        return cookies

    # Fallback: dict of name -> value
    if isinstance(data, dict):
        for name, value in data.items():
            if isinstance(value, dict) and "value" in value:
                cookies.set(
                    name,
                    value["value"],
                    domain=value.get("domain"),
                    path=value.get("path", "/"),
                )
            else:
                cookies.set(name, value)
        return cookies

    raise ValueError("Unsupported cookies JSON format")


def load_tokens_from_json(path: str) -> Dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Tokens file must be a JSON object")
    return data


def _export_cookies(cookies: httpx.Cookies) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    jar = cookies.jar
    for c in jar:
        out.append(
            {
                "name": c.name,
                "value": c.value,
                "domain": c.domain,
                "path": c.path,
            }
        )
    return out


def save_session(
    path: str,
    cookies: httpx.Cookies,
    tokens: Dict[str, Any],
) -> None:
    session_path = Path(path)
    session_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"cookies": _export_cookies(cookies), "tokens": tokens}
    session_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    os.chmod(session_path, 0o600)


def load_session(path: str) -> Dict[str, Any]:
    session_path = Path(path)
    data = json.loads(session_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Session file must be a JSON object")
    cookies = httpx.Cookies()
    for item in data.get("cookies", []):
        name = item.get("name")
        value = item.get("value")
        domain = item.get("domain")
        cookie_path = item.get("path", "/")
        if name and value:
            cookies.set(name, value, domain=domain, path=cookie_path)
    return {"cookies": cookies, "tokens": data.get("tokens", {})}




def load_session_from_har(path: str) -> Dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    entries = data.get("log", {}).get("entries", [])

    cookies = httpx.Cookies()
    tokens: Dict[str, Any] = {}

    def add_cookie(name: str, value: str, domain: str = None, cpath: str = "/") -> None:
        if name and value:
            cookies.set(name, value, domain=domain, path=cpath)

    for entry in entries:
        req = entry.get("request", {})
        resp = entry.get("response", {})

        for c in req.get("cookies", []) or []:
            add_cookie(c.get("name"), c.get("value"), c.get("domain"), c.get("path", "/"))
        for c in resp.get("cookies", []) or []:
            add_cookie(c.get("name"), c.get("value"), c.get("domain"), c.get("path", "/"))

        # header fallbacks
        for h in req.get("headers", []) or []:
            if h.get("name", "").lower() == "cookie":
                for part in h.get("value", "").split(";"):
                    if "=" in part:
                        name, value = part.strip().split("=", 1)
                        add_cookie(name.strip(), value.strip())

        for h in resp.get("headers", []) or []:
            if h.get("name", "").lower() == "set-cookie":
                # Best-effort parse: name=value; Path=/; Domain=...
                parts = [p.strip() for p in h.get("value", "").split(";") if p.strip()]
                if parts and "=" in parts[0]:
                    name, value = parts[0].split("=", 1)
                    domain = None
                    cpath = "/"
                    for p in parts[1:]:
                        if p.lower().startswith("domain="):
                            domain = p.split("=", 1)[1]
                        if p.lower().startswith("path="):
                            cpath = p.split("=", 1)[1]
                    add_cookie(name, value, domain, cpath)

        # token extraction
        content = (resp.get("content") or {}).get("text")
        if content and isinstance(content, str):
            try:
                body = json.loads(content)
            except Exception:
                body = None
            if isinstance(body, dict):
                data_obj = body.get("data", {})
                if "id_token" in data_obj:
                    tokens["id_token"] = data_obj.get("id_token")
                if "token" in data_obj:
                    tokens["token"] = data_obj.get("token")

        # access_token might be in request body
        post = req.get("postData", {}) or {}
        post_text = post.get("text")
        if post_text:
            try:
                post_obj = json.loads(post_text)
            except Exception:
                post_obj = None
            if isinstance(post_obj, dict) and "access_token" in post_obj:
                tokens["access_token"] = post_obj.get("access_token")

    return {"cookies": cookies, "tokens": tokens}
