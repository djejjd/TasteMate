from __future__ import annotations

from typing import Any

from tastemate.core.scoring import feedback_score, preference_fit, profile_adjustment, query_relevance
from tastemate.schemas.candidates import validate_candidates

FACTUAL_MARKERS = ("在哪", "是什么", "配置文件", "路径", "when", "where", "what is")
RECOMMENDATION_MARKERS = ("推荐", "适合我的", "几个", "compare", "recommend")


class Ranker:
    def __init__(self, profile: dict[str, Any]) -> None:
        self.profile = profile

    def rank(self, query: str, candidates: list[dict[str, Any]], taste_mode: str = "force") -> dict[str, Any]:
        if not candidates:
            return {
                "ranking_needed": False,
                "mode": "factual",
                "action": "passthrough",
                "reason": "确定性事实问题或没有可排序候选集合",
            }

        if self._is_factual(query):
            return {
                "ranking_needed": False,
                "mode": "factual",
                "action": "passthrough",
                "reason": "确定性事实问题或没有可排序候选集合",
            }

        validation = validate_candidates(candidates)
        if validation["invalid_candidates"]:
            return {
                "ranking_needed": True,
                "mode": "recommendation",
                "action": "invalid_candidates",
                "reason": "候选不满足最小协议",
                "valid_candidates": validation["valid_candidates"],
                "invalid_candidates": validation["invalid_candidates"],
                "ranked_candidates": [],
            }

        if len(validation["valid_candidates"]) < 2:
            return {
                "ranking_needed": True,
                "mode": "recommendation",
                "action": "needs_more_candidates",
                "reason": "候选数量不足或缺少关键方向",
                "suggested_search_hints": [
                    "local-first knowledge base open source",
                    "self-hosted note taking app",
                    "MCP compatible personal knowledge base",
                ],
            }

        ranked = [self._score_candidate(query, candidate) for candidate in validation["valid_candidates"]]
        ranked.sort(key=lambda item: item["final_score"], reverse=True)
        return {
            "ranking_needed": True,
            "mode": "recommendation",
            "action": "ranked",
            "ranked_candidates": ranked,
        }

    def _score_candidate(self, query: str, candidate: dict[str, Any]) -> dict[str, Any]:
        relevance, relevance_reasons, relevance_risks = query_relevance(query, candidate)
        fit, fit_reasons, fit_risks = preference_fit(candidate)
        history, history_reasons = feedback_score(candidate, self.profile)
        profile_delta, profile_reasons, profile_risks = profile_adjustment(candidate, self.profile)
        if relevance < 0.35:
            fit = min(fit, 0.35)
            profile_delta = min(profile_delta, 0.05)
        final = round(relevance * 0.55 + fit * 0.20 + history * 0.10 + profile_delta * 0.15, 4)
        return {
            "id": candidate["id"],
            "title": candidate["title"],
            "final_score": final,
            "query_relevance": relevance,
            "preference_fit": fit,
            "feedback_score": history,
            "reasons": relevance_reasons + fit_reasons + history_reasons + profile_reasons or ["候选满足基本排序条件"],
            "risks": relevance_risks + fit_risks + profile_risks,
        }

    def _is_factual(self, query: str) -> bool:
        query_lower = query.lower()
        return any(marker in query_lower for marker in FACTUAL_MARKERS) and not self._is_recommendation(query)

    def _is_recommendation(self, query: str) -> bool:
        query_lower = query.lower()
        return any(marker in query_lower for marker in RECOMMENDATION_MARKERS)
