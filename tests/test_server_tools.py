from tastemate.tools.get_profile import get_profile_tool
from tastemate.tools.rank_candidates import rank_candidates_tool
from tastemate.tools.record_feedback import record_feedback_tool
from tastemate.tools.record_preference_signal import record_preference_signal_tool


def test_get_profile_tool_returns_summary(tmp_path):
    result = get_profile_tool(profile_path=tmp_path / "profile.json")

    assert result["stable_preferences"] == {}
    assert result["negative_preferences"] == {}
    assert result["current_focus"] == {}
    assert result["summary"] == "当前暂无稳定偏好。"


def test_get_profile_tool_returns_compatible_empty_shape(tmp_path):
    result = get_profile_tool(profile_path=tmp_path / "profile.json")

    assert result["stable_preferences"] == {}
    assert result["negative_preferences"] == {}
    assert result["current_focus"] == {}
    assert result["evidence_summary"]["total_count"] == 0
    assert result["summary"] == "当前暂无稳定偏好。"


def test_rank_candidates_tool_returns_ranked(tmp_path):
    result = rank_candidates_tool(
        query="@taste 推荐几个适合我的本地知识库工具",
        candidates=[
            {"id": "a", "title": "Local", "summary": "Open source local-first knowledge base.", "metadata": {}},
            {"id": "b", "title": "Cloud", "summary": "Enterprise SaaS knowledge base.", "metadata": {}},
        ],
        taste_mode="force",
        profile_path=tmp_path / "profile.json",
    )

    assert result["action"] == "ranked"


def test_record_feedback_tool_persists_evidence(tmp_path):
    profile_path = tmp_path / "profile.json"

    result = record_feedback_tool(
        query="@taste 推荐几个工具",
        user_feedback="我选 a",
        selected_candidate_ids=["a"],
        rejected_candidate_ids=[],
        candidates_snapshot=[{"id": "a", "title": "A", "summary": "local-first"}],
        profile_path=profile_path,
    )

    profile = get_profile_tool(profile_path=profile_path)
    assert result["feedback_valid"] is True
    assert profile["summary"] != "当前暂无稳定偏好。"


def test_record_preference_signal_tool_records_interest_without_stable_promotion(tmp_path):
    profile_path = tmp_path / "profile.json"

    result = record_preference_signal_tool(
        signal_type="interest",
        user_signal="我最近更关注本地优先和开源工具。",
        source="normal_conversation",
        profile_path=profile_path,
    )

    profile = get_profile_tool(profile_path=profile_path)
    assert result["accepted"] is True
    assert result["signal_type"] == "interest"
    assert result["applied_features"] == ["local_first", "open_source"]
    assert "local_first" in profile["current_focus"]
    assert "open_source" in profile["current_focus"]
    assert profile["stable_preferences"] == {}
    assert profile["evidence_summary"]["total_count"] == 2


def test_server_exports_mcp_app():
    from tastemate.server import mcp

    assert mcp.name == "tastemate"


def test_server_exports_unified_preference_signal_without_record_interest():
    from tastemate.server import mcp

    tool_names = list(mcp._tool_manager._tools)
    assert "record_preference_signal" in tool_names
    assert "record_feedback" in tool_names
    assert "record_interest" not in tool_names
    assert tool_names.index("record_preference_signal") < tool_names.index("record_feedback")
