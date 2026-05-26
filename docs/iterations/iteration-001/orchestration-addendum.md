# Iteration 001 Addendum：Hermes @taste rewrite 编排补充

## 适用阶段

```text
Iteration 001 / Verify 后验收补充
```

## 一句话结论

```text
Iteration 001 不单独拆新迭代；Hermes @taste rewrite 编排用于补齐 A-002 验收，不扩大 TasteMate 当前能力边界。
```

## 背景

原计划依赖 Hermes 模型在显式 `@taste` 推荐类问题中自主调用 `mcp_tastemate_rank_candidates`。

Verify 阶段已否定以下软提示路线：

```text
Prompt 强制调用。
临时 AGENTS.md 强规则。
pre_llm_call 插件注入。
```

失败现象一致：

```text
Hermes 可能输出像 TasteMate 排序的文本，但日志没有真实 mcp_tastemate_rank_candidates 调用。
```

因此 A-002 的验收路径需要从“模型自发工具调用”修正为“插件确定性编排工具调用”。

## 目标

补齐当前迭代验收标准：

```text
A-002：@taste 推荐类问题触发 rank_candidates。
```

本补充的目标是：

```text
Hermes 在用户显式输入 @taste 推荐类问题时，
由插件在 pre_gateway_dispatch 阶段检测请求，
主动调用 mcp_tastemate_rank_candidates，
再把真实 TasteMate 结果 rewrite 回 Hermes 自有 agent 回复通道。
```

## 非目标

```text
不修改 Hermes 源码。
不做搜索前偏好注入。
不做 gateway send API 直发闭环。
不做 UI。
不做多用户系统。
不做 record_feedback 自动编排。
不做复杂候选缓存。
不把 Hermes 搜索结果自动抽取作为本补充的必交付项。
```

gateway send API 可以作为后续探索项，但不阻塞当前 rewrite 编排闭环。

## 数据流

```text
用户输入 @taste 推荐类问题
  ↓
Hermes gateway 收到 MessageEvent
  ↓
pre_gateway_dispatch hook
  ↓
TasteMate route plugin 判断是否命中显式 @taste 推荐类 gate
  ↓
未命中：return {"action": "allow"}
  ↓
命中：插件主动调用 mcp_tastemate_rank_candidates
  ↓
TasteMate 返回 structuredContent
  ↓
插件生成包含真实排序结果的 rewrite text
  ↓
return {"action": "rewrite", "text": "..."}
  ↓
Hermes agent 通过原有回复通道组织最终回答
```

## Gate 规则

第一版 gate 必须保守：

```text
必须包含 @taste。
必须包含推荐类意图词，例如：推荐、比较、选型、排序、适合、工具。
```

普通问题不触发 TasteMate：

```text
Hermes 的配置在哪？
```

事实类 `@taste` 问题仍由 TasteMate ranker 的 passthrough 逻辑兜底：

```text
@taste Hermes 的 MCP 配置文件在哪？
```

## 候选策略

本补充的穿刺阶段允许使用固定候选，原因是：

```text
本轮优先验证 @taste 检测、主动 dispatch 和 rewrite 通道。
Hermes 搜索候选如何抽取是下一步工程问题，不作为当前穿刺通过条件。
```

正式固化时，候选来源必须单独设计和验收，不能把固定候选伪装成真实推荐能力。

## 验收标准

### O-001 普通消息不介入

验证方式：

```text
模拟或发送普通消息。
```

通过条件：

```text
pre_gateway_dispatch 返回 {"action": "allow"}。
无 mcp_tastemate_rank_candidates 调用。
```

### O-002 @taste 推荐消息触发真实 TasteMate 调用

验证方式：

```text
模拟或发送 @taste 推荐类消息。
```

通过条件：

```text
pre_gateway_dispatch 返回 {"action": "rewrite", "text": "..."}。
rewrite text 来自真实 mcp_tastemate_rank_candidates structuredContent。
日志或验证输出包含 action=ranked 或 needs_more_candidates。
```

### O-003 不修改 Hermes 源码

验证方式：

```text
检查变更范围。
```

通过条件：

```text
本补充只使用用户插件或 TasteMate 仓库文档，不修改 Hermes 源码目录。
```

## 已完成穿刺证据

证据入口：

```text
docs/iterations/iteration-001/probes/hermes-plugin-dispatch-probe.md
```

已验证：

```text
discover_mcp_tools() 能发现 mcp_tastemate_rank_candidates。
handle_function_call("mcp_tastemate_rank_candidates", args) 返回 structuredContent.action=ranked。
普通消息触发 pre_gateway_dispatch 时返回 action=allow。
@taste 推荐消息触发 pre_gateway_dispatch 时返回 action=rewrite。
rewrite text 包含真实 TasteMate 排序结果。
```

## 风险

```text
rewrite 后仍由 Hermes agent 组织最终回复，可能改写排序表达方式。
固定候选只能证明编排通道，不证明真实推荐质量。
候选来源仍需下一步设计。
explicit_candidates 尚未设计输入格式，不能写成当前实现能力。
observed_tool_candidates 尚未穿刺验证，不能写成当前可行能力。
gateway send API 直发能力未验证。
```

## 当前判定

```text
Hermes 主动调用 TasteMate：PASS。
@taste 检测：PASS。
rewrite 回 Hermes 自有回复通道：PASS。
真实端到端用户消息验收：待执行。
候选来源固化：待设计。
```
