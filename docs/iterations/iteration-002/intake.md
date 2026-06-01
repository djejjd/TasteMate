# Iteration 002 Intake：真实候选排序

## 一、原始需求

```text
基于迭代一现状进入迭代二。
迭代二优先验证 Hermes 主动整理真实候选并传给 TasteMate 是否可行。
如果不可行，再考虑插件抽取 observed_tool_candidates。
```

## 二、当前理解

迭代一已经证明 `@taste` 通道和 TasteMate MCP 调用可用，但主路径仍使用 `fixed_probe_candidates`。迭代二要解决的问题是：

```text
不要再对固定候选排序。
让 Hermes 把真实候选整理成 candidates。
TasteMate 只负责排序和解释。
```

## 三、目标

```text
定义真实 candidates 协议。
支持用户给定候选的结构化排序。
支持 Hermes 基于已有知识生成候选并排序。
```

## 四、非目标

```text
不做 Hermes 工具结果自动抽取。
不做搜索前偏好注入。
不做 feedback 画像增强。
不做 Obsidian 偏好底座。
不改 Hermes 源码。
```

## 五、约束

```text
技术约束：TasteMate 继续作为 MCP server；Hermes 主动调用 mcp_tastemate_rank_candidates。
范围约束：只替换固定候选主路径，不扩展反馈学习。
成本约束：候选整理必须服务于排序，不扩展成长报告生成。
时间约束：先完成设计和开发规格，再进入 Plan。
```

## 六、当前阶段

```text
Plan 准备
```

## 七、需要调研的问题

```text
1. candidates 最小字段如何定义。
2. Hermes 主动整理 candidates 的提示和编排边界如何写入文档。
3. fixed_probe_candidates 如何保留为测试路径，但不进入迭代二主路径。
4. Hermes 未形成足够 candidates 时如何降级。
```

## 八、输出产物

```text
docs/iterations/iteration-002/intake.md
docs/iterations/iteration-002/discovery.md
docs/iterations/iteration-002/design.md
后续进入 development spec 和 plan。
```
