# TasteMate 设计文档

## 一、设计目标

TasteMate 第一阶段要解决的问题是：

```text
当 Hermes 已经收集到一批候选结果时，
TasteMate 能否按我的个人偏好进行可解释重排，
并在后续反馈中逐步学习我的偏好。
```

第一阶段不解决：

```text
不替代 Hermes 搜索
不修改 Hermes 源码
不做多用户推荐系统
不训练复杂推荐模型
不默认介入所有问题
```

---

## 二、系统边界

TasteMate 在整体数据流中处于 Hermes 的后置偏好层。

```text
用户
  ↓
Hermes
  ↓
搜索、读取、整理候选
  ↓
TasteMate
  ↓
个性化判断、评分、重排、反馈学习
  ↓
Hermes
  ↓
最终回答
```

第一阶段 TasteMate 不进入搜索召回阶段，只处理 Hermes 已经拿到的候选。

---

## 三、核心数据流

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

```text
用户使用 @taste 提问
  ↓
Hermes 正常理解问题
  ↓
Hermes 调用搜索、读取、资料整理等工具
  ↓
形成候选结果
  ↓
Hermes 调用 mcp_tastemate_rank_candidates
  ↓
TasteMate 判断是否需要个性化排序
  ↓
不需要：返回 passthrough
需要：执行评分和重排
  ↓
Hermes 根据 TasteMate 结果输出
```

### 3. 反馈学习流程

```text
Hermes 输出推荐结果
  ↓
用户选择、追问、否定或表达偏好
  ↓
Hermes 调用 mcp_tastemate_record_feedback
  ↓
TasteMate 判断反馈是否有效
  ↓
抽取偏好信号
  ↓
更新 evidence_log、current_focus、stable_preferences 或 negative_preferences
```

---

## 四、关键模块

### 1. MCP Server

TasteMate 作为外部 MCP server 接入 Hermes。

第一阶段暴露工具：

```text
rank_candidates
record_feedback
get_profile
```

后续可扩展：

```text
get_search_hints
classify_task
explain_profile
```

这些扩展工具不进入迭代一，只用于后续增强：

| 工具 | 作用 | 使用阶段 |
| --- | --- | --- |
| `get_search_hints` | 根据个人画像生成轻量搜索提示，例如优先本地部署、开源、低维护，避免纯 SaaS 或企业销售导向 | 搜索前增强 |
| `classify_task` | 单独判断某个问题是否需要个性化、是否适合排序。迭代一先合并在 `rank_candidates` 内部，不单独暴露 | 成本控制或流程前置判断 |
| `explain_profile` | 解释当前画像为什么形成某些偏好，方便用户审计和纠正，例如“为什么本地优先权重较高” | 画像解释与人工校正 |

因此第一阶段的边界是：

```text
rank_candidates / record_feedback / get_profile 是核心工具。
get_search_hints / classify_task / explain_profile 是后续增强工具。
```

### 2. Ranker

Ranker 负责候选排序。

职责：

```text
判断 ranking_needed
计算 query_relevance
计算 preference_fit
合并 feedback_score
输出 final_score
输出解释和风险
```

### 3. Feedback Processor

Feedback Processor 负责从用户后续行为中学习。

职责：

```text
判断 feedback_valid
识别 selected/rejected candidates
抽取偏好特征
估算 signal_strength
生成 profile_updates
写入 evidence_log
```

### 4. Profile Store

Profile Store 保存可解释画像。

建议第一阶段用本地文件或 SQLite，不引入复杂数据库。

画像包含：

```text
stable_preferences
negative_preferences
current_focus
evidence_log
```

---

## 五、评分设计

第一阶段评分是后置重排分，不是搜索召回分，也不是候选的永久质量分。
TasteMate 只对 Hermes 已经收集到的本轮候选做排序，排序结果只服务于当前回答。

迭代一不依赖 LLM 评分。分数来自规则信号：

```text
query 文本：是否是推荐类问题、是否包含明确主题或约束。
candidate 字段：title、summary、url、source、metadata。
candidate metadata：open_source、local_first、supports_mcp、cloud_required、enterprise_oriented 等。
profile evidence_log：历史反馈中抽取出的 feature、direction、strength。
```

候选最终评分：

```text
final_score =
  query_relevance * 0.55
+ preference_fit * 0.30
+ feedback_score * 0.15
```

权重意图：

```text
query_relevance 是门槛，明显不相关候选不能因为符合偏好排到前面。
preference_fit 体现个人偏好，但只能在相关候选之间调整顺序。
feedback_score 使用历史反馈，但第一阶段权重较低，避免早期少量反馈污染排序。
```

### query_relevance

判断候选是否回答当前问题。

考虑：

```text
主题是否匹配
约束是否匹配
是否有明确依据
信息是否完整
是否足够新
```

### preference_fit

判断候选是否符合个人偏好。

考虑：

```text
是否本地优先
是否开源
是否低维护
是否外置集成友好
是否避免企业化或高复杂度方案
```

### feedback_score

来自历史选择、否定和明确表达。

第一阶段反馈优先按 feature 泛化，而不是只绑定某个候选 ID。例如用户选择了本地优先工具，TasteMate 记录 `local_first` 正向 evidence；后续新的本地优先候选也可以获得轻微信号加成。

反馈权重第一版应保守，避免一次选择影响过大。

---

## 六、模型调用策略

TasteMate 不做每轮固定模型调用。

这里的“最多一次模型调用”是设计预算上限，不表示迭代一 Build 必须调用 LLM。迭代一实现口径是：`rank_candidates` 和 `record_feedback` 都先使用规则逻辑，不接真实 LLM；后续如接入 LLM，仍不得超过这里的预算上限。

```text
无 @taste：不调用
有 @taste 且无候选：不调用或直接 passthrough
有 @taste 且有候选：rank_candidates 最多一次模型调用
上一轮是 @taste 推荐上下文且用户给出明确反馈：record_feedback 最多一次模型调用
```

这里的“候选”不是指偏好，而是指 Hermes 已经收集到的、可以被比较和排序的对象。

候选可以是：

```text
几个工具
几篇文章
几个开源项目
几个技术方案
几个资料来源
几个候选答案
```

例如：

```text
@taste 推荐几个适合我的本地知识库工具
```

如果 Hermes 已经收集到 Obsidian、Logseq、SiYuan、Anytype 等对象，这些就是候选，TasteMate 可以进入 `rank_candidates`。

而下面这种问题即使带了 `@taste`，通常也没有候选集合：

```text
@taste Hermes 的 MCP 配置文件在哪？
```

它更接近确定性事实问题，没有多个对象需要比较。此时 TasteMate 应返回 `passthrough`，不做排序。

因此更准确的判断是：

```text
有 @taste 只是允许 TasteMate 介入。
是否调用 LLM 排序，取决于本轮是否存在可排序候选集合。
```

规则可判断的场景优先走规则。

LLM 主要用于：

```text
语义相关性评分
偏好匹配解释
自然语言反馈抽取
复杂冲突判断
```

---

## 七、错误与降级

如果 TasteMate 不可用：

```text
Hermes 应继续给出普通回答。
```

如果 rank_candidates 判断不需要排序：

```text
返回 passthrough，不强行个性化。
```

如果候选信息不足：

```text
返回 needs_more_candidates 或 low_confidence，
由 Hermes 决定是否继续搜索。
```

这里依赖 Hermes 的多轮工具调用机制。Hermes 执行一个工具后，会把工具结果放回对话上下文，并进入下一轮模型调用；模型可以基于上一个工具结果继续调用搜索工具或给出最终回答。

因此 TasteMate 可以返回：

```json
{
  "action": "needs_more_candidates",
  "reason": "候选数量不足，且缺少本地部署或开源方向的结果",
  "suggested_search_hints": [
    "local-first knowledge base open source",
    "self-hosted note taking app",
    "MCP compatible personal knowledge base"
  ]
}
```

Hermes 下一轮看到这个工具结果后，可以继续搜索。

但第一阶段要明确限制：

```text
TasteMate 不能强制 Hermes 自动重搜。
Hermes 有继续搜索的机制，但是否继续搜索由模型根据工具结果决定。
如果后续需要强制编排，需要进入 Hermes plugin/hook 增强阶段。
```

如果反馈无法识别：

```text
只记录原始事件，不更新稳定偏好。
```

### 反馈触发边界

用户不需要在反馈消息里再次输入 `@taste`。

第一阶段反馈收集依赖 Hermes 的上下文判断：

```text
上一轮不是 @taste 推荐结果：TasteMate 不介入，不调用 record_feedback。
上一轮是 @taste 推荐结果：用户后续表达选择、否定或偏好时，Hermes 可以调用 record_feedback。
record_feedback 必须携带上一轮 query、用户反馈文本、候选快照、selected/rejected candidate ids。
```

示例：

```text
用户：@taste 推荐几个适合我的本地知识库工具
Hermes：搜索候选，调用 rank_candidates，给出排序结果
用户：我选第一个，不要企业 SaaS 那种
Hermes：基于上一轮 @taste 上下文调用 record_feedback
TasteMate：写入 evidence_log，并保守更新 current_focus 或已有 stable preference
```

如果 Hermes 不能稳定识别上一轮 TasteMate 上下文并调用 `record_feedback`，这是迭代一验证风险，不在本阶段通过 plugin/hook 强制编排。

---

## 八、后续增强位置

第二阶段可增强搜索前偏好注入。

它在数据流中的位置是：

```text
用户提问
  ↓
Hermes pre_llm_call hook
  ↓
TasteMate 生成轻量偏好上下文
  ↓
Hermes 更有方向地搜索
```

该能力不进入第一阶段实现范围。
