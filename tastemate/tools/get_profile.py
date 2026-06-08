from __future__ import annotations

from pathlib import Path
from typing import Any

from tastemate.core.profile import summarize_evidence, summarize_profile
from tastemate.storage.json_store import JsonProfileStore
from tastemate.tools.rank_candidates import resolve_profile_path


def get_profile_tool(profile_path: str | Path | None = None) -> dict[str, Any]:
    profile = JsonProfileStore(resolve_profile_path(profile_path)).load()
    return {
        "stable_preferences": profile["stable_preferences"],
        "negative_preferences": profile["negative_preferences"],
        "current_focus": profile["current_focus"],
        "evidence_summary": summarize_evidence(profile),
        "summary": summarize_profile(profile),
    }
