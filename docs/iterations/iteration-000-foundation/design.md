# Iteration 000 Design：TasteMate 基础方案设计

## 一、当前结论

TasteMate 当前采用“外置 MCP + 显式启用 + 后置重排 + 反馈学习”的最小可验证方案。

```text
用户不使用 @taste 时，TasteMate 不介入。
用户使用 @taste 时，Hermes 先正常收集候选。
TasteMate 通过 rank_candidates 对候选进行判断、评分、重排或 passthrough。
用户后续选择或反馈后，TasteMate 通过 record_feedback 写入偏好证据。
```

本设计是迭代一开发计划的输入，不包含代码实现。

## 二、背景与问题

Hermes 可以搜索、读取、整理和回答，但默认没有稳定的个人长期偏好层。

TasteMate 要验证的是：

```text
在不改 Hermes 源码的前提下，
是否可以通过外部 MCP server 让 Hermes 的候选推荐更符合个人偏好，
并通过反馈逐步形成可解释的偏好画像。
```

## 三、目标

迭代一目标：

```text
实现显式 @taste 启用的后置候选重排闭环。
验证 Hermes 能发现并调用 TasteMate MCP 工具。
验证 rank_candidates 能处理 ranked / passthrough / needs_more_candidates。
验证 record_feedback 能把用户反馈写入 evidence_log。
```

## 四、非目标

迭代一明确不做：

```text
不修改 Hermes 源码。
不做搜索前偏好注入。
不做 Hermes plugin/hook 自动编排。
不做 UI。
不做多用户系统。
不训练复杂推荐模型。
不承诺自动强制重搜。
```

## 五、数据流

### 1. 默认流程

```text
用户提问
  ↓
未使用 @taste
  ↓
Hermes 正常回答
  ↓
TasteMate 不介入
```

### 2. 个性化重排流程

这是迭代一的目标流程，不是已验证的硬保证。

Discovery 已确认：

```text
Hermes 支持外部 MCP 工具注册。
Hermes 工具结果会进入下一轮模型上下文。
```

Discovery 仍将以下内容标为 Assumption：

```text
Hermes 在用户使用 @taste 时，会稳定按工具说明调用 mcp_tastemate_rank_candidates。
Hermes 看到 needs_more_candidates 后，会根据 suggested_search_hints 继续搜索。
```

因此本流程在迭代一必须通过验证标准 A-002 和 A-004 验证。

```text
用户使用 @taste 提问
  ↓
Hermes 正常理解问题
  ↓
Hermes 搜索、读取、整理候选
  ↓
Hermes 调用 mcp_tastemate_rank_candidates
  ↓
TasteMate 判断候选是否需要排序
  ↓
passthrough / needs_more_candidates / ranked
  ↓
目标行为：Hermes 基于 TasteMate 结果继续搜索或输出回答
```

### 3. 反馈学习流程

```text
Hermes 输出结果
  ↓
用户选择、追问、否定或表达偏好
  ↓
Hermes 调用 mcp_tastemate_record_feedback
  ↓
TasteMate 判断反馈是否有效
  ↓
抽取偏好信号
  ↓
写入 evidence_log
  ↓
保守更新 current_focus / stable_preferences / negative_preferences
```

## 六、模块边界

### MCP Server

职责：

```text
对 Hermes 暴露 TasteMate 工具。
处理 MCP 输入输出。
不承担 Hermes 搜索职责。
```

迭代一工具：

```text
rank_candidates
record_feedback
get_profile
```

### Ranker

职责：

```text
判断 ranking_needed。
计算 query_relevance。
计算 preference_fit。
合并 feedback_score。
返回解释和风险。
```

Ranker 不负责更新偏好画像。

### Feedback Processor

职责：

```text
判断 feedback_valid。
识别 selected / rejected candidates。
抽取偏好特征。
估算 signal_strength。
写入 evidence_log。
生成保守 profile_updates。
```

Feedback Processor 不负责候选排序。

### Profile Store

职责：

```text
保存 stable_preferences。
保存 negative_preferences。
保存 current_focus。
保存 evidence_log。
```

迭代一建议先使用本地 JSON 文件或 SQLite，具体由 Plan 阶段决定。

## 七、接口设计

### rank_candidates

输入：

```json
{
  "query": "用户问题",
  "candidates": [
    {
      "id": "candidate-1",
      "title": "候选标题",
      "summary": "候选摘要",
      "url": "https://example.com",
      "metadata": {}
    }
  ],
  "taste_mode": "force"
}
```

输出：排序成功。

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

输出：无需排序。

```json
{
  "ranking_needed": false,
  "mode": "factual",
  "action": "passthrough",
  "reason": "确定性事实问题或没有可排序候选集合"
}
```

输出：候选不足。

```json
{
  "ranking_needed": true,
  "mode": "recommendation",
  "action": "needs_more_candidates",
  "reason": "候选数量不足或缺少关键方向",
  "suggested_search_hints": []
}
```

### record_feedback

输入：

```json
{
  "query": "上一轮问题",
  "user_feedback": "用户后续反馈",
  "selected_candidate_ids": [],
  "rejected_candidate_ids": [],
  "candidates_snapshot": []
}
```

输出：

```json
{
  "feedback_valid": true,
  "signal_strength": 0.7,
  "extracted_signals": [],
  "profile_updates": []
}
```

### get_profile

输入：

```json
{}
```

输出：

```json
{
  "stable_preferences": {},
  "negative_preferences": {},
  "current_focus": {},
  "summary": "当前偏好摘要"
}
```

## 八、错误与降级

```text
TasteMate 不可用：Hermes 继续普通回答。
无 @taste：TasteMate 不介入。
@taste 但无可排序候选：rank_candidates 返回 passthrough。
候选不足：rank_candidates 返回 needs_more_candidates 和 suggested_search_hints。
反馈无法识别：只记录原始事件，不更新稳定偏好。
模型评分低置信：返回 low_confidence，并附解释。
```

## 九、成本与性能

成本策略：

```text
无 @taste：0 次 TasteMate 模型调用。
有 @taste 且无候选：0 到 1 次轻量判断。
有 @taste 且有候选：rank_candidates 最多 1 次模型调用。
用户明确反馈：record_feedback 最多 1 次模型调用。
画像更新：可即时，也可后续批处理。
```

设计原则：

```text
TasteMate 不做每轮固定调用。
rank_candidates 内部合并判断、评分、解释，避免拆成多次模型调用。
规则可判断的字段优先用规则，LLM 只处理语义评分和反馈抽取。
```

## 十、风险与应对

| 风险 | 影响 | 应对 |
| --- | --- | --- |
| Hermes 不稳定调用 `rank_candidates` | @taste 体验不稳定 | 工具描述明确调用时机；验收中验证触发稳定性；后续进入 plugin/hook 编排 |
| 候选格式不统一 | 排序输入不稳定 | `rank_candidates` 兼容松散候选结构；要求候选至少有 title/summary/id |
| LLM 评分不稳定 | 排序结果波动 | 输出评分理由；保留规则评分；后续增加样例和缓存 |
| 一次反馈学歪 | 长期画像污染 | 先写 evidence；低学习率；current_focus 与 stable_preferences 分层 |
| 继续搜索不是强制机制 | `needs_more_candidates` 可能被忽略 | 迭代一只作为提示；后续用 plugin/hook 增强编排 |

## 十一、验收标准

```text
A-001 未使用 @taste 时 TasteMate 不介入。
验证方式：普通问题流程中观察无 mcp_tastemate_* 工具调用。
通过条件：无 TasteMate 工具调用。
失败条件：出现 TasteMate 工具调用。

A-002 @taste 推荐类问题触发 rank_candidates。
验证方式：输入 @taste 推荐类问题。
通过条件：Hermes 调用 mcp_tastemate_rank_candidates。
失败条件：Hermes 未调用 TasteMate 直接回答。

A-003 事实类问题返回 passthrough。
验证方式：输入 @taste 确定性事实问题。
通过条件：rank_candidates 返回 action=passthrough。
失败条件：强行排序或生成个性化推荐。

A-004 候选不足时返回 needs_more_candidates。
验证方式：传入数量不足或缺少关键方向的候选。
通过条件：返回 action=needs_more_candidates 和 suggested_search_hints。
失败条件：在低置信候选上强行排序。

A-005 推荐类候选输出结构化评分。
验证方式：传入多个候选。
通过条件：每个已排序候选包含 query_relevance、preference_fit、final_score、reasons。
失败条件：只返回无解释排序。

A-006 用户明确反馈写入 evidence_log。
验证方式：调用 record_feedback。
通过条件：生成 evidence 记录，并可追溯来源。
失败条件：反馈丢失或直接覆盖画像。

A-007 单次反馈不得直接新增稳定长期偏好。
验证方式：单次强反馈后检查画像更新。
通过条件：单次反馈必须写入 evidence_log；允许更新 current_focus；不得新增 stable_preferences 条目；不得将任一 stable_preferences 权重提升超过 0.10；不得将任一 stable_preferences confidence 设置到 0.70 以上。
失败条件：单次反馈未写入 evidence_log；或直接新增 stable_preferences 条目；或任一 stable_preferences 权重增量超过 0.10；或任一 stable_preferences confidence 被设置到 0.70 以上。

A-008 不修改 Hermes 源码。
验证方式：检查变更范围。
通过条件：TasteMate 作为外部 MCP 接入。
失败条件：未获批准修改 Hermes 源码。
```

## 十二、后续迭代

迭代二：搜索前轻量偏好增强。

```text
get_search_hints
pre_llm_call hook 注入偏好摘要
负向偏好提示
current_focus 提示
```

迭代三：更强 Hermes 外置编排。

```text
transform_tool_result
post_tool_call
自动标记候选来源
更可靠地触发 rank_candidates
```

长期方向：

```text
批处理 profile updater
离线推荐质量评估
模型成本路由
候选特征缓存
可视化偏好画像
```

这些都不进入迭代一。
