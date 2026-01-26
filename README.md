# captcha-spider-service

A small FastAPI service that fetches a captcha image, runs local OCR, and submits a query request with cookies.

## Setup

1) Create a virtual environment and install deps:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

2) This project uses `ddddocr`, so no external OCR binary is required.

3) Copy `.env.example` to `.env` and confirm the endpoints, field names, and `EXTRA_HEADERS_JSON`.
   If the captcha URL expects a bare timestamp query (e.g. `captcha.html?{ts}`), set `CAPTCHA_REFRESH_PARAM_NAME` to an empty value.
   If the server returns a specific message for captcha errors, set `CAPTCHA_ERROR_HINT` to enable retries.

## Run

```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Or run:

```bash
python run.py
```

## API

- `GET /health`
- `GET /captcha?include_image=true`
- `GET /query?phone=15286610576`
- `POST /query` with JSON body:

```json
{
  "phone": "15286610576",
  "captcha": null
}
```

If `captcha` is omitted or null, the service will fetch and OCR a captcha before submitting the request.
