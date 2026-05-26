from tastemate.core.ranker import Ranker
from tastemate.schemas.candidates import normalize_candidate


def test_normalize_candidate_generates_stable_id_from_title_and_url():
    raw = {
        "title": "Local Tool",
        "url": "https://example.com/local",
        "summary": "A local-first open source tool.",
    }

    candidate = normalize_candidate(raw)

    assert candidate["id"]
    assert candidate["title"] == "Local Tool"
    assert candidate["summary"] == "A local-first open source tool."
    assert candidate["url"] == "https://example.com/local"


def test_normalize_candidate_uses_url_as_title_fallback():
    raw = {
        "url": "https://example.com/only-url",
        "summary": "Only URL candidate.",
    }

    candidate = normalize_candidate(raw)

    assert candidate["title"] == "https://example.com/only-url"


def test_rank_candidates_passthrough_for_factual_question():
    result = Ranker(profile={}).rank(
        query="Hermes 的 MCP 配置文件在哪？",
        candidates=[
            {"id": "a", "title": "Hermes config", "summary": "The config path is ~/.hermes/config.yaml"}
        ],
        taste_mode="force",
    )

    assert result["ranking_needed"] is False
    assert result["mode"] == "factual"
    assert result["action"] == "passthrough"


def test_rank_candidates_passthrough_for_taste_factual_question():
    result = Ranker(profile={}).rank(
        query="@taste Hermes 的 MCP 配置文件在哪？",
        candidates=[
            {"id": "a", "title": "Hermes config", "summary": "The config path is ~/.hermes/config.yaml"}
        ],
        taste_mode="force",
    )

    assert result["ranking_needed"] is False
    assert result["mode"] == "factual"
    assert result["action"] == "passthrough"


def test_rank_candidates_needs_more_candidates_for_single_recommendation_candidate():
    result = Ranker(profile={}).rank(
        query="@taste 推荐几个适合我的本地知识库工具",
        candidates=[
            {"id": "a", "title": "Only Tool", "summary": "A local-first tool."}
        ],
        taste_mode="force",
    )

    assert result["ranking_needed"] is True
    assert result["mode"] == "recommendation"
    assert result["action"] == "needs_more_candidates"
    assert result["suggested_search_hints"]


def test_rank_candidates_ranked_schema_for_recommendation_candidates():
    result = Ranker(profile={}).rank(
        query="@taste 推荐几个适合我的本地知识库工具",
        candidates=[
            {
                "id": "local-open",
                "title": "Local Open Tool",
                "summary": "Open source local-first knowledge base.",
                "metadata": {"open_source": True, "local_first": True},
            },
            {
                "id": "cloud-enterprise",
                "title": "Cloud Enterprise Tool",
                "summary": "Enterprise SaaS knowledge base.",
                "metadata": {"cloud_required": True, "enterprise_oriented": True},
            },
        ],
        taste_mode="force",
    )

    assert result["ranking_needed"] is True
    assert result["mode"] == "recommendation"
    assert result["action"] == "ranked"
    assert result["ranked_candidates"][0]["id"] == "local-open"
    for candidate in result["ranked_candidates"]:
        assert 0.0 <= candidate["query_relevance"] <= 1.0
        assert 0.0 <= candidate["preference_fit"] <= 1.0
        assert 0.0 <= candidate["feedback_score"] <= 1.0
        assert 0.0 <= candidate["final_score"] <= 1.0
        assert candidate["reasons"]


def test_rank_candidates_low_confidence_schema_for_missing_summaries():
    result = Ranker(profile={}).rank(
        query="@taste 推荐几个适合我的本地知识库工具",
        candidates=[
            {"id": "a", "title": "A"},
            {"id": "b", "title": "B"},
        ],
        taste_mode="force",
    )

    assert result["ranking_needed"] is True
    assert result["mode"] == "recommendation"
    assert result["action"] == "low_confidence"
    assert result["ranked_candidates"] == []
    assert result["risks"]


def test_rank_candidates_feedback_score_uses_feature_evidence_for_new_candidates():
    profile = {
        "evidence_log": [
            {
                "candidate_id": "old-local",
                "feature": "local_first",
                "direction": "positive",
                "strength": 0.7,
            }
        ]
    }

    result = Ranker(profile=profile).rank(
        query="@taste 推荐几个适合我的本地知识库工具",
        candidates=[
            {
                "id": "new-local",
                "title": "New Local Tool",
                "summary": "Open source local-first knowledge base.",
                "metadata": {"local_first": True},
            },
            {
                "id": "cloud-tool",
                "title": "Cloud Tool",
                "summary": "Enterprise SaaS knowledge base.",
                "metadata": {"cloud_required": True},
            },
        ],
        taste_mode="force",
    )

    local = next(item for item in result["ranked_candidates"] if item["id"] == "new-local")
    cloud = next(item for item in result["ranked_candidates"] if item["id"] == "cloud-tool")
    assert local["feedback_score"] > cloud["feedback_score"]
    assert any("历史反馈" in reason for reason in local["reasons"])
