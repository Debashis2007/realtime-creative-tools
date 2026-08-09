# Copyright (c) 2026 Debashis Bhattacharjee. All Rights Reserved.
# Unauthorized copying, modification, or distribution is prohibited.
# https://github.com/Debashis2007

"""Standard /health payload helper."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional


def health_payload(use_case: str, extra: Optional[Dict[str, Any]] = None) -> dict:
    body = {
        "status": "ok",
        "use_case": use_case,
        "ts": datetime.now(timezone.utc).isoformat(),
        "self_contained": True,
    }
    if extra:
        body.update(extra)
    return body
