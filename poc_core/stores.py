# Copyright (c) 2026 Debashis Bhattacharjee. All Rights Reserved.
# Unauthorized copying, modification, or distribution is prohibited.
# https://github.com/Debashis2007

"""Tiny in-memory stores for POC demos."""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set


class InMemoryStore:
    def __init__(self) -> None:
        self._data: Dict[str, Any] = {}

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def delete(self, key: str) -> None:
        self._data.pop(key, None)

    def keys(self, prefix: str = "") -> List[str]:
        return [k for k in self._data if k.startswith(prefix)]


def _embed(text: str, dim: int = 16) -> List[float]:
    """Deterministic fake embedding from token hashes."""
    toks = re.findall(r"[a-z0-9]+", text.lower()) or ["empty"]
    vec = [0.0] * dim
    for t in toks:
        h = int(hashlib.md5(t.encode()).hexdigest(), 16)
        vec[h % dim] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def _cos(a: List[float], b: List[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    text: str
    acl: Set[str]
    embedding: List[float] = field(default_factory=list)


class MockVectorIndex:
    def __init__(self) -> None:
        self.chunks: List[Chunk] = []

    def upsert(
        self, chunk_id: str, doc_id: str, text: str, acl: Optional[Set[str]] = None
    ) -> Chunk:
        ch = Chunk(
            chunk_id=chunk_id,
            doc_id=doc_id,
            text=text,
            acl=acl or {"public"},
            embedding=_embed(text),
        )
        self.chunks = [c for c in self.chunks if c.chunk_id != chunk_id]
        self.chunks.append(ch)
        return ch

    def search(self, query: str, user_acl: Set[str], top_k: int = 3) -> List[dict]:
        q = _embed(query)
        scored = []
        for c in self.chunks:
            if not (c.acl & user_acl) and "admin" not in user_acl:
                continue
            scored.append(
                {
                    "chunk_id": c.chunk_id,
                    "doc_id": c.doc_id,
                    "text": c.text,
                    "score": round(_cos(q, c.embedding), 4),
                    "acl": sorted(c.acl),
                }
            )
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]
