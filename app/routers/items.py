import logging
import uuid
from io import BytesIO

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from PIL import UnidentifiedImageError
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError, OperationalError, ProgrammingError, StatementError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only, selectinload

from app.config import settings
from app.database import get_db
from app.models import Item, ItemEmbedding, ItemImage
from app.schemas import ItemCreateResponse, ItemResponse
from app.services.dedup import dedup_service
from app.services.embedding import embedding_service
from app.utils.image import compress_image

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/items", tags=["items"])

_DB_ERR_TYPES = (OperationalError, ProgrammingError, StatementError, DBAPIError)


def _expose_exc(exc: BaseException) -> str | None:
    if not settings.expose_internal_errors:
        return None
    return str(exc)[:1200]


def _raise_from_image_error(exc: BaseException) -> None:
    msg = (
        _expose_exc(exc)
        or "Could not read this image. Use JPEG, PNG, or WebP, or try a smaller file."
    )
    raise HTTPException(status_code=400, detail=msg) from exc


def _raise_from_db_error(exc: BaseException, where: str) -> None:
    logger.exception("Database error in %s", where)
    base = (
        "Database error. Ensure PostgreSQL has CREATE EXTENSION vector, DATABASE_URL is "
        "correct, and TLS is enabled for managed hosts (see README)."
    )
    if extra := _expose_exc(exc):
        base = f"{base} Details: {extra}"
    raise HTTPException(status_code=503, detail=base) from exc


def _raise_unexpected(where: str, exc: BaseException) -> None:
    logger.exception("Unexpected error in %s", where)
    detail = _expose_exc(exc) or "Internal server error"
    raise HTTPException(status_code=500, detail=detail) from exc


def _item_response_selectinloads():
    """ItemResponse only needs image ids and embedding counts — never load pgvector blobs."""
    return (
        selectinload(Item.images),
        selectinload(Item.embeddings).load_only(
            ItemEmbedding.id,
            ItemEmbedding.item_id,
            ItemEmbedding.image_id,
            ItemEmbedding.embedding_type,
            ItemEmbedding.created_at,
        ),
    )


def _item_to_response(item: Item) -> ItemResponse:
    md = item.metadata_ or {}
    if not isinstance(md, dict):
        md = {}
    return ItemResponse(
        id=str(item.id),
        name=item.name,
        description=item.description,
        metadata=md,
        image_ids=[str(img.id) for img in item.images] if item.images else [],
        image_count=len(item.images) if item.images else 0,
        embedding_count=len(item.embeddings) if item.embeddings else 0,
        created_at=item.created_at,
    )


@router.post("", response_model=ItemCreateResponse, status_code=201)
async def create_item(
    name: str = Form(...),
    description: str = Form(None),
    image: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    if not embedding_service.is_ready:
        raise HTTPException(status_code=503, detail="Model still loading")

    try:
        raw_bytes = await image.read()
        if not raw_bytes:
            raise HTTPException(status_code=400, detail="Empty image upload")

        try:
            stored_bytes = compress_image(raw_bytes)
        except (UnidentifiedImageError, OSError, ValueError) as e:
            _raise_from_image_error(e)

        try:
            query_embedding = await embedding_service.generate_single_embedding(raw_bytes)
        except (UnidentifiedImageError, OSError, ValueError) as e:
            _raise_from_image_error(e)

        try:
            dup = await dedup_service.check_duplicate(db, query_embedding)
        except _DB_ERR_TYPES as e:
            _raise_from_db_error(e, "create_item (dedup)")

        if dup:
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "Duplicate item detected",
                    "existing_item_id": dup.existing_item_id,
                    "existing_item_name": dup.existing_item_name,
                    "similarity": dup.similarity,
                },
            )

        item = Item(name=name, description=description)
        db.add(item)
        try:
            await db.flush()
        except _DB_ERR_TYPES as e:
            _raise_from_db_error(e, "create_item (insert item)")

        item_image = ItemImage(item_id=item.id, image_data=stored_bytes)
        db.add(item_image)
        try:
            await db.flush()
        except _DB_ERR_TYPES as e:
            _raise_from_db_error(e, "create_item (insert image)")

        try:
            multi_embeddings = await embedding_service.generate_multi_embeddings(
                raw_bytes
            )
        except (UnidentifiedImageError, OSError, ValueError) as e:
            _raise_from_image_error(e)
        except MemoryError as e:
            logger.exception("Out of memory generating embeddings")
            raise HTTPException(
                status_code=503,
                detail="Server ran out of memory processing this image; try a smaller image.",
            ) from e
        except RuntimeError as e:
            err = str(e).lower()
            if "out of memory" in err or "mps backend out of memory" in err:
                raise HTTPException(
                    status_code=503,
                    detail="Model ran out of memory; try a smaller image.",
                ) from e
            _raise_unexpected("create_item (embeddings)", e)

        for emb_type, emb_vector in multi_embeddings.items():
            db.add(
                ItemEmbedding(
                    item_id=item.id,
                    image_id=item_image.id,
                    embedding_type=emb_type,
                    embedding=emb_vector,
                )
            )

        try:
            await db.flush()
        except _DB_ERR_TYPES as e:
            _raise_from_db_error(e, "create_item (insert embeddings)")

        result = await db.execute(
            select(Item)
            .options(*_item_response_selectinloads())
            .where(Item.id == item.id)
        )
        item = result.scalar_one()

        return ItemCreateResponse(item=_item_to_response(item))
    except HTTPException:
        raise
    except MemoryError as e:
        logger.exception("MemoryError in create_item")
        raise HTTPException(
            status_code=503,
            detail="Server out of memory; try a smaller image or upgrade instance RAM.",
        ) from e
    except Exception as e:
        _raise_unexpected("create_item", e)


@router.get("", response_model=list[ItemResponse])
async def list_items(
    skip: int = 0, limit: int = 50, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Item)
        .options(*_item_response_selectinloads())
        .order_by(Item.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    items = result.scalars().unique().all()
    return [_item_to_response(i) for i in items]


@router.get("/{item_id}", response_model=ItemResponse)
async def get_item(item_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Item)
        .options(*_item_response_selectinloads())
        .where(Item.id == item_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return _item_to_response(item)


@router.delete("/{item_id}", status_code=204)
async def delete_item(item_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Item).where(Item.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    await db.delete(item)


@router.post("/{item_id}/images", response_model=ItemResponse)
async def add_image(
    item_id: uuid.UUID,
    image: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Add another reference image to an existing item (boosts accuracy)."""
    if not embedding_service.is_ready:
        raise HTTPException(status_code=503, detail="Model still loading")

    try:
        result = await db.execute(select(Item).where(Item.id == item_id))
        item = result.scalar_one_or_none()
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")

        raw_bytes = await image.read()
        if not raw_bytes:
            raise HTTPException(status_code=400, detail="Empty image upload")
        try:
            stored_bytes = compress_image(raw_bytes)
        except (UnidentifiedImageError, OSError, ValueError) as e:
            _raise_from_image_error(e)

        item_image = ItemImage(item_id=item.id, image_data=stored_bytes)
        db.add(item_image)
        try:
            await db.flush()
        except _DB_ERR_TYPES as e:
            _raise_from_db_error(e, "add_image (insert image)")

        try:
            multi_embeddings = await embedding_service.generate_multi_embeddings(
                raw_bytes
            )
        except (UnidentifiedImageError, OSError, ValueError) as e:
            _raise_from_image_error(e)
        except MemoryError as e:
            raise HTTPException(
                status_code=503,
                detail="Server ran out of memory; try a smaller image.",
            ) from e
        except RuntimeError as e:
            if "out of memory" in str(e).lower():
                raise HTTPException(
                    status_code=503,
                    detail="Model ran out of memory; try a smaller image.",
                ) from e
            _raise_unexpected("add_image (embeddings)", e)

        for emb_type, emb_vector in multi_embeddings.items():
            db.add(
                ItemEmbedding(
                    item_id=item.id,
                    image_id=item_image.id,
                    embedding_type=emb_type,
                    embedding=emb_vector,
                )
            )

        try:
            await db.flush()
        except _DB_ERR_TYPES as e:
            _raise_from_db_error(e, "add_image (insert embeddings)")

        result = await db.execute(
            select(Item)
            .options(*_item_response_selectinloads())
            .where(Item.id == item.id)
        )
        item = result.scalar_one()
        return _item_to_response(item)
    except HTTPException:
        raise
    except Exception as e:
        _raise_unexpected("add_image", e)


@router.get("/{item_id}/images/{image_id}")
async def get_image(
    item_id: uuid.UUID, image_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(ItemImage).where(
            ItemImage.id == image_id, ItemImage.item_id == item_id
        )
    )
    img = result.scalar_one_or_none()
    if not img:
        raise HTTPException(status_code=404, detail="Image not found")
    return StreamingResponse(BytesIO(img.image_data), media_type="image/jpeg")
