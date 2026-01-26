import base64
from typing import Optional

from fastapi import APIRouter, HTTPException, Request

from ..schemas.query import CaptchaResponse, QueryRequest, QueryResponse


router = APIRouter()


def _run_query(spider, code: str, captcha: Optional[str]) -> QueryResponse:
    result = spider.query(code, captcha=captcha)
    if not result.ok and result.status_code == 0:
        raise HTTPException(status_code=500, detail=result.error or "query_failed")
    return QueryResponse(**result.to_dict())


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/captcha", response_model=CaptchaResponse)
def captcha(request: Request, include_image: bool = False) -> CaptchaResponse:
    spider = request.app.state.spider
    result = spider.get_captcha()
    image_b64 = None
    if include_image:
        image_b64 = base64.b64encode(result.image_bytes).decode("ascii")
    return CaptchaResponse(text=result.text, image_base64=image_b64)


@router.get("/query", response_model=QueryResponse)
def query_get(
    request: Request,
    phone: Optional[str] = None,
    code: Optional[str] = None,
    captcha: Optional[str] = None,
) -> QueryResponse:
    spider = request.app.state.spider
    value = code or phone
    if not value:
        raise HTTPException(status_code=400, detail="code_or_phone_required")
    return _run_query(spider, value, captcha)


@router.post("/query", response_model=QueryResponse)
def query(request: Request, payload: QueryRequest) -> QueryResponse:
    spider = request.app.state.spider
    code = payload.code or payload.phone
    if not code:
        raise HTTPException(status_code=400, detail="code_or_phone_required")
    return _run_query(spider, code, payload.captcha)
