import json
from typing import Dict

import requests

from .config import COOKIE_FILE, EXTRA_HEADERS, ORIGIN, REFERER, USER_AGENT


DEFAULT_HEADERS: Dict[str, str] = {
    "User-Agent": USER_AGENT,
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": REFERER,
    "Origin": ORIGIN,
}
DEFAULT_HEADERS.update({str(k): str(v) for k, v in EXTRA_HEADERS.items()})


def create_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)
    load_cookies(session)
    return session


def save_cookies(session: requests.Session) -> None:
    COOKIE_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = requests.utils.dict_from_cookiejar(session.cookies)
    COOKIE_FILE.write_text(json.dumps(data, ensure_ascii=True), encoding="utf-8")


def load_cookies(session: requests.Session) -> None:
    if not COOKIE_FILE.exists():
        return
    try:
        data = json.loads(COOKIE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return
    session.cookies.update(data)
