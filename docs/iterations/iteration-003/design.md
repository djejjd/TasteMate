# Iteration 003 Design：反馈画像增强与有限排序生效

## 一、当前结论

```text
Iteration 003 只做本地可验证闭环内的反馈画像增强。
本轮目标不是做开放式画像系统，也不是补齐远端 feedback/evidence 主路径，而是在受控 feature 白名单内，让 feedback 能沉淀为 stable_preferences / negative_preferences / current_focus，并对排序产生有限但明确、可解释、可验证的影响。
```

## 二、背景与问题

```text
iteration-001 已验证 record_feedback 能写入 evidence_log，但当时明确限制单次反馈不得直接形成长期偏好。
iteration-002 已验证真实 candidates 排序主路径成立，但排序仍主要消费 query_relevance、preference_fit 和 feedback_score，长期画像与临时画像没有清晰分层。

当前缺口是：
1. evidence_log 还没有系统沉淀为 stable_preferences / negative_preferences。
2. negative_preferences 还没有稳定进入排序减分。
3. current_focus 还没有作为轻量临时信号参与排序。
4. get_profile 对偏好来源的解释能力不足。
5. 反馈前后排序变化还没有形成本地可验收闭环。
```

## 三、目标

```text
1. 在受控 feature 白名单内，实现 evidence_log -> stable_preferences / negative_preferences / current_focus 的沉淀规则。
2. 实现强显式反馈 1 次升级、普通 feedback 2 次同向升级。
3. 让 rank_candidates 消费长期正向偏好、长期负向偏好和 current_focus。
4. 让 get_profile 能解释偏好来源、证据数量和当前状态。
5. 用本地固定样例验证反馈前后排序变化。
```

## 四、非目标

```text
1. 不修改 Hermes 源码。
2. 不把远端 feedback/evidence 主路径纳入本轮阻塞验收。
3. 不做搜索前偏好注入。
4. 不做 observed_tool_candidates。
5. 不做 Obsidian 偏好底座。
6. 不做 UI、多用户、人工编辑画像界面。
7. 不做复杂衰减模型。
8. 不做高级冲突求解。
9. 不允许白名单外 feature 升级为长期偏好。
```

## 五、数据流

### 1. 反馈写入与升级

```text
用户反馈
  ↓
mcp_tastemate_record_feedback
  ↓
反馈分类：
- strong_positive
- strong_negative
- normal_positive
- normal_negative
- invalid
  ↓
先写 evidence_log
  ↓
按白名单 feature 判断是否可升级
  ↓
满足升级条件：
- strong 1 次
- normal 同向 2 次
  ↓
写入 stable_preferences 或 negative_preferences
  ↓
更新 current_focus
```

### 2. 排序消费画像

```text
用户发起新的 @taste 推荐请求
  ↓
Hermes 整理 candidates
  ↓
mcp_tastemate_rank_candidates
  ↓
读取 profile：
- stable_preferences
- negative_preferences
- current_focus
- evidence_log
  ↓
计算 query_relevance
  ↓
在相关候选之间应用画像加减分
  ↓
输出 ranked_candidates 和结构化 reasons
```

### 3. 画像解释

```text
用户调用 get_profile
  ↓
读取 profile
  ↓
汇总：
- 长期正向偏好
- 长期负向偏好
- 当前关注
- 证据数量
- 来源摘要
  ↓
返回结构化摘要
```

## 六、模块边界

### FeedbackProcessor

职责：

```text
1. 判断 feedback 是否有效。
2. 从 user_feedback + selected/rejected 提取 feature 和方向。
3. 判定 strong / normal。
4. 写 evidence_log。
5. 根据升级规则更新 stable_preferences / negative_preferences / current_focus。
```

不负责：

```text
1. 排序打分。
2. 候选生成。
3. Hermes 编排。
```

### Ranker

职责：

```text
1. 消费 stable_preferences / negative_preferences / current_focus。
2. 在 query_relevance 门槛内调整候选顺序。
3. 输出结构化 reasons。
```

不负责：

```text
1. 写 profile。
2. 生成长期偏好。
3. 解析 Hermes 外部状态。
```

### get_profile

职责：

```text
1. 汇总当前画像状态。
2. 输出长期偏好、负向偏好、当前关注和来源摘要。
```

不负责：

```text
1. 重新计算排序。
2. 修改画像。
```

## 七、接口设计

### 输入边界

本轮不修改 feedback 工具输入协议：

```json
{
  "query": "上一轮问题",
  "user_feedback": "用户反馈文本",
  "selected_candidate_ids": ["candidate-a"],
  "rejected_candidate_ids": ["candidate-b"],
  "candidates_snapshot": []
}
```

### 输出边界

本轮允许兼容扩展输出语义，不收缩已有字段，不要求 Hermes 侧改输入。

口径：

```text
1. record_feedback 的输出可增加更明确的 profile_updates 语义，但保持结构化 JSON 兼容。
2. get_profile 的输出可增加 stable_preferences / negative_preferences / current_focus 的摘要细节。
3. rank_candidates 的 ranked_candidates[].reasons 可增加“长期正向偏好命中 / 长期负向偏好触发 / current_focus 命中”这类解释短句。
```

这属于：

```text
输入协议不变；
输出做兼容扩展；
不引入新的外部调用契约依赖。
```

## 八、错误与降级

### 无效 feedback

条件：

```text
user_feedback 为空，且 selected/rejected 都为空。
```

降级：

```text
feedback_valid=false
不写 evidence_log
不更新长期偏好
不更新 current_focus
```

### 白名单外强反馈

条件：

```text
文本强烈，但 feature 无法映射到白名单。
```

降级：

```text
只写 evidence_log
不得升级 stable_preferences / negative_preferences
profile_updates 必须明确标识“未升级：feature 不在白名单”
```

### 冲突 feedback

条件：

```text
同一 feature 出现与既有长期偏好相反方向的新强反馈。
```

处理：

```text
按冲突覆盖规则处理；
必须在 profile_updates 中记录发生冲突覆盖。
```

## 九、成本与性能

```text
1. 仍保持本地规则逻辑，不引入模型调用。
2. 单次 record_feedback 与 rank_candidates 仍应维持毫秒级到低毫秒级处理。
3. 新增逻辑主要是 profile 读写、feature 聚合和结构化解释，不应引入明显等待。
```

本轮不优化：

```text
大规模 evidence 历史压缩
复杂画像重算
离线批处理
```

## 十、风险与应对

### R-001 强反馈误判

风险：

```text
文本规则过宽，把普通表达误判成强反馈。
```

应对：

```text
第一版只接受明确关键词和白名单 feature 映射；
宁可保守，不追求过高召回。
```

### R-002 长期偏好升级过快

风险：

```text
用户单次反馈把画像推得过重。
```

应对：

```text
使用本轮写死的 weight / confidence 上限和单次增量上限。
```

### R-003 白名单过窄导致很多 feedback 不升级

风险：

```text
真实反馈很多只进 evidence_log，不进入长期偏好。
```

应对：

```text
本轮接受这个保守限制；
后续迭代再扩 feature registry。
```

### R-004 current_focus 影响过强

风险：

```text
临时兴趣压过长期偏好或 query relevance。
```

应对：

```text
current_focus 只允许轻量修正；
验收直接检查其影响边界。
```

## 十一、验收标准

### A-001 强显式正向反馈 1 次可升级 stable_preferences

描述：

```text
强显式正向反馈 1 次可升级 stable_preferences。
```

验证方式：

```text
输入包含明确正向偏好词和白名单 feature 的 feedback。
```

通过条件：

```text
对应 feature 出现在 stable_preferences。
```

失败条件：

```text
未出现，或只写 evidence_log。
```

适用阶段：

```text
Iteration 003 本地 Verify
```

### A-002 强显式负向反馈 1 次可升级 negative_preferences

描述：

```text
强显式负向反馈 1 次可升级 negative_preferences。
```

验证方式：

```text
输入包含明确负向偏好词和白名单 feature 的 feedback。
```

通过条件：

```text
对应 feature 出现在 negative_preferences。
```

失败条件：

```text
未出现，或只写 evidence_log。
```

适用阶段：

```text
Iteration 003 本地 Verify
```

### A-003 普通 feedback 1 次只写 evidence，不直接升级长期偏好

描述：

```text
普通 feedback 1 次只写 evidence，不直接升级长期偏好。
```

验证方式：

```text
输入只有 selected/rejected 或弱文本表达的 feedback。
```

通过条件：

```text
evidence_log 新增；stable_preferences / negative_preferences 不新增该 feature。
```

失败条件：

```text
一次普通 feedback 直接形成长期偏好。
```

适用阶段：

```text
Iteration 003 本地 Verify
```

### A-004 普通同向 feedback 达到 2 次后可升级长期偏好

描述：

```text
普通同向 feedback 达到 2 次后可升级长期偏好。
```

验证方式：

```text
对同一白名单 feature 连续输入 2 次同向普通 feedback。
```

通过条件：

```text
第 2 次后对应 feature 出现在 stable_preferences 或 negative_preferences。
```

失败条件：

```text
第 2 次后仍未升级，或第 1 次就升级。
```

适用阶段：

```text
Iteration 003 本地 Verify
```

### A-005 长期正向偏好会对相关候选产生可解释加分

描述：

```text
长期正向偏好会对相关候选产生可解释加分。
```

验证方式：

```text
构造两个 query_relevance 相近的候选，其中一个命中 stable_preferences。
```

通过条件：

```text
命中长期正向偏好的候选排序更高，reasons 包含长期正向偏好命中说明。
```

失败条件：

```text
排序不变，或 reasons 无对应说明。
```

适用阶段：

```text
Iteration 003 本地 Verify
```

### A-006 长期负向偏好会对相关候选产生可解释减分

描述：

```text
长期负向偏好会对相关候选产生可解释减分。
```

验证方式：

```text
构造两个 query_relevance 相近的候选，其中一个命中 negative_preferences。
```

通过条件：

```text
命中长期负向偏好的候选排序更低，reasons 包含长期负向偏好触发说明。
```

失败条件：

```text
排序不变，或 reasons 无对应说明。
```

适用阶段：

```text
Iteration 003 本地 Verify
```

### A-007 current_focus 只做轻量修正，不压过 query relevance

描述：

```text
current_focus 只做轻量修正，不压过 query relevance。
```

验证方式：

```text
构造一组候选，其中高相关候选不命中 current_focus，低相关候选命中 current_focus。
```

通过条件：

```text
current_focus 加成后，低相关候选不得因为 current_focus 反超高相关候选。
```

失败条件：

```text
仅因 current_focus 命中，低相关候选反超更高 query_relevance 候选。
```

适用阶段：

```text
Iteration 003 本地 Verify
```

### A-008 get_profile 能解释偏好来源和证据数量

描述：

```text
get_profile 能解释偏好来源和证据数量。
```

验证方式：

```text
写入可升级 feedback 后调用 get_profile。
```

通过条件：

```text
输出中包含 stable_preferences / negative_preferences、对应 evidence_count 和来源摘要。
```

失败条件：

```text
只有空泛 summary，没有证据数量或来源摘要。
```

适用阶段：

```text
Iteration 003 本地 Verify
```

### A-009 给定固定候选集时，反馈前后排序变化符合指定样例

描述：

```text
给定固定候选集时，反馈前后排序变化符合指定样例。
```

验证方式：

```text
固定候选集包含 local-first 候选和 cloud-required 候选；先记录排序，再写入“明确偏好本地优先、不要 SaaS”类 feedback，再次排序。
```

通过条件：

```text
写入反馈后，local-first 候选排名上升，cloud-required 候选排名下降。
```

失败条件：

```text
排序无变化，或变化方向相反。
```

适用阶段：

```text
Iteration 003 本地 Verify
```

### A-010 单次反馈不会把长期画像推得过高

描述：

```text
单次反馈不会把长期画像推得过高。
```

验证方式：

```text
输入 1 次强反馈后读取 profile。
```

通过条件：

```text
新增或更新的 feature 满足：
weight <= 0.35
confidence <= 0.65
单次 weight 增长 <= 0.10
单次 confidence 增长 <= 0.05
```

失败条件：

```text
任一阈值超出。
```

适用阶段：

```text
Iteration 003 本地 Verify
```

## 十二、后续迭代

```text
1. 扩展 feature registry。
2. 更复杂的冲突处理与衰减规则。
3. 远端 feedback/evidence 主路径验证。
4. Obsidian 偏好底座。
5. 搜索前偏好注入。
```
