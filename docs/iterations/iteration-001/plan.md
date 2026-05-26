# Iteration 001 Plan：显式 @taste 后置重排闭环

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 交付一个本地 stdio MCP server，让 Hermes 在显式 `@taste` 场景下调用 TasteMate 完成候选后置重排、反馈记录和 profile 查询。

**Architecture:** TasteMate 作为独立 Python 包运行，不修改 Hermes 源码。MCP 层只注册工具并做输入输出适配；排序、反馈学习、profile 存储分别放在 `core/`、`tools/`、`storage/` 中，第一版使用 JSON 文件持久化和规则评分降级。

**Tech Stack:** Python 3.11+、`mcp` Python SDK、`pytest`、标准库 `json/pathlib/hashlib/datetime`。

---

## 外部事实确认

MCP Python SDK 采用官方 `modelcontextprotocol/python-sdk` v1.x README 作为依据。该 README 明确 `from mcp.server.fastmcp import FastMCP`、`@mcp.tool()`、`mcp.run()` 的 direct execution 用法，并说明 `dict[str, T]` 可作为结构化工具输出。

## 一、适用阶段

```text
Plan
```

本计划基于：

```text
docs/design.md
docs/iteration-plan.md
docs/development.md
docs/iterations/iteration-001/development.md
docs/iterations/iteration-001/review.md
```

当前仓库没有 `docs/iterations/iteration-001/design.md`。迭代一设计来源以项目级 `docs/design.md` 为准。

## 二、范围

本轮 Build 只包含：

```text
Python 包脚手架
stdio MCP server
rank_candidates
record_feedback
get_profile
JSON profile store
规则评分与可解释输出
反馈写入 evidence_log
单元测试与本地 smoke test
Hermes 配置接入说明与手工验证记录
```

本轮不做：

```text
不修改 Hermes 源码。
不实现搜索前偏好注入。
不实现 Hermes plugin/hook 自动编排。
不实现 UI。
不实现多用户系统。
不实现复杂推荐模型训练。
不把 SQLite 作为默认实现。
不保证 Hermes 一定自动重搜；TasteMate 只返回 suggested_search_hints。
```

## 三、分支或 Worktree 策略

Build 前必须使用独立分支或 worktree。

```text
推荐分支名：feat/iteration-001-tastemate-mcp
推荐 worktree：.worktrees/iteration-001-tastemate-mcp
原因：本轮会新增 Python 包、测试和文档，属于多文件功能开发。
```

执行者在进入 Build 前必须：

```bash
git status --short --branch
```

通过条件：

```text
已确认当前是否在独立分支或 worktree。
如仍在 main，先按 using-git-worktrees 规则创建隔离 workspace，或取得用户明确批准后再在当前目录执行。
不得覆盖用户已有未提交变更。
```

## 四、文件影响范围

新增：

```text
pyproject.toml
tastemate/__init__.py
tastemate/server.py
tastemate/tools/__init__.py
tastemate/tools/rank_candidates.py
tastemate/tools/record_feedback.py
tastemate/tools/get_profile.py
tastemate/core/__init__.py
tastemate/core/ranker.py
tastemate/core/feedback.py
tastemate/core/profile.py
tastemate/core/scoring.py
tastemate/storage/__init__.py
tastemate/storage/json_store.py
tastemate/schemas/__init__.py
tastemate/schemas/candidates.py
tastemate/schemas/feedback.py
tastemate/schemas/profile.py
tests/test_rank_candidates.py
tests/test_record_feedback.py
tests/test_profile_store.py
tests/test_server_tools.py
docs/iterations/iteration-001/verification.md
```

可修改：

```text
docs/iterations/iteration-001/review.md
```

禁止修改：

```text
Hermes 源码目录。
搜索前偏好注入相关 hook/plugin 文件。
与 TasteMate 迭代一无关的 UI、多用户、训练模块。
```

## 五、实现约定

### 默认 profile 路径

Plan 决定默认 profile 路径为：

```text
~/.tastemate/profile.json
```

覆盖方式：

```text
TASTEMATE_PROFILE_PATH=/absolute/path/profile.json
```

### LLM 策略

迭代一 Build 不实现真实 LLM 调用。

```text
TASTEMATE_LLM_PROVIDER、TASTEMATE_LLM_MODEL、TASTEMATE_LLM_API_KEY 只保留为后续扩展环境变量。
rank_candidates 第一版使用规则评分，依赖 query、candidate 字段、candidate metadata 和 profile.evidence_log。
当候选缺少 summary 且无法可靠评分时，返回 low_confidence。
```

这样可以满足本轮闭环，同时避免把未验证模型行为写成硬保证。

规则评分含义：

```text
query_relevance：候选是否回答当前问题，是后置重排门槛。
preference_fit：候选是否符合个人偏好，只在相关候选之间调整顺序。
feedback_score：历史反馈抽取出的 feature 对本轮候选的轻微信号，优先按 feature 泛化。
final_score：仅用于 Hermes 本轮候选排序，不是候选永久质量分。
```

### 反馈上下文策略

用户不需要在反馈消息里再次输入 `@taste`。

```text
上一轮不是 @taste 推荐结果：TasteMate 不介入，不调用 record_feedback。
上一轮是 @taste 推荐结果：用户后续明确选择、否定或表达偏好时，Hermes 可以调用 record_feedback。
record_feedback 必须接收上一轮 query、用户反馈文本、候选快照、selected/rejected candidate ids。
```

如果 Hermes 不能稳定基于上一轮上下文调用 `record_feedback`，Verify 必须记录为未验证项或失败项；不得在迭代一引入 Hermes plugin/hook 自动编排。

### 工具函数边界

MCP 工具函数只做适配：

```text
rank_candidates 工具：调用 core.ranker。
record_feedback 工具：调用 core.feedback 和 storage.json_store。
get_profile 工具：读取 JSON profile 并生成 summary。
```

## 六、任务清单

### Task 1: 项目脚手架与依赖

**Files:**

- Create: `pyproject.toml`
- Create: `tastemate/__init__.py`
- Create: `tastemate/core/__init__.py`
- Create: `tastemate/tools/__init__.py`
- Create: `tastemate/storage/__init__.py`
- Create: `tastemate/schemas/__init__.py`

- [ ] **Step 1: 创建 Python 包配置**

写入 `pyproject.toml`：

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "tastemate"
version = "0.1.0"
description = "Local TasteMate MCP server for explicit @taste candidate reranking"
readme = "docs/design.md"
requires-python = ">=3.11"
dependencies = [
  "mcp>=1.0.0",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.0.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

- [ ] **Step 2: 创建包初始化文件**

写入 `tastemate/__init__.py`：

```python
"""TasteMate MCP server package."""

__all__ = ["__version__"]

__version__ = "0.1.0"
```

其余 `__init__.py` 写入：

```python
"""TasteMate module namespace."""
```

- [ ] **Step 3: 安装开发依赖**

Run:

```bash
python -m pip install -e ".[dev]"
```

Expected:

```text
Successfully installed tastemate
```

如果网络或权限导致安装失败，按环境权限规则请求用户批准后重试，不得改用未记录的依赖方案。

- [ ] **Step 4: 运行空测试基线**

Run:

```bash
pytest -q
```

Expected:

```text
no tests ran
```

或 pytest exit code 5。此结果只作为脚手架基线记录，不代表功能通过。

### Task 2: Schema 与 Candidate 规范化

**Files:**

- Create: `tastemate/schemas/candidates.py`
- Test: `tests/test_rank_candidates.py`

- [ ] **Step 1: 写失败测试：缺失 id/title/summary 的候选可被规范化**

在 `tests/test_rank_candidates.py` 写入：

```python
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
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
pytest tests/test_rank_candidates.py -q
```

Expected:

```text
ModuleNotFoundError: No module named 'tastemate.schemas.candidates'
```

- [ ] **Step 3: 实现 Candidate 规范化**

写入 `tastemate/schemas/candidates.py`：

```python
from __future__ import annotations

import hashlib
from typing import Any


def _stable_id(parts: list[str]) -> str:
    source = "|".join(part.strip() for part in parts if part and part.strip())
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]
    return f"candidate-{digest}"


def normalize_candidate(raw: dict[str, Any]) -> dict[str, Any]:
    title = str(raw.get("title") or raw.get("url") or raw.get("source") or "Untitled candidate")
    summary = str(raw.get("summary") or "")
    url = raw.get("url")
    source = raw.get("source")
    metadata = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
    candidate_id = raw.get("id") or _stable_id([title, str(url or ""), summary])

    return {
        "id": str(candidate_id),
        "title": title,
        "summary": summary,
        "url": url,
        "source": source,
        "metadata": metadata,
    }


def normalize_candidates(raw_candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [normalize_candidate(item) for item in raw_candidates]
```

- [ ] **Step 4: 运行测试确认通过**

Run:

```bash
pytest tests/test_rank_candidates.py -q
```

Expected:

```text
2 passed
```

### Task 3: JSON Profile Store

**Files:**

- Create: `tastemate/storage/json_store.py`
- Create: `tastemate/schemas/profile.py`
- Test: `tests/test_profile_store.py`

- [ ] **Step 1: 写失败测试：profile 文件不存在时初始化默认结构**

写入 `tests/test_profile_store.py`：

```python
import json

import pytest

from tastemate.storage.json_store import CorruptProfileError, JsonProfileStore


def test_profile_store_initializes_default_profile(tmp_path):
    path = tmp_path / "profile.json"
    store = JsonProfileStore(path)

    profile = store.load()

    assert profile == {
        "stable_preferences": {},
        "negative_preferences": {},
        "current_focus": {},
        "evidence_log": [],
    }
    assert json.loads(path.read_text()) == profile


def test_profile_store_does_not_overwrite_corrupt_file(tmp_path):
    path = tmp_path / "profile.json"
    path.write_text("{not-json", encoding="utf-8")
    store = JsonProfileStore(path)

    with pytest.raises(CorruptProfileError):
        store.load()

    assert path.read_text(encoding="utf-8") == "{not-json"
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
pytest tests/test_profile_store.py -q
```

Expected:

```text
ModuleNotFoundError: No module named 'tastemate.storage.json_store'
```

- [ ] **Step 3: 实现默认 profile schema**

写入 `tastemate/schemas/profile.py`：

```python
from __future__ import annotations

from copy import deepcopy
from typing import Any

DEFAULT_PROFILE: dict[str, Any] = {
    "stable_preferences": {},
    "negative_preferences": {},
    "current_focus": {},
    "evidence_log": [],
}


def default_profile() -> dict[str, Any]:
    return deepcopy(DEFAULT_PROFILE)


def normalize_profile(raw: dict[str, Any]) -> dict[str, Any]:
    profile = default_profile()
    for key in profile:
        if key in raw and isinstance(raw[key], type(profile[key])):
            profile[key] = raw[key]
    return profile
```

- [ ] **Step 4: 实现 JSON store**

写入 `tastemate/storage/json_store.py`：

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tastemate.schemas.profile import default_profile, normalize_profile


class CorruptProfileError(ValueError):
    """Raised when the profile file exists but is not valid JSON."""


class JsonProfileStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser()

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            profile = default_profile()
            self.save(profile)
            return profile

        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CorruptProfileError(f"Profile file is corrupt: {self.path}") from exc

        if not isinstance(raw, dict):
            return default_profile()
        return normalize_profile(raw)

    def save(self, profile: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        normalized = normalize_profile(profile)
        self.path.write_text(
            json.dumps(normalized, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
```

- [ ] **Step 5: 运行测试确认通过**

Run:

```bash
pytest tests/test_profile_store.py -q
```

Expected:

```text
2 passed
```

### Task 4: Ranker 与评分

**Files:**

- Create: `tastemate/core/scoring.py`
- Create: `tastemate/core/ranker.py`
- Modify: `tests/test_rank_candidates.py`

- [ ] **Step 1: 写失败测试：事实类问题 passthrough**

追加到 `tests/test_rank_candidates.py`：

```python
from tastemate.core.ranker import Ranker


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
```

- [ ] **Step 2: 写失败测试：候选不足时 needs_more_candidates**

追加：

```python
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
```

- [ ] **Step 3: 写失败测试：带 @taste 的事实类问题仍 passthrough**

追加：

```python
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
```

`@taste` 只表示允许 TasteMate 介入，不等于推荐意图。事实类问题仍应返回 passthrough。

- [ ] **Step 4: 写失败测试：推荐候选输出结构化评分**

追加：

```python
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
```

- [ ] **Step 5: 写失败测试：信息不足时 low_confidence**

追加：

```python
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
```

- [ ] **Step 6: 写失败测试：历史 feature feedback 可影响新候选**

追加：

```python
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
```

- [ ] **Step 7: 运行测试确认失败**

Run:

```bash
pytest tests/test_rank_candidates.py -q
```

Expected:

```text
ModuleNotFoundError: No module named 'tastemate.core.ranker'
```

- [ ] **Step 8: 实现评分函数**

写入 `tastemate/core/scoring.py`：

```python
from __future__ import annotations

from typing import Any

POSITIVE_TERMS = ("local", "local-first", "self-hosted", "open source", "mcp", "plugin", "low maintenance")
NEGATIVE_TERMS = ("enterprise", "sales", "saas", "cloud required", "vendor lock")


def clamp(value: float) -> float:
    return max(0.0, min(1.0, round(value, 4)))


def query_relevance(query: str, candidate: dict[str, Any]) -> tuple[float, list[str], list[str]]:
    text = f"{candidate.get('title', '')} {candidate.get('summary', '')}".lower()
    query_lower = query.lower()
    score = 0.55
    reasons: list[str] = []
    risks: list[str] = []

    if not candidate.get("summary"):
        risks.append("候选缺少 summary，相关性置信度较低")
        score -= 0.25
    if "知识库" in query or "knowledge" in query_lower:
        if "knowledge" in text or "知识" in text or "note" in text:
            score += 0.25
            reasons.append("候选内容与知识库需求相关")
    if "推荐" in query or "@taste" in query:
        score += 0.1
    return clamp(score), reasons, risks


def preference_fit(candidate: dict[str, Any]) -> tuple[float, list[str], list[str]]:
    metadata = candidate.get("metadata") if isinstance(candidate.get("metadata"), dict) else {}
    text = f"{candidate.get('title', '')} {candidate.get('summary', '')}".lower()
    score = 0.5
    reasons: list[str] = []
    risks: list[str] = []

    if metadata.get("open_source") or "open source" in text or "开源" in text:
        score += 0.18
        reasons.append("符合开源偏好")
    if metadata.get("local_first") or "local-first" in text or "self-hosted" in text or "本地" in text:
        score += 0.22
        reasons.append("符合本地优先偏好")
    if metadata.get("supports_mcp") or "mcp" in text:
        score += 0.08
        reasons.append("具备外置集成友好信号")
    if metadata.get("cloud_required") or "cloud required" in text:
        score -= 0.18
        risks.append("存在云端依赖风险")
    if metadata.get("enterprise_oriented") or "enterprise" in text:
        score -= 0.12
        risks.append("存在企业化复杂度风险")
    return clamp(score), reasons, risks


def feedback_score(candidate: dict[str, Any], profile: dict[str, Any]) -> tuple[float, list[str]]:
    evidence_log = profile.get("evidence_log", []) if isinstance(profile, dict) else []
    features = _candidate_features(candidate)
    score = 0.5
    reasons: list[str] = []

    for evidence in evidence_log:
        if not isinstance(evidence, dict):
            continue
        feature = evidence.get("feature")
        if feature not in features:
            continue
        strength = float(evidence.get("strength", 0.0))
        if evidence.get("direction") == "positive":
            score += min(strength, 1.0) * 0.15
            reasons.append(f"历史反馈对 {feature} 有正向信号")
        if evidence.get("direction") == "negative":
            score -= min(strength, 1.0) * 0.15
            reasons.append(f"历史反馈对 {feature} 有负向信号")
    return clamp(score), reasons


def _candidate_features(candidate: dict[str, Any]) -> set[str]:
    metadata = candidate.get("metadata") if isinstance(candidate.get("metadata"), dict) else {}
    text = f"{candidate.get('title', '')} {candidate.get('summary', '')}".lower()
    features: set[str] = set()
    if metadata.get("local_first") or "local-first" in text or "self-hosted" in text or "本地" in text:
        features.add("local_first")
    if metadata.get("open_source") or "open source" in text or "开源" in text:
        features.add("open_source")
    if metadata.get("supports_mcp") or "mcp" in text:
        features.add("supports_mcp")
    if metadata.get("cloud_required") or "cloud" in text or "saas" in text:
        features.add("cloud_required")
    if metadata.get("enterprise_oriented") or "enterprise" in text:
        features.add("enterprise_oriented")
    if not features:
        features.add("general_preference")
    return features
```

- [ ] **Step 9: 实现 Ranker**

写入 `tastemate/core/ranker.py`：

```python
from __future__ import annotations

from typing import Any

from tastemate.core.scoring import feedback_score, preference_fit, query_relevance
from tastemate.schemas.candidates import normalize_candidates

FACTUAL_MARKERS = ("在哪", "是什么", "配置文件", "路径", "when", "where", "what is")
RECOMMENDATION_MARKERS = ("推荐", "适合我的", "几个", "compare", "recommend")


class Ranker:
    def __init__(self, profile: dict[str, Any]) -> None:
        self.profile = profile

    def rank(self, query: str, candidates: list[dict[str, Any]], taste_mode: str = "force") -> dict[str, Any]:
        normalized = normalize_candidates(candidates)
        if self._is_factual(query):
            return {
                "ranking_needed": False,
                "mode": "factual",
                "action": "passthrough",
                "reason": "确定性事实问题或没有可排序候选集合",
            }

        if not normalized:
            return {
                "ranking_needed": False,
                "mode": "recommendation",
                "action": "passthrough",
                "reason": "没有候选集合，无法执行后置排序",
            }

        if self._is_recommendation(query) and len(normalized) < 2:
            return {
                "ranking_needed": True,
                "mode": "recommendation",
                "action": "needs_more_candidates",
                "reason": "候选数量不足或缺少关键方向",
                "suggested_search_hints": [
                    "local-first knowledge base open source",
                    "self-hosted note taking app",
                    "MCP compatible personal knowledge base",
                ],
            }

        if any(not candidate.get("summary") for candidate in normalized):
            return {
                "ranking_needed": True,
                "mode": "recommendation",
                "action": "low_confidence",
                "reason": "候选信息不足，无法给出可靠排序",
                "ranked_candidates": [],
                "suggested_search_hints": ["补充每个候选的 summary、来源和关键约束"],
                "risks": ["评分置信度不足"],
            }

        ranked = [self._score_candidate(query, candidate) for candidate in normalized]
        ranked.sort(key=lambda item: item["final_score"], reverse=True)
        return {
            "ranking_needed": True,
            "mode": "recommendation",
            "action": "ranked",
            "ranked_candidates": ranked,
        }

    def _score_candidate(self, query: str, candidate: dict[str, Any]) -> dict[str, Any]:
        relevance, relevance_reasons, relevance_risks = query_relevance(query, candidate)
        fit, fit_reasons, fit_risks = preference_fit(candidate)
        history, history_reasons = feedback_score(candidate, self.profile)
        if relevance < 0.35:
            fit = min(fit, 0.35)
        final = round(relevance * 0.55 + fit * 0.30 + history * 0.15, 4)
        return {
            "id": candidate["id"],
            "title": candidate["title"],
            "final_score": final,
            "query_relevance": relevance,
            "preference_fit": fit,
            "feedback_score": history,
            "reasons": relevance_reasons + fit_reasons + history_reasons or ["候选满足基本排序条件"],
            "risks": relevance_risks + fit_risks,
        }

    def _is_factual(self, query: str) -> bool:
        query_lower = query.lower()
        return any(marker in query_lower for marker in FACTUAL_MARKERS) and not self._is_recommendation(query)

    def _is_recommendation(self, query: str) -> bool:
        query_lower = query.lower()
        return any(marker in query_lower for marker in RECOMMENDATION_MARKERS)
```

- [ ] **Step 10: 运行测试确认通过**

Run:

```bash
pytest tests/test_rank_candidates.py -q
```

Expected:

```text
8 passed
```

### Task 5: Feedback Processor 与 profile 更新限制

**Files:**

- Create: `tastemate/schemas/feedback.py`
- Create: `tastemate/core/feedback.py`
- Modify: `tests/test_record_feedback.py`

- [ ] **Step 1: 写失败测试：明确反馈写入 evidence_log**

写入 `tests/test_record_feedback.py`：

```python
from tastemate.core.feedback import FeedbackProcessor


def test_record_feedback_writes_evidence():
    profile = {
        "stable_preferences": {},
        "negative_preferences": {},
        "current_focus": {},
        "evidence_log": [],
    }

    result = FeedbackProcessor(profile).record(
        query="@taste 推荐几个适合我的本地知识库工具",
        user_feedback="我选 local-open，不要 cloud-enterprise",
        selected_candidate_ids=["local-open"],
        rejected_candidate_ids=["cloud-enterprise"],
        candidates_snapshot=[
            {"id": "local-open", "title": "Local Open", "summary": "Open source local-first tool."},
            {"id": "cloud-enterprise", "title": "Cloud Enterprise", "summary": "Enterprise SaaS."},
        ],
    )

    assert result["feedback_valid"] is True
    assert result["signal_strength"] == 0.7
    assert result["extracted_signals"]
    assert len(profile["evidence_log"]) == 2
    assert profile["evidence_log"][0]["source"] == "explicit_user_feedback"
```

该测试里的 `user_feedback` 不包含 `@taste`。这表示反馈消息本身不需要显式触发词；是否调用 `record_feedback` 由 Hermes 根据上一轮 `@taste` 推荐上下文决定。

- [ ] **Step 2: 写失败测试：单次反馈不得新增 stable_preferences**

追加：

```python
def test_record_feedback_does_not_create_stable_preference_from_single_event():
    profile = {
        "stable_preferences": {},
        "negative_preferences": {},
        "current_focus": {},
        "evidence_log": [],
    }

    FeedbackProcessor(profile).record(
        query="@taste 推荐几个工具",
        user_feedback="我喜欢本地优先",
        selected_candidate_ids=["a"],
        rejected_candidate_ids=[],
        candidates_snapshot=[{"id": "a", "title": "A", "summary": "local-first"}],
    )

    assert profile["stable_preferences"] == {}
```

- [ ] **Step 3: 写失败测试：已有 stable_preferences 权重增量与 confidence 上限受限**

追加：

```python
def test_record_feedback_limits_stable_preference_weight_delta_and_confidence():
    profile = {
        "stable_preferences": {
            "local_first": {
                "weight": 0.5,
                "confidence": 0.68,
                "evidence_count": 2,
                "last_seen": "2026-05-26T00:00:00+08:00",
            }
        },
        "negative_preferences": {},
        "current_focus": {},
        "evidence_log": [],
    }

    FeedbackProcessor(profile).record(
        query="@taste 推荐几个工具",
        user_feedback="我明确选择本地优先方案",
        selected_candidate_ids=["a"],
        rejected_candidate_ids=[],
        candidates_snapshot=[{"id": "a", "title": "A", "summary": "local-first"}],
    )

    updated = profile["stable_preferences"]["local_first"]
    assert updated["weight"] <= 0.6
    assert updated["confidence"] <= 0.7
```

- [ ] **Step 4: 运行测试确认失败**

Run:

```bash
pytest tests/test_record_feedback.py -q
```

Expected:

```text
ModuleNotFoundError: No module named 'tastemate.core.feedback'
```

- [ ] **Step 5: 实现反馈 schema 辅助函数**

写入 `tastemate/schemas/feedback.py`：

```python
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def make_evidence(
    *,
    query: str,
    candidate_id: str,
    feature: str,
    direction: str,
    strength: float,
    event_type: str,
) -> dict[str, Any]:
    return {
        "timestamp": now_iso(),
        "event_type": event_type,
        "query": query,
        "candidate_id": candidate_id,
        "feature": feature,
        "direction": direction,
        "strength": strength,
        "source": "explicit_user_feedback",
    }
```

- [ ] **Step 6: 实现 FeedbackProcessor**

写入 `tastemate/core/feedback.py`：

```python
from __future__ import annotations

from typing import Any

from tastemate.schemas.feedback import make_evidence, now_iso


class FeedbackProcessor:
    def __init__(self, profile: dict[str, Any]) -> None:
        self.profile = profile

    def record(
        self,
        *,
        query: str,
        user_feedback: str,
        selected_candidate_ids: list[str],
        rejected_candidate_ids: list[str],
        candidates_snapshot: list[dict[str, Any]],
    ) -> dict[str, Any]:
        selected = [str(item) for item in selected_candidate_ids]
        rejected = [str(item) for item in rejected_candidate_ids]
        feedback_valid = bool(user_feedback.strip()) and bool(selected or rejected)
        if not feedback_valid:
            return {
                "feedback_valid": False,
                "signal_strength": 0.0,
                "extracted_signals": [],
                "profile_updates": [],
            }

        candidates_by_id = {str(item.get("id")): item for item in candidates_snapshot}
        extracted_signals: list[dict[str, Any]] = []
        evidence_log = self.profile.setdefault("evidence_log", [])

        for candidate_id in selected:
            feature = self._extract_feature(candidates_by_id.get(candidate_id, {}), user_feedback)
            evidence = make_evidence(
                query=query,
                candidate_id=candidate_id,
                feature=feature,
                direction="positive",
                strength=0.7,
                event_type="selected",
            )
            evidence_log.append(evidence)
            extracted_signals.append({"feature": feature, "direction": "positive", "candidate_id": candidate_id})
            self._conservatively_update_existing_stable_preference(feature, 0.10)

        for candidate_id in rejected:
            feature = self._extract_feature(candidates_by_id.get(candidate_id, {}), user_feedback)
            evidence = make_evidence(
                query=query,
                candidate_id=candidate_id,
                feature=feature,
                direction="negative",
                strength=0.7,
                event_type="rejected",
            )
            evidence_log.append(evidence)
            extracted_signals.append({"feature": feature, "direction": "negative", "candidate_id": candidate_id})

        self.profile["current_focus"] = {
            "last_query": query,
            "last_feedback": user_feedback,
            "last_seen": now_iso(),
        }

        return {
            "feedback_valid": True,
            "signal_strength": 0.7,
            "extracted_signals": extracted_signals,
            "profile_updates": [{"section": "evidence_log", "count": len(extracted_signals)}],
        }

    def _extract_feature(self, candidate: dict[str, Any], user_feedback: str) -> str:
        text = f"{candidate.get('title', '')} {candidate.get('summary', '')} {user_feedback}".lower()
        if "local" in text or "本地" in text:
            return "local_first"
        if "open source" in text or "开源" in text:
            return "open_source"
        if "cloud" in text or "saas" in text:
            return "cloud_required"
        return "general_preference"

    def _conservatively_update_existing_stable_preference(self, feature: str, delta: float) -> None:
        stable = self.profile.setdefault("stable_preferences", {})
        if feature not in stable:
            return
        current = stable[feature]
        old_weight = float(current.get("weight", 0.0))
        old_confidence = float(current.get("confidence", 0.0))
        current["weight"] = round(min(1.0, old_weight + min(delta, 0.10)), 4)
        current["confidence"] = round(min(0.70, old_confidence + 0.02), 4)
        current["evidence_count"] = int(current.get("evidence_count", 0)) + 1
        current["last_seen"] = now_iso()
```

- [ ] **Step 7: 运行测试确认通过**

Run:

```bash
pytest tests/test_record_feedback.py -q
```

Expected:

```text
3 passed
```

### Task 6: Tools 适配层

**Files:**

- Create: `tastemate/core/profile.py`
- Create: `tastemate/tools/rank_candidates.py`
- Create: `tastemate/tools/record_feedback.py`
- Create: `tastemate/tools/get_profile.py`
- Test: `tests/test_server_tools.py`

- [ ] **Step 1: 写失败测试：tool 层使用 JSON profile store**

写入 `tests/test_server_tools.py`：

```python
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
            {"id": "a", "title": "Local", "summary": "Open source local-first knowledge base."},
            {"id": "b", "title": "Cloud", "summary": "Enterprise SaaS knowledge base."},
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
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
pytest tests/test_server_tools.py -q
```

Expected:

```text
ModuleNotFoundError: No module named 'tastemate.tools.get_profile'
```

- [ ] **Step 3: 实现 rank_candidates tool**

写入 `tastemate/tools/rank_candidates.py`：

```python
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from tastemate.core.ranker import Ranker
from tastemate.storage.json_store import JsonProfileStore

DEFAULT_PROFILE_PATH = "~/.tastemate/profile.json"


def resolve_profile_path(profile_path: str | Path | None = None) -> Path:
    return Path(profile_path or os.environ.get("TASTEMATE_PROFILE_PATH", DEFAULT_PROFILE_PATH)).expanduser()


def rank_candidates_tool(
    *,
    query: str,
    candidates: list[dict[str, Any]],
    taste_mode: str = "force",
    profile_path: str | Path | None = None,
) -> dict[str, Any]:
    profile = JsonProfileStore(resolve_profile_path(profile_path)).load()
    return Ranker(profile).rank(query=query, candidates=candidates, taste_mode=taste_mode)
```

- [ ] **Step 4: 实现 profile summary**

写入 `tastemate/core/profile.py`：

```python
from __future__ import annotations

from typing import Any


def summarize_profile(profile: dict[str, Any]) -> str:
    stable = profile.get("stable_preferences", {})
    current = profile.get("current_focus", {})
    evidence_count = len(profile.get("evidence_log", []))
    if stable:
        names = ", ".join(sorted(stable.keys()))
        return f"当前稳定偏好：{names}。"
    if evidence_count:
        last_query = current.get("last_query", "未知问题")
        return f"已有 {evidence_count} 条反馈证据，最近关注：{last_query}。"
    return "当前暂无稳定偏好。"
```

- [ ] **Step 5: 实现 record_feedback tool**

写入 `tastemate/tools/record_feedback.py`：

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

from tastemate.core.feedback import FeedbackProcessor
from tastemate.storage.json_store import JsonProfileStore
from tastemate.tools.rank_candidates import resolve_profile_path


def record_feedback_tool(
    *,
    query: str,
    user_feedback: str,
    selected_candidate_ids: list[str],
    rejected_candidate_ids: list[str],
    candidates_snapshot: list[dict[str, Any]],
    profile_path: str | Path | None = None,
) -> dict[str, Any]:
    store = JsonProfileStore(resolve_profile_path(profile_path))
    profile = store.load()
    result = FeedbackProcessor(profile).record(
        query=query,
        user_feedback=user_feedback,
        selected_candidate_ids=selected_candidate_ids,
        rejected_candidate_ids=rejected_candidate_ids,
        candidates_snapshot=candidates_snapshot,
    )
    store.save(profile)
    return result
```

- [ ] **Step 6: 实现 get_profile tool**

写入 `tastemate/tools/get_profile.py`：

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

from tastemate.core.profile import summarize_profile
from tastemate.storage.json_store import JsonProfileStore
from tastemate.tools.rank_candidates import resolve_profile_path


def get_profile_tool(profile_path: str | Path | None = None) -> dict[str, Any]:
    profile = JsonProfileStore(resolve_profile_path(profile_path)).load()
    return {
        "stable_preferences": profile["stable_preferences"],
        "negative_preferences": profile["negative_preferences"],
        "current_focus": profile["current_focus"],
        "summary": summarize_profile(profile),
    }
```

- [ ] **Step 7: 运行测试确认通过**

Run:

```bash
pytest tests/test_server_tools.py -q
```

Expected:

```text
3 passed
```

### Task 7: MCP Server

**Files:**

- Create: `tastemate/server.py`
- Modify: `tests/test_server_tools.py`

- [ ] **Step 1: 写失败测试：server 暴露 app 对象**

追加到 `tests/test_server_tools.py`：

```python
def test_server_exports_mcp_app():
    from tastemate.server import mcp

    assert mcp.name == "tastemate"
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
pytest tests/test_server_tools.py::test_server_exports_mcp_app -q
```

Expected:

```text
ModuleNotFoundError: No module named 'tastemate.server'
```

- [ ] **Step 3: 实现 MCP server**

写入 `tastemate/server.py`：

```python
from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from tastemate.tools.get_profile import get_profile_tool
from tastemate.tools.rank_candidates import rank_candidates_tool
from tastemate.tools.record_feedback import record_feedback_tool

mcp = FastMCP("tastemate")


@mcp.tool()
def rank_candidates(query: str, candidates: list[dict[str, Any]], taste_mode: str = "force") -> dict[str, Any]:
    """Rank recommendation candidates when the user explicitly asks with @taste."""
    return rank_candidates_tool(query=query, candidates=candidates, taste_mode=taste_mode)


@mcp.tool()
def record_feedback(
    query: str,
    user_feedback: str,
    selected_candidate_ids: list[str],
    rejected_candidate_ids: list[str],
    candidates_snapshot: list[dict[str, Any]],
) -> dict[str, Any]:
    """Record explicit user feedback after a TasteMate-ranked answer."""
    return record_feedback_tool(
        query=query,
        user_feedback=user_feedback,
        selected_candidate_ids=selected_candidate_ids,
        rejected_candidate_ids=rejected_candidate_ids,
        candidates_snapshot=candidates_snapshot,
    )


@mcp.tool()
def get_profile() -> dict[str, Any]:
    """Return the current local TasteMate profile summary."""
    return get_profile_tool()


if __name__ == "__main__":
    mcp.run()
```

- [ ] **Step 4: 运行 server 单测**

Run:

```bash
pytest tests/test_server_tools.py -q
```

Expected:

```text
4 passed
```

- [ ] **Step 5: 执行 MCP stdio smoke test**

Run:

```bash
python -m tastemate.server
```

Expected:

```text
进程保持运行并等待 stdio 输入；使用 Ctrl+C 结束。
```

如果 SDK 版本导致 `FastMCP` API 不兼容，停止实现并更新 Plan Review，不得猜测替代 API。

### Task 8: 全量 Verify 与验证记录

**Files:**

- Create: `docs/iterations/iteration-001/verification.md`

- [ ] **Step 1: 执行全量单元测试**

Run:

```bash
pytest -q
```

Expected:

```text
全部测试通过，失败数为 0。
```

- [ ] **Step 2: 执行 import smoke test**

Run:

```bash
python -c "from tastemate.server import mcp; print(mcp.name)"
```

Expected:

```text
tastemate
```

- [ ] **Step 3: 执行变更范围检查**

Run:

```bash
git status --short
git diff --name-only
```

Expected:

```text
变更只包含 TasteMate 仓库内文件。
没有 Hermes 源码路径。
```

- [ ] **Step 4: 写验证记录**

执行 Step 1 到 Step 3 后，才能写入 `docs/iterations/iteration-001/verification.md`。文件必须包含真实命令、真实输出摘要、退出码、失败数、手工验证结论、未验证项和失败项；不得预先写占位结论。

必须写入的验收映射：

```text
A-001：普通问题未使用 @taste，手工观察 Hermes 无 mcp_tastemate_* 调用。
A-002：@taste 推荐类问题，手工观察 Hermes 调用 rank_candidates。
A-003：pytest 覆盖事实类问题返回 passthrough。
A-004：pytest 覆盖候选不足返回 needs_more_candidates。
A-005：pytest 覆盖推荐候选输出 query_relevance、preference_fit、final_score。
A-006：pytest 覆盖明确反馈写入 evidence_log。
A-007：pytest 覆盖单次反馈限制 stable_preferences 更新。
A-008：git 变更范围检查不包含 Hermes 源码。
```

手工验证步骤必须逐条记录结果：

```text
1. 在 Hermes 配置中临时接入 TasteMate MCP server。
2. 输入普通问题，确认无 mcp_tastemate_* 调用。
3. 输入 @taste 推荐几个适合我的本地知识库工具。
4. 确认 Hermes 调用 mcp_tastemate_rank_candidates。
5. 输入 @taste Hermes 的 MCP 配置文件在哪？
6. 确认 TasteMate 返回 passthrough 或 Hermes 不触发排序。
7. 对推荐结果给出明确反馈，例如“我选第一个，不要企业 SaaS”。
8. 确认 mcp_tastemate_record_feedback 写入 evidence_log。
```

服务器 Hermes 部署验证必须补充：

```text
TasteMate 作为服务器上的外部 stdio MCP server 接入 Hermes，不修改 Hermes 源码。
推荐在服务器使用独立目录和虚拟环境，例如 /opt/tastemate/.venv/bin/python -m tastemate.server。
Hermes 的 ~/.hermes/config.yaml 只追加 mcp_servers.tastemate，不覆盖其他 MCP server。
TASTEMATE_PROFILE_PATH 指向服务器可持久化路径，例如 /var/lib/tastemate/profile.json。
验证必须记录 Hermes 部署方式、重启命令、配置片段、工具发现日志、每个用例的工具调用结果和 profile evidence_log 变化。
回滚方式是移除或注释 mcp_servers.tastemate 并重启 Hermes。
```

## 七、验收标准与任务映射

| ID | 标准 | 覆盖任务 |
| --- | --- | --- |
| A-001 | 未使用 @taste 时 TasteMate 不介入 | Task 8 手工验证 |
| A-002 | @taste 推荐类问题触发 rank_candidates | Task 7、Task 8 手工验证 |
| A-003 | 事实类问题返回 passthrough | Task 4 |
| A-004 | 候选不足时返回 needs_more_candidates | Task 4 |
| A-005 | 推荐类候选输出结构化评分 | Task 4 |
| A-006 | 用户明确反馈写入 evidence_log | Task 5、Task 6 |
| A-007 | 单次反馈写 evidence_log 且限制 stable_preferences | Task 5 |
| A-008 | 不修改 Hermes 源码 | Task 8 变更范围检查 |

## 八、风险处理

### MCP SDK API 不兼容

处理：

```text
停止 Build。
记录实际错误。
用官方 MCP Python SDK 文档确认当前 FastMCP API。
更新本计划或 Development Spec 后再继续。
```

### Hermes 未稳定调用 rank_candidates

处理：

```text
不在迭代一修改 Hermes 源码。
在 verification.md 记录为未通过或未验证项。
进入 Multi-Agent Review，由用户决定是否进入迭代三的 plugin/hook 编排。
```

### 规则评分个性化不足

处理：

```text
只要结构化评分、解释、反馈写入和后续排序使用 evidence 成立，迭代一可验收。
真实 LLM 评分留作后续增强，不作为当前 BLOCK。
```

### Profile 文件损坏

处理：

```text
JsonProfileStore.load 抛出 CorruptProfileError。
不得覆盖原文件。
MCP tool 层如遇该异常，应在后续修复中返回结构化 error；本计划第一轮测试已覆盖 store 不覆盖损坏文件。
```

## 九、回滚或降级思路

### 代码回滚

```text
如 Build 后出现阻塞问题，回滚本轮新增的 tastemate/、tests/、pyproject.toml 和 verification.md。
不得回滚用户在本轮前已有的文档或未提交变更。
```

### 运行降级

```text
如 MCP server 无法启动，Hermes 移除或禁用 tastemate mcp_servers 配置后应继续普通回答。
如 rank_candidates 无法可靠评分，返回 action=low_confidence，不伪装成 ranked。
如候选不足，返回 needs_more_candidates 和 suggested_search_hints，不强制 Hermes 重搜。
如 record_feedback 无法识别明确反馈，返回 feedback_valid=false，不更新 stable_preferences。
```

### 数据降级

```text
如 profile 文件不存在，初始化默认 profile。
如 profile 文件损坏，保留原文件并返回错误，不覆盖损坏内容。
如用户需要清空 TasteMate 学习结果，可在确认后移走 ~/.tastemate/profile.json；该动作不在自动 Build 步骤内执行。
```

## 十、Plan Review 要求

进入 Build 前必须完成 Plan Review。

默认审核角色：

```text
Design Reviewer
Architecture Reviewer
Verification Reviewer
Documentation Reviewer
Implementation Reviewer
```

审核范围：

```text
docs/iterations/iteration-001/plan.md
```

审核结论只能是：

```text
PASS
BLOCK
FOLLOW_UP
```

Build 进入条件：

```text
Plan Review 无 BLOCK。
用户确认可以进入 Build。
```

## 十一、执行顺序

```text
1. 完成 Plan Review。
2. 创建独立分支或 worktree。
3. Task 1 到 Task 7 按 TDD 顺序执行。
4. Task 8 执行 Verify 并写入真实证据。
5. 进入 Multi-Agent Review。
6. 无 BLOCK 后进入 Closeout。
```
