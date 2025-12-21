from __future__ import annotations
from typing import List
from vertexai.preview.language_models import TextEmbeddingModel
from ..shared.vertex_client import init_vertex
from ..config.settings import Settings


class VertexEmbedder:
    def __init__(self, cfg: Settings):
        init_vertex(cfg)
        self.cfg = cfg
        self.model = TextEmbeddingModel.from_pretrained(cfg.vertex_embed_model)

    def embed(self, texts: List[str]) -> List[List[float]]:
        embs = self.model.get_embeddings(texts)
        return [e.values for e in embs]