from __future__ import annotations

from typing import Any

from tastemate.schemas.feedback import make_evidence, now_iso


class FeedbackProcessor:
    def __init__(self, profile: dict[str, Any]) -> None:
        self.profile = profile

    def record(
        self,
        *,
        query: str,
        user_feedback: str,
        selected_candidate_ids: list[str],
        rejected_candidate_ids: list[str],
        candidates_snapshot: list[dict[str, Any]],
    ) -> dict[str, Any]:
        selected = [str(item) for item in selected_candidate_ids]
        rejected = [str(item) for item in rejected_candidate_ids]
        feedback_valid = bool(user_feedback.strip()) and bool(selected or rejected)
        if not feedback_valid:
            return {
                "feedback_valid": False,
                "signal_strength": 0.0,
                "extracted_signals": [],
                "profile_updates": [],
            }

        candidates_by_id = {str(item.get("id")): item for item in candidates_snapshot}
        extracted_signals: list[dict[str, Any]] = []
        evidence_log = self.profile.setdefault("evidence_log", [])

        for candidate_id in selected:
            feature = self._extract_feature(candidates_by_id.get(candidate_id, {}), user_feedback)
            evidence = make_evidence(
                query=query,
                candidate_id=candidate_id,
                feature=feature,
                direction="positive",
                strength=0.7,
                event_type="selected",
            )
            evidence_log.append(evidence)
            extracted_signals.append({"feature": feature, "direction": "positive", "candidate_id": candidate_id})
            self._conservatively_update_existing_stable_preference(feature, 0.10)

        for candidate_id in rejected:
            feature = self._extract_feature(candidates_by_id.get(candidate_id, {}), user_feedback)
            evidence = make_evidence(
                query=query,
                candidate_id=candidate_id,
                feature=feature,
                direction="negative",
                strength=0.7,
                event_type="rejected",
            )
            evidence_log.append(evidence)
            extracted_signals.append({"feature": feature, "direction": "negative", "candidate_id": candidate_id})

        self.profile["current_focus"] = {
            "last_query": query,
            "last_feedback": user_feedback,
            "last_seen": now_iso(),
        }

        return {
            "feedback_valid": True,
            "signal_strength": 0.7,
            "extracted_signals": extracted_signals,
            "profile_updates": [{"section": "evidence_log", "count": len(extracted_signals)}],
        }

    def _extract_feature(self, candidate: dict[str, Any], user_feedback: str) -> str:
        text = f"{candidate.get('title', '')} {candidate.get('summary', '')} {user_feedback}".lower()
        if "local" in text or "本地" in text:
            return "local_first"
        if "open source" in text or "开源" in text:
            return "open_source"
        if "cloud" in text or "saas" in text:
            return "cloud_required"
        return "general_preference"

    def _conservatively_update_existing_stable_preference(self, feature: str, delta: float) -> None:
        stable = self.profile.setdefault("stable_preferences", {})
        if feature not in stable:
            return
        current = stable[feature]
        old_weight = float(current.get("weight", 0.0))
        old_confidence = float(current.get("confidence", 0.0))
        current["weight"] = round(min(1.0, old_weight + min(delta, 0.10)), 4)
        current["confidence"] = round(min(0.70, old_confidence + 0.02), 4)
        current["evidence_count"] = int(current.get("evidence_count", 0)) + 1
        current["last_seen"] = now_iso()
