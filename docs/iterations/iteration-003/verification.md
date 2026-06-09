# Iteration 003 Verification

## 适用阶段

```text
Verify
```

## 结论

```text
Iteration 003 的本地闭环实现已完成验证。
2026-06-08 本地执行 pytest -q，结果 54 passed。
2026-06-09 本地再次执行 pytest -q，结果 57 passed。
当前状态已完成本地 Verify，等待修订后的 Multi-Agent Review 复核。
```

## 验证命令

```bash
pytest tests/test_record_feedback.py -q
pytest tests/test_rank_candidates.py -q
pytest tests/test_get_profile.py -q
pytest tests/test_server_tools.py -q
pytest tests/test_profile_store.py -q
pytest -q
```

## 关键结果

```text
tests/test_rank_candidates.py：20 passed
tests/test_record_feedback.py：15 passed
tests/test_get_profile.py：4 passed
tests/test_server_tools.py：5 passed
tests/test_profile_store.py：4 passed
全量 pytest：57 passed
```

## 验收映射

### A-001 强显式反馈可一次升级

```text
证据测试：
- tests/test_record_feedback.py::test_record_feedback_strong_positive_promotes_whitelisted_feature_once
- tests/test_record_feedback.py::test_record_feedback_strong_negative_promotes_negative_preferences

通过条件：
- strong_positive 单次反馈后，stable_preferences.local_first 升级为 strong。
- strong_negative 单次反馈后，negative_preferences 写入 cloud_required / enterprise_oriented。
```

### A-002 普通反馈需两次同向升级

```text
证据测试：
- tests/test_record_feedback.py::test_record_feedback_promotes_normal_signal_on_second_match

通过条件：
- 第 1 次 normal_positive 不升级。
- 第 2 次同向命中后，stable_preferences.local_first.evidence_count >= 2。
```

### A-003 白名单外 feature 不污染长期画像

```text
证据测试：
- tests/test_record_feedback.py::test_record_feedback_non_whitelisted_feature_only_writes_evidence
- tests/test_record_feedback.py::test_record_feedback_does_not_create_stable_preference_from_single_event
- tests/test_record_feedback.py::test_record_feedback_invalid_does_not_write_evidence_or_profile

通过条件：
- 白名单外 feature 只写 evidence_log，不进入 stable_preferences / negative_preferences。
- 单次 normal feedback 不升级 stable_preferences。
- invalid feedback 不写 evidence_log / stable_preferences / negative_preferences / current_focus。
```

### A-004 长期正向偏好会对后续排序产生有限正向影响

```text
证据测试：
- tests/test_rank_candidates.py::test_rank_candidates_profile_adjustment_changes_order_against_empty_profile
- tests/test_rank_candidates.py::test_rank_candidates_supports_metadata_features_array_for_profile_adjustment

通过条件：
- 空画像下 `mcp` 候选领先；命中 local_first 长期偏好后 `local` 候选前移。
- `metadata.features` 输入形态也能驱动同样的排序前移。
```

### A-005 长期负向偏好会对后续排序产生有限负向影响

```text
证据测试：
- tests/test_rank_candidates.py::test_rank_candidates_negative_profile_adjustment_changes_order_against_empty_profile
- tests/test_rank_candidates.py::test_rank_candidates_negative_preference_demotes_candidate

通过条件：
- 空画像下 `cloud` 候选领先；命中 cloud_required 长期负向偏好后 `plain` 候选前移。
- reasons 含“长期负向偏好”解释。
```

### A-006 current_focus 只做轻量修正，不压过 query relevance

```text
证据测试：
- tests/test_rank_candidates.py::test_rank_candidates_current_focus_cannot_flip_low_relevance_candidate

通过条件：
- 仅命中 current_focus 的低相关候选不能反超更高相关候选。
```

### A-007 get_profile 能解释偏好来源、证据数和当前状态

```text
证据测试：
- tests/test_get_profile.py::test_get_profile_tool_returns_explained_profile
- tests/test_get_profile.py::test_get_profile_tool_summarizes_current_focus_without_stable_preferences
- tests/test_server_tools.py::test_get_profile_tool_returns_compatible_empty_shape

通过条件：
- get_profile 返回 stable_preferences / negative_preferences / current_focus。
- 返回 evidence_summary.total_count。
- summary 使用中文标签解释长期偏好或当前关注状态。
```

### A-008 不修改 Hermes 输入协议，不修改 Hermes 源码

```text
审查证据：
- tastemate/tools/record_feedback.py 仅扩展返回字段，未新增输入参数。
- 本轮提交范围只涉及 tastemate/*、tests/*、docs/iterations/iteration-003/*，未修改 Hermes 源码。

通过条件：
- record_feedback / rank_candidates / get_profile 的调用输入协议保持兼容。
- git 提交范围不进入 Hermes 代码。
```

### A-009 固定候选集下反馈前后排序变化符合指定样例

```text
证据测试：
- tests/test_rank_candidates.py::test_rank_candidates_profile_adjustment_changes_order_against_empty_profile
- tests/test_rank_candidates.py::test_rank_candidates_negative_profile_adjustment_changes_order_against_empty_profile

通过条件：
- local-first 正向样例在反馈画像生效后发生顺序翻转。
- cloud-required 负向样例在反馈画像生效后发生顺序翻转。
```

### A-010 单次反馈不会把长期画像推得过高

```text
证据测试：
- tests/test_record_feedback.py::test_record_feedback_strong_update_respects_iteration003_thresholds
- tests/test_record_feedback.py::test_record_feedback_limits_stable_preference_weight_delta_and_confidence
- tests/test_record_feedback.py::test_record_feedback_single_update_delta_stays_within_iteration003_increment_limits

通过条件：
- 单次 strong 更新后，weight <= 0.35。
- 单次 strong 更新后，confidence <= 0.65。
- 单次更新相对原值的增量不超过 weight +0.10 / confidence +0.05。
```

## 残留事项

```text
无阻塞性失败。
存在 1 个非阻塞 follow-up：可补 normal_negative 的对称测试，但不影响本轮验收。
```
