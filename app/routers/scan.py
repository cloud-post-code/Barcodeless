from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import ScanResponse
from app.services.embedding import embedding_service
from app.services.matching import matching_service

router = APIRouter(tags=["scan"])


@router.post("/scan", response_model=ScanResponse)
async def scan_image(
    image: UploadFile = File(...),
    top_k: int = 5,
    db: AsyncSession = Depends(get_db),
):
    """Upload an image to identify against the item database.

    Returns the top K matches ranked by confidence, using multi-embedding
    vector search with max-similarity re-ranking.
    """
    if not embedding_service.is_ready:
        raise HTTPException(status_code=503, detail="Model still loading")

    raw_bytes = await image.read()
    query_embedding = await embedding_service.generate_single_embedding(raw_bytes)
    return await matching_service.search(db, query_embedding, top_k=top_k)
