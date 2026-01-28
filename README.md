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
   If you use a proxy, set `PROXY_MODE` and the proxy settings in `.env`.

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

## Proxy (optional)

- `PROXY_MODE=static`: use `PROXY_URL` directly (can include `user:pass@host:port`).
- `PROXY_MODE=api`: use `PROXY_API_URL` to fetch `ip:port`, then apply `PROXY_USERNAME/PROXY_PASSWORD`.
- `PROXY_ROTATE_ON_LIMIT=true`: rotate when `PROXY_LIMIT_HINT` appears in the upstream `msg`.
- `PROXY_RELEASE_ON_LIMIT=true`: call `PROXY_API_RELEASE_URL` before rotating.

For QingGuo long-term proxies, the API usually returns a plain `ip:port` string. Put that API into `PROXY_API_URL`,
and set `PROXY_USERNAME/PROXY_PASSWORD` if your proxy uses account auth.
If the API returns JSON with `data.ips[].server`, it will be parsed automatically. You can also set
`PROXY_API_PARAMS_JSON` to append query params (for API auth), and `PROXY_API_ACTIVE_URL` to fall back to
the "query in-use IP" API when `NO_AVAILABLE_CHANNEL` is returned.
For QingGuo, set `PROXY_API_RELEASE_URL` to the "delete IP" endpoint so the service can release the current
IP when the daily limit message appears.
