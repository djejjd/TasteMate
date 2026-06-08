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
