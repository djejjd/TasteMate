"""Hermes route plugin for explicit @taste TasteMate orchestration."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RECOMMENDATION_MARKERS = ("推荐", "比较", "选型", "排序", "适合", "工具", "方案", "选择")
POSITIVE_FEEDBACK_MARKERS = ("更喜欢", "优先", "选择", "我选", "保留")
NEGATIVE_FEEDBACK_MARKERS = ("不要", "排除", "拒绝", "不喜欢")
LOG_PATH = Path("/opt/data/logs/tastemate-route.jsonl")
CONTEXT_PATH = Path("/opt/data/tastemate-route-context.json")
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


@dataclass(frozen=True)
class FeedbackDecision:
    matched: bool
    reason: str
    user_feedback: str
    query: str = ""
    selected_candidate_ids: tuple[str, ...] = ()
    rejected_candidate_ids: tuple[str, ...] = ()
    candidates_snapshot: tuple[dict[str, Any], ...] = ()


def route_decision(text: str) -> RouteDecision:
    query = text or ""
    if "@taste" not in query:
        return RouteDecision(matched=False, reason="missing_taste_marker", query=query)
    if not any(marker in query for marker in RECOMMENDATION_MARKERS):
        return RouteDecision(matched=False, reason="missing_recommendation_marker", query=query)
    return RouteDecision(matched=True, reason="explicit_taste_recommendation", query=query)


def _normalize_text(text: str) -> str:
    return (text or "").strip().lower()


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    normalized = _normalize_text(text)
    return any(marker in normalized for marker in markers)


def _split_feedback_clauses(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"[，。！？；;\n]+", text or "") if part.strip()]


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


def build_context_candidates(candidates: list[dict[str, Any]], ranked_candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    order: list[str] = []

    for item in list(candidates or []) + list(ranked_candidates or []):
        if not isinstance(item, dict):
            continue
        candidate_id = str(item.get("id") or "").strip()
        if not candidate_id:
            continue
        if candidate_id not in merged:
            merged[candidate_id] = {
                "id": candidate_id,
                "title": str(item.get("title") or candidate_id),
                "summary": str(item.get("summary") or ""),
                "metadata": item.get("metadata") or {},
            }
            order.append(candidate_id)
            continue
        existing = merged[candidate_id]
        if not existing.get("title") and item.get("title"):
            existing["title"] = str(item.get("title"))
        if not existing.get("summary") and item.get("summary"):
            existing["summary"] = str(item.get("summary"))
        if not existing.get("metadata") and item.get("metadata"):
            existing["metadata"] = item.get("metadata") or {}

    return [merged[candidate_id] for candidate_id in order]


def build_candidate_index(candidates_snapshot: list[dict[str, Any]]) -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}
    for item in candidates_snapshot:
        if not isinstance(item, dict):
            continue
        candidate_id = str(item.get("id") or "").strip()
        if not candidate_id:
            continue
        aliases = {candidate_id.lower()}
        title = str(item.get("title") or "").strip()
        if title:
            aliases.add(title.lower())
        index[candidate_id] = sorted(aliases, key=len, reverse=True)
    return index


def save_recommendation_context(*, query: str, candidates: list[dict[str, Any]], ranked_candidates: list[dict[str, Any]]) -> None:
    candidates_snapshot = build_context_candidates(candidates, ranked_candidates)
    payload = {
        "query": query,
        "candidates_snapshot": candidates_snapshot,
        "ranked_candidates": ranked_candidates,
        "candidate_index": build_candidate_index(candidates_snapshot),
    }
    try:
        CONTEXT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with CONTEXT_PATH.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
    except Exception:
        return


def load_recommendation_context() -> dict[str, Any]:
    try:
        with CONTEXT_PATH.open("r", encoding="utf-8") as fh:
            payload = json.load(fh)
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def extract_feedback_matches(text: str, candidate_index: dict[str, list[str]]) -> tuple[list[str], list[str]]:
    selected: list[str] = []
    rejected: list[str] = []

    for clause in _split_feedback_clauses(text):
        positive = _contains_any(clause, POSITIVE_FEEDBACK_MARKERS)
        negative = _contains_any(clause, NEGATIVE_FEEDBACK_MARKERS)
        if positive == negative:
            continue
        normalized_clause = _normalize_text(clause)
        matched: list[str] = []
        for candidate_id, aliases in candidate_index.items():
            if any(alias and alias in normalized_clause for alias in aliases):
                matched.append(candidate_id)
        if len(matched) != 1:
            continue
        if positive:
            selected.append(matched[0])
        else:
            rejected.append(matched[0])

    selected_unique = sorted(set(selected))
    rejected_unique = sorted(set(rejected))
    overlap = set(selected_unique) & set(rejected_unique)
    if overlap:
        selected_unique = [candidate_id for candidate_id in selected_unique if candidate_id not in overlap]
        rejected_unique = [candidate_id for candidate_id in rejected_unique if candidate_id not in overlap]
    return selected_unique, rejected_unique


def feedback_route_decision(text: str) -> FeedbackDecision:
    user_feedback = text or ""
    if not _contains_any(user_feedback, POSITIVE_FEEDBACK_MARKERS + NEGATIVE_FEEDBACK_MARKERS):
        return FeedbackDecision(matched=False, reason="missing_feedback_marker", user_feedback=user_feedback)

    context = load_recommendation_context()
    if not context:
        return FeedbackDecision(matched=False, reason="feedback_context_missing", user_feedback=user_feedback)

    candidate_index = context.get("candidate_index")
    if not isinstance(candidate_index, dict) or not candidate_index:
        return FeedbackDecision(matched=False, reason="feedback_context_invalid", user_feedback=user_feedback)

    selected_candidate_ids, rejected_candidate_ids = extract_feedback_matches(user_feedback, candidate_index)
    if not selected_candidate_ids and not rejected_candidate_ids:
        return FeedbackDecision(matched=False, reason="feedback_candidate_unmatched", user_feedback=user_feedback)

    candidates_snapshot = context.get("candidates_snapshot")
    if not isinstance(candidates_snapshot, list):
        candidates_snapshot = []

    return FeedbackDecision(
        matched=True,
        reason="explicit_tastemate_feedback",
        user_feedback=user_feedback,
        query=str(context.get("query") or ""),
        selected_candidate_ids=tuple(selected_candidate_ids),
        rejected_candidate_ids=tuple(rejected_candidate_ids),
        candidates_snapshot=tuple(item for item in candidates_snapshot if isinstance(item, dict)),
    )


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


def format_feedback_rewrite_text(result: DispatchResult) -> str:
    structured = result.structured
    if structured.get("accepted") is True or structured.get("feedback_valid") is True:
        return "TasteMate 已记录这次偏好反馈。请确认已记录用户选择与排除方向，不要再次调用 TasteMate。"
    return "TasteMate 未接受这次反馈写入。请按普通 Hermes 流程回复，不要伪装成已记录长期偏好。"


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
    ctx = kwargs.get("_ctx")
    recommendation = route_decision(text)
    if recommendation.matched:
        log_record: dict[str, Any] = {
            "hook": "pre_gateway_dispatch",
            "matched": True,
            "route_reason": recommendation.reason,
            "query_hash": hash_query(recommendation.query),
            "query_preview": recommendation.query[:QUERY_PREVIEW_LIMIT],
        }
        if ctx is None:
            log_record.update({"action": "allow", "dispatch_ok": False, "error_type": "missing_context"})
            write_operation_log(log_record)
            return {"action": "allow"}

        candidates = build_candidates(recommendation.query)
        args = {
            "query": recommendation.query,
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
                "candidate_source": "fixed_probe_candidates",
                "candidate_count": len(candidates),
                "action": "rewrite" if dispatch_result.ok else "allow",
                "dispatch_ok": dispatch_result.ok,
                "dispatch_action": dispatch_result.action if dispatch_result.ok else None,
                "error_type": dispatch_result.error_type,
            }
        )
        if dispatch_result.ok:
            ranked_candidates = dispatch_result.structured.get("ranked_candidates")
            if isinstance(ranked_candidates, list):
                save_recommendation_context(
                    query=recommendation.query,
                    candidates=candidates,
                    ranked_candidates=ranked_candidates,
                )
        write_operation_log(log_record)
        if not dispatch_result.ok:
            return {"action": "allow"}
        return {"action": "rewrite", "text": format_rewrite_text(recommendation.query, dispatch_result)}

    feedback = feedback_route_decision(text)
    log_record = {
        "hook": "pre_gateway_dispatch",
        "matched": feedback.matched,
        "route_reason": feedback.reason,
        "query_hash": hash_query(feedback.user_feedback),
        "query_preview": feedback.user_feedback[:QUERY_PREVIEW_LIMIT],
    }
    if not feedback.matched:
        log_record.update({"action": "allow", "dispatch_ok": None})
        write_operation_log(log_record)
        return {"action": "allow"}
    if ctx is None:
        log_record.update({"action": "allow", "dispatch_ok": False, "error_type": "missing_context"})
        write_operation_log(log_record)
        return {"action": "allow"}

    args = {
        "signal_type": "candidate_feedback",
        "user_signal": feedback.user_feedback,
        "source": "tastemate_recommendation",
        "query": feedback.query,
        "candidate_feedback": {
            "selected_candidate_ids": list(feedback.selected_candidate_ids),
            "rejected_candidate_ids": list(feedback.rejected_candidate_ids),
            "candidates_snapshot": list(feedback.candidates_snapshot),
        },
        "context": {"route": "tastemate-route"},
        "metadata": {},
    }
    try:
        raw = ctx.dispatch_tool("mcp_tastemate_record_preference_signal", args)
        dispatch_result = parse_dispatch_result(raw)
    except Exception as exc:
        log_record.update(
            {
                "action": "allow",
                "dispatch_ok": False,
                "error_type": "feedback_dispatch_failed",
                "message": str(exc),
                "selected_candidate_ids": list(feedback.selected_candidate_ids),
                "rejected_candidate_ids": list(feedback.rejected_candidate_ids),
            }
        )
        write_operation_log(log_record)
        return {"action": "allow"}

    log_record.update(
        {
            "action": "rewrite" if dispatch_result.ok else "allow",
            "dispatch_ok": dispatch_result.ok,
            "dispatch_action": "record_preference_signal" if dispatch_result.ok else None,
            "error_type": dispatch_result.error_type,
            "selected_candidate_ids": list(feedback.selected_candidate_ids),
            "rejected_candidate_ids": list(feedback.rejected_candidate_ids),
        }
    )
    write_operation_log(log_record)
    if not dispatch_result.ok:
        return {"action": "allow"}
    return {"action": "rewrite", "text": format_feedback_rewrite_text(dispatch_result)}


def register(ctx: Any) -> None:
    def hook(**kwargs: Any) -> dict[str, Any]:
        kwargs["_ctx"] = ctx
        return on_pre_gateway_dispatch(**kwargs)

    ctx.register_hook("pre_gateway_dispatch", hook)
