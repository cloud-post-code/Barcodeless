import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import init_db
from app.routers import items, scan
from app.schemas import HealthResponse
from app.services.embedding import embedding_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _log_clip_task_result(task: asyncio.Task) -> None:
    try:
        task.result()
    except asyncio.CancelledError:
        pass
    except Exception:
        logger.exception("Background CLIP load failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Barcodeless...")
    await init_db()
    logger.info("Database initialized.")
    clip_task = asyncio.create_task(embedding_service.initialize())
    clip_task.add_done_callback(_log_clip_task_result)
    logger.info("HTTP up; loading CLIP in background...")
    yield
    clip_task.cancel()
    try:
        await clip_task
    except asyncio.CancelledError:
        pass
    logger.info("Shutting down.")


app = FastAPI(
    title="Barcodeless",
    description="Image-based product identification without barcodes",
    version="1.0.0",
    lifespan=lifespan,
)

# Wildcard origins must not use allow_credentials=True (browser CORS rules).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(items.router)
app.include_router(scan.router)


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="healthy" if embedding_service.is_ready else "loading",
        model_loaded=embedding_service.is_ready,
    )

_frontend_dir = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if _frontend_dir.is_dir():
    app.mount("/", StaticFiles(directory=_frontend_dir, html=True), name="frontend")
