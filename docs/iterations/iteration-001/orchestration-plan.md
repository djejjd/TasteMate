# Iteration 001 Hermes @taste Rewrite Orchestration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将临时 Hermes rewrite probe 固化为最小可维护用户插件，让显式 `@taste` 推荐类消息稳定触发真实 `mcp_tastemate_rank_candidates` 调用，并通过 rewrite 回到 Hermes 自有 agent 回复通道。

**Architecture:** 插件作为 TasteMate 仓库内可发布集成代码维护，部署到 Hermes 用户插件目录后由 `pre_gateway_dispatch` 检测消息。命中保守 `@taste` gate 时，插件通过 `ctx.dispatch_tool` 调用 TasteMate MCP，解析 `structuredContent/result/error`，生成 rewrite text；失败时 fail-open 返回 `allow`。本计划不实现 Hermes 搜索结果候选抽取，`observed_tool_candidates` 进入后续迭代。

**Tech Stack:** Python 3.11+、Hermes user plugin API、pytest、JSONL operation log、TasteMate MCP server。

---

## 一、适用阶段

```text
Plan
```

本计划基于：

```text
docs/design.md
docs/iterations/iteration-001/development.md
docs/iterations/iteration-001/orchestration-addendum.md
docs/iterations/iteration-001/orchestration-development.md
docs/iterations/iteration-001/probes/hermes-plugin-dispatch-probe.md
```

## 二、范围

本轮 Build 只包含：

```text
TasteMate 仓库内新增 Hermes 用户插件源码。
@taste 推荐类 gate。
fixed_probe_candidates 候选源，用于固化当前已通过的 rewrite 编排通道验证。
TasteMate dispatch wrapper。
Hermes MCP wrapper 返回解析。
rewrite formatter。
JSONL operation log。
fail-open 错误降级。
本地单元测试。
远程部署与回滚说明。
hook 级验证和真实端到端验收步骤。
```

本轮不做：

```text
不修改 Hermes 源码。
不实现 observed_tool_candidates。
不从 Hermes 搜索/浏览/工具结果中自动抽取候选。
不实现 explicit_candidates 解析。
不实现 gateway send API 直发。
不实现搜索前偏好注入。
不实现 record_feedback 自动编排。
不实现 UI。
不实现多用户系统。
```

## 三、文件影响范围

新增：

```text
integrations/hermes/plugins/tastemate-route/plugin.yaml
integrations/hermes/plugins/tastemate-route/__init__.py
tests/test_hermes_route_plugin.py
```

修改：

```text
docs/iterations/iteration-001/verification.md
docs/iterations/iteration-001/review.md
```

禁止修改：

```text
/Users/lanser/code/hermes 或远程 <HERMES_APP_DIR> 源码目录。
TasteMate ranker 评分逻辑，除非测试证明插件接口需要兼容现有输出。
```

## 四、实现结构

插件文件职责：

```text
plugin.yaml：Hermes 插件 manifest。
__init__.py：插件全部逻辑，保持单文件，避免为临时补充引入复杂包结构。
tests/test_hermes_route_plugin.py：用 fake ctx 和 fake event 验证 gate、dispatch、parse、rewrite、fail-open。
```

`__init__.py` 内部函数：

```text
register(ctx)
on_pre_gateway_dispatch(...)
route_decision(text)
build_candidates(text)
dispatch_rank_candidates(ctx, query, candidates)
parse_dispatch_result(raw)
format_rewrite_text(original_text, dispatch_result)
write_operation_log(record)
hash_query(text)
```

## 五、任务清单

### Task 1: 创建插件 manifest 和基础注册

**Files:**
- Create: `integrations/hermes/plugins/tastemate-route/plugin.yaml`
- Create: `integrations/hermes/plugins/tastemate-route/__init__.py`
- Create: `tests/test_hermes_route_plugin.py`

- [ ] **Step 1: 写失败测试：插件注册 pre_gateway_dispatch hook**

在 `tests/test_hermes_route_plugin.py` 写入：

```python
from __future__ import annotations

import importlib.util
from pathlib import Path


PLUGIN_PATH = Path("integrations/hermes/plugins/tastemate-route/__init__.py")


class FakeContext:
    def __init__(self):
        self.hooks = {}
        self.dispatch_calls = []

    def register_hook(self, name, callback):
        self.hooks[name] = callback

    def dispatch_tool(self, tool_name, args):
        self.dispatch_calls.append((tool_name, args))
        return '{"structuredContent":{"action":"ranked","ranked_candidates":[]}}'


def load_plugin():
    spec = importlib.util.spec_from_file_location("tastemate_route_plugin", PLUGIN_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_registers_pre_gateway_dispatch_hook():
    module = load_plugin()
    ctx = FakeContext()

    module.register(ctx)

    assert "pre_gateway_dispatch" in ctx.hooks
```

- [ ] **Step 2: 运行测试，确认失败**

Run:

```bash
python -m pytest tests/test_hermes_route_plugin.py::test_registers_pre_gateway_dispatch_hook -q
```

Expected:

```text
FAIL，原因是 integrations/hermes/plugins/tastemate-route/__init__.py 不存在。
```

- [ ] **Step 3: 创建 plugin.yaml**

写入 `integrations/hermes/plugins/tastemate-route/plugin.yaml`：

```yaml
name: tastemate-route
version: 0.1.0
description: "Route explicit @taste recommendation requests to TasteMate MCP via gateway rewrite."
author: "TasteMate"
hooks:
  - pre_gateway_dispatch
```

- [ ] **Step 4: 创建最小插件注册代码**

写入 `integrations/hermes/plugins/tastemate-route/__init__.py`：

```python
"""Hermes route plugin for explicit @taste TasteMate orchestration."""

from __future__ import annotations

from typing import Any


def on_pre_gateway_dispatch(*, event: Any, gateway: Any = None, session_store: Any = None, **kwargs: Any) -> dict[str, Any]:
    return {"action": "allow"}


def register(ctx: Any) -> None:
    ctx.register_hook("pre_gateway_dispatch", on_pre_gateway_dispatch)
```

- [ ] **Step 5: 运行测试，确认通过**

Run:

```bash
python -m pytest tests/test_hermes_route_plugin.py::test_registers_pre_gateway_dispatch_hook -q
```

Expected:

```text
1 passed
```

### Task 2: 实现保守 @taste gate

**Files:**
- Modify: `integrations/hermes/plugins/tastemate-route/__init__.py`
- Modify: `tests/test_hermes_route_plugin.py`

- [ ] **Step 1: 写失败测试：普通消息 allow 且不 dispatch**

追加到 `tests/test_hermes_route_plugin.py`：

```python
class FakeEvent:
    def __init__(self, text):
        self.text = text


def test_plain_message_allows_without_dispatch():
    module = load_plugin()
    ctx = FakeContext()
    module.register(ctx)

    result = ctx.hooks["pre_gateway_dispatch"](event=FakeEvent("Hermes 的配置在哪？"))

    assert result == {"action": "allow"}
    assert ctx.dispatch_calls == []
```

- [ ] **Step 2: 写失败测试：@taste 推荐消息命中 gate 并 dispatch**

追加到 `tests/test_hermes_route_plugin.py`：

```python
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
```

- [ ] **Step 3: 运行测试，确认新增测试失败**

Run:

```bash
python -m pytest tests/test_hermes_route_plugin.py -q
```

Expected:

```text
test_taste_recommendation_dispatches_rank_candidates FAIL，因为当前 hook 不调用 dispatch_tool。
```

- [ ] **Step 4: 实现 route_decision 和 gate 常量**

替换 `integrations/hermes/plugins/tastemate-route/__init__.py` 为：

```python
"""Hermes route plugin for explicit @taste TasteMate orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


RECOMMENDATION_MARKERS = ("推荐", "比较", "选型", "排序", "适合", "工具", "方案", "选择")


@dataclass(frozen=True)
class RouteDecision:
    matched: bool
    reason: str
    query: str


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


def on_pre_gateway_dispatch(*, event: Any, gateway: Any = None, session_store: Any = None, **kwargs: Any) -> dict[str, Any]:
    text = getattr(event, "text", "") or ""
    decision = route_decision(text)
    if not decision.matched:
        return {"action": "allow"}

    args = {
        "query": decision.query,
        "candidates": build_candidates(decision.query),
        "taste_mode": "force",
    }
    ctx = kwargs.get("_ctx")
    if ctx is None:
        return {"action": "allow"}
    ctx.dispatch_tool("mcp_tastemate_rank_candidates", args)
    return {"action": "allow"}


def register(ctx: Any) -> None:
    def hook(**kwargs: Any) -> dict[str, Any]:
        kwargs["_ctx"] = ctx
        return on_pre_gateway_dispatch(**kwargs)

    ctx.register_hook("pre_gateway_dispatch", hook)
```

- [ ] **Step 5: 运行测试，确认通过**

Run:

```bash
python -m pytest tests/test_hermes_route_plugin.py -q
```

Expected:

```text
3 passed
```

### Task 3: 解析 dispatch 返回并生成 ranked rewrite

**Files:**
- Modify: `integrations/hermes/plugins/tastemate-route/__init__.py`
- Modify: `tests/test_hermes_route_plugin.py`

- [ ] **Step 1: 调整 FakeContext 返回 ranked 结果**

修改 `FakeContext.dispatch_tool` 为：

```python
    def dispatch_tool(self, tool_name, args):
        self.dispatch_calls.append((tool_name, args))
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
```

- [ ] **Step 2: 写失败测试：@taste 返回 rewrite**

追加到 `tests/test_hermes_route_plugin.py`：

```python
def test_taste_recommendation_rewrites_with_ranked_result():
    module = load_plugin()
    ctx = FakeContext()
    module.register(ctx)

    result = ctx.hooks["pre_gateway_dispatch"](event=FakeEvent("@taste 推荐几个适合我的本地知识库工具"))

    assert result["action"] == "rewrite"
    assert "TasteMate 已完成真实后置重排" in result["text"]
    assert "Local-first KB" in result["text"]
    assert "final_score=0.864" in result["text"]
```

- [ ] **Step 3: 运行测试，确认失败**

Run:

```bash
python -m pytest tests/test_hermes_route_plugin.py::test_taste_recommendation_rewrites_with_ranked_result -q
```

Expected:

```text
FAIL，因为 hook 当前返回 allow。
```

- [ ] **Step 4: 实现 parse_dispatch_result 和 ranked formatter**

在 `integrations/hermes/plugins/tastemate-route/__init__.py` 增加 import：

```python
import json
```

在 `build_candidates` 后追加：

```python
@dataclass(frozen=True)
class DispatchResult:
    ok: bool
    action: str
    structured: dict[str, Any]
    error_type: str | None = None
    message: str = ""
    raw_preview: str = ""


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

    reason = structured.get("reason") or ""
    return (
        "TasteMate 判断本轮不适合个性化排序。请按普通 Hermes 流程回答用户。\n\n"
        f"原始请求：\n{original_text}\n\n"
        f"TasteMate reason：{reason}"
    )
```

修改 `on_pre_gateway_dispatch` 命中分支：

```python
    raw = ctx.dispatch_tool("mcp_tastemate_rank_candidates", args)
    dispatch_result = parse_dispatch_result(raw)
    if not dispatch_result.ok:
        return {"action": "allow"}
    return {"action": "rewrite", "text": format_rewrite_text(decision.query, dispatch_result)}
```

- [ ] **Step 5: 运行测试，确认通过**

Run:

```bash
python -m pytest tests/test_hermes_route_plugin.py -q
```

Expected:

```text
4 passed
```

### Task 4: 支持 needs_more_candidates、passthrough、错误 fail-open

**Files:**
- Modify: `integrations/hermes/plugins/tastemate-route/__init__.py`
- Modify: `tests/test_hermes_route_plugin.py`

- [ ] **Step 1: 扩展 FakeContext 支持可配置返回**

修改 `FakeContext.__init__` 和 `dispatch_tool`：

```python
class FakeContext:
    def __init__(self, dispatch_result=None):
        self.hooks = {}
        self.dispatch_calls = []
        self.dispatch_result = dispatch_result

    def register_hook(self, name, callback):
        self.hooks[name] = callback

    def dispatch_tool(self, tool_name, args):
        self.dispatch_calls.append((tool_name, args))
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
```

- [ ] **Step 2: 写失败测试：needs_more_candidates rewrite**

追加：

```python
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
```

- [ ] **Step 3: 写失败测试：Unknown tool fail-open**

追加：

```python
def test_unknown_tool_fails_open():
    module = load_plugin()
    ctx = FakeContext(dispatch_result='{"error": "Unknown tool: mcp_tastemate_rank_candidates"}')
    module.register(ctx)

    result = ctx.hooks["pre_gateway_dispatch"](event=FakeEvent("@taste 推荐几个适合我的本地知识库工具"))

    assert result == {"action": "allow"}
```

- [ ] **Step 4: 更新 formatter 支持 needs_more_candidates 和 low_confidence**

在 `format_rewrite_text` 的 ranked 分支后加入：

```python
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
```

- [ ] **Step 5: 运行测试，确认通过**

Run:

```bash
python -m pytest tests/test_hermes_route_plugin.py -q
```

Expected:

```text
6 passed
```

### Task 5: 实现 operation log 和异常 fail-open

**Files:**
- Modify: `integrations/hermes/plugins/tastemate-route/__init__.py`
- Modify: `tests/test_hermes_route_plugin.py`

- [ ] **Step 1: 写失败测试：dispatch 异常 fail-open**

追加：

```python
class RaisingContext(FakeContext):
    def dispatch_tool(self, tool_name, args):
        self.dispatch_calls.append((tool_name, args))
        raise RuntimeError("boom")


def test_dispatch_exception_fails_open():
    module = load_plugin()
    ctx = RaisingContext()
    module.register(ctx)

    result = ctx.hooks["pre_gateway_dispatch"](event=FakeEvent("@taste 推荐几个适合我的本地知识库工具"))

    assert result == {"action": "allow"}
```

- [ ] **Step 2: 写失败测试：operation log 写入**

追加：

```python
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
```

- [ ] **Step 3: 增加日志实现**

在 `integrations/hermes/plugins/tastemate-route/__init__.py` 增加 import：

```python
import hashlib
from datetime import datetime, timezone
from pathlib import Path
```

增加常量：

```python
LOG_PATH = Path("<HERMES_DATA_DIR>/logs/tastemate-route.jsonl")
QUERY_PREVIEW_LIMIT = 200
```

增加函数：

```python
def hash_query(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:16]


def write_operation_log(record: dict[str, Any]) -> None:
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        **record,
    }
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        return
```

修改 `on_pre_gateway_dispatch`：

```python
    log_record = {
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
```

在 dispatch 成功后记录：

```python
    log_record.update(
        {
            "action": "rewrite" if dispatch_result.ok else "allow",
            "candidate_source": "fixed_probe_candidates",
            "candidate_count": len(args["candidates"]),
            "dispatch_ok": dispatch_result.ok,
            "dispatch_action": dispatch_result.action if dispatch_result.ok else None,
            "error_type": dispatch_result.error_type,
        }
    )
    write_operation_log(log_record)
```

用 try/except 包裹命中分支：

```python
    try:
        raw = ctx.dispatch_tool("mcp_tastemate_rank_candidates", args)
        dispatch_result = parse_dispatch_result(raw)
    except Exception as exc:
        log_record.update({"action": "allow", "dispatch_ok": False, "error_type": "plugin_exception", "message": str(exc)})
        write_operation_log(log_record)
        return {"action": "allow"}
```

- [ ] **Step 4: 运行测试，确认通过**

Run:

```bash
python -m pytest tests/test_hermes_route_plugin.py -q
```

Expected:

```text
8 passed
```

### Task 6: 明确候选来源能力边界并更新文档

**Files:**
- Modify: `docs/iterations/iteration-001/orchestration-development.md`
- Modify: `docs/iterations/iteration-001/orchestration-addendum.md`

- [ ] **Step 1: 更新 Development Spec 候选策略段**

在 `orchestration-development.md` 的候选策略段补充：

```text
fixed_probe_candidates 仅用于固化当前已通过的 @taste -> dispatch -> rewrite 通道验证。
explicit_candidates 不进入本轮实现，需要单独设计用户或 Hermes 如何明确传入候选。
observed_tool_candidates 不进入本轮实现，需要独立穿刺验证 post_tool_call / transform_tool_result 是否能稳定观察搜索类工具结果、归一候选结构、判断候选充足时机。
explicit_candidates 和 observed_tool_candidates 都作为后续候选来源优化方向，不作为 Iteration 001 A-002 验收条件。
```

- [ ] **Step 2: 更新 Addendum 风险段**

在 `orchestration-addendum.md` 风险段补充：

```text
explicit_candidates 尚未设计输入格式，不能写成当前实现能力。
observed_tool_candidates 尚未穿刺验证，不能写成当前可行能力。
```

- [ ] **Step 3: 文档占位符扫描**

Run:

```bash
rg -n "TBD|TODO|FIXME|待定|占位" docs/iterations/iteration-001/orchestration-development.md docs/iterations/iteration-001/orchestration-addendum.md
```

Expected:

```text
无输出，exit code 1。
```

### Task 7: 全量本地验证

**Files:**
- Test only.

- [ ] **Step 1: 运行插件测试**

Run:

```bash
python -m pytest tests/test_hermes_route_plugin.py -q
```

Expected:

```text
8 passed
```

- [ ] **Step 2: 运行全量测试**

Run:

```bash
python -m pytest -q
```

Expected:

```text
25 passed
```

如果现有测试数量变化，以实际输出为准，但必须为 0 failures。

### Task 8: 远程部署与 hook 级验证

**Files:**
- Remote deploy only.

- [ ] **Step 1: 备份远程旧 probe 插件**

Run:

```bash
ssh -o BatchMode=yes -o ConnectTimeout=8 <HERMES_SSH_USER>@<HERMES_HOST> 'docker exec hermes sh -lc "if [ -d <HERMES_DATA_DIR>/plugins/tastemate-route-probe ]; then cp -a <HERMES_DATA_DIR>/plugins/tastemate-route-probe <HERMES_DATA_DIR>/plugins/tastemate-route-probe.bak.$(date +%Y%m%d%H%M%S); fi"'
```

Expected:

```text
exit code 0。
```

- [ ] **Step 2: 上传正式插件到远程**

Run:

```bash
ssh -o BatchMode=yes -o ConnectTimeout=8 <HERMES_SSH_USER>@<HERMES_HOST> 'docker exec hermes sh -lc "mkdir -p <HERMES_DATA_DIR>/plugins/tastemate-route && cat > <HERMES_DATA_DIR>/plugins/tastemate-route/__init__.py"' < integrations/hermes/plugins/tastemate-route/__init__.py
ssh -o BatchMode=yes -o ConnectTimeout=8 <HERMES_SSH_USER>@<HERMES_HOST> 'docker exec hermes sh -lc "cat > <HERMES_DATA_DIR>/plugins/tastemate-route/plugin.yaml"' < integrations/hermes/plugins/tastemate-route/plugin.yaml
```

Expected:

```text
exit code 0。
```

- [ ] **Step 3: 启用插件**

使用安全配置编辑脚本，把 `<HERMES_DATA_DIR>/config.yaml` 中 `plugins.enabled` 加入 `tastemate-route`，并保留已有插件。

验证命令：

```bash
ssh -o BatchMode=yes -o ConnectTimeout=8 <HERMES_SSH_USER>@<HERMES_HOST> 'docker exec hermes sh -lc "grep -n \"plugins:\" -A8 <HERMES_DATA_DIR>/config.yaml"'
```

Expected:

```text
plugins.enabled 包含 tastemate-route。
```

- [ ] **Step 4: 重启 Hermes gateway**

Run:

```bash
ssh -o BatchMode=yes -o ConnectTimeout=8 <HERMES_SSH_USER>@<HERMES_HOST> 'docker restart hermes'
```

Expected:

```text
hermes
exit code 0。
```

- [ ] **Step 5: 执行 hook 级验证脚本**

在远程容器内模拟普通消息和 `@taste` 消息，调用 `invoke_hook("pre_gateway_dispatch", ...)`。

Expected:

```text
普通消息返回 action=allow。
@taste 推荐消息返回 action=rewrite。
rewrite text 包含 TasteMate 已完成真实后置重排。
```

- [ ] **Step 6: 检查 operation log**

Run:

```bash
ssh -o BatchMode=yes -o ConnectTimeout=8 <HERMES_SSH_USER>@<HERMES_HOST> 'docker exec hermes sh -lc "tail -n 20 <HERMES_DATA_DIR>/logs/tastemate-route.jsonl"'
```

Expected:

```text
存在 matched=true、dispatch_ok=true、dispatch_action=ranked。
存在普通消息 matched=false 或 action=allow 记录。
```

### Task 9: 真实端到端验收

**Files:**
- Remote manual verification.
- Modify: `docs/iterations/iteration-001/verification.md`
- Modify: `docs/iterations/iteration-001/review.md`

- [ ] **Step 1: 普通消息验收**

通过真实用户入口发送：

```text
Hermes 的配置在哪？
```

Expected:

```text
Hermes 正常回答。
operation log 记录 action=allow 或无 TasteMate dispatch。
无 mcp_tastemate_rank_candidates 调用。
```

- [ ] **Step 2: @taste 推荐消息验收**

通过真实用户入口发送：

```text
@taste 推荐几个适合我的本地知识库工具
```

Expected:

```text
operation log 记录 matched=true、dispatch_ok=true、dispatch_action=ranked。
Hermes 回复中能体现 TasteMate 排序结果。
```

- [ ] **Step 3: @taste 事实类消息验收**

通过真实用户入口发送：

```text
@taste Hermes 的 MCP 配置文件在哪？
```

Expected:

```text
不伪装成推荐排序。
如果触发 TasteMate，结果应为 passthrough 或 low_confidence；如果 gate 未命中，应按普通 Hermes 流程回答。
```

- [ ] **Step 4: 更新 verification.md**

在 `docs/iterations/iteration-001/verification.md` 追加真实端到端验收记录：

```text
命令或入口：
输入：
日志证据：
结果：
退出码或人工观察结论：
```

- [ ] **Step 5: 更新 review.md**

追加 “Orchestration Build 后审核”，审核正式插件实现和端到端验收结果。

## 六、风险与回滚

风险：

```text
插件未加载：检查 plugins.enabled 和 plugin.yaml。
MCP 工具未注册：检查 mcp_servers.tastemate 和 discover_mcp_tools。
rewrite 后 Hermes 回复偏离排序：收紧 rewrite formatter。
日志过多：限制 query_preview 和 raw_preview。
```

回滚：

```text
从 plugins.enabled 移除 tastemate-route。
重启 Hermes gateway。
保留 TasteMate MCP server 配置，不影响普通 Hermes 流程。
```

## 七、验收门槛

当前补充可进入 Closeout 的最低条件：

```text
本地插件测试通过。
全量测试通过。
远程 hook 级验证通过。
真实普通消息不触发 TasteMate。
真实 @taste 推荐消息触发 TasteMate 并 rewrite。
未修改 Hermes 源码。
verification.md 和 review.md 已记录证据。
```

未达到以上条件时，Iteration 001 不能标记 ACCEPTED。
