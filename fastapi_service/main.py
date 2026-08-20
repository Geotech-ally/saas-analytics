import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from routes.analytics import router as analytics_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("FastAPI Analytics Service starting up…")
    yield
    logger.info("FastAPI Analytics Service shutting down…")


PRODUCTION = os.getenv("ENV", "development") == "production"

app = FastAPI(
    title="Analytics Microservice",
    description="High-performance analytics: KPIs, trends, anomalies, insights.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None if PRODUCTION else "/docs",
    redoc_url=None if PRODUCTION else "/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3002", "http://127.0.0.1:3002"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Service-Key"],
)

app.include_router(analytics_router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal error occurred."},
    )


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "service": "analytics"}
