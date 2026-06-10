from tastemate.core.feedback import FeedbackProcessor


def test_record_feedback_writes_evidence():
    profile = {
        "stable_preferences": {},
        "negative_preferences": {},
        "current_focus": {},
        "evidence_log": [],
    }

    result = FeedbackProcessor(profile).record(
        query="@taste 推荐几个适合我的本地知识库工具",
        user_feedback="我选 local-open，不要 cloud-enterprise",
        selected_candidate_ids=["local-open"],
        rejected_candidate_ids=["cloud-enterprise"],
        candidates_snapshot=[
            {"id": "local-open", "title": "Local Open", "summary": "Open source local-first tool."},
            {"id": "cloud-enterprise", "title": "Cloud Enterprise", "summary": "Enterprise SaaS."},
        ],
    )

    assert result["feedback_valid"] is True
    assert result["signal_strength"] == 0.7
    assert result["extracted_signals"]
    assert len(profile["evidence_log"]) == 4
    assert profile["evidence_log"][0]["source"] == "explicit_user_feedback"


def test_record_feedback_does_not_create_stable_preference_from_single_event():
    profile = {
        "stable_preferences": {},
        "negative_preferences": {},
        "current_focus": {},
        "evidence_log": [],
    }

    FeedbackProcessor(profile).record(
        query="@taste 推荐几个工具",
        user_feedback="我喜欢本地优先",
        selected_candidate_ids=["a"],
        rejected_candidate_ids=[],
        candidates_snapshot=[{"id": "a", "title": "A", "summary": "local-first"}],
    )

    assert profile["stable_preferences"] == {}


def test_record_feedback_non_whitelisted_feature_only_writes_evidence():
    profile = {
        "stable_preferences": {},
        "negative_preferences": {},
        "current_focus": {},
        "evidence_log": [],
    }

    result = FeedbackProcessor(profile).record(
        query="@taste 推荐几个工具",
        user_feedback="我喜欢这个方向",
        selected_candidate_ids=["a"],
        rejected_candidate_ids=[],
        candidates_snapshot=[
            {"id": "a", "title": "A", "summary": "tool", "metadata": {"features": ["custom_signal"]}}
        ],
    )

    assert result["feedback_valid"] is True
    assert profile["stable_preferences"] == {}
    assert profile["negative_preferences"] == {}
    assert result["applied_features"] == []
    assert profile["evidence_log"][0]["feature"] == "general_preference"


def test_record_feedback_promotes_normal_signal_on_second_match():
    profile = {
        "stable_preferences": {},
        "negative_preferences": {},
        "current_focus": {},
        "evidence_log": [],
    }
    processor = FeedbackProcessor(profile)

    kwargs = dict(
        query="@taste 推荐几个知识库工具",
        user_feedback="我比较喜欢本地优先",
        selected_candidate_ids=["a"],
        rejected_candidate_ids=[],
        candidates_snapshot=[
            {"id": "a", "title": "A", "summary": "local-first", "metadata": {"local_first": True}}
        ],
    )

    first = processor.record(**kwargs)

    assert first["feedback_type"] == "normal_positive"
    assert "local_first" not in profile["stable_preferences"]

    second = processor.record(**kwargs)

    assert second["feedback_type"] == "normal_positive"
    assert profile["stable_preferences"]["local_first"]["evidence_count"] >= 2


def test_record_feedback_deduplicates_same_feature_across_metadata_shapes():
    profile = {
        "stable_preferences": {},
        "negative_preferences": {},
        "current_focus": {},
        "evidence_log": [],
    }

    result = FeedbackProcessor(profile).record(
        query="@taste 推荐几个工具",
        user_feedback="我比较喜欢本地优先",
        selected_candidate_ids=["a"],
        rejected_candidate_ids=[],
        candidates_snapshot=[
            {
                "id": "a",
                "title": "A",
                "summary": "tool",
                "metadata": {"features": ["local_first"], "local_first": True},
            }
        ],
    )

    assert result["feedback_type"] == "normal_positive"
    assert "local_first" not in profile["stable_preferences"]
    matches = [item for item in profile["evidence_log"] if item["feature"] == "local_first"]
    assert len(matches) == 1


def test_record_feedback_strong_update_respects_iteration003_thresholds():
    profile = {
        "stable_preferences": {
            "local_first": {
                "feature": "local_first",
                "label": "本地优先",
                "weight": 0.30,
                "confidence": 0.60,
                "strength": "normal",
                "evidence_count": 2,
                "source": "feedback",
                "last_updated": "2026-06-08T00:00:00+08:00",
            }
        },
        "negative_preferences": {},
        "current_focus": {},
        "evidence_log": [],
    }

    FeedbackProcessor(profile).record(
        query="@taste 推荐几个工具",
        user_feedback="我明确更喜欢本地优先，这个方向以后优先。",
        selected_candidate_ids=["a"],
        rejected_candidate_ids=[],
        candidates_snapshot=[
            {"id": "a", "title": "A", "summary": "local-first", "metadata": {"local_first": True}}
        ],
    )

    updated = profile["stable_preferences"]["local_first"]
    assert updated["weight"] <= 0.35
    assert updated["confidence"] <= 0.65


def test_record_feedback_limits_stable_preference_weight_delta_and_confidence():
    profile = {
        "stable_preferences": {
            "local_first": {
                "weight": 0.5,
                "confidence": 0.68,
                "evidence_count": 2,
                "last_seen": "2026-05-26T00:00:00+08:00",
            }
        },
        "negative_preferences": {},
        "current_focus": {},
        "evidence_log": [],
    }

    FeedbackProcessor(profile).record(
        query="@taste 推荐几个工具",
        user_feedback="我明确选择本地优先方案",
        selected_candidate_ids=["a"],
        rejected_candidate_ids=[],
        candidates_snapshot=[{"id": "a", "title": "A", "summary": "local-first"}],
    )

    updated = profile["stable_preferences"]["local_first"]
    assert updated["weight"] <= 0.35
    assert updated["confidence"] <= 0.65
    assert updated["weight"] - 0.5 <= 0.10
    assert updated["confidence"] - 0.68 <= 0.05


def test_record_feedback_single_update_delta_stays_within_iteration003_increment_limits():
    profile = {
        "stable_preferences": {
            "local_first": {
                "feature": "local_first",
                "label": "本地优先",
                "weight": 0.20,
                "confidence": 0.50,
                "strength": "normal",
                "evidence_count": 2,
                "source": "feedback",
                "last_updated": "2026-06-08T00:00:00+08:00",
            }
        },
        "negative_preferences": {},
        "current_focus": {},
        "evidence_log": [],
    }

    FeedbackProcessor(profile).record(
        query="@taste 推荐几个工具",
        user_feedback="我明确更喜欢本地优先，这个方向以后优先。",
        selected_candidate_ids=["a"],
        rejected_candidate_ids=[],
        candidates_snapshot=[
            {"id": "a", "title": "A", "summary": "local-first", "metadata": {"local_first": True}}
        ],
    )

    updated = profile["stable_preferences"]["local_first"]
    assert updated["weight"] - 0.20 <= 0.10
    assert round(updated["confidence"] - 0.50, 4) <= 0.05


def test_record_feedback_negative_update_delta_stays_within_iteration003_increment_limits():
    profile = {
        "stable_preferences": {},
        "negative_preferences": {
            "cloud_required": {
                "feature": "cloud_required",
                "label": "云依赖",
                "weight": 0.20,
                "confidence": 0.50,
                "strength": "normal",
                "evidence_count": 2,
                "source": "feedback",
                "last_updated": "2026-06-08T00:00:00+08:00",
            }
        },
        "current_focus": {},
        "evidence_log": [],
    }

    FeedbackProcessor(profile).record(
        query="@taste 推荐几个工具",
        user_feedback="我明确不要云依赖，这类以后拒绝。",
        selected_candidate_ids=[],
        rejected_candidate_ids=["a"],
        candidates_snapshot=[
            {"id": "a", "title": "A", "summary": "cloud tool", "metadata": {"cloud_required": True}}
        ],
    )

    updated = profile["negative_preferences"]["cloud_required"]
    assert updated["weight"] - 0.20 <= 0.10
    assert round(updated["confidence"] - 0.50, 4) <= 0.05


def test_record_feedback_strong_positive_promotes_whitelisted_feature_once():
    profile = {
        "stable_preferences": {},
        "negative_preferences": {},
        "current_focus": {},
        "evidence_log": [],
    }

    result = FeedbackProcessor(profile).record(
        query="@taste 推荐几个适合我的本地知识库工具",
        user_feedback="我明确更喜欢本地优先、开源的工具，这个方向以后优先。",
        selected_candidate_ids=["local-open"],
        rejected_candidate_ids=[],
        candidates_snapshot=[
            {
                "id": "local-open",
                "title": "Local Open",
                "summary": "Open source local-first tool.",
                "metadata": {"local_first": True, "open_source": True},
            }
        ],
    )

    assert result["feedback_valid"] is True
    assert result["feedback_type"] == "strong_positive"
    assert profile["stable_preferences"]["local_first"]["strength"] == "strong"
    assert profile["current_focus"]["local_first"]["evidence_count"] == 1


def test_record_feedback_invalid_does_not_write_evidence_or_profile():
    profile = {
        "stable_preferences": {},
        "negative_preferences": {},
        "current_focus": {},
        "evidence_log": [],
    }

    result = FeedbackProcessor(profile).record(
        query="@taste 推荐几个工具",
        user_feedback="",
        selected_candidate_ids=[],
        rejected_candidate_ids=[],
        candidates_snapshot=[],
    )

    assert result["feedback_valid"] is False
    assert result["feedback_type"] == "invalid"
    assert profile["evidence_log"] == []
    assert profile["stable_preferences"] == {}
    assert profile["negative_preferences"] == {}
    assert profile["current_focus"] == {}


def test_record_feedback_mixed_selection_and_rejection_split_positive_negative_updates():
    profile = {
        "stable_preferences": {},
        "negative_preferences": {},
        "current_focus": {},
        "evidence_log": [],
    }

    FeedbackProcessor(profile).record(
        query="@taste 推荐几个工具",
        user_feedback="我选 local-open，不要 cloud-enterprise",
        selected_candidate_ids=["local-open"],
        rejected_candidate_ids=["cloud-enterprise"],
        candidates_snapshot=[
            {
                "id": "local-open",
                "title": "Local Open",
                "summary": "Open source local-first tool.",
                "metadata": {"local_first": True, "open_source": True},
            },
            {
                "id": "cloud-enterprise",
                "title": "Cloud Enterprise",
                "summary": "Enterprise SaaS.",
                "metadata": {"cloud_required": True, "enterprise_oriented": True},
            },
        ],
    )

    assert sorted(profile["stable_preferences"].keys()) == ["local_first", "open_source"]
    assert sorted(profile["negative_preferences"].keys()) == ["cloud_required", "enterprise_oriented"]


def test_record_feedback_strong_positive_existing_stable_preference_counts_once():
    profile = {
        "stable_preferences": {
            "local_first": {
                "feature": "local_first",
                "label": "本地优先",
                "weight": 0.5,
                "confidence": 0.6,
                "strength": "strong",
                "evidence_count": 2,
                "source": "feedback",
                "last_updated": "2026-05-26T00:00:00+08:00",
                "last_seen": "2026-05-26T00:00:00+08:00",
            }
        },
        "negative_preferences": {},
        "current_focus": {},
        "evidence_log": [],
    }

    FeedbackProcessor(profile).record(
        query="@taste 推荐几个工具",
        user_feedback="我明确更喜欢本地优先，这个方向以后优先。",
        selected_candidate_ids=["a"],
        rejected_candidate_ids=[],
        candidates_snapshot=[
            {
                "id": "a",
                "title": "A",
                "summary": "local-first tool.",
                "metadata": {"local_first": True},
            }
        ],
    )

    assert profile["stable_preferences"]["local_first"]["evidence_count"] == 3


def test_record_feedback_strong_positive_multi_feature_keeps_evidence_signals_and_profile_consistent():
    profile = {
        "stable_preferences": {},
        "negative_preferences": {},
        "current_focus": {},
        "evidence_log": [],
    }

    result = FeedbackProcessor(profile).record(
        query="@taste 推荐几个适合我的本地知识库工具",
        user_feedback="我明确更喜欢本地优先、开源的工具，这个方向以后优先。",
        selected_candidate_ids=["local-open"],
        rejected_candidate_ids=[],
        candidates_snapshot=[
            {
                "id": "local-open",
                "title": "Local Open",
                "summary": "Open source local-first tool.",
                "metadata": {"local_first": True, "open_source": True},
            }
        ],
    )

    evidence_features = sorted(item["feature"] for item in profile["evidence_log"])
    extracted_features = sorted(item["feature"] for item in result["extracted_signals"])
    stable_features = sorted(profile["stable_preferences"].keys())

    assert evidence_features == ["local_first", "open_source"]
    assert extracted_features == ["local_first", "open_source"]
    assert stable_features == ["local_first", "open_source"]
    assert sorted(result["applied_features"]) == ["local_first", "open_source"]


def test_record_feedback_supports_metadata_features_array_for_whitelisted_promotion():
    profile = {
        "stable_preferences": {},
        "negative_preferences": {},
        "current_focus": {},
        "evidence_log": [],
    }

    result = FeedbackProcessor(profile).record(
        query="@taste 推荐几个工具",
        user_feedback="我明确更喜欢本地优先和开源，这个方向以后优先。",
        selected_candidate_ids=["a"],
        rejected_candidate_ids=[],
        candidates_snapshot=[
            {
                "id": "a",
                "title": "A",
                "summary": "tool",
                "metadata": {"features": ["local_first", "open_source"]},
            }
        ],
    )

    assert result["feedback_type"] == "strong_positive"
    assert sorted(result["applied_features"]) == ["local_first", "open_source"]
    assert sorted(profile["stable_preferences"].keys()) == ["local_first", "open_source"]


def test_record_feedback_strong_negative_promotes_negative_preferences():
    profile = {
        "stable_preferences": {},
        "negative_preferences": {},
        "current_focus": {},
        "evidence_log": [],
    }

    result = FeedbackProcessor(profile).record(
        query="@taste 推荐几个工具",
        user_feedback="我明确不要云端企业方案，以后拒绝这个方向。",
        selected_candidate_ids=[],
        rejected_candidate_ids=["cloud-enterprise"],
        candidates_snapshot=[
            {
                "id": "cloud-enterprise",
                "title": "Cloud Enterprise",
                "summary": "Enterprise SaaS.",
                "metadata": {"cloud_required": True, "enterprise_oriented": True},
            }
        ],
    )

    assert result["feedback_type"] == "strong_negative"
    assert sorted(profile["negative_preferences"].keys()) == ["cloud_required", "enterprise_oriented"]
    assert sorted(result["applied_features"]) == ["cloud_required", "enterprise_oriented"]
