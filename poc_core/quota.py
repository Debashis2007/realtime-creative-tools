# Copyright (c) 2026 Debashis Bhattacharjee. All Rights Reserved.
# Unauthorized copying, modification, or distribution is prohibited.
# https://github.com/Debashis2007

"""Simple in-memory token bucket for RPM/TPM style quotas."""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class TokenBucket:
    capacity: float
    refill_per_sec: float
    tokens: float = field(init=False)
    updated_at: float = field(init=False)

    def __post_init__(self) -> None:
        self.tokens = self.capacity
        self.updated_at = time.monotonic()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self.updated_at
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_per_sec)
        self.updated_at = now

    def allow(self, cost: float = 1.0) -> bool:
        self._refill()
        if self.tokens >= cost:
            self.tokens -= cost
            return True
        return False

    def remaining(self) -> float:
        self._refill()
        return self.tokens
