# Copyright (c) 2026 Debashis Bhattacharjee. All Rights Reserved.
# Unauthorized copying, modification, or distribution is prohibited.
# https://github.com/Debashis2007

"""SSE helpers for streaming POCs."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional


def sse_event(event: str, data: Any, event_id: Optional[str] = None) -> Dict[str, str]:
    payload = data if isinstance(data, str) else json.dumps(data)
    item: Dict[str, str] = {"event": event, "data": payload}
    if event_id is not None:
        item["id"] = event_id
    return item


def format_sse(event: str, data: Any, event_id: Optional[str] = None) -> str:
    """Raw SSE string if not using sse-starlette EventSourceResponse."""
    payload = data if isinstance(data, str) else json.dumps(data)
    lines = []
    if event_id is not None:
        lines.append(f"id: {event_id}")
    lines.append(f"event: {event}")
    for line in payload.splitlines() or [payload]:
        lines.append(f"data: {line}")
    lines.append("")
    return "\n".join(lines) + "\n"
