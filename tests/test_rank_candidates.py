from tastemate.core.ranker import Ranker
from tastemate.schemas.candidates import normalize_candidate, validate_candidates


def test_validate_candidates_reports_missing_required_fields():
    result = validate_candidates(
        [
            {"title": "Missing id and metadata", "summary": "ok"},
            {"id": "b", "title": "Missing summary", "metadata": {}},
        ]
    )

    assert result["valid_candidates"] == []
    assert len(result["invalid_candidates"]) == 2
    assert result["invalid_candidates"][0]["missing_fields"] == ["id", "metadata"]
    assert result["invalid_candidates"][1]["missing_fields"] == ["summary"]


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


def test_normalize_candidate_uses_untitled_as_title_fallback():
    raw = {
        "url": "https://example.com/only-url",
        "summary": "Only URL candidate.",
    }

    candidate = normalize_candidate(raw)

    assert candidate["title"] == "Untitled candidate"


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
            {"id": "a", "title": "Only Tool", "summary": "A local-first tool.", "metadata": {}}
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
    assert result["action"] == "invalid_candidates"
    assert result["ranked_candidates"] == []
    assert result["invalid_candidates"]


def test_ranker_returns_passthrough_for_empty_candidates():
    result = Ranker(profile={}).rank(
        query="@taste 推荐几个适合我的本地知识库工具",
        candidates=[],
        taste_mode="force",
    )

    assert result["ranking_needed"] is False
    assert result["mode"] == "factual"
    assert result["action"] == "passthrough"


def test_ranker_returns_invalid_candidates_for_missing_metadata():
    result = Ranker(profile={}).rank(
        query="@taste 推荐几个适合我的本地知识库工具",
        candidates=[
            {"id": "a", "title": "A", "summary": "ok"},
            {"id": "b", "title": "B", "summary": "ok", "metadata": {}},
        ],
        taste_mode="force",
    )

    assert result["action"] == "invalid_candidates"
    assert result["invalid_candidates"][0]["missing_fields"] == ["metadata"]
    assert result["ranked_candidates"] == []


def test_ranker_returns_invalid_candidates_for_missing_summary():
    result = Ranker(profile={}).rank(
        query="@taste 推荐几个适合我的本地知识库工具",
        candidates=[
            {"id": "a", "title": "A", "metadata": {}},
            {"id": "b", "title": "B", "summary": "ok", "metadata": {}},
        ],
        taste_mode="force",
    )

    assert result["action"] == "invalid_candidates"
    assert result["invalid_candidates"][0]["missing_fields"] == ["summary"]


def test_ranker_returns_needs_more_candidates_for_single_valid_candidate():
    result = Ranker(profile={}).rank(
        query="@taste 推荐几个适合我的本地知识库工具",
        candidates=[
            {"id": "a", "title": "A", "summary": "ok", "metadata": {}},
        ],
        taste_mode="force",
    )

    assert result["action"] == "needs_more_candidates"
    assert result["ranking_needed"] is True


def test_ranker_returns_ranked_for_valid_candidates():
    result = Ranker(profile={}).rank(
        query="@taste 推荐几个适合我的本地知识库工具",
        candidates=[
            {"id": "local", "title": "Local Tool", "summary": "Open source local-first knowledge base.", "metadata": {"open_source": True, "local_first": True}},
            {"id": "cloud", "title": "Cloud Tool", "summary": "Enterprise SaaS knowledge base.", "metadata": {"cloud_required": True}},
        ],
        taste_mode="force",
    )

    assert result["action"] == "ranked"
    assert result["ranked_candidates"][0]["id"] == "local"
    assert "final_score" in result["ranked_candidates"][0]


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


def test_rank_candidates_reorders_fixed_sample_after_feedback():
    profile = {
        "stable_preferences": {
            "local_first": {
                "feature": "local_first",
                "label": "本地优先",
                "weight": 0.35,
                "confidence": 0.65,
                "strength": "strong",
                "evidence_count": 1,
                "source": "feedback",
                "last_updated": "2026-06-08T00:00:00+08:00",
            }
        },
        "negative_preferences": {
            "cloud_required": {
                "feature": "cloud_required",
                "label": "云依赖",
                "weight": 0.35,
                "confidence": 0.65,
                "strength": "strong",
                "evidence_count": 1,
                "source": "feedback",
                "last_updated": "2026-06-08T00:00:00+08:00",
            }
        },
        "current_focus": {},
        "evidence_log": [],
    }

    result = Ranker(profile=profile).rank(
        query="@taste 推荐几个适合我的本地知识库工具",
        candidates=[
            {
                "id": "cloud",
                "title": "Cloud Tool",
                "summary": "Enterprise SaaS knowledge base.",
                "metadata": {"cloud_required": True},
            },
            {
                "id": "local",
                "title": "Local Tool",
                "summary": "Open source local-first knowledge base.",
                "metadata": {"local_first": True, "open_source": True},
            },
        ],
        taste_mode="force",
    )

    assert result["action"] == "ranked"
    assert result["ranked_candidates"][0]["id"] == "local"
    assert any("长期正向偏好" in reason for reason in result["ranked_candidates"][0]["reasons"])


def test_rank_candidates_current_focus_cannot_flip_low_relevance_candidate():
    profile = {
        "stable_preferences": {},
        "negative_preferences": {},
        "current_focus": {
            "open_source": {
                "feature": "open_source",
                "label": "开源优先",
                "evidence_count": 1,
                "last_updated": "2026-06-08T00:00:00+08:00",
            }
        },
        "evidence_log": [],
    }

    result = Ranker(profile=profile).rank(
        query="@taste 推荐几个适合我的本地知识库工具",
        candidates=[
            {
                "id": "relevant",
                "title": "Relevant Local Tool",
                "summary": "Knowledge base local-first tool.",
                "metadata": {},
            },
            {
                "id": "low",
                "title": "Open Source SDK",
                "summary": "A generic open source developer SDK.",
                "metadata": {"open_source": True},
            },
        ],
        taste_mode="force",
    )

    assert result["ranked_candidates"][0]["id"] == "relevant"
