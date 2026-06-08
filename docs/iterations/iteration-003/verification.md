# Iteration 003 Verification

## 适用阶段

```text
Verify
```

## 结论

```text
Iteration 003 的本地闭环实现已完成验证。
2026-06-08 本地执行 pytest -q，结果 48 passed。
当前状态可进入 Multi-Agent Review。
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
tests/test_rank_candidates.py：17 passed
tests/test_record_feedback.py：11 passed
tests/test_get_profile.py：2 passed
tests/test_server_tools.py：5 passed
tests/test_profile_store.py：4 passed
全量 pytest：48 passed
```

## 验收映射

### A-001 强显式正向反馈 1 次可升级 stable_preferences

```text
证据测试：
- tests/test_record_feedback.py::test_record_feedback_strong_positive_promotes_whitelisted_feature_once

通过条件：
- strong_positive 单次反馈后，stable_preferences.local_first 升级为 strong。
```

### A-002 强显式负向反馈 1 次可升级 negative_preferences

```text
证据测试：
- tests/test_record_feedback.py::test_record_feedback_strong_negative_promotes_negative_preferences

通过条件：
- strong_negative 单次反馈后，negative_preferences 写入 cloud_required / enterprise_oriented。
```

### A-003 普通 feedback 1 次只写 evidence，不直接升级长期偏好

```text
证据测试：
- tests/test_record_feedback.py::test_record_feedback_does_not_create_stable_preference_from_single_event
- tests/test_record_feedback.py::test_record_feedback_invalid_does_not_write_evidence_or_profile

通过条件：
- 单次 normal feedback 不升级 stable_preferences。
- invalid feedback 不写 evidence_log / stable_preferences / negative_preferences / current_focus。
```

### A-004 普通同向 feedback 达到 2 次后可升级长期偏好

```text
证据测试：
- tests/test_record_feedback.py::test_record_feedback_promotes_normal_signal_on_second_match

通过条件：
- 第 1 次 normal_positive 不升级。
- 第 2 次同向命中后，stable_preferences.local_first.evidence_count >= 2。
```

### A-005 长期正向偏好会对相关候选产生可解释加分

```text
证据测试：
- tests/test_rank_candidates.py::test_rank_candidates_reorders_fixed_sample_after_feedback

通过条件：
- local-first 候选前移到第一名。
- ranked_candidates[].reasons 含“长期正向偏好”解释。
```

### A-006 长期负向偏好会对相关候选产生可解释减分

```text
证据测试：
- tests/test_rank_candidates.py::test_rank_candidates_negative_preference_demotes_candidate

通过条件：
- 命中 cloud_required 的候选被降到非第一名。
- reasons 含“长期负向偏好”解释。
```

### A-007 current_focus 只做轻量修正，不压过 query relevance

```text
证据测试：
- tests/test_rank_candidates.py::test_rank_candidates_current_focus_cannot_flip_low_relevance_candidate

通过条件：
- 仅命中 current_focus 的低相关候选不能反超更高相关候选。
```

### A-008 get_profile 能解释偏好来源和证据数量

```text
证据测试：
- tests/test_get_profile.py::test_get_profile_tool_returns_explained_profile
- tests/test_server_tools.py::test_get_profile_tool_returns_compatible_empty_shape

通过条件：
- get_profile 返回 stable_preferences / negative_preferences / current_focus。
- 返回 evidence_summary.total_count。
- summary 使用中文标签解释画像状态。
```

### A-009 给定固定候选集时，反馈前后排序变化符合指定样例

```text
证据测试：
- tests/test_rank_candidates.py::test_rank_candidates_reorders_fixed_sample_after_feedback
- tests/test_rank_candidates.py::test_rank_candidates_negative_preference_demotes_candidate

通过条件：
- local-first 样例前移。
- cloud-required 样例后移。
```

### A-010 单次反馈不会把长期画像推得过高

```text
证据测试：
- tests/test_record_feedback.py::test_record_feedback_strong_update_respects_iteration003_thresholds
- tests/test_record_feedback.py::test_record_feedback_limits_stable_preference_weight_delta_and_confidence

通过条件：
- 单次 strong 更新后，weight <= 0.35。
- 单次 strong 更新后，confidence <= 0.65。
```

## 残留事项

```text
无阻塞性失败。
存在 1 个非阻塞 follow-up：可补 normal_negative 的对称测试，但不影响本轮验收。
```
