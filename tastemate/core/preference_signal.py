from __future__ import annotations

import hashlib
from typing import Any

from tastemate.core.feedback import FeedbackProcessor
from tastemate.schemas.feedback import WHITELISTED_FEATURES, make_preference_entry, now_iso

POSITIVE_INTEREST_MARKERS = ("更关注", "更感兴趣", "偏好", "喜欢", "优先", "以后推荐", "以后优先")
NEGATIVE_INTEREST_MARKERS = ("不要", "排除", "拒绝", "不喜欢", "避免")


def build_profile_update_details(profile: dict[str, Any], result: dict[str, Any]) -> dict[str, list[str]]:
    applied = list(result.get("applied_features", []))
    extracted = [
        item.get("feature")
        for item in result.get("extracted_signals", [])
        if isinstance(item, dict) and item.get("feature") in WHITELISTED_FEATURES
    ]
    stable = sorted(feature for feature in applied if feature in profile.get("stable_preferences", {}))
    negative = sorted(feature for feature in applied if feature in profile.get("negative_preferences", {}))
    current = sorted({feature for feature in extracted + applied if feature in profile.get("current_focus", {})})
    return {
        "stable_preferences": stable,
        "negative_preferences": negative,
        "current_focus": current,
    }


def record_preference_signal(
    profile: dict[str, Any],
    *,
    signal_type: str,
    user_signal: str,
    source: str = "normal_conversation",
    query: str = "",
    candidate_feedback: dict[str, Any] | None = None,
    interest: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_type = (signal_type or "").strip()
    signal = user_signal.strip()
    if normalized_type == "candidate_feedback":
        return _record_candidate_feedback(
            profile,
            user_signal=signal,
            source=source,
            query=query,
            candidate_feedback=candidate_feedback or {},
        )
    if normalized_type == "interest":
        return _record_interest(
            profile,
            user_signal=signal,
            source=source,
            interest=interest or {},
        )
    return _reject(normalized_type, "unsupported_signal_type")


def _record_candidate_feedback(
    profile: dict[str, Any],
    *,
    user_signal: str,
    source: str,
    query: str,
    candidate_feedback: dict[str, Any],
) -> dict[str, Any]:
    selected = candidate_feedback.get("selected_candidate_ids")
    rejected = candidate_feedback.get("rejected_candidate_ids")
    snapshot = candidate_feedback.get("candidates_snapshot")
    if not query or not isinstance(selected, list) or not isinstance(rejected, list) or not isinstance(snapshot, list):
        return _reject("candidate_feedback", "invalid_candidate_feedback_payload")
    if not selected and not rejected:
        return _reject("candidate_feedback", "invalid_candidate_feedback_payload")

    result = FeedbackProcessor(profile).record(
        query=query,
        user_feedback=user_signal,
        selected_candidate_ids=selected,
        rejected_candidate_ids=rejected,
        candidates_snapshot=snapshot,
    )
    result["signal_type"] = "candidate_feedback"
    result["signal_id"] = _signal_id("candidate_feedback", source, query, user_signal)
    result["reason"] = "accepted_candidate_feedback" if result.get("accepted") else "invalid_candidate_feedback_payload"
    result["profile_update_details"] = build_profile_update_details(profile, result)
    return result


def _record_interest(
    profile: dict[str, Any],
    *,
    user_signal: str,
    source: str,
    interest: dict[str, Any],
) -> dict[str, Any]:
    direction = interest.get("direction") or _detect_interest_direction(user_signal)
    features = interest.get("features") or _extract_interest_features(user_signal)
    features = [feature for feature in features if feature in WHITELISTED_FEATURES]
    if not user_signal or direction is None or not features:
        return _reject("interest", "missing_explicit_interest_signal")
    if direction == "negative":
        return _reject("interest", "negative_interest_not_supported")

    evidence_log = profile.setdefault("evidence_log", [])
    current_focus = profile.setdefault("current_focus", {})
    timestamp = now_iso()
    for feature in features:
        evidence_log.append(
            {
                "timestamp": timestamp,
                "event_type": "interest_signal",
                "query": user_signal,
                "candidate_id": "__interest__",
                "feature": feature,
                "direction": direction,
                "strength": 0.45,
                "source": source,
            }
        )
        entry = make_preference_entry(
            feature=feature,
            strength="normal",
            weight=0.12,
            confidence=0.4,
            evidence_count=1,
        )
        entry["source"] = source
        entry["last_updated"] = timestamp
        entry["last_seen"] = timestamp
        current_focus[feature] = entry

    current_focus["last_feedback"] = user_signal
    current_focus["last_seen"] = timestamp
    applied = sorted(features)
    result = {
        "accepted": True,
        "signal_type": "interest",
        "signal_id": _signal_id("interest", source, "", user_signal),
        "applied_features": applied,
        "profile_updates": [
            {"section": "current_focus", "features": applied},
            {"section": "evidence_log", "count": len(applied)},
        ],
        "profile_update_details": {
            "stable_preferences": [],
            "negative_preferences": [],
            "current_focus": applied,
        },
        "reason": "accepted_interest",
    }
    return result


def _extract_interest_features(text: str) -> list[str]:
    normalized = text.lower()
    features: list[str] = []
    if ("本地" in normalized or "local" in normalized) and "local_first" not in features:
        features.append("local_first")
    if ("开源" in normalized or "open source" in normalized) and "open_source" not in features:
        features.append("open_source")
    if ("云依赖" in normalized or "纯云" in normalized or "saas" in normalized) and "cloud_required" not in features:
        features.append("cloud_required")
    if ("企业" in normalized or "销售导向" in normalized or "enterprise" in normalized) and "enterprise_oriented" not in features:
        features.append("enterprise_oriented")
    return features


def _detect_interest_direction(text: str) -> str | None:
    if any(marker in text for marker in NEGATIVE_INTEREST_MARKERS):
        return "negative"
    if any(marker in text for marker in POSITIVE_INTEREST_MARKERS):
        return "positive"
    return None


def _reject(signal_type: str, reason: str) -> dict[str, Any]:
    return {
        "accepted": False,
        "signal_type": signal_type,
        "signal_id": "",
        "applied_features": [],
        "profile_updates": [],
        "profile_update_details": {
            "stable_preferences": [],
            "negative_preferences": [],
            "current_focus": [],
        },
        "reason": reason,
    }


def _signal_id(signal_type: str, source: str, query: str, user_signal: str) -> str:
    raw = "\n".join([signal_type, source, query, user_signal])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
