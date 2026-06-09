from tastemate.tools.get_profile import get_profile_tool
from tastemate.tools.record_feedback import record_feedback_tool


def test_record_feedback_tool_returns_compatible_iteration003_payload(tmp_path):
    result = record_feedback_tool(
        query="@taste 推荐几个工具",
        user_feedback="我明确更喜欢本地优先。",
        selected_candidate_ids=["a"],
        rejected_candidate_ids=[],
        candidates_snapshot=[
            {"id": "a", "title": "A", "summary": "local-first", "metadata": {"local_first": True}}
        ],
        profile_path=tmp_path / "profile.json",
    )

    assert "feedback_valid" in result
    assert "signal_strength" in result
    assert "profile_updates" in result
    assert "feedback_type" in result
    assert "profile_update_details" in result
    assert result["feedback_valid"] is True
    assert result["feedback_type"] == "strong_positive"
    assert result["profile_update_details"] == {
        "stable_preferences": ["local_first"],
        "negative_preferences": [],
        "current_focus": ["local_first"],
    }


def test_get_profile_tool_returns_explained_profile(tmp_path):
    record_feedback_tool(
        query="@taste 推荐几个工具",
        user_feedback="我明确更喜欢本地优先。",
        selected_candidate_ids=["a"],
        rejected_candidate_ids=[],
        candidates_snapshot=[
            {"id": "a", "title": "A", "summary": "local-first", "metadata": {"local_first": True}}
        ],
        profile_path=tmp_path / "profile.json",
    )

    result = get_profile_tool(profile_path=tmp_path / "profile.json")

    assert "local_first" in result["stable_preferences"]
    assert result["stable_preferences"]["local_first"]["evidence_count"] >= 1
    assert result["evidence_summary"]["total_count"] >= 1
    assert "本地优先" in result["summary"]


def test_get_profile_tool_summarizes_current_focus_without_stable_preferences(tmp_path):
    record_feedback_tool(
        query="@taste 推荐几个工具",
        user_feedback="我比较喜欢开源工具。",
        selected_candidate_ids=["a"],
        rejected_candidate_ids=[],
        candidates_snapshot=[
            {
                "id": "a",
                "title": "A",
                "summary": "open source tool",
                "metadata": {"open_source": True},
            }
        ],
        profile_path=tmp_path / "profile.json",
    )

    result = get_profile_tool(profile_path=tmp_path / "profile.json")

    assert result["stable_preferences"] == {}
    assert "当前关注" in result["summary"]
    assert "开源优先" in result["summary"]


def test_record_feedback_tool_reports_current_focus_write_for_first_normal_feedback(tmp_path):
    result = record_feedback_tool(
        query="@taste 推荐几个工具",
        user_feedback="我比较喜欢开源工具。",
        selected_candidate_ids=["a"],
        rejected_candidate_ids=[],
        candidates_snapshot=[
            {
                "id": "a",
                "title": "A",
                "summary": "open source tool",
                "metadata": {"open_source": True},
            }
        ],
        profile_path=tmp_path / "profile.json",
    )

    assert result["feedback_type"] == "normal_positive"
    assert result["profile_update_details"]["stable_preferences"] == []
    assert result["profile_update_details"]["current_focus"] == ["open_source"]
