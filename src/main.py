from contextlib import asynccontextmanager

from fastapi import FastAPI

from .core.logging import setup_logging
from .routes.query import router as query_router
from .services.spider import SpiderService

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.spider = SpiderService()
    yield
    app.state.spider.close()


app = FastAPI(title="captcha-spider", lifespan=lifespan)
app.include_router(query_router)
