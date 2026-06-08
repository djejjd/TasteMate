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
    assert len(profile["evidence_log"]) == 2
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
    assert updated["weight"] <= 0.6
    assert updated["confidence"] <= 0.7


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

    assert "local_first" in profile["stable_preferences"]
    assert "cloud_required" in profile["negative_preferences"]
