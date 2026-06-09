from __future__ import annotations

from pathlib import Path
from typing import Any

from tastemate.core.feedback import FeedbackProcessor
from tastemate.schemas.feedback import WHITELISTED_FEATURES
from tastemate.storage.json_store import JsonProfileStore
from tastemate.tools.rank_candidates import resolve_profile_path


def _build_profile_update_details(profile: dict[str, Any], result: dict[str, Any]) -> dict[str, list[str]]:
    applied = list(result.get("applied_features", []))
    extracted = [
        item.get("feature")
        for item in result.get("extracted_signals", [])
        if isinstance(item, dict) and item.get("feature") in WHITELISTED_FEATURES
    ]
    stable = sorted(feature for feature in applied if feature in profile.get("stable_preferences", {}))
    negative = sorted(feature for feature in applied if feature in profile.get("negative_preferences", {}))
    current = sorted({feature for feature in extracted if feature in profile.get("current_focus", {})})
    return {
        "stable_preferences": stable,
        "negative_preferences": negative,
        "current_focus": current,
    }


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
    result = FeedbackProcessor(profile).record(
        query=query,
        user_feedback=user_feedback,
        selected_candidate_ids=selected_candidate_ids,
        rejected_candidate_ids=rejected_candidate_ids,
        candidates_snapshot=candidates_snapshot,
    )
    store.save(profile)
    result["profile_update_details"] = _build_profile_update_details(profile, result)
    return result
