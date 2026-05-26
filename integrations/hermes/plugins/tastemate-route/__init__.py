"""Hermes route plugin for explicit @taste TasteMate orchestration."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RECOMMENDATION_MARKERS = ("推荐", "比较", "选型", "排序", "适合", "工具", "方案", "选择")
LOG_PATH = Path("/opt/data/logs/tastemate-route.jsonl")
QUERY_PREVIEW_LIMIT = 200


@dataclass(frozen=True)
class RouteDecision:
    matched: bool
    reason: str
    query: str


@dataclass(frozen=True)
class DispatchResult:
    ok: bool
    action: str
    structured: dict[str, Any]
    error_type: str | None = None
    message: str = ""
    raw_preview: str = ""


def route_decision(text: str) -> RouteDecision:
    query = text or ""
    if "@taste" not in query:
        return RouteDecision(matched=False, reason="missing_taste_marker", query=query)
    if not any(marker in query for marker in RECOMMENDATION_MARKERS):
        return RouteDecision(matched=False, reason="missing_recommendation_marker", query=query)
    return RouteDecision(matched=True, reason="explicit_taste_recommendation", query=query)


def build_candidates(text: str) -> list[dict[str, Any]]:
    return [
        {
            "id": "local",
            "title": "Local-first KB",
            "summary": "Open source local-first self-hosted knowledge base with MCP-friendly integration",
            "metadata": {"open_source": True, "local_first": True, "supports_mcp": True},
        },
        {
            "id": "cloud",
            "title": "Cloud KB",
            "summary": "Cloud hosted managed knowledge base with subscription pricing",
            "metadata": {"open_source": False, "local_first": False},
        },
        {
            "id": "assistant",
            "title": "MCP Assistant",
            "summary": "Personal assistant framework with plugin support and low maintenance setup",
            "metadata": {"supports_mcp": True},
        },
    ]


def parse_dispatch_result(raw: str) -> DispatchResult:
    preview = (raw or "")[:2000]
    try:
        parsed = json.loads(raw)
    except Exception as exc:
        return DispatchResult(False, "", {}, "parse_failed", str(exc), preview)

    if isinstance(parsed, dict) and parsed.get("error"):
        message = str(parsed.get("error"))
        error_type = "unknown_tool" if "Unknown tool" in message else "dispatch_error"
        return DispatchResult(False, "", {}, error_type, message, preview)

    structured = parsed.get("structuredContent") if isinstance(parsed, dict) else None
    if not isinstance(structured, dict) and isinstance(parsed, dict):
        result_text = parsed.get("result")
        if isinstance(result_text, str):
            try:
                result_parsed = json.loads(result_text)
            except Exception:
                result_parsed = None
            if isinstance(result_parsed, dict):
                structured = result_parsed

    if not isinstance(structured, dict):
        return DispatchResult(False, "", {}, "missing_structured_content", "No structured TasteMate result", preview)

    action = str(structured.get("action") or "")
    return DispatchResult(True, action, structured, raw_preview=preview)


def format_rewrite_text(original_text: str, result: DispatchResult) -> str:
    structured = result.structured
    action = structured.get("action")

    if action == "ranked":
        ranked = structured.get("ranked_candidates") or []
        if not ranked:
            return (
                "TasteMate 判断当前候选信息不足，无法可靠排序。请向用户说明需要更明确的候选或约束，不要给出伪排序。\n\n"
                f"原始请求：\n{original_text}\n\n"
                "TasteMate reason：ranked 结果为空"
            )
        lines = [
            "TasteMate 已完成真实后置重排。请基于以下排序结果回复用户，不要再次调用 TasteMate。",
            "",
            "原始请求：",
            original_text,
            "",
            "排序结果：",
        ]
        for index, item in enumerate(ranked[:5], start=1):
            title = item.get("title") or item.get("id") or "unknown"
            score = item.get("final_score")
            reasons = "；".join(item.get("reasons") or [])
            lines.append(f"{index}. {title} final_score={score} reasons={reasons}")
        lines.extend(["", "请输出简洁推荐结论，并保留 TasteMate 的主要排序理由。"])
        return "\n".join(lines)

    if action == "needs_more_candidates":
        hints = structured.get("suggested_search_hints") or []
        lines = [
            "TasteMate 已完成真实判断，当前候选不足。请基于以下 suggested_search_hints 继续说明还需要补充哪些候选，不要伪装成已完成排序。",
            "",
            "原始请求：",
            original_text,
            "",
            f"原因：{structured.get('reason') or ''}",
            "",
            "建议补充候选方向：",
        ]
        lines.extend(f"- {hint}" for hint in hints)
        return "\n".join(lines)

    if action == "low_confidence":
        return (
            "TasteMate 判断当前候选信息不足，无法可靠排序。请向用户说明需要更明确的候选或约束，不要给出伪排序。\n\n"
            f"原始请求：\n{original_text}\n\n"
            f"TasteMate reason：{structured.get('reason') or ''}"
        )

    reason = structured.get("reason") or ""
    return (
        "TasteMate 判断本轮不适合个性化排序。请按普通 Hermes 流程回答用户。\n\n"
        f"原始请求：\n{original_text}\n\n"
        f"TasteMate reason：{reason}"
    )


def hash_query(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:16]


def write_operation_log(record: dict[str, Any]) -> None:
    payload = {"ts": datetime.now(timezone.utc).isoformat(), **record}
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        return


def on_pre_gateway_dispatch(*, event: Any, gateway: Any = None, session_store: Any = None, **kwargs: Any) -> dict[str, Any]:
    text = getattr(event, "text", "") or ""
    decision = route_decision(text)
    log_record: dict[str, Any] = {
        "hook": "pre_gateway_dispatch",
        "matched": decision.matched,
        "route_reason": decision.reason,
        "query_hash": hash_query(decision.query),
        "query_preview": decision.query[:QUERY_PREVIEW_LIMIT],
    }
    if not decision.matched:
        log_record.update({"action": "allow", "dispatch_ok": None})
        write_operation_log(log_record)
        return {"action": "allow"}

    ctx = kwargs.get("_ctx")
    if ctx is None:
        log_record.update({"action": "allow", "dispatch_ok": False, "error_type": "missing_context"})
        write_operation_log(log_record)
        return {"action": "allow"}

    candidates = build_candidates(decision.query)
    args = {
        "query": decision.query,
        "candidates": candidates,
        "taste_mode": "force",
    }
    try:
        raw = ctx.dispatch_tool("mcp_tastemate_rank_candidates", args)
        dispatch_result = parse_dispatch_result(raw)
    except Exception as exc:
        log_record.update(
            {
                "action": "allow",
                "candidate_source": "fixed_probe_candidates",
                "candidate_count": len(candidates),
                "dispatch_ok": False,
                "error_type": "plugin_exception",
                "message": str(exc),
            }
        )
        write_operation_log(log_record)
        return {"action": "allow"}

    log_record.update(
        {
            "action": "rewrite" if dispatch_result.ok else "allow",
            "candidate_source": "fixed_probe_candidates",
            "candidate_count": len(candidates),
            "dispatch_ok": dispatch_result.ok,
            "dispatch_action": dispatch_result.action if dispatch_result.ok else None,
            "error_type": dispatch_result.error_type,
        }
    )
    write_operation_log(log_record)
    if not dispatch_result.ok:
        return {"action": "allow"}

    return {"action": "rewrite", "text": format_rewrite_text(decision.query, dispatch_result)}


def register(ctx: Any) -> None:
    def hook(**kwargs: Any) -> dict[str, Any]:
        kwargs["_ctx"] = ctx
        return on_pre_gateway_dispatch(**kwargs)

    ctx.register_hook("pre_gateway_dispatch", hook)
