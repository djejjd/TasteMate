from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


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
