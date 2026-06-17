from tastemate.tools.get_profile import get_profile_tool
from tastemate.tools.record_preference_signal import record_preference_signal_tool


def test_record_preference_signal_candidate_feedback_persists_profile_update(tmp_path):
    profile_path = tmp_path / "profile.json"

    result = record_preference_signal_tool(
        signal_type="candidate_feedback",
        user_signal="我明确更喜欢 Logseq，以后优先。",
        source="tastemate_recommendation",
        query="@taste 推荐几个适合我的知识库工具",
        candidate_feedback={
            "selected_candidate_ids": ["logseq"],
            "rejected_candidate_ids": [],
            "candidates_snapshot": [
                {
                    "id": "logseq",
                    "title": "Logseq",
                    "summary": "Open source local-first knowledge base.",
                    "metadata": {"local_first": True, "open_source": True},
                }
            ],
        },
        profile_path=profile_path,
    )

    profile = get_profile_tool(profile_path=profile_path)
    assert result["accepted"] is True
    assert result["signal_type"] == "candidate_feedback"
    assert result["reason"] == "accepted_candidate_feedback"
    assert {"local_first", "open_source"}.issubset(set(result["applied_features"]))
    assert profile["evidence_summary"]["total_count"] == 2
    assert "local_first" in profile["stable_preferences"]


def test_record_preference_signal_interest_writes_current_focus_without_stable_promotion(tmp_path):
    profile_path = tmp_path / "profile.json"

    result = record_preference_signal_tool(
        signal_type="interest",
        user_signal="我最近更关注本地优先和开源工具。",
        source="normal_conversation",
        query="",
        interest={},
        profile_path=profile_path,
    )

    profile = get_profile_tool(profile_path=profile_path)
    assert result["accepted"] is True
    assert result["signal_type"] == "interest"
    assert result["reason"] == "accepted_interest"
    assert result["applied_features"] == ["local_first", "open_source"]
    assert "local_first" in profile["current_focus"]
    assert "open_source" in profile["current_focus"]
    assert profile["stable_preferences"] == {}
    assert profile["evidence_summary"]["total_count"] == 2


def test_record_preference_signal_unknown_type_does_not_write_profile(tmp_path):
    profile_path = tmp_path / "profile.json"

    result = record_preference_signal_tool(
        signal_type="future_type",
        user_signal="未来某种偏好信号",
        source="normal_conversation",
        profile_path=profile_path,
    )

    profile = get_profile_tool(profile_path=profile_path)
    assert result["accepted"] is False
    assert result["reason"] == "unsupported_signal_type"
    assert result["applied_features"] == []
    assert profile["evidence_summary"]["total_count"] == 0
    assert profile["stable_preferences"] == {}
    assert profile["current_focus"] == {}


def test_record_preference_signal_invalid_interest_does_not_write_profile(tmp_path):
    profile_path = tmp_path / "profile.json"

    result = record_preference_signal_tool(
        signal_type="interest",
        user_signal="今天下午开会。",
        source="normal_conversation",
        profile_path=profile_path,
    )

    profile = get_profile_tool(profile_path=profile_path)
    assert result["accepted"] is False
    assert result["reason"] == "missing_explicit_interest_signal"
    assert profile["evidence_summary"]["total_count"] == 0
    assert profile["current_focus"] == {}


def test_record_preference_signal_negative_interest_does_not_write_positive_current_focus(tmp_path):
    profile_path = tmp_path / "profile.json"

    result = record_preference_signal_tool(
        signal_type="interest",
        user_signal="以后不要推荐 SaaS 工具。",
        source="normal_conversation",
        profile_path=profile_path,
    )

    profile = get_profile_tool(profile_path=profile_path)
    assert result["accepted"] is False
    assert result["reason"] == "negative_interest_not_supported"
    assert profile["evidence_summary"]["total_count"] == 0
    assert profile["current_focus"] == {}
