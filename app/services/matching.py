import logging
import time

from sqlalchemy import func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Item, ItemEmbedding
from app.schemas import ScanResponse, ScanResult

logger = logging.getLogger(__name__)


def _vec_literal(embedding: list[float]) -> str:
    return "[" + ",".join(f"{x:.8f}" for x in embedding) + "]"


class MatchingService:
    async def search(
        self, db: AsyncSession, query_embedding: list[float], top_k: int = 5
    ) -> ScanResponse:
        start = time.perf_counter()
        vec = _vec_literal(query_embedding)

        # Stage 1: Vector recall — top N embeddings by cosine similarity
        recall_result = await db.execute(
            text(
                """
                SELECT e.item_id,
                       1 - (e.embedding <=> :qvec::vector) AS similarity
                FROM item_embeddings e
                ORDER BY e.embedding <=> :qvec::vector
                LIMIT :topk
                """
            ),
            {"qvec": vec, "topk": settings.top_k_recall},
        )
        rows = recall_result.fetchall()

        # Stage 2: Re-rank — max similarity per item (best-view wins)
        item_best: dict[str, float] = {}
        for row in rows:
            item_id = str(row.item_id)
            sim = float(row.similarity)
            if item_id not in item_best or sim > item_best[item_id]:
                item_best[item_id] = sim

        ranked_ids = sorted(item_best, key=item_best.get, reverse=True)[:top_k]

        # Stage 3: Fetch item details
        results: list[ScanResult] = []
        for rank, item_id in enumerate(ranked_ids, start=1):
            item_row = await db.execute(
                text("SELECT id, name, description, metadata FROM items WHERE id = :id"),
                {"id": item_id},
            )
            item = item_row.fetchone()
            if item:
                results.append(
                    ScanResult(
                        rank=rank,
                        item_id=str(item.id),
                        name=item.name,
                        confidence=round(item_best[item_id] * 100, 2),
                        description=item.description,
                        metadata=item.metadata or {},
                    )
                )

        total_items = await db.execute(text("SELECT count(*) FROM items"))
        count = total_items.scalar() or 0
        elapsed_ms = (time.perf_counter() - start) * 1000

        return ScanResponse(
            results=results,
            total_items_searched=count,
            scan_time_ms=round(elapsed_ms, 2),
        )


matching_service = MatchingService()
