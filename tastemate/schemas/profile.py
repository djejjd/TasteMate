from __future__ import annotations

from copy import deepcopy
from typing import Any

DEFAULT_PROFILE: dict[str, Any] = {
    "stable_preferences": {},
    "negative_preferences": {},
    "current_focus": {},
    "evidence_log": [],
}


def default_profile() -> dict[str, Any]:
    return deepcopy(DEFAULT_PROFILE)


def normalize_profile(raw: dict[str, Any]) -> dict[str, Any]:
    profile = default_profile()
    for key in profile:
        if key in raw and isinstance(raw[key], type(profile[key])):
            profile[key] = raw[key]
    return profile
