# Hermes Plugin Dispatch Probe：最小穿刺验证

## 适用阶段

```text
Iteration 001 Verify / 技术方向穿刺
```

## 结论先行

```text
本穿刺只验证 Hermes 插件是否能不依赖 LLM 决策，主动调用已注册的 TasteMate MCP 工具。
```

## 目标

验证以下技术方向是否成立：

```text
Hermes plugin -> ctx.dispatch_tool("mcp_tastemate_rank_candidates", args) -> TasteMate MCP server
```

## 非目标

```text
不修改 Hermes 源码。
不解决 Hermes 搜索候选如何传给 TasteMate。
不继续强化 prompt、AGENTS 或 pre_llm_call。
不把 plugin 编排写成迭代一已交付能力。
不验证 record_feedback。
```

## 最小探针设计

创建临时用户插件：

```text
插件名：tastemate-route-probe
入口：/taste-probe
动作：使用固定 candidates 调用 mcp_tastemate_rank_candidates
证据：命令返回包含 action=ranked 或 needs_more_candidates，且 Hermes 日志出现真实 mcp_tastemate_rank_candidates 调用
```

固定候选只用于穿刺：

```text
local-first 知识库工具
云端优先知识库工具
MCP 兼容个人助手
```

## 判定标准

PASS：

```text
插件命令能通过 ctx.dispatch_tool 调用 mcp_tastemate_rank_candidates，并返回 TasteMate 结构化结果。
```

FOLLOW_UP：

```text
插件能调用 MCP 工具，但当前入口不能自然承接 @taste 消息或 Hermes 搜索候选。
```

BLOCK：

```text
插件上下文无法主动 dispatch MCP 工具，或 MCP 工具在 registry 中不可见。
```

## 后续决策

```text
PASS 后进入候选传递 Discovery。
FOLLOW_UP 后继续找 message route / gateway hook / post-search hook。
BLOCK 后转向外部 wrapper，或由用户决定是否批准 Hermes 源码补丁。
```

## Gateway rewrite 穿刺

### 验证问题

```text
P1：pre_gateway_dispatch 是否能检测 @taste 消息。
P2：检测后是否能把真实 TasteMate 调用结果 rewrite 回 Hermes 自有 agent 回复通道。
```

### 探针行为

```text
普通消息：返回 {"action": "allow"}。
@taste 推荐类消息：调用 mcp_tastemate_rank_candidates，生成包含排序结果的 rewrite text，返回 {"action": "rewrite", "text": "..."}。
```

### 2026-05-27 结果摘要

命令摘要：

```text
在远程 hermes 容器内使用 <HERMES_APP_DIR>/.venv/bin/python 执行 hook 验证脚本。
脚本调用 discover_mcp_tools()、discover_plugins(force=True)，再通过 invoke_hook("pre_gateway_dispatch", event=...) 模拟 gateway 消息。
```

结果摘要：

```text
普通消息：RESULTS=[{"action": "allow"}]。
@taste 推荐消息：RESULTS=[{"action": "rewrite", "text": "..."}]。
rewrite text 包含 "TasteMate 已完成真实后置重排"，并包含 Local-first KB、Cloud KB、MCP Assistant 的 final_score 和 reasons。
```

判定：

```text
P1 PASS：pre_gateway_dispatch 能检测 @taste。
P2 PASS（rewrite 路线）：插件能真实调用 TasteMate，并把排序结果 rewrite 回 Hermes 自有 agent 回复通道。
P2 FOLLOW_UP（直发路线）：pre_gateway_dispatch 返回协议没有直接 reply；gateway send API 列为后续探索，不阻塞当前 rewrite 闭环。
```

## 执行记录

### 2026-05-26 最小 registry 探针

命令摘要：

```text
在远程 hermes 容器内使用 <HERMES_APP_DIR>/.venv/bin/python 执行探针脚本。
脚本先调用 tools.mcp_tool.discover_mcp_tools()，再通过 model_tools.handle_function_call 调用 mcp_tastemate_rank_candidates。
```

结果摘要：

```text
discover_mcp_tools() 返回 mcp_tastemate_rank_candidates、mcp_tastemate_record_feedback、mcp_tastemate_get_profile。
handle_function_call("mcp_tastemate_rank_candidates", args) 返回 structuredContent.action=ranked。
```

判定：

```text
PASS：Hermes 工具调度层可以主动调用 TasteMate MCP 工具。
FOLLOW_UP：独立进程未显式 discover_mcp_tools() 时，registry 返回 Unknown tool；正式插件必须运行在已完成 MCP discovery 的 agent/gateway 进程内，或在探针入口显式确认 MCP 工具已注册。
```
