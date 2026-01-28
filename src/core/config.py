import json
import os
from pathlib import Path

from dotenv import load_dotenv


ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=True)


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


def _get_list(name: str, default: str = "") -> list[str]:
    value = os.getenv(name, default)
    if value is None:
        return []
    normalized = value.replace("|", ",")
    return [item.strip() for item in normalized.split(",") if item.strip()]


def _get_int_list(name: str) -> list[int]:
    items = _get_list(name, "")
    result = []
    for item in items:
        try:
            result.append(int(item))
        except ValueError:
            continue
    return result


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
CAPTCHA_ERROR_HINT = os.getenv("CAPTCHA_ERROR_HINT", "")
CAPTCHA_ERROR_HINTS = _get_list("CAPTCHA_ERROR_HINTS", CAPTCHA_ERROR_HINT)
CAPTCHA_MAX_TRIES = _get_int("CAPTCHA_MAX_TRIES", 3)
CAPTCHA_REFRESH_PARAM = _get_bool("CAPTCHA_REFRESH_PARAM", True)
CAPTCHA_REFRESH_PARAM_NAME = os.getenv("CAPTCHA_REFRESH_PARAM_NAME", "t")
SAVE_CAPTCHA = _get_bool("SAVE_CAPTCHA", False)

OCR_WHITELIST = os.getenv(
    "OCR_WHITELIST",
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
)
OCR_THRESHOLD = _get_int("OCR_THRESHOLD", 140)

PROXY_MODE = os.getenv("PROXY_MODE", "none").lower()
PROXY_URL = os.getenv("PROXY_URL", "")
PROXY_API_URL = os.getenv("PROXY_API_URL", "")
PROXY_API_ACTIVE_URL = os.getenv("PROXY_API_ACTIVE_URL", "")
PROXY_API_RELEASE_URL = os.getenv("PROXY_API_RELEASE_URL", "")
PROXY_API_HEADERS_JSON = os.getenv("PROXY_API_HEADERS_JSON", "{}")
try:
    PROXY_API_HEADERS = json.loads(PROXY_API_HEADERS_JSON)
    if not isinstance(PROXY_API_HEADERS, dict):
        PROXY_API_HEADERS = {}
except json.JSONDecodeError:
    PROXY_API_HEADERS = {}
PROXY_API_PARAMS_JSON = os.getenv("PROXY_API_PARAMS_JSON", "{}")
try:
    PROXY_API_PARAMS = json.loads(PROXY_API_PARAMS_JSON)
    if not isinstance(PROXY_API_PARAMS, dict):
        PROXY_API_PARAMS = {}
except json.JSONDecodeError:
    PROXY_API_PARAMS = {}
PROXY_API_TIMEOUT = _get_float("PROXY_API_TIMEOUT", 10.0)
PROXY_API_REGEX = os.getenv(
    "PROXY_API_REGEX",
    r"\b\d{1,3}(?:\.\d{1,3}){3}:\d{2,5}\b",
)
PROXY_SCHEME = os.getenv("PROXY_SCHEME", "http")
PROXY_USERNAME = os.getenv("PROXY_USERNAME", "")
PROXY_PASSWORD = os.getenv("PROXY_PASSWORD", "")
PROXY_ALWAYS_REFRESH = _get_bool("PROXY_ALWAYS_REFRESH", False)
PROXY_ROTATE_EACH_REQUEST = _get_bool("PROXY_ROTATE_EACH_REQUEST", False)
PROXY_REFRESH_BEFORE_SECONDS = _get_int("PROXY_REFRESH_BEFORE_SECONDS", 5)
PROXY_ROTATE_ON_LIMIT = _get_bool("PROXY_ROTATE_ON_LIMIT", False)
PROXY_LIMIT_HINT = os.getenv("PROXY_LIMIT_HINT", "")
PROXY_LIMIT_HINTS = _get_list("PROXY_LIMIT_HINTS", PROXY_LIMIT_HINT)
PROXY_LIMIT_STATUSES = _get_int_list("PROXY_LIMIT_STATUSES")
PROXY_RELEASE_ON_LIMIT = _get_bool("PROXY_RELEASE_ON_LIMIT", False)
PROXY_DEBUG_IP_CHECK = _get_bool("PROXY_DEBUG_IP_CHECK", False)
PROXY_DEBUG_IP_URL = os.getenv("PROXY_DEBUG_IP_URL", "https://api.ipify.org")
PROXY_DEBUG_IP_TIMEOUT = _get_float("PROXY_DEBUG_IP_TIMEOUT", 5.0)

DATA_DIR = Path("data")
COOKIE_FILE = DATA_DIR / "cookies.json"
COOKIE_PERSIST = _get_bool("COOKIE_PERSIST", True)
CAPTCHA_DIR = DATA_DIR / "captcha"
