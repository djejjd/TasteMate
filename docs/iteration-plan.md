# TasteMate 迭代规划

## 一、当前阶段

```text
迭代一已完成。
迭代二已完成。
下一步进入迭代三 Intake / Discovery 准备阶段。
```

迭代一已经验证：

```text
Hermes 能发现 TasteMate MCP。
显式 @taste 能通过 Hermes 插件触发 TasteMate。
TasteMate 能完成候选重排。
用户明确反馈能写入 profile evidence_log。
```

迭代一的主要限制：

```text
tastemate-route 插件仍使用 fixed_probe_candidates。
固定候选只能验证通道，不能验证真实推荐质量。
```

---

## 二、迭代二：真实候选排序

### 目标

把固定候选替换为真实候选，让 Hermes 主动整理 candidates 后调用 TasteMate 排序。

核心流程：

```text
用户 @taste 提问
  ↓
Hermes 基于用户给定候选或已有知识整理真实候选
  ↓
Hermes 按 candidates 协议调用 mcp_tastemate_rank_candidates
  ↓
TasteMate 对真实候选排序
  ↓
Hermes 基于排序结果回复
```

### 范围

```text
candidates 协议
用户给定候选的结构化
Hermes 基于已有知识生成候选
真实 candidates 排序
候选整理边界提示
```

### 不做

```text
不做 Hermes 工具结果自动抽取
不做搜索前偏好注入
不做 feedback 画像增强
不做 Obsidian 偏好底座
不修改 Hermes 源码
```

### 已完成穿刺结论

```text
问题 1：用户给候选 -> Hermes 结构化 -> TasteMate 排序，PASS。
问题 2：用户不给候选 -> Hermes 基于已有知识生成候选 -> TasteMate 排序，PASS。
问题 3：允许一次补全查询 -> 最终 fallback 并排序，部分 PASS；补全步骤耗时 60s，不作为必需路径。
```

### 验收标准

```text
不再用 fixed_probe_candidates 作为主路径。
Hermes 调用 mcp_tastemate_rank_candidates 时传入真实 candidates。
candidates 必填字段至少包含 id、title、summary、metadata。
url、source 是推荐字段；缺失时不能阻止真实候选排序验收。
用户给定候选和 Hermes 已有知识候选两类输入都能完成排序。
Hermes 候选整理不能替代 TasteMate 排序，也不能只生成普通推荐报告。
```

### 主要风险

```text
Hermes 只生成普通推荐报告，不调用 TasteMate。
Hermes 生成的 candidates 字段不稳定。
真实候选路径仍误走 fixed_probe_candidates。
候选整理扩展成长链路调研，拖慢 @taste 回复。
```

### 风险应对

```text
@taste 推荐流程必须明确最终调用 mcp_tastemate_rank_candidates。
验收以工具调用日志和 candidates 参数为准，不以最终回复文本为准。
candidates 必填字段只要求 id、title、summary、metadata；url 和 source 作为推荐字段。
检查 tastemate-route 日志，确认真实候选验收没有新增 fixed_probe_candidates 记录。
提示 Hermes 尽快形成 3-5 个 candidates 并调用 TasteMate，候选整理不能替代排序。
```

### 完成结论

```text
Build、Verify、Multi-Agent Review、Closeout 已完成。
用户给定候选和 Hermes 已有知识候选两类路径均已通过验收。
真实候选验收中没有 fixed_probe_candidates 主路径记录。
iteration-002 已可作为 iteration-003 的输入基线。
```

---

## 三、迭代三：反馈画像增强

### 目标

把 record_feedback 写入的 evidence_log 更系统地沉淀为稳定画像，让反馈真正影响后续排序。

### 可能能力

```text
profile updater
stable_preferences 沉淀规则
negative_preferences 沉淀规则
多次反馈聚合
单次反馈权重上限
```

### 验收标准

```text
选择“本地优先”后，后续类似问题本地候选排名上升。
拒绝“企业 SaaS”后，类似候选排名下降。
单次反馈不会过度污染长期画像。
```

---

## 四、迭代四：Obsidian 偏好底座

### 目标

把 Obsidian 作为长期偏好和个人知识材料来源，同时保留 profile.json 作为机器可读画像索引。

### 定位

```text
Obsidian：人类可读、可编辑、可审计的偏好知识库。
profile.json：机器可读、排序稳定使用的画像索引。
```

### 可能能力

```text
配置 Obsidian vault 路径
定义 TasteMate 专用目录
从 Markdown 笔记抽取 preference evidence
同步到 profile.json
让 get_profile 能解释偏好来源
```

---

## 五、迭代五：自动候选抽取

### 目标

验证并实现 observed_tool_candidates，从 Hermes 搜索或工具结果中自动抽取候选。

### 触发条件

```text
迭代二真实候选排序稳定后再进入。
```

### 关键风险

```text
Hermes 是否向插件暴露搜索结果或工具 observation。
工具结果格式是否稳定。
候选去重、字段补全、置信度判断是否可控。
```

---

## 六、迭代六：搜索前偏好注入

### 目标

在搜索前给 Hermes 提供轻量偏好 hints，提高召回质量。

### 边界

```text
只提供轻量 hints。
不强行改写用户问题。
事实类问题不介入。
用户未显式 @taste 默认不介入。
```

---

## 七、迭代七：gateway send API / 更自然回复通道

### 目标

探索比 pre_gateway_dispatch rewrite 更自然的回复方式。

### 可能能力

```text
gateway send API
追加回复
结构化结果
多阶段回复
```

这些能力不阻塞当前 rewrite 主链路。
