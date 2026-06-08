from __future__ import annotations

from typing import Any


def summarize_evidence(profile: dict[str, Any]) -> dict[str, int]:
    return {"total_count": len(profile.get("evidence_log", []))}


def summarize_profile(profile: dict[str, Any]) -> str:
    stable = profile.get("stable_preferences", {})
    current = profile.get("current_focus", {})
    evidence_count = summarize_evidence(profile)["total_count"]
    if stable:
        names = ", ".join(sorted(stable.keys()))
        return f"当前稳定偏好：{names}。"
    if evidence_count:
        last_query = current.get("last_query", "未知问题")
        return f"已有 {evidence_count} 条反馈证据，最近关注：{last_query}。"
    return "当前暂无稳定偏好。"
