# Iteration 001 Development Spec：显式 @taste 后置重排闭环

## 适用阶段

```text
Development Spec
```

本文件在 Design 通过后、Plan 之前编写，用于约束后续迭代一的开发计划和实现。

本文件不是代码实现，也不是开发计划。后续 `plan.md` 必须引用本文件。

## 一、开发原则

迭代一只验证最小闭环：

```text
显式 @taste 启用
Hermes 后置候选重排
可解释评分
反馈写入 evidence_log
本地持久化
外部 MCP 接入
不改 Hermes 源码
```

禁止在迭代一实现：

```text
搜索前偏好注入
Hermes plugin/hook 自动编排
UI
多用户系统
复杂推荐模型训练
自动强制重搜
```

## 二、技术形态

TasteMate 迭代一作为本地 stdio MCP server 运行。

Hermes 通过 `~/.hermes/config.yaml` 的 `mcp_servers` 接入 TasteMate。

建议配置形态：

```yaml
mcp_servers:
  tastemate:
    command: "python"
    args: ["-m", "tastemate.server"]
    timeout: 120
```

具体命令、包管理方式和模块路径由 Plan 阶段根据实际项目结构确认。

## 三、目录结构

建议目录结构：

```text
tastemate/
  __init__.py
  server.py
  tools/
    __init__.py
    rank_candidates.py
    record_feedback.py
    get_profile.py
  core/
    __init__.py
    ranker.py
    feedback.py
    profile.py
    scoring.py
  storage/
    __init__.py
    json_store.py
  llm/
    __init__.py
    client.py
    prompts.py
  schemas/
    __init__.py
    candidates.py
    feedback.py
    profile.py
tests/
  test_rank_candidates.py
  test_record_feedback.py
  test_profile_store.py
```

迭代一默认只保留 `json_store.py`。SQLite 属于后续可替换实现，不在迭代一默认实现。

## 四、核心模块

### MCP Server

职责：

```text
启动 stdio MCP server。
注册 rank_candidates、record_feedback、get_profile。
处理工具输入输出。
不负责搜索。
不直接修改 Hermes 配置。
```

### tools.rank_candidates

职责：

```text
接收 query、candidates、taste_mode。
调用 Ranker。
返回 ranked / passthrough / needs_more_candidates。
```

### tools.record_feedback

职责：

```text
接收用户反馈和上一轮候选快照。
调用 Feedback Processor。
写入 evidence_log。
返回 feedback_valid、signal_strength、extracted_signals、profile_updates。
```

### tools.get_profile

职责：

```text
读取当前 profile。
返回 stable_preferences、negative_preferences、current_focus 和 summary。
```

### core.ranker

职责：

```text
判断是否存在可排序候选集合。
判断 ranking_needed。
计算 query_relevance、preference_fit、feedback_score、final_score。
生成 reasons 和 risks。
```

Ranker 不写 profile，不处理反馈学习。

### core.feedback

职责：

```text
判断 feedback_valid。
识别 selected_candidate_ids / rejected_candidate_ids。
抽取偏好信号。
估算 signal_strength。
生成 evidence。
保守生成 profile_updates。
```

Feedback Processor 不做候选排序。

### core.profile

职责：

```text
定义 profile 读写接口。
聚合 stable_preferences、negative_preferences、current_focus、evidence_log。
限制单次反馈对 stable_preferences 的影响。
```

### storage.json_store

职责：

```text
读写本地 JSON profile 文件。
文件不存在时初始化默认 profile。
写入时保持结构合法。
```

## 五、接口约定

### Candidate

最小字段：

```json
{
  "id": "candidate-1",
  "title": "候选标题",
  "summary": "候选摘要"
}
```

可选字段：

```json
{
  "url": "https://example.com",
  "source": "github",
  "metadata": {
    "open_source": true,
    "local_first": true,
    "supports_mcp": false
  }
}
```

兼容策略：

```text
id 缺失时，可由 title + url 或 title + summary 生成稳定 hash。
title 缺失时，使用 url 或 source 作为标题 fallback。
summary 缺失时，允许进入低置信评分，但应在 risks 中说明。
```

### rank_candidates 输入

```json
{
  "query": "用户问题",
  "candidates": [],
  "taste_mode": "force"
}
```

字段约束：

```text
query：必填，字符串。
candidates：必填，数组，可为空。
taste_mode：可选，默认 force；迭代一只支持 force。
```

### rank_candidates 输出

排序成功：

```json
{
  "ranking_needed": true,
  "mode": "recommendation",
  "action": "ranked",
  "ranked_candidates": [
    {
      "id": "candidate-1",
      "final_score": 0.82,
      "query_relevance": 0.78,
      "preference_fit": 0.88,
      "feedback_score": 0.15,
      "reasons": [],
      "risks": []
    }
  ]
}
```

无需排序：

```json
{
  "ranking_needed": false,
  "mode": "factual",
  "action": "passthrough",
  "reason": "确定性事实问题或没有可排序候选集合"
}
```

候选不足：

```json
{
  "ranking_needed": true,
  "mode": "recommendation",
  "action": "needs_more_candidates",
  "reason": "候选数量不足或缺少关键方向",
  "suggested_search_hints": []
}
```

低置信：

```json
{
  "ranking_needed": true,
  "mode": "recommendation",
  "action": "low_confidence",
  "reason": "LLM 不可用或候选信息不足，无法给出可靠排序",
  "ranked_candidates": [],
  "suggested_search_hints": [],
  "risks": [
    "评分置信度不足"
  ]
}
```

`low_confidence` 是独立 action，不应伪装成 `ranked`。

### record_feedback 输入

```json
{
  "query": "上一轮问题",
  "user_feedback": "用户后续反馈",
  "selected_candidate_ids": [],
  "rejected_candidate_ids": [],
  "candidates_snapshot": []
}
```

### record_feedback 输出

```json
{
  "feedback_valid": true,
  "signal_strength": 0.7,
  "extracted_signals": [],
  "profile_updates": []
}
```

### get_profile 输入

```json
{}
```

字段约束：

```text
迭代一不接受参数。
后续如需按 profile section 查询，应新增字段并更新 schema。
```

### get_profile 输出

```json
{
  "stable_preferences": {},
  "negative_preferences": {},
  "current_focus": {},
  "summary": "当前偏好摘要"
}
```

## 六、配置说明

迭代一建议支持环境变量：

```text
TASTEMATE_PROFILE_PATH：profile JSON 文件路径。
TASTEMATE_LLM_PROVIDER：LLM provider 名称。
TASTEMATE_LLM_MODEL：评分模型名称。
TASTEMATE_LLM_API_KEY：评分模型 API key。
```

默认策略：

```text
如果未配置 LLM，rank_candidates 可返回 low_confidence 或使用规则评分降级。
如果未配置 profile 路径，使用项目内或用户目录下的默认本地路径，具体路径由 Plan 阶段确认。
```

## 七、数据结构

### Profile

```json
{
  "stable_preferences": {},
  "negative_preferences": {},
  "current_focus": {},
  "evidence_log": []
}
```

### Evidence

```json
{
  "timestamp": "2026-05-26T00:00:00+08:00",
  "event_type": "selected",
  "query": "用户问题",
  "candidate_id": "candidate-1",
  "feature": "local_first",
  "direction": "positive",
  "strength": 0.6,
  "source": "explicit_user_feedback"
}
```

### Preference Weight

```json
{
  "weight": 0.62,
  "confidence": 0.45,
  "evidence_count": 3,
  "last_seen": "2026-05-26T00:00:00+08:00"
}
```

## 八、错误处理

### TasteMate MCP 工具异常

```text
返回结构化 error，不抛出未处理异常。
Hermes 应能继续普通回答。
```

### 候选为空

```text
candidates=[] 时返回 passthrough 或 needs_more_candidates。
不得崩溃。
```

### LLM 不可用

```text
rank_candidates 返回 action=low_confidence。
保留规则评分或 passthrough。
不得阻塞 Hermes 正常回答。
```

### Profile 文件不存在

```text
初始化默认 profile。
```

### Profile 文件损坏

```text
返回错误并保留原始文件。
不得覆盖损坏文件。
Plan 阶段应决定是否需要备份策略。
```

### 用户反馈无法识别

```text
feedback_valid=false。
只记录原始事件或不更新 profile。
不得更新 stable_preferences。
```

## 九、评分策略

迭代一 Build 不实现真实 LLM 评分。`rank_candidates` 使用规则评分，依赖输入 query、候选字段、候选 metadata 和本地 profile evidence。

规则输入：

```text
query：用于判断事实类/推荐类、主题和约束。
candidates[].title / summary / source / url：用于判断相关性和偏好信号。
candidates[].metadata：用于读取 open_source、local_first、supports_mcp、cloud_required、enterprise_oriented 等结构化信号。
profile.evidence_log：用于读取历史 feature、direction、strength，形成轻量 feedback_score。
```

第一版评分：

```text
final_score =
  query_relevance * 0.55
+ preference_fit * 0.30
+ feedback_score * 0.15
```

硬规则：

```text
query_relevance 是门槛。
明显不相关候选不得因为 preference_fit 高而排到前面。
preference_fit 只在相关候选之间影响顺序。
feedback_score 必须优先按 feature 泛化，不得只按 candidate_id 绑定旧候选。
每个 ranked candidate 必须包含 reasons。
低置信评分必须包含 risks。
```

LLM 调用策略：

```text
rank_candidates 设计预算最多一次 LLM 调用；迭代一 Build 不接真实 LLM，使用规则评分。
record_feedback 设计预算最多一次 LLM 调用；迭代一 Build 不接真实 LLM，使用规则抽取。
规则可判断字段优先走规则。
```

## 十、反馈学习约束

反馈收集不要求用户在反馈消息里再次输入 `@taste`。

触发边界：

```text
上一轮不是 @taste 推荐结果：TasteMate 不介入，不调用 record_feedback。
上一轮是 @taste 推荐结果：用户后续明确选择、否定或表达偏好时，Hermes 可以调用 record_feedback。
record_feedback 输入必须包含上一轮 query、user_feedback、selected_candidate_ids、rejected_candidate_ids、candidates_snapshot。
```

单次反馈必须满足：

```text
必须写入 evidence_log。
允许更新 current_focus。
不得新增 stable_preferences 条目。
不得将任一 stable_preferences 权重提升超过 0.10。
不得将任一 stable_preferences confidence 设置到 0.70 以上。
```

升级为 stable_preferences 的条件由后续迭代或 Plan 阶段进一步定义；迭代一只保证不会被单次反馈污染。

迭代一风险：

```text
Hermes 是否稳定在上一轮 @taste 上下文后调用 record_feedback，需要手工验证。
如果不稳定，记录为 Verify 未验证项或失败项，不在迭代一引入 Hermes plugin/hook 强制编排。
```

## 十一、测试策略

测试必须覆盖设计验收标准：

```text
A-001 未使用 @taste 时 TasteMate 不介入。
A-002 @taste 推荐类问题触发 rank_candidates。
A-003 事实类问题返回 passthrough。
A-004 候选不足时返回 needs_more_candidates。
A-005 推荐类候选输出结构化评分。
A-006 用户明确反馈写入 evidence_log。
A-007 单次反馈必须写 evidence_log，且不得直接新增或过度提升 stable_preferences。
A-008 不修改 Hermes 源码。
```

单元测试建议：

```text
test_rank_candidates_low_confidence_schema
test_rank_candidates_passthrough
test_rank_candidates_needs_more_candidates
test_rank_candidates_ranked_schema
test_record_feedback_writes_evidence
test_record_feedback_does_not_create_stable_preference_from_single_event
test_record_feedback_limits_stable_preference_weight_delta
test_record_feedback_limits_stable_preference_confidence
test_profile_store_initializes_default_profile
test_profile_store_does_not_overwrite_corrupt_file
```

A-007 测试矩阵：

```text
必须断言 evidence_log 增加一条可追溯 evidence。
必须断言单次反馈不会新增 stable_preferences 条目。
如果已有 stable_preferences 条目，必须断言任一权重增量 <= 0.10。
如果已有 stable_preferences 条目，必须断言任一 confidence <= 0.70。
```

集成/手工验证建议：

```text
普通问题未使用 @taste 时，不出现 mcp_tastemate_* 工具调用。
Hermes 能发现 mcp_tastemate_rank_candidates。
@taste 推荐类问题能触发 TasteMate。
@taste 事实类问题返回 passthrough。
needs_more_candidates 能把 suggested_search_hints 返回给 Hermes。
变更范围检查不包含 Hermes 源码路径。
```

变更范围验证：

```text
通过条件：git diff / changed files 只包含 TasteMate 仓库内文件，不包含 /Users/lanser/code/hermes 下的源码改动。
失败条件：未获批准修改 Hermes 源码。
```

## 十二、本地运行方式

本地运行命令由 Plan 阶段最终确认。

建议形态：

```bash
python -m tastemate.server
```

测试命令由 Plan 阶段根据包管理和测试框架确认。

## 十三、禁止事项

迭代一禁止：

```text
修改 Hermes 源码。
实现搜索前偏好注入。
实现 Hermes plugin/hook 自动编排。
实现 UI。
实现多用户权限或账号系统。
引入复杂推荐模型训练。
把 SQLite 作为默认必须实现项。
把未验证模型行为写成硬保证。
```

## 十四、进入 Plan 的条件

进入 Plan 前必须确认：

```text
本 Development Spec 已被用户接受。
Profile Store 第一版默认 JSON。
Candidate schema 最小字段已明确。
evidence_log 结构已明确。
Plan 将说明分支或 worktree 隔离策略。
```
