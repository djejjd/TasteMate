from __future__ import annotations

from pathlib import Path
from typing import Any

from tastemate.core.feedback import FeedbackProcessor
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
    result = FeedbackProcessor(profile).record(
        query=query,
        user_feedback=user_feedback,
        selected_candidate_ids=selected_candidate_ids,
        rejected_candidate_ids=rejected_candidate_ids,
        candidates_snapshot=candidates_snapshot,
    )
    store.save(profile)
    return result
