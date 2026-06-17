from __future__ import annotations

from pathlib import Path
from typing import Any

from tastemate.core.preference_signal import record_preference_signal
from tastemate.storage.json_store import JsonProfileStore
from tastemate.tools.rank_candidates import resolve_profile_path


def record_feedback_tool(
    *,
    query: str,
    user_feedback: str,
    selected_candidate_ids: list[str],
    rejected_candidate_ids: list[str],
    candidates_snapshot: list[dict[str, Any]],
    profile_path: str | Path | None = None,
) -> dict[str, Any]:
    store = JsonProfileStore(resolve_profile_path(profile_path))
    profile = store.load()
    result = record_preference_signal(
        profile,
        signal_type="candidate_feedback",
        source="compat_record_feedback",
        query=query,
        user_signal=user_feedback,
        candidate_feedback={
            "selected_candidate_ids": selected_candidate_ids,
            "rejected_candidate_ids": rejected_candidate_ids,
            "candidates_snapshot": candidates_snapshot,
        },
    )
    result.setdefault("feedback_valid", bool(result.get("accepted")))
    result.setdefault("signal_strength", 0.0)
    result.setdefault("extracted_signals", [])
    result.setdefault("feedback_type", "invalid")
    if result.get("accepted") is True:
        store.save(profile)
    return result
