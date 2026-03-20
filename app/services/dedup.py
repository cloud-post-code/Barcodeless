import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.schemas import DuplicateInfo

logger = logging.getLogger(__name__)


def _vec_literal(embedding: list[float]) -> str:
    return "[" + ",".join(f"{x:.8f}" for x in embedding) + "]"


class DedupService:
    async def check_duplicate(
        self, db: AsyncSession, embedding: list[float]
    ) -> DuplicateInfo | None:
        """Check if a similar item already exists in the database.

        Returns match info if similarity exceeds the configured threshold.
        """
        vec = _vec_literal(embedding)

        result = await db.execute(
            text(
                """
                SELECT e.item_id, i.name,
                       1 - (e.embedding <=> :qvec::vector) AS similarity
                FROM item_embeddings e
                JOIN items i ON i.id = e.item_id
                ORDER BY e.embedding <=> :qvec::vector
                LIMIT 1
                """
            ),
            {"qvec": vec},
        )
        row = result.fetchone()

        if row and float(row.similarity) >= settings.duplicate_threshold:
            logger.info(
                "Duplicate detected: %.3f similarity to item %s (%s)",
                row.similarity,
                row.item_id,
                row.name,
            )
            return DuplicateInfo(
                existing_item_id=str(row.item_id),
                existing_item_name=row.name,
                similarity=round(float(row.similarity), 4),
            )
        return None


dedup_service = DedupService()
