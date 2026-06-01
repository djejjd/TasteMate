# 迭代 002 真实候选排序实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` 或 `superpowers:executing-plans` 按任务逐步执行。本计划使用 checkbox 跟踪进度。

**Goal:** 将迭代二落到“真实 candidates 协议 + 真实候选排序 + 受控回归路径”的可验收实现。

**Architecture:** `tastemate/schemas/candidates.py` 负责候选最小协议校验和缺失字段报告，`tastemate/core/ranker.py` 只接收已验证候选并返回排序或降级结果，`tastemate/tools/rank_candidates.py` 暴露 MCP 工具入口并读取本地 profile。`integrations/hermes/plugins/tastemate-route` 仅保留为迭代一回归路径，不作为迭代二真实候选主路径；所有验收以本地 pytest 和一次远端 Hermes 真实调用烟测共同完成。

**Tech Stack:** Python 3.13, `FastMCP`, `pytest`, 本地 JSON profile store, Hermes `pre_gateway_dispatch` hook.

---

### Task 1: 锁定 candidates 最小协议

**Files:**
- Modify: `tastemate/schemas/candidates.py`
- Modify: `tests/test_rank_candidates.py`

- [ ] **Step 1: Write the failing test**

```python
from tastemate.schemas.candidates import validate_candidates


def test_validate_candidates_reports_missing_required_fields():
    result = validate_candidates(
        [
            {"title": "Missing id and metadata", "summary": "ok"},
            {"id": "b", "title": "Missing summary", "metadata": {}},
        ]
    )

    assert result["valid_candidates"] == []
    assert result["invalid_candidates"][0]["missing_fields"] == ["id", "metadata"]
    assert result["invalid_candidates"][1]["missing_fields"] == ["summary"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_rank_candidates.py -k validate_candidates -v`
Expected: FAIL because `validate_candidates` does not exist or does not report missing fields.

- [ ] **Step 3: Write minimal implementation**

```python
def validate_candidate(raw: dict[str, Any]) -> dict[str, Any]:
    missing_fields = [field for field in ("id", "title", "summary") if not raw.get(field)]
    if "metadata" not in raw or raw.get("metadata") is None:
        missing_fields.append("metadata")
    return {
        "valid": not missing_fields,
        "candidate_id": raw.get("id"),
        "missing_fields": missing_fields,
        "candidate": {
            "id": raw.get("id"),
            "title": raw.get("title"),
            "summary": raw.get("summary"),
            "metadata": raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {},
            "url": raw.get("url"),
            "source": raw.get("source"),
        },
    }
```

`normalize_candidate` 只能保留候选已有字段，不得再用 `url` / `source` / `summary` 伪造通过协议的候选。

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_rank_candidates.py -k validate_candidates -v`
Expected: PASS，且 `invalid_candidates` 明确包含缺失字段。

- [ ] **Step 5: Commit**

```bash
git add tastemate/schemas/candidates.py tests/test_rank_candidates.py
git commit -m "feat: validate real candidates explicitly"
```

### Task 2: 统一排序、降级与工具输出

**Files:**
- Modify: `tastemate/core/ranker.py`
- Modify: `tastemate/tools/rank_candidates.py`
- Modify: `tests/test_rank_candidates.py`
- Modify: `tests/test_server_tools.py`

- [ ] **Step 1: Write the failing test**

```python
from tastemate.core.ranker import Ranker


def test_ranker_returns_passthrough_for_factual_query():
    result = Ranker(profile={}).rank(
        query="@taste Hermes 的 MCP 配置文件在哪？",
        candidates=[
            {"id": "a", "title": "Hermes config", "summary": "配置路径说明", "metadata": {}},
        ],
        taste_mode="force",
    )

    assert result["ranking_needed"] is False
    assert result["mode"] == "factual"
    assert result["action"] == "passthrough"


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_rank_candidates.py -k "passthrough or invalid_candidates or needs_more_candidates or ranked_for_valid_candidates" -v`
Expected: FAIL until `Ranker` returns the explicit `passthrough`、`invalid_candidates`、`needs_more_candidates`、`ranked` 结果。

- [ ] **Step 3: Write minimal implementation**

```python
if not normalized_candidates:
    return {"ranking_needed": False, "mode": "factual", "action": "passthrough", "reason": "确定性事实问题或没有可排序候选集合"}

if self._is_factual(query):
    return {"ranking_needed": False, "mode": "factual", "action": "passthrough", "reason": "确定性事实问题或没有可排序候选集合"}

validation = validate_candidates(candidates)
if validation["invalid_candidates"]:
    return {
        "ranking_needed": True,
        "mode": "recommendation",
        "action": "invalid_candidates",
        "reason": "候选不满足最小协议",
        "valid_candidates": validation["valid_candidates"],
        "invalid_candidates": validation["invalid_candidates"],
        "ranked_candidates": [],
    }

if len(validation["valid_candidates"]) < 2:
    return {
        "ranking_needed": True,
        "mode": "recommendation",
        "action": "needs_more_candidates",
        "reason": "候选数量不足",
    }

ranked = [self._score_candidate(query, candidate) for candidate in validation["valid_candidates"]]
ranked.sort(key=lambda item: item["final_score"], reverse=True)
return {
    "ranking_needed": True,
    "mode": "recommendation",
    "action": "ranked",
    "ranked_candidates": ranked,
}
```

映射关系必须写死：

```text
事实类 query 或 candidates 为空 -> passthrough
缺少 id/title/summary/metadata -> invalid_candidates
有效候选少于 2 个 -> needs_more_candidates
候选满足协议且数量足够 -> ranked
```

`rank_candidates_tool` 只透传结构化结果，不再补写伪候选。

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python -m pytest tests/test_rank_candidates.py -k "passthrough or invalid_candidates or needs_more_candidates or ranked_for_valid_candidates" -v
python -m pytest tests/test_server_tools.py -q
```

Expected: PASS，且 `passthrough`、`invalid_candidates`、`needs_more_candidates`、`ranked` 四类结果都被显式覆盖，`action`、`mode`、`ranking_needed`、`ranked_candidates`、`suggested_search_hints` 的结构一致。

- [ ] **Step 5: Commit**

```bash
git add tastemate/core/ranker.py tastemate/tools/rank_candidates.py tests/test_rank_candidates.py tests/test_server_tools.py
git commit -m "feat: unify candidate ranking and downgrade payloads"
```

### Task 3: 保留 Hermes 回归路径，但不混入主路径

**Files:**
- Modify: `integrations/hermes/plugins/tastemate-route/__init__.py`
- Modify: `tests/test_hermes_route_plugin.py`

- [ ] **Step 1: Write the failing test**

```python
def test_operation_log_marks_fixed_probe_candidates_only_for_plugin_regression(tmp_path, monkeypatch):
    module = load_plugin()
    monkeypatch.setattr(module, "LOG_PATH", tmp_path / "tastemate-route.jsonl")
    ctx = FakeContext()
    module.register(ctx)

    ctx.hooks["pre_gateway_dispatch"](event=FakeEvent("@taste 推荐几个适合我的本地知识库工具"))

    content = (tmp_path / "tastemate-route.jsonl").read_text(encoding="utf-8")
    assert '"candidate_source": "fixed_probe_candidates"' in content
    assert '"dispatch_action": "ranked"' in content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_hermes_route_plugin.py -k fixed_probe -v`
Expected: FAIL if the regression boundary is not clearly recorded.

- [ ] **Step 3: Write minimal implementation**

```python
# 保留 fixed_probe_candidates 作为迭代一回归路径，
# 但不要把它描述成迭代二真实候选主路径。
log_record.update({
    "candidate_source": "fixed_probe_candidates",
    "candidate_count": len(candidates),
})
```

不要引入 `observed_tool_candidates`，也不要让插件日志暗示它已经代表真实候选路径。

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_hermes_route_plugin.py -q`
Expected: PASS，且日志中只有回归路径标记，没有主路径伪装。

- [ ] **Step 5: Commit**

```bash
git add integrations/hermes/plugins/tastemate-route/__init__.py tests/test_hermes_route_plugin.py
git commit -m "test: keep hermes route as fixed probe regression path"
```

### Task 4: 远端烟测与迭代收口

**Files:**
- Modify: `docs/iterations/iteration-002/status.md`
- Add: `docs/iterations/iteration-002/verification.md`
- Add: `docs/iterations/iteration-002/review.md`

- [ ] **Step 1: Write the failing verification checklist**

```markdown
## 验证目标

- `mcp_tastemate_rank_candidates` 收到真实 candidates。
- 用户给定候选路径和 Hermes 已有知识候选路径都能返回 `action=ranked` 或明确降级结果。
- `fixed_probe_candidates` 只出现在插件回归日志，不出现在真实候选验收主路径。
- facts 类问题返回 `action=passthrough`。
```

- [ ] **Step 2: Run local verification**

Run:

```bash
python -m pytest tests/test_rank_candidates.py -q
python -m pytest tests/test_server_tools.py -q
python -m pytest tests/test_hermes_route_plugin.py -q
python -m pytest -q
```

Expected: 全部通过。

- [ ] **Step 3: Run remote Hermes smoke check**

Run:

```bash
ssh -o BatchMode=yes -o ConnectTimeout=8 ubuntu@124.223.102.241 'docker inspect hermes --format "STATUS={{.State.Status}} RESTARTS={{.RestartCount}} IMAGE={{.Config.Image}}"'
```

Expected: `STATUS=running`，`RESTARTS=0`，镜像稳定。

- [ ] **Step 4: Run remote real-candidate verification**

Run:

```bash
ssh -o BatchMode=yes -o ConnectTimeout=8 ubuntu@124.223.102.241 'docker logs hermes --since 10m | rg "mcp_tastemate_rank_candidates|candidate_source|fixed_probe_candidates"'
ssh -o BatchMode=yes -o ConnectTimeout=8 ubuntu@124.223.102.241 'tail -n 50 /home/ubuntu/hermes-data/logs/tastemate-route.jsonl'
```

Expected:

```text
能看到 mcp_tastemate_rank_candidates completed 或等价成功证据。
真实候选验收路径中能看到 ranked 或明确降级 action。
真实候选验收路径中没有新增 fixed_probe_candidates 主路径记录。
如需要补充 candidates 参数证据，必须把实际调用参数或等价截图/日志摘录写入 verification.md。
```

- [ ] **Step 5: Write the verification record**

把真实候选验收结果写入 `docs/iterations/iteration-002/verification.md`，并把 `status.md` 更新为“Plan 已完成，等待 Build / 复核结果”或对应的实际阶段描述。

- [ ] **Step 6: Commit**

```bash
git add docs/iterations/iteration-002/status.md docs/iterations/iteration-002/verification.md docs/iterations/iteration-002/review.md
git commit -m "docs: prepare iteration 002 implementation and verification"
```

## 进入下一阶段条件

```text
1. 迭代二 Plan Review 无 BLOCK。
2. 本地 pytest 覆盖候选协议、排序降级和 Hermes 回归路径。
3. 远端 Hermes 真实调用烟测确认主服务稳定，且真实候选主路径没有回落到 fixed_probe_candidates。
```
