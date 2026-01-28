from dataclasses import dataclass
import logging
import re
from typing import Any, Dict, Optional

import requests

from ..core.captcha import fetch_captcha
from ..core.config import (
    CAPTCHA_ERROR_HINT,
    CAPTCHA_ERROR_HINTS,
    CAPTCHA_FIELD,
    CAPTCHA_MAX_TRIES,
    CODE_FIELD,
    EXTRA_FORM,
    INDEX_URL,
    PROXY_API_URL,
    PROXY_LIMIT_HINT,
    PROXY_LIMIT_HINTS,
    PROXY_LIMIT_STATUSES,
    PROXY_MODE,
    PROXY_PASSWORD,
    PROXY_RELEASE_ON_LIMIT,
    PROXY_ROTATE_EACH_REQUEST,
    PROXY_ROTATE_ON_LIMIT,
    PROXY_SCHEME,
    PROXY_USERNAME,
    PROXY_DEBUG_IP_CHECK,
    PROXY_DEBUG_IP_TIMEOUT,
    PROXY_DEBUG_IP_URL,
    QUERY_CONTENT_TYPE,
    QUERY_METHOD,
    QUERY_URL,
    REQUEST_TIMEOUT,
    VERIFY_SSL,
)
from ..core.http import create_session, save_cookies
from ..core.ocr import is_valid, read_captcha_text
from ..core.proxy import ProxyManager


@dataclass
class CaptchaResult:
    text: str
    image_bytes: bytes
    image_path: Optional[str] = None


@dataclass
class SpiderResult:
    ok: bool
    status_code: int
    captcha: Optional[str]
    attempts: int
    data: Optional[Dict[str, Any]]
    text: Optional[str]
    error: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "status_code": self.status_code,
            "captcha": self.captcha,
            "attempts": self.attempts,
            "data": self.data,
            "text": self.text,
            "error": self.error,
        }


class SpiderService:
    def __init__(self) -> None:
        self._warmed = False
        self._logger = logging.getLogger(__name__)
        self._proxy_manager = ProxyManager()
        self._proxy_info = None
        self._cookie_key = None
        self.session = create_session()
        self._log_proxy_config()
        self._ensure_session()

    def close(self) -> None:
        save_cookies(self.session, self._cookie_key)
        self.session.close()

    def _reset_session(self) -> None:
        save_cookies(self.session, self._cookie_key)
        self.session.close()
        self.session = create_session()
        self._proxy_info = None
        self._cookie_key = None
        self._warmed = False

    def _log_proxy_config(self) -> None:
        if PROXY_MODE == "none":
            self._logger.info("proxy_config: mode=none")
            return
        auth_set = bool(PROXY_USERNAME and PROXY_PASSWORD)
        api_set = bool(PROXY_API_URL)
        self._logger.info(
            "proxy_config: mode=%s api_url_set=%s auth_set=%s scheme=%s",
            PROXY_MODE,
            api_set,
            auth_set,
            PROXY_SCHEME,
        )

    @staticmethod
    def _is_proxy_error(exc: requests.RequestException) -> bool:
        return isinstance(
            exc,
            (
                requests.exceptions.ProxyError,
                requests.exceptions.ConnectTimeout,
                requests.exceptions.ReadTimeout,
                requests.exceptions.SSLError,
                requests.exceptions.ConnectionError,
            ),
        )

    def _ensure_session(self, refresh_proxy: bool = True) -> None:
        if not refresh_proxy and self._proxy_info is not None:
            return
        proxy_info = self._proxy_manager.get_proxy()
        if proxy_info and (
            self._proxy_info is None
            or self._proxy_info.url != proxy_info.url
            or self._cookie_key != proxy_info.cookie_key
        ):
            save_cookies(self.session, self._cookie_key)
            self.session.close()
            proxies = {"http": proxy_info.url, "https": proxy_info.url}
            self.session = create_session(proxies=proxies, cookie_key=proxy_info.cookie_key)
            self._proxy_info = proxy_info
            self._cookie_key = proxy_info.cookie_key
            self._warmed = False
            self._logger.info(
                "proxy_in_use: endpoint=%s proxy_ip=%s source=%s",
                proxy_info.endpoint,
                proxy_info.proxy_ip or "",
                proxy_info.source,
            )
            self._log_proxy_exit_ip()
            return
        if proxy_info is None and self._proxy_info is not None:
            save_cookies(self.session, self._cookie_key)
            self.session.close()
            self.session = create_session()
            self._proxy_info = None
            self._cookie_key = None
            self._warmed = False
            self._logger.info("proxy_in_use: none")

    def _log_proxy_exit_ip(self) -> None:
        if not PROXY_DEBUG_IP_CHECK:
            return
        if self._proxy_info is None:
            self._logger.info("proxy_exit_ip: none")
            return
        try:
            resp = self.session.get(
                PROXY_DEBUG_IP_URL,
                timeout=PROXY_DEBUG_IP_TIMEOUT,
                verify=VERIFY_SSL,
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            self._logger.warning("proxy_exit_ip_error: %s", exc)
            return
        text = resp.text.strip()
        self._logger.info("proxy_exit_ip: %s", text)

    def warm_up(self) -> None:
        self._ensure_session(refresh_proxy=False)
        if self._warmed:
            return
        self._logger.info("warm_up: url=%s", INDEX_URL)
        resp = self.session.get(INDEX_URL, timeout=REQUEST_TIMEOUT, verify=VERIFY_SSL)
        resp.raise_for_status()
        self._logger.info("warm_up: status=%s", resp.status_code)
        self._warmed = True
        save_cookies(self.session, self._cookie_key)

    def get_captcha(self) -> CaptchaResult:
        self._ensure_session(refresh_proxy=False)
        image_bytes, image_path = fetch_captcha(self.session)
        text = read_captcha_text(image_bytes)
        self._logger.info(
            "captcha_ocr: text=%s len=%s saved=%s",
            text,
            len(text),
            image_path or "",
        )
        return CaptchaResult(text=text, image_bytes=image_bytes, image_path=image_path)

    def _build_payload(self, code: str, captcha: str) -> Dict[str, Any]:
        payload = dict(EXTRA_FORM)
        payload[CODE_FIELD] = code
        payload[CAPTCHA_FIELD] = captcha
        return payload

    def _send_query(self, payload: Dict[str, Any]) -> requests.Response:
        if QUERY_METHOD == "GET":
            return self.session.get(
                QUERY_URL,
                params=payload,
                timeout=REQUEST_TIMEOUT,
                verify=VERIFY_SSL,
            )
        if QUERY_CONTENT_TYPE == "json":
            return self.session.post(
                QUERY_URL,
                json=payload,
                timeout=REQUEST_TIMEOUT,
                verify=VERIFY_SSL,
            )
        return self.session.post(
            QUERY_URL,
            data=payload,
            timeout=REQUEST_TIMEOUT,
            verify=VERIFY_SSL,
        )

    def _is_captcha_error(self, response: requests.Response) -> bool:
        if not CAPTCHA_ERROR_HINT:
            return False
        return CAPTCHA_ERROR_HINT.lower() in response.text.lower()

    def _matches_hint(self, message: Optional[str], hints: list[str]) -> bool:
        if not message or not hints:
            return False
        for hint in hints:
            if hint and hint in message:
                return True
        return False

    def _parse_response(self, response: requests.Response) -> Dict[str, Any]:
        data: Optional[Dict[str, Any]] = None
        text: Optional[str] = None
        content_type = response.headers.get("Content-Type", "")
        if "application/json" in content_type:
            try:
                data = response.json()
            except ValueError:
                text = response.text
        else:
            text = response.text
        return {"data": data, "text": text}

    def _apply_mark_summary(self, parsed: Dict[str, Any]) -> None:
        summary = self._build_mark_summary(parsed.get("data"))
        if not summary:
            return
        target = "\u57fa\u4e8e\u5e73\u53f0\u6807\u8bb0\u4e0e\u6b21\u6570\u7efc\u5408\u5224\u65ad"
        data = parsed.get("data")
        if isinstance(data, dict):
            replaced = self._replace_text(data, target, summary)
            if not replaced:
                data.setdefault("mark_summary", summary)
        text = parsed.get("text")
        if isinstance(text, str) and target in text:
            parsed["text"] = text.replace(target, summary)

    def _replace_text(self, obj: Any, target: str, replacement: str) -> bool:
        if isinstance(obj, dict):
            changed = False
            for key, value in obj.items():
                if isinstance(value, str) and target in value:
                    obj[key] = value.replace(target, replacement)
                    changed = True
                else:
                    changed = self._replace_text(value, target, replacement) or changed
            return changed
        if isinstance(obj, list):
            changed = False
            for idx, value in enumerate(obj):
                if isinstance(value, str) and target in value:
                    obj[idx] = value.replace(target, replacement)
                    changed = True
                else:
                    changed = self._replace_text(value, target, replacement) or changed
            return changed
        return False

    def _build_mark_summary(self, payload: Any) -> Optional[str]:
        if not isinstance(payload, dict):
            return None
        mark_list = self._find_mark_list(payload)
        if not mark_list:
            return None
        platform_count, mark_count = self._summarize_mark_list(mark_list)
        template = "\u88ab{platforms}\u4e2a\u5e73\u53f0\u6807\u8bb0\uff0c\u6807\u8bb0\u6b21\u6570:{count}"
        return template.format(platforms=platform_count, count=mark_count)

    def _find_mark_list(self, payload: Dict[str, Any]) -> Optional[list[Dict[str, Any]]]:
        best_list: Optional[list[Dict[str, Any]]] = None
        best_score = 0
        best_len = 0
        for items in self._iter_lists(payload):
            if not items or not all(isinstance(item, dict) for item in items):
                continue
            score = self._score_mark_list(items)
            if score <= 0:
                continue
            if score > best_score or (score == best_score and len(items) > best_len):
                best_list = items
                best_score = score
                best_len = len(items)
        return best_list

    def _iter_lists(self, node: Any):
        if isinstance(node, dict):
            for value in node.values():
                yield from self._iter_lists(value)
        elif isinstance(node, list):
            yield node
            for value in node:
                yield from self._iter_lists(value)

    def _score_mark_list(self, items: list[Dict[str, Any]]) -> int:
        score = 0
        for item in items:
            for key in item.keys():
                if self._is_mark_key(key):
                    score += 1
        return score

    def _summarize_mark_list(self, items: list[Dict[str, Any]]) -> tuple[int, int]:
        platform_count = 0
        mark_count = 0
        for item in items:
            entry_count = self._extract_entry_count(item)
            if entry_count is None:
                if not self._entry_is_marked(item):
                    continue
                entry_count = 1
            if entry_count > 0:
                platform_count += 1
                mark_count += entry_count
        return platform_count, mark_count

    def _extract_entry_count(self, entry: Dict[str, Any]) -> Optional[int]:
        has_context = any(self._is_mark_key(key) for key in entry.keys())
        for key, value in entry.items():
            key_lower = key.lower()
            if not has_context and not self._is_mark_key(key):
                continue
            if self._is_mark_key(key) or any(part in key_lower for part in ("count", "num", "times")):
                count = self._extract_int(value)
                if count is not None:
                    return count
        return None

    def _entry_is_marked(self, entry: Dict[str, Any]) -> bool:
        has_context = any(self._is_mark_key(key) for key in entry.keys())
        for key, value in entry.items():
            key_lower = key.lower()
            if self._is_mark_key(key) or (has_context and key_lower in {"status", "state", "flag"}):
                if self._value_is_marked(value):
                    return True
        return False

    def _is_mark_key(self, key: str) -> bool:
        key_lower = key.lower()
        return "mark" in key_lower or "tag" in key_lower or "\u6807\u8bb0" in key

    def _value_is_marked(self, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value > 0
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return False
            number = self._extract_int(text)
            if number is not None:
                return number > 0
            if "\u672a\u6807\u8bb0" in text:
                return False
            if text.lower() in {"1", "true", "yes", "y", "marked"}:
                return True
            if "\u5df2\u6807\u8bb0" in text or "\u6807\u8bb0" in text:
                return True
        return False

    def _extract_int(self, value: Any) -> Optional[int]:
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            match = re.search(r"\d+", value)
            if match:
                return int(match.group(0))
        return None

    def query(self, code: str, captcha: Optional[str] = None) -> SpiderResult:
        last_error: Optional[str] = None
        attempts = 0
        proxy_failures = 0
        max_proxy_failures = max(3, CAPTCHA_MAX_TRIES * 2)
        self._logger.info("query_start: code=%s", code)
        refresh_proxy = True
        if PROXY_ROTATE_EACH_REQUEST and self._proxy_manager.enabled():
            self._proxy_manager.rotate("per_request")
            self._warmed = False
        while attempts < CAPTCHA_MAX_TRIES:
            self._ensure_session(refresh_proxy=refresh_proxy)
            refresh_proxy = False
            try:
                self.warm_up()
                attempt_no = attempts + 1
                if captcha:
                    text = captcha
                    captcha = None
                    self._logger.info(
                        "captcha_manual: text=%s len=%s attempt=%s",
                        text,
                        len(text),
                        attempt_no,
                    )
                else:
                    cap = self.get_captcha()
                    text = cap.text
            except requests.RequestException as exc:
                if self._is_proxy_error(exc) and self._proxy_manager.enabled():
                    proxy_failures += 1
                    last_error = "proxy_error"
                    self._logger.warning("proxy_error: %s", exc)
                    self._reset_session()
                    self._proxy_manager.rotate("proxy_error")
                    refresh_proxy = True
                    if proxy_failures >= max_proxy_failures:
                        break
                    continue
                raise
            attempts = attempt_no
            if not is_valid(text):
                last_error = "captcha_text_invalid"
                self._logger.info(
                    "captcha_invalid: text=%s len=%s attempt=%s",
                    text,
                    len(text),
                    attempt_no,
                )
                continue
            payload = self._build_payload(code, text)
            try:
                resp = self._send_query(payload)
            except requests.RequestException as exc:
                if self._is_proxy_error(exc) and self._proxy_manager.enabled():
                    proxy_failures += 1
                    last_error = "proxy_error"
                    self._logger.warning("proxy_error: %s", exc)
                    self._reset_session()
                    self._proxy_manager.rotate("proxy_error")
                    refresh_proxy = True
                    if proxy_failures >= max_proxy_failures:
                        break
                    continue
                raise
            self._logger.info(
                "query_response: status=%s attempt=%s",
                resp.status_code,
                attempt_no,
            )
            if self._is_captcha_error(resp):
                last_error = "captcha_rejected"
                self._logger.info("captcha_rejected: attempt=%s", attempt_no)
                continue
            parsed = self._parse_response(resp)
            if isinstance(parsed.get("data"), dict):
                upstream_status = parsed["data"].get("status")
                upstream_msg = parsed["data"].get("msg")
                if upstream_status is not None or upstream_msg is not None:
                    self._logger.info(
                        "query_payload: status=%s msg=%s",
                        upstream_status,
                        upstream_msg,
                    )
                if self._matches_hint(upstream_msg, CAPTCHA_ERROR_HINTS):
                    last_error = "captcha_rejected"
                    self._logger.info("captcha_rejected: msg=%s attempt=%s", upstream_msg, attempt_no)
                    continue
                limit_hit = self._matches_hint(upstream_msg, PROXY_LIMIT_HINTS)
                if not limit_hit and PROXY_LIMIT_STATUSES:
                    try:
                        status_int = int(upstream_status)
                    except (TypeError, ValueError):
                        status_int = None
                    if status_int in PROXY_LIMIT_STATUSES:
                        limit_hit = True
                if PROXY_ROTATE_ON_LIMIT and limit_hit:
                    last_error = "limit_reached"
                    if PROXY_RELEASE_ON_LIMIT:
                        self._proxy_manager.release_current("limit_hint")
                    self._proxy_manager.rotate("limit_hint")
                    self._warmed = False
                    refresh_proxy = True
                    continue
            self._apply_mark_summary(parsed)
            return SpiderResult(
                ok=resp.ok,
                status_code=resp.status_code,
                captcha=text,
                attempts=attempts,
                data=parsed["data"],
                text=parsed["text"],
                error=None if resp.ok else "http_error",
            )
        return SpiderResult(
            ok=False,
            status_code=0,
            captcha=None,
            attempts=attempts,
            data=None,
            text=None,
            error=last_error or "captcha_failed",
        )
