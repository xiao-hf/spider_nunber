import json
import logging
import re
import time
from dataclasses import dataclass
from typing import Optional, Tuple
from urllib.parse import quote, urlparse

import requests

from .config import (
    PROXY_API_ACTIVE_URL,
    PROXY_API_HEADERS,
    PROXY_API_PARAMS,
    PROXY_API_RELEASE_URL,
    PROXY_API_REGEX,
    PROXY_API_TIMEOUT,
    PROXY_API_URL,
    PROXY_MODE,
    PROXY_PASSWORD,
    PROXY_SCHEME,
    PROXY_URL,
    PROXY_USERNAME,
    PROXY_ALWAYS_REFRESH,
    PROXY_REFRESH_BEFORE_SECONDS,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class ProxyPayload:
    server: str
    proxy_ip: Optional[str] = None
    task_id: Optional[str] = None
    deadline: Optional[str] = None


@dataclass
class ProxyInfo:
    endpoint: str
    url: str
    source: str
    fetched_at: float
    server: Optional[str] = None
    proxy_ip: Optional[str] = None
    task_id: Optional[str] = None
    cookie_key: Optional[str] = None
    expires_at: Optional[float] = None


class ProxyManager:
    def __init__(self) -> None:
        self._session = requests.Session()
        if PROXY_API_HEADERS:
            self._session.headers.update({str(k): str(v) for k, v in PROXY_API_HEADERS.items()})
        self._current: Optional[ProxyInfo] = None

    def enabled(self) -> bool:
        return PROXY_MODE in {"static", "api"}

    def get_proxy(self) -> Optional[ProxyInfo]:
        if PROXY_MODE == "static":
            raw = PROXY_URL.strip()
            if not raw:
                return None
            url = self._build_proxy_url(raw)
            endpoint = self._endpoint_key(url)
            fetched_at = time.time()
            return ProxyInfo(
                endpoint=endpoint,
                url=url,
                source="static",
                fetched_at=fetched_at,
                server=endpoint,
                cookie_key=endpoint,
            )
        if PROXY_MODE == "api":
            if self._current and self._should_refresh(self._current):
                self._current = None
            if self._current is None:
                self._current = self._fetch_from_api()
            return self._current
        return None

    def rotate(self, reason: str) -> Optional[ProxyInfo]:
        if PROXY_MODE != "api":
            return self.get_proxy()
        _LOGGER.info("proxy_rotate: reason=%s", reason)
        self._current = None
        return self.get_proxy()

    def release_current(self, reason: str) -> bool:
        if PROXY_MODE != "api" or not PROXY_API_RELEASE_URL:
            return False
        if not self._current:
            return False
        params = PROXY_API_PARAMS.copy() if PROXY_API_PARAMS else {}
        if self._current.task_id:
            params["task"] = self._current.task_id
        elif self._current.proxy_ip:
            params["ip"] = self._current.proxy_ip
        elif self._current.server:
            params["ip"] = self._current.server
        else:
            return False
        try:
            text, status = self._request_api(PROXY_API_RELEASE_URL, params=params)
        except requests.RequestException as exc:
            _LOGGER.warning("proxy_release_error: reason=%s err=%s", reason, exc)
            return False
        _LOGGER.info("proxy_release: reason=%s status=%s body=%s", reason, status, text)
        return True

    def _build_proxy_url(self, endpoint: str) -> str:
        if "://" in endpoint:
            url = endpoint
        else:
            url = f"{PROXY_SCHEME}://{endpoint}"
        if PROXY_USERNAME and PROXY_PASSWORD and "@" not in url:
            user = quote(PROXY_USERNAME, safe="")
            password = quote(PROXY_PASSWORD, safe="")
            scheme, rest = url.split("://", 1)
            url = f"{scheme}://{user}:{password}@{rest}"
        return url

    def _fetch_from_api(self) -> ProxyInfo:
        if not PROXY_API_URL:
            raise ValueError("proxy_api_url_missing")
        payload = self._fetch_payload(PROXY_API_URL, allow_active=True)
        url = self._build_proxy_url(payload.server)
        safe_endpoint = self._endpoint_key(url)
        fetched_at = time.time()
        cookie_key = self._cookie_key(payload, safe_endpoint, fetched_at)
        expires_at = self._parse_deadline(payload.deadline)
        _LOGGER.info("proxy_api: endpoint=%s", safe_endpoint)
        return ProxyInfo(
            endpoint=safe_endpoint,
            url=url,
            source="api",
            fetched_at=fetched_at,
            server=payload.server,
            proxy_ip=payload.proxy_ip,
            task_id=payload.task_id,
            cookie_key=cookie_key,
            expires_at=expires_at,
        )

    def _fetch_payload(self, url: str, allow_active: bool) -> ProxyPayload:
        text, status_code = self._request_api(url)
        payload, code, message = self._parse_endpoint(text)
        if payload:
            return payload
        if allow_active and code == "NO_AVAILABLE_CHANNEL" and PROXY_API_ACTIVE_URL:
            _LOGGER.info("proxy_api_active_fallback: code=%s", code)
            return self._fetch_payload(PROXY_API_ACTIVE_URL, allow_active=False)
        if code:
            raise ValueError(f"proxy_api_error:{code}:{message or ''}")
        if status_code >= 400:
            raise ValueError(f"proxy_api_http_error:{status_code}")
        raise ValueError("proxy_api_parse_failed")

    def _request_api(self, url: str, params: Optional[dict] = None) -> Tuple[str, int]:
        if params is None:
            params = PROXY_API_PARAMS or None
        resp = self._session.get(url, params=params, timeout=PROXY_API_TIMEOUT)
        text = resp.text
        if resp.status_code >= 400:
            _LOGGER.warning("proxy_api_http_error: status=%s body=%s", resp.status_code, text)
        return text, resp.status_code

    def _parse_endpoint(self, text: str) -> Tuple[Optional[ProxyPayload], Optional[str], Optional[str]]:
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict):
            code = str(payload.get("code", "")).strip()
            message = str(payload.get("message", "")).strip()
            if code and code != "SUCCESS":
                return None, code, message
            data = payload.get("data") or {}
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        server = item.get("server")
                        if server:
                            return ProxyPayload(
                                server=str(server),
                                proxy_ip=item.get("proxy_ip"),
                                task_id=item.get("task_id"),
                                deadline=item.get("deadline"),
                            ), code or None, message or None
                        ips = item.get("ips")
                        if isinstance(ips, list):
                            task_id = item.get("task_id")
                            for ip_item in ips:
                                if isinstance(ip_item, dict):
                                    server = ip_item.get("server")
                                    if server:
                                        return ProxyPayload(
                                            server=str(server),
                                            proxy_ip=ip_item.get("proxy_ip"),
                                            task_id=task_id or ip_item.get("task_id"),
                                            deadline=ip_item.get("deadline"),
                                        ), code or None, message or None
                return None, code or None, message or None
            if isinstance(data, dict):
                task_id = data.get("task_id")
                ips = data.get("ips") or []
                if isinstance(ips, list):
                    for item in ips:
                        if isinstance(item, dict):
                            server = item.get("server")
                            if server:
                                return ProxyPayload(
                                    server=str(server),
                                    proxy_ip=item.get("proxy_ip"),
                                    task_id=task_id,
                                    deadline=item.get("deadline"),
                                ), code or None, message or None
                tasks = data.get("tasks") or []
                if isinstance(tasks, list):
                    for task in tasks:
                        if not isinstance(task, dict):
                            continue
                        task_id = task.get("task_id") or task_id
                        ips = task.get("ips") or []
                        if not isinstance(ips, list):
                            continue
                        for item in ips:
                            if isinstance(item, dict):
                                server = item.get("server")
                                if server:
                                    return ProxyPayload(
                                        server=str(server),
                                        proxy_ip=item.get("proxy_ip"),
                                        task_id=task_id,
                                        deadline=item.get("deadline"),
                                    ), code or None, message or None
        match = re.search(PROXY_API_REGEX, text)
        if match:
            return ProxyPayload(server=match.group(0)), None, None
        return None, None, None

    @staticmethod
    def _endpoint_key(url: str) -> str:
        if "://" not in url:
            return url
        parsed = urlparse(url)
        if parsed.hostname and parsed.port:
            return f"{parsed.hostname}:{parsed.port}"
        if parsed.hostname:
            return parsed.hostname
        return url

    @staticmethod
    def _cookie_key(payload: ProxyPayload, endpoint: str, fetched_at: float) -> str:
        if payload.proxy_ip:
            if PROXY_ALWAYS_REFRESH:
                return f"{payload.proxy_ip}-{int(fetched_at)}"
            return str(payload.proxy_ip)
        if payload.task_id:
            if PROXY_ALWAYS_REFRESH:
                return f"{payload.task_id}-{int(fetched_at)}"
            return str(payload.task_id)
        return f"{endpoint}-{int(fetched_at)}"

    def _should_refresh(self, proxy_info: ProxyInfo) -> bool:
        if PROXY_ALWAYS_REFRESH:
            return True
        if proxy_info.expires_at is None:
            return False
        return time.time() >= proxy_info.expires_at - PROXY_REFRESH_BEFORE_SECONDS

    @staticmethod
    def _parse_deadline(deadline: Optional[str]) -> Optional[float]:
        if not deadline:
            return None
        try:
            struct_time = time.strptime(deadline, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None
        return time.mktime(struct_time)
