from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


PLUGIN_PATH = Path("integrations/hermes/plugins/tastemate-route/__init__.py")


class FakeContext:
    def __init__(self, dispatch_result=None, dispatch_results=None):
        self.hooks = {}
        self.dispatch_calls = []
        self.dispatch_result = dispatch_result
        self.dispatch_results = dispatch_results or {}

    def register_hook(self, name, callback):
        self.hooks[name] = callback

    def dispatch_tool(self, tool_name, args):
        self.dispatch_calls.append((tool_name, args))
        if tool_name in self.dispatch_results:
            result = self.dispatch_results[tool_name]
            if isinstance(result, Exception):
                raise result
            return result
        if self.dispatch_result is not None:
            return self.dispatch_result
        return (
            '{"structuredContent": {'
            '"ranking_needed": true, '
            '"mode": "recommendation", '
            '"action": "ranked", '
            '"ranked_candidates": ['
            '{"id": "local", "title": "Local-first KB", "final_score": 0.864, '
            '"reasons": ["候选内容与知识库需求相关", "符合本地优先偏好"]}'
            ']}}'
        )


class FakeEvent:
    def __init__(self, text):
        self.text = text


class RaisingContext(FakeContext):
    def dispatch_tool(self, tool_name, args):
        self.dispatch_calls.append((tool_name, args))
        raise RuntimeError("boom")


def load_plugin():
    spec = importlib.util.spec_from_file_location("tastemate_route_plugin", PLUGIN_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_registers_pre_gateway_dispatch_hook():
    module = load_plugin()
    ctx = FakeContext()

    module.register(ctx)

    assert "pre_gateway_dispatch" in ctx.hooks


def test_plain_message_allows_without_dispatch():
    module = load_plugin()
    ctx = FakeContext()
    module.register(ctx)

    result = ctx.hooks["pre_gateway_dispatch"](event=FakeEvent("Hermes 的配置在哪？"))

    assert result == {"action": "allow"}
    assert ctx.dispatch_calls == []


def test_taste_recommendation_dispatches_rank_candidates():
    module = load_plugin()
    ctx = FakeContext()
    module.register(ctx)

    ctx.hooks["pre_gateway_dispatch"](event=FakeEvent("@taste 推荐几个适合我的本地知识库工具"))

    assert ctx.dispatch_calls
    tool_name, args = ctx.dispatch_calls[0]
    assert tool_name == "mcp_tastemate_rank_candidates"
    assert args["query"] == "@taste 推荐几个适合我的本地知识库工具"
    assert args["taste_mode"] == "force"


def test_taste_recommendation_rewrites_with_ranked_result():
    module = load_plugin()
    ctx = FakeContext()
    module.register(ctx)

    result = ctx.hooks["pre_gateway_dispatch"](event=FakeEvent("@taste 推荐几个适合我的本地知识库工具"))

    assert result["action"] == "rewrite"
    assert "TasteMate 已完成真实后置重排" in result["text"]
    assert "Local-first KB" in result["text"]
    assert "final_score=0.864" in result["text"]


def test_taste_recommendation_persists_last_recommendation_context(tmp_path, monkeypatch):
    module = load_plugin()
    monkeypatch.setattr(module, "LOG_PATH", tmp_path / "tastemate-route.jsonl")
    monkeypatch.setattr(module, "CONTEXT_PATH", tmp_path / "tastemate-route-context.json")
    ctx = FakeContext()
    module.register(ctx)

    ctx.hooks["pre_gateway_dispatch"](event=FakeEvent("@taste 推荐几个适合我的本地知识库工具"))

    context_path = tmp_path / "tastemate-route-context.json"
    assert context_path.exists()
    content = context_path.read_text(encoding="utf-8")
    assert '"query": "@taste 推荐几个适合我的本地知识库工具"' in content
    assert '"candidates_snapshot"' in content
    assert '"ranked_candidates"' in content
    assert '"candidate_index"' in content


def test_needs_more_candidates_rewrite_does_not_fake_ranking():
    raw = (
        '{"structuredContent": {'
        '"action": "needs_more_candidates", '
        '"reason": "候选数量不足", '
        '"suggested_search_hints": ["local-first knowledge base", "self-hosted notes"]'
        '}}'
    )
    module = load_plugin()
    ctx = FakeContext(dispatch_result=raw)
    module.register(ctx)

    result = ctx.hooks["pre_gateway_dispatch"](event=FakeEvent("@taste 推荐几个适合我的本地知识库工具"))

    assert result["action"] == "rewrite"
    assert "当前候选不足" in result["text"]
    assert "local-first knowledge base" in result["text"]
    assert "已完成真实后置重排" not in result["text"]


def test_unknown_tool_fails_open():
    module = load_plugin()
    ctx = FakeContext(dispatch_result='{"error": "Unknown tool: mcp_tastemate_rank_candidates"}')
    module.register(ctx)

    result = ctx.hooks["pre_gateway_dispatch"](event=FakeEvent("@taste 推荐几个适合我的本地知识库工具"))

    assert result == {"action": "allow"}


def test_dispatch_exception_fails_open():
    module = load_plugin()
    ctx = RaisingContext()
    module.register(ctx)

    result = ctx.hooks["pre_gateway_dispatch"](event=FakeEvent("@taste 推荐几个适合我的本地知识库工具"))

    assert result == {"action": "allow"}


def test_feedback_dispatches_record_preference_signal_with_last_recommendation_context(tmp_path, monkeypatch):
    recommendation_raw = (
        '{"structuredContent": {'
        '"action": "ranked", '
        '"ranked_candidates": ['
        '{"id": "logseq", "title": "Logseq", "final_score": 0.725, "reasons": ["符合本地优先偏好"]}, '
        '{"id": "trilium", "title": "Trilium Notes", "final_score": 0.681, "reasons": ["符合开源偏好"]}'
        ']}}'
    )
    feedback_raw = (
        '{"structuredContent": {'
        '"accepted": true, '
        '"signal_type": "candidate_feedback", '
        '"profile_update_details": {"stable_preferences": ["local_first"], "negative_preferences": [], "current_focus": []}'
        '}}'
    )
    module = load_plugin()
    monkeypatch.setattr(module, "LOG_PATH", tmp_path / "tastemate-route.jsonl")
    monkeypatch.setattr(module, "CONTEXT_PATH", tmp_path / "tastemate-route-context.json")
    ctx = FakeContext(
        dispatch_results={
            "mcp_tastemate_rank_candidates": recommendation_raw,
            "mcp_tastemate_record_preference_signal": feedback_raw,
        }
    )
    module.register(ctx)

    ctx.hooks["pre_gateway_dispatch"](event=FakeEvent("@taste 推荐几个适合我的知识库工具"))
    result = ctx.hooks["pre_gateway_dispatch"](event=FakeEvent("我更喜欢 Logseq，以后优先。不要 Trilium Notes。"))

    assert result["action"] == "rewrite"
    tool_name, args = ctx.dispatch_calls[-1]
    assert tool_name == "mcp_tastemate_record_preference_signal"
    assert args["signal_type"] == "candidate_feedback"
    assert args["source"] == "tastemate_recommendation"
    assert args["query"] == "@taste 推荐几个适合我的知识库工具"
    assert args["user_signal"] == "我更喜欢 Logseq，以后优先。不要 Trilium Notes。"
    assert args["candidate_feedback"]["selected_candidate_ids"] == ["logseq"]
    assert args["candidate_feedback"]["rejected_candidate_ids"] == ["trilium"]
    snapshot_ids = {item["id"] for item in args["candidate_feedback"]["candidates_snapshot"]}
    assert {"logseq", "trilium"}.issubset(snapshot_ids)


def test_feedback_without_context_fails_open_without_preference_signal(tmp_path, monkeypatch):
    module = load_plugin()
    monkeypatch.setattr(module, "LOG_PATH", tmp_path / "tastemate-route.jsonl")
    monkeypatch.setattr(module, "CONTEXT_PATH", tmp_path / "missing-context.json")
    ctx = FakeContext()
    module.register(ctx)

    result = ctx.hooks["pre_gateway_dispatch"](event=FakeEvent("我更喜欢 Logseq，以后优先。"))

    assert result == {"action": "allow"}
    assert all(tool_name != "mcp_tastemate_record_preference_signal" for tool_name, _ in ctx.dispatch_calls)


def test_feedback_without_candidate_match_fails_open_without_preference_signal(tmp_path, monkeypatch):
    recommendation_raw = (
        '{"structuredContent": {'
        '"action": "ranked", '
        '"ranked_candidates": ['
        '{"id": "logseq", "title": "Logseq", "final_score": 0.725, "reasons": ["符合本地优先偏好"]}'
        ']}}'
    )
    module = load_plugin()
    monkeypatch.setattr(module, "LOG_PATH", tmp_path / "tastemate-route.jsonl")
    monkeypatch.setattr(module, "CONTEXT_PATH", tmp_path / "tastemate-route-context.json")
    ctx = FakeContext(dispatch_results={"mcp_tastemate_rank_candidates": recommendation_raw})
    module.register(ctx)

    ctx.hooks["pre_gateway_dispatch"](event=FakeEvent("@taste 推荐几个适合我的知识库工具"))
    result = ctx.hooks["pre_gateway_dispatch"](event=FakeEvent("我更喜欢 AFFiNE，以后优先。"))

    assert result == {"action": "allow"}
    assert all(tool_name != "mcp_tastemate_record_preference_signal" for tool_name, _ in ctx.dispatch_calls)


def test_feedback_dispatch_exception_fails_open(tmp_path, monkeypatch):
    recommendation_raw = (
        '{"structuredContent": {'
        '"action": "ranked", '
        '"ranked_candidates": ['
        '{"id": "logseq", "title": "Logseq", "final_score": 0.725, "reasons": ["符合本地优先偏好"]}'
        ']}}'
    )
    module = load_plugin()
    monkeypatch.setattr(module, "LOG_PATH", tmp_path / "tastemate-route.jsonl")
    monkeypatch.setattr(module, "CONTEXT_PATH", tmp_path / "tastemate-route-context.json")
    ctx = FakeContext(
        dispatch_results={
            "mcp_tastemate_rank_candidates": recommendation_raw,
            "mcp_tastemate_record_preference_signal": RuntimeError("boom"),
        }
    )
    module.register(ctx)

    ctx.hooks["pre_gateway_dispatch"](event=FakeEvent("@taste 推荐几个适合我的知识库工具"))
    result = ctx.hooks["pre_gateway_dispatch"](event=FakeEvent("我更喜欢 Logseq，以后优先。"))

    assert result == {"action": "allow"}


def test_operation_log_records_matched_route(tmp_path, monkeypatch):
    module = load_plugin()
    monkeypatch.setattr(module, "LOG_PATH", tmp_path / "tastemate-route.jsonl")
    ctx = FakeContext()
    module.register(ctx)

    ctx.hooks["pre_gateway_dispatch"](event=FakeEvent("@taste 推荐几个适合我的本地知识库工具"))

    content = (tmp_path / "tastemate-route.jsonl").read_text(encoding="utf-8")
    assert '"matched": true' in content
    assert '"dispatch_ok": true' in content
    assert '"dispatch_action": "ranked"' in content


def test_operation_log_marks_fixed_probe_candidates_only_for_plugin_regression(tmp_path, monkeypatch):
    module = load_plugin()
    monkeypatch.setattr(module, "LOG_PATH", tmp_path / "tastemate-route.jsonl")
    ctx = FakeContext()
    module.register(ctx)

    ctx.hooks["pre_gateway_dispatch"](event=FakeEvent("@taste 推荐几个适合我的本地知识库工具"))

    content = (tmp_path / "tastemate-route.jsonl").read_text(encoding="utf-8")
    assert '"candidate_source": "fixed_probe_candidates"' in content
    assert '"dispatch_action": "ranked"' in content
