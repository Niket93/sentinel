from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from google.api_core.client_options import ClientOptions
from google.cloud import discoveryengine_v1 as discoveryengine

from ..config.settings import Settings


@dataclass(frozen=True)
class SearchAnswer:
    answer_text: str
    snippets: List[str]
    raw: Any

def _api_endpoint(location: str) -> Optional[str]:
    if location == "global":
        return None
    return f"{location}-discoveryengine.googleapis.com"


def _serving_config(project_id: str, location: str, engine_id: str) -> str:
    return (
        f"projects/{project_id}/locations/{location}/collections/default_collection/"
        f"engines/{engine_id}/servingConfigs/default_serving_config"
    )

def answer_query(cfg: Settings, query: str, session_id: str | None = None) -> SearchAnswer:
    client_options = (
        ClientOptions(api_endpoint=_api_endpoint(cfg.vertex_search_location))
        if _api_endpoint(cfg.vertex_search_location)
        else None
    )
    client = discoveryengine.ConversationalSearchServiceClient(client_options=client_options)
    request = discoveryengine.AnswerQueryRequest(
        serving_config=_serving_config(cfg.gcp_project, cfg.vertex_search_location, cfg.vertex_search_engine_id),
        query=discoveryengine.Query(text=query),
        session=session_id,
        answer_generation_spec=discoveryengine.AnswerQueryRequest.AnswerGenerationSpec(
            model_spec=discoveryengine.AnswerQueryRequest.AnswerGenerationSpec.ModelSpec(
                model_version="gemini-2.0-flash-001/answer_gen/v1",
            ),
            prompt_spec=discoveryengine.AnswerQueryRequest.AnswerGenerationSpec.PromptSpec(
                preamble=cfg.vertex_search_prompt_preamble or "Answer using the SOP sources.",
            ),
            include_citations=True,
            answer_language_code="en",
        ),
        user_pseudo_id="video-analytics",
    )
    resp = client.answer_query(request)
    answer_text = ""
    snippets: List[str] = []
    ans = getattr(resp, "answer", None)
    if ans:
        answer_text = getattr(ans, "answer_text", "") or ""
        citations = getattr(ans, "citations", None) or []
        for c in citations:
            srcs = getattr(c, "sources", None) or []
            for s in srcs:
                for field in ("snippet", "extractive_answer", "text"):
                    val = getattr(s, field, None)
                    if isinstance(val, str) and val.strip():
                        snippets.append(val.strip())
    seen = set()
    deduped = []
    for s in snippets:
        if s in seen:
            continue
        seen.add(s)
        deduped.append(s)
    return SearchAnswer(answer_text=answer_text.strip(), snippets=deduped, raw=resp)