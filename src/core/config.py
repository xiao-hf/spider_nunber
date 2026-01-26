import json
import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


def _get_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _get_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


BASE_URL = os.getenv("BASE_URL", "https://www.opene164.org.cn")
INDEX_URL = os.getenv("INDEX_URL", f"{BASE_URL}/mark/index.html")
CAPTCHA_URL = os.getenv("CAPTCHA_URL", f"{BASE_URL}/captcha.html")
QUERY_URL = os.getenv("QUERY_URL", f"{BASE_URL}/mark/data.do")

REQUEST_TIMEOUT = _get_float("REQUEST_TIMEOUT", 15.0)
VERIFY_SSL = _get_bool("VERIFY_SSL", True)

USER_AGENT = os.getenv(
    "USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
)
REFERER = os.getenv("REFERER", INDEX_URL)
ORIGIN = os.getenv("ORIGIN", BASE_URL)

QUERY_METHOD = os.getenv("QUERY_METHOD", "POST").upper()
QUERY_CONTENT_TYPE = os.getenv("QUERY_CONTENT_TYPE", "form").lower()
CODE_FIELD = os.getenv("CODE_FIELD", "code")
CAPTCHA_FIELD = os.getenv("CAPTCHA_FIELD", "captcha")

EXTRA_FORM_JSON = os.getenv("EXTRA_FORM_JSON", "{}")
try:
    EXTRA_FORM = json.loads(EXTRA_FORM_JSON)
    if not isinstance(EXTRA_FORM, dict):
        EXTRA_FORM = {}
except json.JSONDecodeError:
    EXTRA_FORM = {}

EXTRA_HEADERS_JSON = os.getenv(
    "EXTRA_HEADERS_JSON",
    '{"X-Requested-With":"XMLHttpRequest"}',
)
try:
    EXTRA_HEADERS = json.loads(EXTRA_HEADERS_JSON)
    if not isinstance(EXTRA_HEADERS, dict):
        EXTRA_HEADERS = {}
except json.JSONDecodeError:
    EXTRA_HEADERS = {}

CAPTCHA_LEN = _get_int("CAPTCHA_LEN", 4)
CAPTCHA_CASE = os.getenv("CAPTCHA_CASE", "lower").lower()
CAPTCHA_REGEX = os.getenv("CAPTCHA_REGEX", "")
CAPTCHA_MAX_TRIES = _get_int("CAPTCHA_MAX_TRIES", 3)
CAPTCHA_ERROR_HINT = os.getenv("CAPTCHA_ERROR_HINT", "")
CAPTCHA_REFRESH_PARAM = _get_bool("CAPTCHA_REFRESH_PARAM", True)
CAPTCHA_REFRESH_PARAM_NAME = os.getenv("CAPTCHA_REFRESH_PARAM_NAME", "t")
SAVE_CAPTCHA = _get_bool("SAVE_CAPTCHA", False)

OCR_WHITELIST = os.getenv(
    "OCR_WHITELIST",
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
)
OCR_THRESHOLD = _get_int("OCR_THRESHOLD", 140)

DATA_DIR = Path("data")
COOKIE_FILE = DATA_DIR / "cookies.json"
CAPTCHA_DIR = DATA_DIR / "captcha"
