"""Layered safety decision plane stub."""

from __future__ import annotations

from dataclasses import dataclass
import re


BLOCKLIST = re.compile(r"\b(hack.?the.?bank|build.?a.?bomb)\b", re.I)


@dataclass
class SafetyDecision:
    action: str  # allow | refuse | block
    reason_code: str
    layer: str


class SafetyPlane:
    def __init__(self, fail_closed: bool = True) -> None:
        self.fail_closed = fail_closed
        self.healthy = True

    def check_input(self, text: str) -> SafetyDecision:
        if not self.healthy:
            if self.fail_closed:
                return SafetyDecision("block", "safety_unavailable", "L0")
            return SafetyDecision("allow", "fail_open", "L0")
        if BLOCKLIST.search(text or ""):
            return SafetyDecision("block", "critical_policy", "L0")
        if "jailbreak" in (text or "").lower():
            return SafetyDecision("refuse", "jailbreak_pattern", "L1")
        return SafetyDecision("allow", "ok", "L1")

    def check_output(self, text: str) -> SafetyDecision:
        if BLOCKLIST.search(text or ""):
            return SafetyDecision("block", "output_policy", "L2")
        return SafetyDecision("allow", "ok", "L2")
