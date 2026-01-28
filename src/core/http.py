import hashlib
import json
from typing import Dict, Optional

import requests

from .config import COOKIE_FILE, COOKIE_PERSIST, EXTRA_HEADERS, ORIGIN, REFERER, USER_AGENT


DEFAULT_HEADERS: Dict[str, str] = {
    "User-Agent": USER_AGENT,
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": REFERER,
    "Origin": ORIGIN,
}
DEFAULT_HEADERS.update({str(k): str(v) for k, v in EXTRA_HEADERS.items()})


def _cookie_path(cookie_key: Optional[str]) -> str:
    if not cookie_key:
        return str(COOKIE_FILE)
    digest = hashlib.sha256(cookie_key.encode("utf-8")).hexdigest()[:16]
    return str(COOKIE_FILE.with_name(f"cookies_{digest}.json"))


def create_session(
    proxies: Optional[Dict[str, str]] = None,
    cookie_key: Optional[str] = None,
) -> requests.Session:
    session = requests.Session()
    # Always honor explicit proxy settings, ignore environment NO_PROXY.
    session.trust_env = False
    session.headers.update(DEFAULT_HEADERS)
    if proxies:
        session.proxies.update(proxies)
    load_cookies(session, cookie_key)
    return session


def save_cookies(session: requests.Session, cookie_key: Optional[str] = None) -> None:
    if not COOKIE_PERSIST:
        return
    cookie_file = _cookie_path(cookie_key)
    COOKIE_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = requests.utils.dict_from_cookiejar(session.cookies)
    with open(cookie_file, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(data, ensure_ascii=True))


def load_cookies(session: requests.Session, cookie_key: Optional[str] = None) -> None:
    if not COOKIE_PERSIST:
        return
    cookie_file = _cookie_path(cookie_key)
    if not COOKIE_FILE.parent.exists():
        return
    try:
        with open(cookie_file, "r", encoding="utf-8") as handle:
            data = json.loads(handle.read())
    except (FileNotFoundError, json.JSONDecodeError):
        return
    session.cookies.update(data)
