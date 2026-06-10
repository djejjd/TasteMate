# 迭代 003 反馈画像增强实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` 或 `superpowers:executing-plans` 按任务逐步执行。本计划使用 checkbox 跟踪进度。

**Goal:** 将迭代三落到“受控白名单反馈升级 + 有限排序生效 + 可解释画像输出”的本地可验收实现。

**Architecture:** `tastemate/core/feedback.py` 负责 feedback 有效性判断、strong/normal 分类、白名单特征抽取、evidence 写入和画像升级；`tastemate/core/scoring.py` 与 `tastemate/core/ranker.py` 只读画像并做有限加减分；`tastemate/tools/get_profile.py` 与 `tastemate/core/profile.py` 负责兼容输出和解释摘要。项目级 `docs/development.md` 只作为通用基线，本轮一切实现边界以 `docs/iterations/iteration-003/design.md` 与 `docs/iterations/iteration-003/development.md` 为准。

**Tech Stack:** Python 3.13, `pytest`, 本地 JSON profile store, FastMCP tool wrappers, 规则逻辑，无真实 LLM 调用。

---

## 计划输入

```text
Design：
- docs/iterations/iteration-003/design.md

Development Spec：
- docs/iterations/iteration-003/development.md

Review：
- docs/iterations/iteration-003/review.md
```

## 当前范围

```text
1. record_feedback 继续沿用现有输入协议。
2. 有效或可归档 feedback 写 evidence_log；完全 invalid feedback 不写 evidence_log。
3. strong 1 次升级、normal 2 次同向升级。
4. stable_preferences / negative_preferences / current_focus 生效到排序。
5. get_profile 输出长期正向、长期负向、当前关注、证据摘要。
6. 本地固定样例验证反馈前后排序变化。
```

## 不做事项

```text
1. 不修改 Hermes 源码。
2. 不做远端 feedback/evidence 主路径阻塞验收。
3. 不做搜索前偏好注入。
4. 不做 observed_tool_candidates。
5. 不引入 sqlite_store.py、llm/*、真实 LLM 评分。
6. 不做复杂衰减模型、高级冲突求解、UI、多用户、Obsidian 偏好底座。
```

## 分支或 Worktree 策略

```text
需要独立分支或 worktree：是。
原因：迭代三会修改 core、tools、schemas、storage、tests 和 docs，多文件变更且需要多轮 review，不应直接在 main 上开发。
建议：进入 Build 前使用独立 worktree 或 feature branch。
```

---

### Task 1: 锁定 profile schema 与白名单基础能力

**Files:**
- Modify: `tastemate/schemas/profile.py`
- Modify: `tastemate/core/profile.py`
- Test: `tests/test_profile_store.py`
- Test: `tests/test_server_tools.py`

- [ ] **Step 1: Write the failing test**

```python
from tastemate.schemas.profile import normalize_profile


def test_normalize_profile_backfills_iteration003_sections():
    profile = normalize_profile(
        {
            "stable_preferences": {
                "local_first": {"weight": 0.4}
            },
            "evidence_log": [{"feature": "local_first"}],
        }
    )

    assert profile["stable_preferences"]["local_first"]["feature"] == "local_first"
    assert profile["stable_preferences"]["local_first"]["evidence_count"] == 0
    assert profile["negative_preferences"] == {}
    assert profile["current_focus"] == {}


def test_get_profile_tool_returns_compatible_empty_shape(tmp_path):
    from tastemate.tools.get_profile import get_profile_tool

    result = get_profile_tool(profile_path=tmp_path / "profile.json")

    assert result["stable_preferences"] == {}
    assert result["negative_preferences"] == {}
    assert result["current_focus"] == {}
    assert result["evidence_summary"]["total_count"] == 0
    assert result["summary"] == "当前暂无稳定偏好。"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tests/test_profile_store.py -k iteration003 -v
python -m pytest tests/test_server_tools.py -k compatible_empty_shape -v
```

Expected: FAIL，因为 `normalize_profile` 还不会补齐迭代三字段细节，`get_profile_tool` 还没有 `evidence_summary`。

- [ ] **Step 3: Write minimal implementation**

```python
DEFAULT_PROFILE = {
    "stable_preferences": {},
    "negative_preferences": {},
    "current_focus": {},
    "evidence_log": [],
}


def _normalize_feature_entry(feature: str, raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "feature": feature,
        "label": str(raw.get("label") or feature),
        "weight": round(float(raw.get("weight", 0.0)), 4),
        "confidence": round(float(raw.get("confidence", 0.0)), 4),
        "strength": str(raw.get("strength") or "normal"),
        "evidence_count": int(raw.get("evidence_count", 0)),
        "source": str(raw.get("source") or "feedback"),
        "last_updated": raw.get("last_updated"),
    }
```

`get_profile_tool` 先保持顶层对象形态不变，只追加：

```python
return {
    "stable_preferences": profile["stable_preferences"],
    "negative_preferences": profile["negative_preferences"],
    "current_focus": profile["current_focus"],
    "evidence_summary": {"total_count": len(profile["evidence_log"])},
    "summary": summarize_profile(profile),
}
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python -m pytest tests/test_profile_store.py -k iteration003 -v
python -m pytest tests/test_server_tools.py -k compatible_empty_shape -v
```

Expected: PASS，且旧 profile 仍能读写。

- [ ] **Step 5: Commit**

```bash
git add tastemate/schemas/profile.py tastemate/core/profile.py tests/test_profile_store.py tests/test_server_tools.py
git commit -m "feat: normalize iteration003 profile schema"
```

### Task 2: 实现 feedback 分类、白名单升级与 invalid 降级

**Files:**
- Modify: `tastemate/core/feedback.py`
- Modify: `tastemate/schemas/feedback.py`
- Modify: `tests/test_record_feedback.py`

- [ ] **Step 1: Write the failing test**

```python
from tastemate.core.feedback import FeedbackProcessor


def test_record_feedback_strong_positive_promotes_whitelisted_feature_once():
    profile = {
        "stable_preferences": {},
        "negative_preferences": {},
        "current_focus": {},
        "evidence_log": [],
    }

    result = FeedbackProcessor(profile).record(
        query="@taste 推荐几个适合我的本地知识库工具",
        user_feedback="我明确更喜欢本地优先、开源的工具，这个方向以后优先。",
        selected_candidate_ids=["local-open"],
        rejected_candidate_ids=[],
        candidates_snapshot=[
            {
                "id": "local-open",
                "title": "Local Open",
                "summary": "Open source local-first tool.",
                "metadata": {"local_first": True, "open_source": True},
            }
        ],
    )

    assert result["feedback_valid"] is True
    assert result["feedback_type"] == "strong_positive"
    assert profile["stable_preferences"]["local_first"]["strength"] == "strong"
    assert profile["current_focus"]["local_first"]["evidence_count"] == 1


def test_record_feedback_invalid_does_not_write_evidence_or_profile():
    profile = {
        "stable_preferences": {},
        "negative_preferences": {},
        "current_focus": {},
        "evidence_log": [],
    }

    result = FeedbackProcessor(profile).record(
        query="@taste 推荐几个工具",
        user_feedback="",
        selected_candidate_ids=[],
        rejected_candidate_ids=[],
        candidates_snapshot=[],
    )

    assert result["feedback_valid"] is False
    assert result["feedback_type"] == "invalid"
    assert profile["evidence_log"] == []
    assert profile["stable_preferences"] == {}
    assert profile["negative_preferences"] == {}
    assert profile["current_focus"] == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tests/test_record_feedback.py -k "strong_positive or invalid_does_not_write" -v
```

Expected: FAIL，因为当前实现没有 `feedback_type`、白名单升级和 invalid 降级保护。

- [ ] **Step 3: Write minimal implementation**

```python
WHITELISTED_FEATURES = {
    "local_first": "本地优先",
    "open_source": "开源优先",
    "cloud_required": "云依赖",
    "enterprise_oriented": "企业导向",
}


def _classify_feedback(self, user_feedback: str, selected: list[str], rejected: list[str]) -> str:
    text = user_feedback.strip().lower()
    if not text and not selected and not rejected:
        return "invalid"
    if any(marker in text for marker in ("明确", "以后优先", "不要", "拒绝", "must", "never")):
        return "strong_negative" if rejected and not selected else "strong_positive"
    return "normal_negative" if rejected and not selected else "normal_positive"
```

升级逻辑写死：

```python
if feedback_type == "strong_positive":
    self._upsert_preference("stable_preferences", feature, strength="strong", weight=0.35, confidence=0.65)
elif feedback_type == "strong_negative":
    self._upsert_preference("negative_preferences", feature, strength="strong", weight=0.35, confidence=0.65)
elif feedback_type == "normal_positive":
    self._promote_after_second_signal("stable_preferences", feature)
elif feedback_type == "normal_negative":
    self._promote_after_second_signal("negative_preferences", feature)
```

invalid 分支必须直接返回：

```python
return {
    "feedback_valid": False,
    "signal_strength": 0.0,
    "extracted_signals": [],
    "profile_updates": [],
    "accepted": False,
    "feedback_type": "invalid",
    "applied_features": [],
}
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python -m pytest tests/test_record_feedback.py -k "strong_positive or invalid_does_not_write" -v
```

Expected: PASS，且 invalid feedback 不写 `evidence_log`。

- [ ] **Step 5: Commit**

```bash
git add tastemate/core/feedback.py tastemate/schemas/feedback.py tests/test_record_feedback.py
git commit -m "feat: classify feedback and promote whitelisted signals"
```

### Task 3: 补齐 normal 2 次升级与单次强反馈阈值保护

**Files:**
- Modify: `tastemate/core/feedback.py`
- Modify: `tests/test_record_feedback.py`

- [ ] **Step 1: Write the failing test**

```python
from tastemate.core.feedback import FeedbackProcessor


def test_record_feedback_promotes_normal_signal_on_second_match():
    profile = {
        "stable_preferences": {},
        "negative_preferences": {},
        "current_focus": {},
        "evidence_log": [],
    }
    processor = FeedbackProcessor(profile)

    kwargs = dict(
        query="@taste 推荐几个知识库工具",
        user_feedback="我比较喜欢本地优先",
        selected_candidate_ids=["a"],
        rejected_candidate_ids=[],
        candidates_snapshot=[{"id": "a", "title": "A", "summary": "local-first", "metadata": {"local_first": True}}],
    )

    first = processor.record(**kwargs)
    second = processor.record(**kwargs)

    assert first["feedback_type"] == "normal_positive"
    assert "local_first" not in profile["stable_preferences"]
    assert second["feedback_type"] == "normal_positive"
    assert profile["stable_preferences"]["local_first"]["evidence_count"] >= 2


def test_record_feedback_strong_update_respects_iteration003_thresholds():
    profile = {
        "stable_preferences": {
            "local_first": {
                "feature": "local_first",
                "label": "本地优先",
                "weight": 0.30,
                "confidence": 0.60,
                "strength": "normal",
                "evidence_count": 2,
                "source": "feedback",
                "last_updated": "2026-06-08T00:00:00+08:00",
            }
        },
        "negative_preferences": {},
        "current_focus": {},
        "evidence_log": [],
    }

    FeedbackProcessor(profile).record(
        query="@taste 推荐几个工具",
        user_feedback="我明确更喜欢本地优先，这个方向以后优先。",
        selected_candidate_ids=["a"],
        rejected_candidate_ids=[],
        candidates_snapshot=[{"id": "a", "title": "A", "summary": "local-first", "metadata": {"local_first": True}}],
    )

    updated = profile["stable_preferences"]["local_first"]
    assert updated["weight"] <= 0.35
    assert updated["confidence"] <= 0.65
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tests/test_record_feedback.py -k "second_match or iteration003_thresholds" -v
```

Expected: FAIL，因为当前实现只会保守更新已有稳定偏好，不会处理 normal 两次升级和迭代三阈值。

- [ ] **Step 3: Write minimal implementation**

```python
def _promote_after_second_signal(self, section: str, feature: str) -> None:
    matching = [
        item
        for item in self.profile.get("evidence_log", [])
        if item.get("feature") == feature and item.get("direction") == ("positive" if section == "stable_preferences" else "negative")
    ]
    if len(matching) < 2:
        return
    self._upsert_preference(section, feature, strength="normal", weight=0.28, confidence=0.55)


def _bounded_update(self, old_weight: float, old_confidence: float) -> tuple[float, float]:
    return min(0.35, old_weight + 0.10), min(0.65, old_confidence + 0.05)
```

current_focus 保持轻量：

```python
self.profile["current_focus"][feature] = {
    "feature": feature,
    "label": WHITELISTED_FEATURES[feature],
    "evidence_count": previous_count + 1,
    "last_updated": now_iso(),
}
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python -m pytest tests/test_record_feedback.py -k "second_match or iteration003_thresholds" -v
```

Expected: PASS，且单次强反馈不会越过 design 规定阈值。

- [ ] **Step 5: Commit**

```bash
git add tastemate/core/feedback.py tests/test_record_feedback.py
git commit -m "feat: enforce feedback promotion thresholds"
```

### Task 4: 让排序消费 stable / negative / current_focus

**Files:**
- Modify: `tastemate/core/scoring.py`
- Modify: `tastemate/core/ranker.py`
- Modify: `tests/test_rank_candidates.py`

- [ ] **Step 1: Write the failing test**

```python
from tastemate.core.ranker import Ranker


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
            {"id": "cloud", "title": "Cloud Tool", "summary": "Enterprise SaaS knowledge base.", "metadata": {"cloud_required": True}},
            {"id": "local", "title": "Local Tool", "summary": "Open source local-first knowledge base.", "metadata": {"local_first": True, "open_source": True}},
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
            "open_source": {"feature": "open_source", "label": "开源优先", "evidence_count": 1, "last_updated": "2026-06-08T00:00:00+08:00"}
        },
        "evidence_log": [],
    }

    result = Ranker(profile=profile).rank(
        query="@taste 推荐几个适合我的本地知识库工具",
        candidates=[
            {"id": "relevant", "title": "Relevant Local Tool", "summary": "Knowledge base local-first tool.", "metadata": {}},
            {"id": "low", "title": "Open Source SDK", "summary": "A generic open source developer SDK.", "metadata": {"open_source": True}},
        ],
        taste_mode="force",
    )

    assert result["ranked_candidates"][0]["id"] == "relevant"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tests/test_rank_candidates.py -k "reorders_fixed_sample or current_focus_cannot_flip" -v
```

Expected: FAIL，因为当前排序只读 `evidence_log`，不会消费长期正负偏好和 current_focus。

- [ ] **Step 3: Write minimal implementation**

```python
def profile_adjustment(candidate: dict[str, Any], profile: dict[str, Any]) -> tuple[float, list[str], list[str]]:
    features = candidate_features(candidate)
    score = 0.0
    reasons: list[str] = []
    risks: list[str] = []

    for feature, item in profile.get("stable_preferences", {}).items():
        if feature in features:
            score += min(float(item.get("weight", 0.0)), 0.35) * 0.30
            reasons.append(f"命中长期正向偏好: {feature}")
    for feature, item in profile.get("negative_preferences", {}).items():
        if feature in features:
            score -= min(float(item.get("weight", 0.0)), 0.35) * 0.30
            reasons.append(f"命中长期负向偏好: {feature}")
    for feature, item in profile.get("current_focus", {}).items():
        if feature in features:
            score += 0.05
            reasons.append(f"命中当前关注: {feature}")
    return clamp(score), reasons, risks
```

在 `Ranker._score_candidate()` 中合并：

```python
profile_delta, profile_reasons, profile_risks = profile_adjustment(candidate, self.profile)
if relevance < 0.35:
    profile_delta = min(profile_delta, 0.05)
final = round(relevance * 0.55 + fit * 0.20 + history * 0.10 + profile_delta * 0.15, 4)
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python -m pytest tests/test_rank_candidates.py -k "reorders_fixed_sample or current_focus_cannot_flip" -v
```

Expected: PASS，且 `current_focus` 不会把低相关候选抬到第一名。

- [ ] **Step 5: Commit**

```bash
git add tastemate/core/scoring.py tastemate/core/ranker.py tests/test_rank_candidates.py
git commit -m "feat: apply profile adjustments during ranking"
```

### Task 5: 收敛工具输出兼容契约与画像解释

**Files:**
- Modify: `tastemate/tools/record_feedback.py`
- Modify: `tastemate/tools/get_profile.py`
- Modify: `tastemate/core/profile.py`
- Modify: `tests/test_server_tools.py`
- Create: `tests/test_get_profile.py`

- [ ] **Step 1: Write the failing test**

```python
from tastemate.tools.get_profile import get_profile_tool
from tastemate.tools.record_feedback import record_feedback_tool


def test_record_feedback_tool_returns_compatible_iteration003_payload(tmp_path):
    result = record_feedback_tool(
        query="@taste 推荐几个工具",
        user_feedback="我明确更喜欢本地优先。",
        selected_candidate_ids=["a"],
        rejected_candidate_ids=[],
        candidates_snapshot=[{"id": "a", "title": "A", "summary": "local-first", "metadata": {"local_first": True}}],
        profile_path=tmp_path / "profile.json",
    )

    assert "feedback_valid" in result
    assert "signal_strength" in result
    assert "profile_updates" in result
    assert "feedback_type" in result
    assert "profile_update_details" in result


def test_get_profile_tool_returns_explained_profile(tmp_path):
    record_feedback_tool(
        query="@taste 推荐几个工具",
        user_feedback="我明确更喜欢本地优先。",
        selected_candidate_ids=["a"],
        rejected_candidate_ids=[],
        candidates_snapshot=[{"id": "a", "title": "A", "summary": "local-first", "metadata": {"local_first": True}}],
        profile_path=tmp_path / "profile.json",
    )

    result = get_profile_tool(profile_path=tmp_path / "profile.json")

    assert "local_first" in result["stable_preferences"]
    assert result["stable_preferences"]["local_first"]["evidence_count"] >= 1
    assert result["evidence_summary"]["total_count"] >= 1
    assert "本地优先" in result["summary"]
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tests/test_server_tools.py -k "compatible_iteration003_payload or explained_profile" -v
```

Expected: FAIL，因为当前 tool 输出还没有 `feedback_type`、`profile_update_details`、`evidence_summary` 和增强 summary。

- [ ] **Step 3: Write minimal implementation**

```python
def summarize_profile(profile: dict[str, Any]) -> str:
    stable = profile.get("stable_preferences", {})
    negative = profile.get("negative_preferences", {})
    current = profile.get("current_focus", {})
    if stable or negative:
        stable_names = "、".join(item.get("label", key) for key, item in stable.items())
        negative_names = "、".join(item.get("label", key) for key, item in negative.items())
        return f"长期正向偏好：{stable_names or '无'}；长期负向偏好：{negative_names or '无'}；当前关注：{'、'.join(current.keys()) or '无'}。"
    if profile.get("evidence_log"):
        return f"已有 {len(profile['evidence_log'])} 条反馈证据。"
    return "当前暂无稳定偏好。"
```

`record_feedback_tool` 不改输入，只透传增强后的处理结果；`get_profile_tool` 返回：

```python
{
    "stable_preferences": profile["stable_preferences"],
    "negative_preferences": profile["negative_preferences"],
    "current_focus": profile["current_focus"],
    "evidence_summary": {"total_count": len(profile["evidence_log"])},
    "summary": summarize_profile(profile),
}
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python -m pytest tests/test_server_tools.py -k "compatible_iteration003_payload or explained_profile" -v
python -m pytest tests/test_get_profile.py -q
```

Expected: PASS，且顶层对象形态保持兼容。

- [ ] **Step 5: Commit**

```bash
git add tastemate/tools/record_feedback.py tastemate/tools/get_profile.py tastemate/core/profile.py tests/test_server_tools.py tests/test_get_profile.py
git commit -m "feat: expose explained iteration003 profile output"
```

### Task 6: 跑回归、补验证记录并收口文档

**Files:**
- Modify: `docs/iterations/iteration-003/verification.md`
- Modify: `docs/iterations/iteration-003/status.md` (如不存在则在本任务一并创建)

- [ ] **Step 1: Write the verification skeleton before final test run**

```md
# Iteration 003 Verification

## 适用阶段

```text
Verify
```

## 一、覆盖范围

```text
A-001 ~ A-010 本地闭环验证
```
```

- [ ] **Step 2: Run focused tests**

Run:

```bash
python -m pytest tests/test_record_feedback.py -q
python -m pytest tests/test_rank_candidates.py -q
python -m pytest tests/test_get_profile.py -q
python -m pytest tests/test_server_tools.py -q
```

Expected: PASS，且 A-001 ~ A-010 对应测试全部通过。

- [ ] **Step 3: Run full regression**

Run:

```bash
python -m pytest -q
```

Expected: PASS，无回归失败。

- [ ] **Step 4: Update verification/status docs with actual evidence**

```text
verification.md：记录各验收条目的验证方式、命令、结果和关键断言。
status.md：更新为“Plan 已完成，等待 Build / Verify 结果”或 Build 完成后的真实状态。
```

- [ ] **Step 5: Commit**

```bash
git add docs/iterations/iteration-003/verification.md docs/iterations/iteration-003/status.md
git commit -m "docs: record iteration003 verification evidence"
```

---

## 进入下一阶段条件

```text
1. Task 1 ~ Task 5 对应测试全部通过。
2. A-001 ~ A-010 都能在 verification.md 中找到对应证据。
3. record_feedback / get_profile / rank_candidates 的兼容输出契约保持不破坏已有调用方。
4. 无剩余 BLOCK 后，进入 Build / Verify / Multi-Agent Review。
```
