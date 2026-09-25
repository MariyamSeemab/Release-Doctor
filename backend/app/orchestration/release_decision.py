"""Release decision logic — implements the 4-state system from Section 8."""
from __future__ import annotations

from typing import List

from app.agents.base import EvidenceFinding
from app.models import OverallStatus, Severity


def compute_release_decision(findings: List[EvidenceFinding]) -> OverallStatus:
    """
    BLOCKED — one or more verified critical release blockers.
    ATTENTION REQUIRED — no verified blocker, but high-impact risks.
    READY FOR RELEASE — no critical/high blockers, required checks satisfied.
    UNVERIFIED — important checks could not complete.
    """
    if not findings:
        return OverallStatus.READY_FOR_RELEASE

    has_unverified = any(f.confidence.value == "LOW" and f.severity.value in ("CRITICAL", "HIGH") for f in findings)
    has_critical = any(f.severity.value == "CRITICAL" and f.confidence.value != "LOW" for f in findings)
    has_high = any(f.severity.value == "HIGH" and f.confidence.value != "LOW" for f in findings)
    has_medium_or_low = any(f.severity.value in ("MEDIUM", "LOW") for f in findings)

    if has_critical:
        return OverallStatus.BLOCKED
    if has_unverified:
        return OverallStatus.UNVERIFIED
    if has_high:
        return OverallStatus.ATTENTION_REQUIRED
    if has_medium_or_low:
        return OverallStatus.ATTENTION_REQUIRED

    return OverallStatus.READY_FOR_RELEASE
