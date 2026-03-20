import uuid
from io import BytesIO

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Item, ItemEmbedding, ItemImage
from app.schemas import ItemCreateResponse, ItemResponse
from app.services.dedup import dedup_service
from app.services.embedding import embedding_service
from app.utils.image import compress_image

router = APIRouter(prefix="/items", tags=["items"])


def _item_to_response(item: Item) -> ItemResponse:
    return ItemResponse(
        id=str(item.id),
        name=item.name,
        description=item.description,
        metadata=item.metadata_ or {},
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

    raw_bytes = await image.read()
    stored_bytes = compress_image(raw_bytes)

    query_embedding = await embedding_service.generate_single_embedding(raw_bytes)

    dup = await dedup_service.check_duplicate(db, query_embedding)
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
    await db.flush()

    item_image = ItemImage(item_id=item.id, image_data=stored_bytes)
    db.add(item_image)
    await db.flush()

    multi_embeddings = await embedding_service.generate_multi_embeddings(raw_bytes)
    for emb_type, emb_vector in multi_embeddings.items():
        db.add(
            ItemEmbedding(
                item_id=item.id,
                image_id=item_image.id,
                embedding_type=emb_type,
                embedding=emb_vector,
            )
        )

    await db.flush()

    result = await db.execute(
        select(Item)
        .options(selectinload(Item.images), selectinload(Item.embeddings))
        .where(Item.id == item.id)
    )
    item = result.scalar_one()

    return ItemCreateResponse(item=_item_to_response(item))


@router.get("", response_model=list[ItemResponse])
async def list_items(
    skip: int = 0, limit: int = 50, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Item)
        .options(selectinload(Item.images), selectinload(Item.embeddings))
        .order_by(Item.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    items = result.scalars().all()
    return [_item_to_response(i) for i in items]


@router.get("/{item_id}", response_model=ItemResponse)
async def get_item(item_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Item)
        .options(selectinload(Item.images), selectinload(Item.embeddings))
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

    result = await db.execute(
        select(Item)
        .options(selectinload(Item.images), selectinload(Item.embeddings))
        .where(Item.id == item_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    raw_bytes = await image.read()
    stored_bytes = compress_image(raw_bytes)

    item_image = ItemImage(item_id=item.id, image_data=stored_bytes)
    db.add(item_image)
    await db.flush()

    multi_embeddings = await embedding_service.generate_multi_embeddings(raw_bytes)
    for emb_type, emb_vector in multi_embeddings.items():
        db.add(
            ItemEmbedding(
                item_id=item.id,
                image_id=item_image.id,
                embedding_type=emb_type,
                embedding=emb_vector,
            )
        )

    await db.flush()

    result = await db.execute(
        select(Item)
        .options(selectinload(Item.images), selectinload(Item.embeddings))
        .where(Item.id == item.id)
    )
    item = result.scalar_one()
    return _item_to_response(item)


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
