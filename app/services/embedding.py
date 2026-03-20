import asyncio
import logging

import numpy as np
import open_clip
import torch
from PIL import Image

from app.config import settings
from app.utils.image import get_image_variants, load_image

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self):
        self.model = None
        self.preprocess = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._ready = False

    async def initialize(self):
        logger.info(
            "Loading CLIP model %s (%s) on %s...",
            settings.clip_model,
            settings.clip_pretrained,
            self.device,
        )
        self.model, _, self.preprocess = await asyncio.to_thread(
            open_clip.create_model_and_transforms,
            settings.clip_model,
            pretrained=settings.clip_pretrained,
        )
        self.model.eval()
        self.model.to(self.device)
        self._ready = True
        logger.info("CLIP model loaded successfully.")

    @property
    def is_ready(self) -> bool:
        return self._ready

    @torch.no_grad()
    def _embed_image(self, image: Image.Image) -> np.ndarray:
        tensor = self.preprocess(image).unsqueeze(0).to(self.device)
        features = self.model.encode_image(tensor)
        features = features / features.norm(dim=-1, keepdim=True)
        return features.cpu().numpy().flatten().astype(np.float32)

    def _generate_multi(self, image_bytes: bytes) -> dict[str, list[float]]:
        image = load_image(image_bytes)
        variants = get_image_variants(image)
        return {
            name: self._embed_image(variant).tolist()
            for name, variant in variants.items()
        }

    def _generate_single(self, image_bytes: bytes) -> list[float]:
        image = load_image(image_bytes)
        return self._embed_image(image).tolist()

    async def generate_multi_embeddings(
        self, image_bytes: bytes
    ) -> dict[str, list[float]]:
        return await asyncio.to_thread(self._generate_multi, image_bytes)

    async def generate_single_embedding(self, image_bytes: bytes) -> list[float]:
        return await asyncio.to_thread(self._generate_single, image_bytes)


embedding_service = EmbeddingService()
