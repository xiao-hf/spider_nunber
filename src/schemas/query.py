from typing import Any, Dict, Optional

from pydantic import BaseModel


class QueryRequest(BaseModel):
    code: Optional[str] = None
    phone: Optional[str] = None
    captcha: Optional[str] = None


class QueryResponse(BaseModel):
    ok: bool
    status_code: int
    captcha: Optional[str] = None
    attempts: int
    data: Optional[Dict[str, Any]] = None
    text: Optional[str] = None
    error: Optional[str] = None


class CaptchaResponse(BaseModel):
    text: str
    image_base64: Optional[str] = None
