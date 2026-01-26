from dataclasses import dataclass
import logging
from typing import Any, Dict, Optional

import requests

from ..core.captcha import fetch_captcha
from ..core.config import (
    CAPTCHA_ERROR_HINT,
    CAPTCHA_FIELD,
    CAPTCHA_MAX_TRIES,
    CODE_FIELD,
    EXTRA_FORM,
    INDEX_URL,
    QUERY_CONTENT_TYPE,
    QUERY_METHOD,
    QUERY_URL,
    REQUEST_TIMEOUT,
    VERIFY_SSL,
)
from ..core.http import create_session, save_cookies
from ..core.ocr import is_valid, read_captcha_text


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
        self.session = create_session()
        self._warmed = False
        self._logger = logging.getLogger(__name__)

    def close(self) -> None:
        save_cookies(self.session)
        self.session.close()

    def warm_up(self) -> None:
        if self._warmed:
            return
        self._logger.info("warm_up: url=%s", INDEX_URL)
        resp = self.session.get(INDEX_URL, timeout=REQUEST_TIMEOUT, verify=VERIFY_SSL)
        resp.raise_for_status()
        self._logger.info("warm_up: status=%s", resp.status_code)
        self._warmed = True
        save_cookies(self.session)

    def get_captcha(self) -> CaptchaResult:
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

    def query(self, code: str, captcha: Optional[str] = None) -> SpiderResult:
        self.warm_up()
        last_error: Optional[str] = None
        attempts = 0
        self._logger.info("query_start: code=%s", code)
        for attempts in range(1, CAPTCHA_MAX_TRIES + 1):
            if captcha:
                text = captcha
                captcha = None
                self._logger.info(
                    "captcha_manual: text=%s len=%s attempt=%s",
                    text,
                    len(text),
                    attempts,
                )
            else:
                cap = self.get_captcha()
                text = cap.text
            if not is_valid(text):
                last_error = "captcha_text_invalid"
                self._logger.info(
                    "captcha_invalid: text=%s len=%s attempt=%s",
                    text,
                    len(text),
                    attempts,
                )
                continue
            payload = self._build_payload(code, text)
            resp = self._send_query(payload)
            self._logger.info(
                "query_response: status=%s attempt=%s",
                resp.status_code,
                attempts,
            )
            if self._is_captcha_error(resp):
                last_error = "captcha_rejected"
                self._logger.info("captcha_rejected: attempt=%s", attempts)
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
