from typing import Literal

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app.core.logging import setup_logging
from app.middleware.request_logger import RequestLoggerMiddleware

setup_logging()

app = FastAPI(title="ungji API", version="0.1.0")

app.add_middleware(RequestLoggerMiddleware)


class HealthResponse(BaseModel):
    status: Literal["ok"]


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")
