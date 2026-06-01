from tastemate.tools.get_profile import get_profile_tool
from tastemate.tools.rank_candidates import rank_candidates_tool
from tastemate.tools.record_feedback import record_feedback_tool


def test_get_profile_tool_returns_summary(tmp_path):
    result = get_profile_tool(profile_path=tmp_path / "profile.json")

    assert result["stable_preferences"] == {}
    assert result["negative_preferences"] == {}
    assert result["current_focus"] == {}
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


def test_server_exports_mcp_app():
    from tastemate.server import mcp

    assert mcp.name == "tastemate"
