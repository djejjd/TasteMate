from __future__ import annotations

from typing import Any

from tastemate.schemas.feedback import WHITELISTED_FEATURES, make_evidence, make_preference_entry, now_iso


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
        feedback_type = self._classify_feedback(user_feedback, selected, rejected)
        if feedback_type == "invalid":
            return {
                "feedback_valid": False,
                "signal_strength": 0.0,
                "extracted_signals": [],
                "profile_updates": [],
                "accepted": False,
                "feedback_type": "invalid",
                "applied_features": [],
            }

        candidates_by_id = {str(item.get("id")): item for item in candidates_snapshot}
        is_strong_feedback = self._is_strong_feedback(user_feedback)
        extracted_signals: list[dict[str, Any]] = []
        profile_updates: list[dict[str, Any]] = []
        applied_features: list[str] = []
        evidence_log = self.profile.setdefault("evidence_log", [])

        for candidate_id in selected:
            candidate = candidates_by_id.get(candidate_id, {})
            features = self._extract_features(candidate)
            for feature in features:
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
            applied_features.extend(
                self._apply_feedback_update(features, direction="positive", is_strong=is_strong_feedback)
            )

        for candidate_id in rejected:
            candidate = candidates_by_id.get(candidate_id, {})
            features = self._extract_features(candidate)
            for feature in features:
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
            applied_features.extend(
                self._apply_feedback_update(features, direction="negative", is_strong=is_strong_feedback)
            )

        current_focus = self.profile.setdefault("current_focus", {})
        current_focus["last_query"] = query
        current_focus["last_feedback"] = user_feedback
        current_focus["last_seen"] = now_iso()

        if extracted_signals:
            profile_updates.append({"section": "evidence_log", "count": len(extracted_signals)})
        if applied_features:
            profile_updates.append({"section": "preferences", "features": sorted(set(applied_features))})

        return {
            "feedback_valid": True,
            "signal_strength": 0.7,
            "extracted_signals": extracted_signals,
            "profile_updates": profile_updates,
            "accepted": True,
            "feedback_type": feedback_type,
            "applied_features": sorted(set(applied_features)),
        }

    def _classify_feedback(self, user_feedback: str, selected: list[str], rejected: list[str]) -> str:
        text = user_feedback.strip().lower()
        if not text and not selected and not rejected:
            return "invalid"
        if self._is_strong_feedback(user_feedback):
            return "strong_negative" if rejected and not selected else "strong_positive"
        return "normal_negative" if rejected and not selected else "normal_positive"

    def _is_strong_feedback(self, user_feedback: str) -> bool:
        text = user_feedback.strip().lower()
        return any(marker in text for marker in ("明确", "以后优先", "不要", "拒绝", "must", "never"))

    def _extract_features(self, candidate: dict[str, Any]) -> list[str]:
        features = self._extract_whitelisted_features(candidate)
        if features:
            return features
        return ["general_preference"]

    def _extract_whitelisted_features(self, candidate: dict[str, Any]) -> list[str]:
        metadata = candidate.get("metadata")
        features: list[str] = []
        if isinstance(metadata, dict):
            for feature in WHITELISTED_FEATURES:
                if metadata.get(feature) is True:
                    features.append(feature)

        text = f"{candidate.get('title', '')} {candidate.get('summary', '')}".lower()
        if ("local" in text or "本地" in text) and "local_first" not in features:
            features.append("local_first")
        if ("open source" in text or "开源" in text) and "open_source" not in features:
            features.append("open_source")
        if ("cloud" in text or "saas" in text) and "cloud_required" not in features:
            features.append("cloud_required")
        if ("enterprise" in text or "企业" in text) and "enterprise_oriented" not in features:
            features.append("enterprise_oriented")
        return features

    def _apply_feedback_update(
        self,
        features: list[str],
        *,
        direction: str,
        is_strong: bool,
    ) -> list[str]:
        applied_features: list[str] = []
        if not is_strong:
            return applied_features

        for feature in features:
            if feature not in WHITELISTED_FEATURES:
                continue
            if direction == "positive":
                self._conservatively_update_existing_stable_preference(feature, 0.10)
                self._upsert_preference(
                    "stable_preferences",
                    feature,
                    strength="strong",
                    weight=0.35,
                    confidence=0.65,
                )
                applied_features.append(feature)
            elif direction == "negative":
                self._upsert_preference(
                    "negative_preferences",
                    feature,
                    strength="strong",
                    weight=0.35,
                    confidence=0.65,
                )
                applied_features.append(feature)
        return applied_features

    def _upsert_preference(
        self,
        section: str,
        feature: str,
        *,
        strength: str,
        weight: float,
        confidence: float,
        increment_evidence_count: bool = True,
    ) -> None:
        target = self.profile.setdefault(section, {})
        current = target.get(feature)
        evidence_count = 1
        if isinstance(current, dict):
            evidence_count = int(current.get("evidence_count", 0)) + (1 if increment_evidence_count else 0)
            target[feature] = {
                **current,
                "label": WHITELISTED_FEATURES.get(feature, feature),
                "strength": strength,
                "weight": round(max(float(current.get("weight", 0.0)), weight), 4),
                "confidence": round(max(float(current.get("confidence", 0.0)), confidence), 4),
                "evidence_count": evidence_count,
                "source": str(current.get("source") or "feedback"),
                "last_updated": now_iso(),
                "last_seen": now_iso(),
            }
        else:
            target[feature] = make_preference_entry(
                feature=feature,
                strength=strength,
                weight=weight,
                confidence=confidence,
                evidence_count=evidence_count,
            )

        current_focus = self.profile.setdefault("current_focus", {})
        current_focus[feature] = {
            "feature": feature,
            "label": WHITELISTED_FEATURES.get(feature, feature),
            "evidence_count": target[feature]["evidence_count"],
            "last_updated": now_iso(),
        }

    def _conservatively_update_existing_stable_preference(self, feature: str, delta: float) -> None:
        stable = self.profile.setdefault("stable_preferences", {})
        if feature not in stable:
            return
        current = stable[feature]
        old_weight = float(current.get("weight", 0.0))
        old_confidence = float(current.get("confidence", 0.0))
        current["weight"] = round(min(1.0, old_weight + min(delta, 0.10)), 4)
        current["confidence"] = round(min(0.70, old_confidence + 0.02), 4)
        current["last_seen"] = now_iso()
