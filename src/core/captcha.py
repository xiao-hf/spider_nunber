import time
from typing import Optional, Tuple

import requests

from .config import (
    CAPTCHA_DIR,
    CAPTCHA_REFRESH_PARAM,
    CAPTCHA_REFRESH_PARAM_NAME,
    CAPTCHA_URL,
    REQUEST_TIMEOUT,
    SAVE_CAPTCHA,
    VERIFY_SSL,
)


def build_captcha_url() -> str:
    if not CAPTCHA_REFRESH_PARAM:
        return CAPTCHA_URL
    sep = "&" if "?" in CAPTCHA_URL else "?"
    ts = int(time.time() * 1000)
    if CAPTCHA_REFRESH_PARAM_NAME:
        return f"{CAPTCHA_URL}{sep}{CAPTCHA_REFRESH_PARAM_NAME}={ts}"
    return f"{CAPTCHA_URL}{sep}{ts}"


def save_captcha(image_bytes: bytes) -> Optional[str]:
    if not SAVE_CAPTCHA:
        return None
    CAPTCHA_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"captcha_{int(time.time() * 1000)}.png"
    path = CAPTCHA_DIR / filename
    path.write_bytes(image_bytes)
    return str(path)


def fetch_captcha(session: requests.Session) -> Tuple[bytes, Optional[str]]:
    url = build_captcha_url()
    resp = session.get(url, timeout=REQUEST_TIMEOUT, verify=VERIFY_SSL)
    resp.raise_for_status()
    image_bytes = resp.content
    saved_path = save_captcha(image_bytes)
    return image_bytes, saved_path
