from datetime import datetime

from pydantic import BaseModel


class ItemCreate(BaseModel):
    name: str
    description: str | None = None
    metadata: dict = {}


class ItemResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    metadata: dict = {}
    image_ids: list[str] = []
    image_count: int = 0
    embedding_count: int = 0
    created_at: datetime | None = None


class DuplicateInfo(BaseModel):
    existing_item_id: str
    existing_item_name: str
    similarity: float


class ItemCreateResponse(BaseModel):
    item: ItemResponse
    duplicate_warning: DuplicateInfo | None = None


class ScanResult(BaseModel):
    rank: int
    item_id: str
    name: str
    confidence: float
    description: str | None = None
    metadata: dict = {}


class ScanResponse(BaseModel):
    results: list[ScanResult]
    total_items_searched: int
    scan_time_ms: float


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    item_count: int | None = None
