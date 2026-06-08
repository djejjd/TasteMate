from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

WHITELISTED_FEATURES = {
    "local_first": "本地优先",
    "open_source": "开源优先",
    "cloud_required": "云依赖",
    "enterprise_oriented": "企业导向",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def make_evidence(
    *,
    query: str,
    candidate_id: str,
    feature: str,
    direction: str,
    strength: float,
    event_type: str,
) -> dict[str, Any]:
    return {
        "timestamp": now_iso(),
        "event_type": event_type,
        "query": query,
        "candidate_id": candidate_id,
        "feature": feature,
        "direction": direction,
        "strength": strength,
        "source": "explicit_user_feedback",
    }


def make_preference_entry(
    *,
    feature: str,
    strength: str,
    weight: float,
    confidence: float,
    evidence_count: int,
) -> dict[str, Any]:
    timestamp = now_iso()
    return {
        "feature": feature,
        "label": WHITELISTED_FEATURES.get(feature, feature),
        "weight": round(weight, 4),
        "confidence": round(confidence, 4),
        "strength": strength,
        "evidence_count": evidence_count,
        "source": "feedback",
        "last_updated": timestamp,
        "last_seen": timestamp,
    }
