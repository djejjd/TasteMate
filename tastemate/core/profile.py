from __future__ import annotations

from typing import Any


def summarize_evidence(profile: dict[str, Any]) -> dict[str, int]:
    return {"total_count": len(profile.get("evidence_log", []))}


def _joined_labels(entries: dict[str, Any]) -> str:
    labels: list[str] = []
    for key, item in entries.items():
        if isinstance(item, dict):
            labels.append(str(item.get("label") or key))
        else:
            labels.append(str(key))
    return "、".join(labels) if labels else "无"


def summarize_profile(profile: dict[str, Any]) -> str:
    stable = profile.get("stable_preferences", {})
    negative = profile.get("negative_preferences", {})
    current = profile.get("current_focus", {})
    evidence_count = summarize_evidence(profile)["total_count"]
    stable_named = {k: v for k, v in stable.items() if k != "last_query" and k != "last_feedback" and k != "last_seen"}
    negative_named = {k: v for k, v in negative.items() if k != "last_query" and k != "last_feedback" and k != "last_seen"}
    current_named = {k: v for k, v in current.items() if k not in {"last_query", "last_feedback", "last_seen"}}
    if stable_named or negative_named:
        return (
            f"长期正向偏好：{_joined_labels(stable_named)}；"
            f"长期负向偏好：{_joined_labels(negative_named)}；"
            f"当前关注：{_joined_labels(current_named)}。"
        )
    if current_named:
        return f"当前关注：{_joined_labels(current_named)}。"
    if evidence_count:
        last_query = current.get("last_query", "未知问题")
        return f"已有 {evidence_count} 条反馈证据，最近关注：{last_query}。"
    return "当前暂无稳定偏好。"
