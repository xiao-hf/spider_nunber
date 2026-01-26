import io
import logging
import re
from typing import Optional

import ddddocr
from PIL import Image, ImageChops, ImageFilter, ImageSequence

from .config import CAPTCHA_CASE, CAPTCHA_LEN, CAPTCHA_REGEX, OCR_THRESHOLD, OCR_WHITELIST

_LOGGER = logging.getLogger(__name__)
_OCR: Optional[ddddocr.DdddOcr] = None


def _get_ocr() -> ddddocr.DdddOcr:
    global _OCR
    if _OCR is None:
        ocr = ddddocr.DdddOcr(show_ad=False)
        if OCR_WHITELIST:
            ocr.set_ranges(OCR_WHITELIST)
        _OCR = ocr
    return _OCR


def _to_bytes(img: Image.Image) -> bytes:
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def _prepare_image(img: Image.Image, threshold: Optional[int]) -> Image.Image:
    img = img.convert("L")
    img = img.filter(ImageFilter.MedianFilter(size=3))
    if threshold is not None and threshold >= 0:
        img = img.point(lambda x: 255 if x > threshold else 0)
    return img


def preprocess(image_bytes: bytes, threshold: Optional[int]) -> bytes:
    img = Image.open(io.BytesIO(image_bytes))
    img = _prepare_image(img, threshold)
    return _to_bytes(img)


def normalize_text(text: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]", "", text)
    if CAPTCHA_CASE == "lower":
        cleaned = cleaned.lower()
    elif CAPTCHA_CASE == "upper":
        cleaned = cleaned.upper()
    if OCR_WHITELIST:
        allowed = set(OCR_WHITELIST)
        cleaned = "".join(ch for ch in cleaned if ch in allowed)
    return cleaned


def is_valid(text: str) -> bool:
    if CAPTCHA_LEN > 0 and len(text) != CAPTCHA_LEN:
        return False
    if CAPTCHA_REGEX:
        return re.fullmatch(CAPTCHA_REGEX, text) is not None
    return True


def _classify(image_bytes: bytes) -> str:
    ocr = _get_ocr()
    return normalize_text(ocr.classification(image_bytes))


def _extract_variants(image_bytes: bytes) -> list[bytes]:
    img = Image.open(io.BytesIO(image_bytes))
    variants: list[bytes] = []
    if getattr(img, "is_animated", False) and getattr(img, "n_frames", 1) > 1:
        frames = []
        for frame in ImageSequence.Iterator(img):
            frames.append(_prepare_image(frame.copy(), None))
        if not frames:
            return variants
        _LOGGER.info("ocr_frames: %s", len(frames))
        darker = frames[0]
        lighter = frames[0]
        for frame in frames[1:]:
            darker = ImageChops.darker(darker, frame)
            lighter = ImageChops.lighter(lighter, frame)
        variants.append(_to_bytes(frames[0]))
        variants.append(_to_bytes(darker))
        variants.append(_to_bytes(lighter))
        if OCR_THRESHOLD >= 0:
            variants.append(_to_bytes(_prepare_image(frames[0].copy(), OCR_THRESHOLD)))
            variants.append(_to_bytes(_prepare_image(darker.copy(), OCR_THRESHOLD)))
            variants.append(_to_bytes(_prepare_image(lighter.copy(), OCR_THRESHOLD)))
        return variants

    variants.append(preprocess(image_bytes, None))
    if OCR_THRESHOLD >= 0:
        variants.append(preprocess(image_bytes, OCR_THRESHOLD))
    return variants


def read_captcha_text(image_bytes: bytes) -> str:
    candidates = []
    candidates.append(_classify(image_bytes))
    for variant in _extract_variants(image_bytes):
        candidates.append(_classify(variant))

    seen = set()
    ordered = []
    for text in candidates:
        if text in seen:
            continue
        seen.add(text)
        ordered.append(text)

    for text in ordered:
        if text and is_valid(text):
            _LOGGER.info("ocr_candidates: %s", ordered)
            return text

    if ordered:
        _LOGGER.info("ocr_candidates: %s", ordered)
        return max(ordered, key=len)
    return ""
