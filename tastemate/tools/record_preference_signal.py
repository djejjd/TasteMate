from __future__ import annotations

from pathlib import Path
from typing import Any

from tastemate.core.preference_signal import record_preference_signal
from tastemate.storage.json_store import JsonProfileStore
from tastemate.tools.rank_candidates import resolve_profile_path


def record_preference_signal_tool(
    *,
    signal_type: str,
    user_signal: str,
    source: str = "normal_conversation",
    query: str = "",
    candidate_feedback: dict[str, Any] | None = None,
    interest: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    profile_path: str | Path | None = None,
) -> dict[str, Any]:
    store = JsonProfileStore(resolve_profile_path(profile_path))
    profile = store.load()
    result = record_preference_signal(
        profile,
        signal_type=signal_type,
        user_signal=user_signal,
        source=source,
        query=query,
        candidate_feedback=candidate_feedback,
        interest=interest,
        context=context,
        metadata=metadata,
    )
    if result.get("accepted") is True:
        store.save(profile)
    return result
