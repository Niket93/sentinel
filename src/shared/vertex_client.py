from __future__ import annotations

from vertexai import init as vertex_init
from ..config.settings import Settings


def init_vertex(cfg: Settings) -> None:
    vertex_init(project=cfg.gcp_project, location=cfg.gcp_region)