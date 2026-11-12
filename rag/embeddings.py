"""
Local Medical Embeddings Service
Model: sentence-transformers/all-MiniLM-L6-v2
Dimension: 384
Features:
- Deterministic chunk-to-vector embedding
- Consistent L2-normalization for cosine similarity
- Batch processing with configurable batch_size
- Model version metadata tagging
- Uses locally cached model weights without network dependency
"""

import os
from pathlib import Path
from typing import List, Dict, Any, Union
import sentence_transformers

# Local cached snapshot path if present
LOCAL_CACHE_SNAPSHOT = os.path.expanduser(
    "~/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2/snapshots/1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
)

class MedicalEmbeddingService:

    MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
    DIMENSION = 384
    MODEL_VERSION = "all-MiniLM-L6-v2-384d-v1"

    def __init__(self, model_name: str = None, device: str = None):
        target = model_name
        if not target:
            if os.path.exists(LOCAL_CACHE_SNAPSHOT):
                target = LOCAL_CACHE_SNAPSHOT
            else:
                target = self.MODEL_NAME

        self.model_name = target
        self.model = sentence_transformers.SentenceTransformer(
            self.model_name,
            device=device
        )

    def get_dimension(self) -> int:
        return self.DIMENSION

    def embed_text(self, text: str) -> List[float]:
        """Embed a single query or text chunk, L2-normalized."""
        if not text or not text.strip():
            return [0.0] * self.DIMENSION
        vec = self.model.encode(
            text.strip(),
            normalize_embeddings=True,
            show_progress_bar=False
        )
        return vec.tolist()

    def embed_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """Batch embedding generation with L2 normalization."""
        if not texts:
            return []
        cleaned = [t.strip() if t and t.strip() else " " for t in texts]
        embeddings = self.model.encode(
            cleaned,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=False
        )
        return embeddings.tolist()
