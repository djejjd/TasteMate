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


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_feature_entry(feature: str, raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "feature": feature,
        "label": str(raw.get("label") or feature),
        "weight": round(_safe_float(raw.get("weight", 0.0)), 4),
        "confidence": round(_safe_float(raw.get("confidence", 0.0)), 4),
        "strength": str(raw.get("strength") or "normal"),
        "evidence_count": _safe_int(raw.get("evidence_count", 0)),
        "source": str(raw.get("source") or "feedback"),
        "last_updated": raw.get("last_updated", raw.get("last_seen")),
    }


def _normalize_feature_map(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {}

    normalized: dict[str, Any] = {}
    for feature, value in raw.items():
        if not isinstance(feature, str) or not isinstance(value, dict):
            continue
        normalized[feature] = _normalize_feature_entry(feature, value)
    return normalized


def normalize_profile(raw: dict[str, Any]) -> dict[str, Any]:
    profile = default_profile()
    if not isinstance(raw, dict):
        return profile

    profile["stable_preferences"] = _normalize_feature_map(raw.get("stable_preferences"))
    profile["negative_preferences"] = _normalize_feature_map(raw.get("negative_preferences"))

    current_focus = raw.get("current_focus")
    if isinstance(current_focus, dict):
        profile["current_focus"] = current_focus

    evidence_log = raw.get("evidence_log")
    if isinstance(evidence_log, list):
        profile["evidence_log"] = evidence_log
    return profile
