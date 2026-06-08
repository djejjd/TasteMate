from __future__ import annotations

from typing import Any


def clamp(value: float) -> float:
    return max(0.0, min(1.0, round(value, 4)))


def clamp_signed(value: float) -> float:
    return max(-1.0, min(1.0, round(value, 4)))


def query_relevance(query: str, candidate: dict[str, Any]) -> tuple[float, list[str], list[str]]:
    text = f"{candidate.get('title', '')} {candidate.get('summary', '')}".lower()
    query_lower = query.lower()
    score = 0.55
    reasons: list[str] = []
    risks: list[str] = []

    if not candidate.get("summary"):
        risks.append("候选缺少 summary，相关性置信度较低")
        score -= 0.25
    if "知识库" in query or "knowledge" in query_lower:
        if "knowledge" in text or "知识" in text or "note" in text:
            score += 0.25
            reasons.append("候选内容与知识库需求相关")
    if "推荐" in query or "@taste" in query:
        score += 0.1
    return clamp(score), reasons, risks


def preference_fit(candidate: dict[str, Any]) -> tuple[float, list[str], list[str]]:
    metadata = candidate.get("metadata") if isinstance(candidate.get("metadata"), dict) else {}
    text = f"{candidate.get('title', '')} {candidate.get('summary', '')}".lower()
    score = 0.5
    reasons: list[str] = []
    risks: list[str] = []

    if metadata.get("open_source") or "open source" in text or "开源" in text:
        score += 0.18
        reasons.append("符合开源偏好")
    if metadata.get("local_first") or "local-first" in text or "self-hosted" in text or "本地" in text:
        score += 0.22
        reasons.append("符合本地优先偏好")
    if metadata.get("supports_mcp") or "mcp" in text:
        score += 0.08
        reasons.append("具备外置集成友好信号")
    if metadata.get("cloud_required") or "cloud required" in text:
        score -= 0.18
        risks.append("存在云端依赖风险")
    if metadata.get("enterprise_oriented") or "enterprise" in text:
        score -= 0.12
        risks.append("存在企业化复杂度风险")
    return clamp(score), reasons, risks


def feedback_score(candidate: dict[str, Any], profile: dict[str, Any]) -> tuple[float, list[str]]:
    evidence_log = profile.get("evidence_log", []) if isinstance(profile, dict) else []
    features = candidate_features(candidate)
    score = 0.5
    reasons: list[str] = []

    for evidence in evidence_log:
        if not isinstance(evidence, dict):
            continue
        feature = evidence.get("feature")
        if feature not in features:
            continue
        strength = float(evidence.get("strength", 0.0))
        if evidence.get("direction") == "positive":
            score += min(strength, 1.0) * 0.15
            reasons.append(f"历史反馈对 {feature} 有正向信号")
        if evidence.get("direction") == "negative":
            score -= min(strength, 1.0) * 0.15
            reasons.append(f"历史反馈对 {feature} 有负向信号")
    return clamp(score), reasons


def profile_adjustment(candidate: dict[str, Any], profile: dict[str, Any]) -> tuple[float, list[str], list[str]]:
    features = candidate_features(candidate)
    score = 0.0
    reasons: list[str] = []
    risks: list[str] = []

    for feature, item in profile.get("stable_preferences", {}).items():
        if feature not in features or not isinstance(item, dict):
            continue
        score += min(float(item.get("weight", 0.0)), 0.35) * 0.30
        reasons.append(f"命中长期正向偏好: {feature}")

    for feature, item in profile.get("negative_preferences", {}).items():
        if feature not in features or not isinstance(item, dict):
            continue
        score -= min(float(item.get("weight", 0.0)), 0.35) * 0.30
        reasons.append(f"命中长期负向偏好: {feature}")

    for feature, item in profile.get("current_focus", {}).items():
        if feature not in features or not isinstance(item, dict):
            continue
        score += 0.05
        reasons.append(f"命中当前关注: {feature}")

    return clamp_signed(score), reasons, risks


def candidate_features(candidate: dict[str, Any]) -> set[str]:
    metadata = candidate.get("metadata") if isinstance(candidate.get("metadata"), dict) else {}
    text = f"{candidate.get('title', '')} {candidate.get('summary', '')}".lower()
    features: set[str] = set()
    if metadata.get("local_first") or "local-first" in text or "self-hosted" in text or "本地" in text:
        features.add("local_first")
    if metadata.get("open_source") or "open source" in text or "开源" in text:
        features.add("open_source")
    if metadata.get("supports_mcp") or "mcp" in text:
        features.add("supports_mcp")
    if metadata.get("cloud_required") or "cloud" in text or "saas" in text:
        features.add("cloud_required")
    if metadata.get("enterprise_oriented") or "enterprise" in text:
        features.add("enterprise_oriented")
    if not features:
        features.add("general_preference")
    return features
