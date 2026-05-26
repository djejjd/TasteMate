from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from tastemate.core.ranker import Ranker
from tastemate.storage.json_store import JsonProfileStore

DEFAULT_PROFILE_PATH = "~/.tastemate/profile.json"


def resolve_profile_path(profile_path: str | Path | None = None) -> Path:
    return Path(profile_path or os.environ.get("TASTEMATE_PROFILE_PATH", DEFAULT_PROFILE_PATH)).expanduser()


def rank_candidates_tool(
    *,
    query: str,
    candidates: list[dict[str, Any]],
    taste_mode: str = "force",
    profile_path: str | Path | None = None,
) -> dict[str, Any]:
    profile = JsonProfileStore(resolve_profile_path(profile_path)).load()
    return Ranker(profile).rank(query=query, candidates=candidates, taste_mode=taste_mode)
