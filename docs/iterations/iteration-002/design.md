# Iteration 002 Design：真实候选排序

## 一、当前结论

```text
迭代二采用 Hermes 主动整理 candidates 的方案。
TasteMate 只接收真实 candidates 并排序，不负责搜索。
```

## 二、背景与问题

迭代一已经打通：

```text
@taste -> Hermes -> TasteMate MCP -> 排序 -> 回复 -> 反馈写入
```

但迭代一的 `tastemate-route` 插件仍使用固定候选：

```text
fixed_probe_candidates
```

固定候选只能证明通道可行，不能证明 TasteMate 对真实推荐问题有价值。迭代二要把排序对象换成真实候选。

## 三、目标

```text
支持真实 candidates 排序。
支持用户给定候选。
支持 Hermes 基于已有知识生成候选。
明确 candidates 最小协议。
明确 Hermes 候选整理不能替代 TasteMate 排序。
```

## 四、非目标

```text
不实现 observed_tool_candidates。
不从 Hermes 工具结果中自动抽取候选。
不实现搜索前偏好注入。
不增强 feedback 画像沉淀。
不接入 Obsidian。
不修改 Hermes 源码。
```

## 五、数据流

### 主路径 A：用户给候选

```text
用户 @taste + 候选列表
  ↓
Hermes 将候选整理为 candidates
  ↓
Hermes 调用 mcp_tastemate_rank_candidates
  ↓
TasteMate 返回 ranked_candidates
  ↓
Hermes 基于排序结果回复
```

### 主路径 B：Hermes 基于已有知识给候选

```text
用户 @taste + 推荐目标
  ↓
Hermes 基于已有知识列出 3-5 个真实候选
  ↓
Hermes 整理 candidates
  ↓
Hermes 调用 mcp_tastemate_rank_candidates
  ↓
TasteMate 返回 ranked_candidates
  ↓
Hermes 基于排序结果回复
```

## 六、模块边界

### Hermes

职责：

```text
识别 @taste 推荐意图。
整理真实 candidates。
调用 mcp_tastemate_rank_candidates。
基于 TasteMate 结果回复。
```

不负责：

```text
偏好评分。
profile 更新。
候选排序算法。
```

### TasteMate

职责：

```text
校验 candidates。
基于 query、candidate、profile 计算排序。
返回 ranked_candidates 和 reasons。
```

不负责：

```text
搜索候选。
判断 Hermes 是否已经充分调研。
```

### tastemate-route 插件

迭代二中的定位：

```text
保留作为迭代一通道穿刺和回归验证路径。
不作为真实候选主路径。
```

## 七、接口设计

### rank_candidates 输入

```json
{
  "query": "推荐适合个人开发者优先尝试的 AI agent 框架",
  "taste_mode": "force",
  "candidates": [
    {
      "id": "smolagents",
      "title": "Smolagents",
      "summary": "Hugging Face 的轻量 agent 框架，适合本地和实验型 agent。",
      "url": "https://github.com/huggingface/smolagents",
      "metadata": {
        "language": "Python",
        "open_source": true,
        "complexity": "Very Low",
        "best_for": "Minimal setups and research experiments",
        "local_first": true,
        "self_hosted": true
      }
    }
  ]
}
```

### Candidate 必填字段

```text
id
title
summary
metadata
```

### Candidate 推荐字段

```text
url
source
```

`url` 和 `source` 缺失不阻塞迭代二真实候选排序验收。

### metadata 最小推荐字段

```text
language
open_source
complexity
best_for
local_first
self_hosted
```

metadata 是开放对象，但迭代二不能要求所有主题都有相同字段。TasteMate 只能把字段作为评分证据，不能假设字段一定存在。

### rank_candidates 输出

```json
{
  "ranking_needed": true,
  "mode": "recommendation",
  "action": "ranked",
  "ranked_candidates": [
    {
      "id": "smolagents",
      "title": "Smolagents",
      "final_score": 0.7025,
      "query_relevance": 0.65,
      "preference_fit": 0.9,
      "feedback_score": 0.5,
      "reasons": ["符合开源偏好", "符合本地优先偏好"],
      "risks": []
    }
  ]
}
```

## 八、错误与降级

### candidates 为空

降级：

```text
TasteMate 返回 passthrough 或 needs_more_candidates。
Hermes 不伪造排序结果。
```

### candidates 少于 2 个

降级：

```text
返回 needs_more_candidates。
Hermes 说明候选不足。
```

### 候选缺少 summary

降级：

```text
返回 low_confidence。
Hermes 要求补充候选信息。
```

### 候选缺少必填字段

缺少以下任一字段时，候选不满足迭代二最小协议：

```text
id
title
summary
metadata
```

降级：

```text
TasteMate 返回 invalid_candidates 或 low_confidence。
Hermes 说明候选字段不足，需要补充候选信息。
Hermes 不能伪造 TasteMate 排序结果。
```

### Hermes 未调用 TasteMate

降级：

```text
不能声称 TasteMate 已排序。
验收判定失败。
```

## 九、成本与性能

```text
TasteMate rank_candidates 调用约 0.00s - 0.01s。
主要成本来自 Hermes 候选整理。
Hermes 应尽快形成 3-5 个 candidates 并调用 TasteMate。
候选整理不能扩展成长报告生成。
```

## 十、风险与应对

### R-001 Hermes 不稳定主动调用 TasteMate

应对：

```text
@taste 流程必须明确最终调用 mcp_tastemate_rank_candidates。
验收以工具调用日志为准。
```

### R-002 Hermes 候选质量不足

应对：

```text
要求 3-5 个候选。
要求 summary 描述候选适用场景。
候选不足时不排序。
```

### R-003 metadata 不足导致排序区分度低

应对：

```text
定义 metadata 最小推荐字段。
评分逻辑只使用存在的字段，不强依赖特定字段。
```

### R-004 Hermes 过度调研

应对：

```text
提示必须要求 Hermes 形成 candidates 后调用 TasteMate。
验收以工具调用日志和 candidates 参数为准，不以普通推荐报告为准。
```

## 十一、验收标准

### A-001 用户给候选

描述：

```text
用户给出候选列表，Hermes 整理 candidates 并调用 TasteMate。
```

验证方式：

```text
发送 @taste + 候选列表。
检查 Hermes 工具调用日志。
```

通过条件：

```text
出现 mcp_tastemate_rank_candidates completed。
candidates 为用户给定候选。
每个 candidate 至少包含 id、title、summary、metadata。
url 和 source 缺失不阻塞验收。
没有 fixed_probe_candidates 记录。
```

失败条件：

```text
Hermes 未调用 TasteMate。
Hermes 只输出普通推荐。
Hermes 使用 fixed_probe_candidates。
```

### A-002 Hermes 基于已有知识生成候选

描述：

```text
用户不给候选，Hermes 基于已有知识生成 3-5 个真实候选。
```

验证方式：

```text
发送 @taste 推荐类问题。
检查工具调用日志和 candidates。
```

通过条件：

```text
Hermes 调用 mcp_tastemate_rank_candidates。
candidates 是真实候选。
每个 candidate 至少包含 id、title、summary、metadata。
url 和 source 缺失不阻塞验收。
```

失败条件：

```text
Hermes 未调用 TasteMate。
Hermes 只生成普通推荐报告。
```

### A-003 fixed_probe_candidates 退出主路径

描述：

```text
迭代二真实候选路径不能依赖 fixed_probe_candidates。
```

验证方式：

```text
检查 tastemate-route 日志和工具调用参数。
```

通过条件：

```text
真实候选验收中没有新增 fixed_probe_candidates 记录。
```

失败条件：

```text
真实候选验收仍走 fixed_probe_candidates。
```

### A-004 候选最小协议校验

描述：

```text
迭代二真实候选必须满足最小 candidates 协议。
```

验证方式：

```text
检查 mcp_tastemate_rank_candidates 工具调用参数。
传入缺少 id、title、summary 或 metadata 的候选。
```

通过条件：

```text
有效候选路径中，每个 candidate 至少包含 id、title、summary、metadata。
缺少必填字段时，TasteMate 返回 invalid_candidates、low_confidence 或等价降级结果。
Hermes 不伪造已完成排序。
```

失败条件：

```text
缺少必填字段的候选仍被当成正常 ranked 结果验收。
Hermes 在 TasteMate 降级后声称已完成排序。
```

## 十二、后续迭代

```text
反馈画像增强：迭代三。
Obsidian 偏好底座：迭代四。
observed_tool_candidates 自动抽取：迭代五。
搜索前偏好注入：迭代六。
gateway send API：迭代七。
```
