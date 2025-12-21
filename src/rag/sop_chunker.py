from __future__ import annotations
from typing import Any, Dict, List


def sop_to_chunks(sop: Dict[str, Any]) -> List[Dict[str, Any]]:
    chunks = []
    base_meta = {
        "process_id": sop.get("process_id"),
        "station_id": sop.get("station_id"),
        "sku_id": sop.get("sku_id"),
        "sop_version": sop.get("sop_version"),
    }
    for step in sop.get("steps", []):
        text = (
            f"Process: {base_meta['process_id']}\n"
            f"Station: {base_meta['station_id']}\n"
            f"SKU: {base_meta['sku_id']}\n"
            f"SOP Version: {base_meta['sop_version']}\n"
            f"Step ID: {step.get('step_id')}\n"
            f"Order: {step.get('order_index')}\n"
            f"Action: {step.get('action')}\n"
            f"Expected tool: {step.get('expected_tool')}\n"
            f"Expected part: {step.get('expected_part')}\n"
            f"Description: {step.get('description')}\n"
        )
        chunks.append({
            "chunk_text": text,
            "metadata": {
                **base_meta,
                "step_id": step.get("step_id"),
                "order_index": step.get("order_index"),
                "expected_tool": step.get("expected_tool"),
                "expected_part": step.get("expected_part"),
            }
        })
    return chunks