# Iteration 000 Discovery：TasteMate 与 Hermes 集成事实确认

## 一、调研问题

本轮调研确认 TasteMate 迭代一设计所依赖的关键事实：

```text
Hermes 是否支持外部 MCP server。
Hermes 如何注册 MCP 工具。
Hermes 工具调用后是否会进入下一轮模型循环。
Hermes 是否存在后续可用的 hook 扩展点。
哪些能力只是模型行为假设，而不是硬编码保证。
```

## 二、调研范围

源码路径：

```text
/Users/lanser/code/hermes/hermes-agent/tools/mcp_tool.py
/Users/lanser/code/hermes/hermes-agent/agent/conversation_loop.py
/Users/lanser/code/hermes/hermes-agent/agent/tool_executor.py
```

文档路径：

```text
/Users/lanser/code/hermes/hermes-agent/website/docs/user-guide/features/mcp.md
/Users/lanser/code/hermes/hermes-agent/website/docs/user-guide/features/hooks.md
```

项目内设计参考：

```text
docs/design.md
docs/development.md
docs/iteration-plan.md
tasteMateHermesPersonalAssistant.md
```

## 三、Confirmed

### 1. Hermes 支持外部 MCP server

Hermes 的 MCP 客户端说明中明确写到：它可以通过 stdio、HTTP/StreamableHTTP 或 SSE 连接外部 MCP server，并将工具注册进 Hermes 工具 registry。

证据：

```text
/Users/lanser/code/hermes/hermes-agent/tools/mcp_tool.py:5
/Users/lanser/code/hermes/hermes-agent/tools/mcp_tool.py:6
/Users/lanser/code/hermes/hermes-agent/tools/mcp_tool.py:7
```

Hermes MCP 配置从 `~/.hermes/config.yaml` 的 `mcp_servers` 读取。

证据：

```text
/Users/lanser/code/hermes/hermes-agent/tools/mcp_tool.py:9
/Users/lanser/code/hermes/hermes-agent/website/docs/user-guide/features/mcp.md:94
```

### 2. MCP 工具注册名有稳定前缀

Hermes 会把 MCP 工具名转换为：

```text
mcp_<server_name>_<tool_name>
```

证据：

```text
/Users/lanser/code/hermes/hermes-agent/tools/mcp_tool.py:2831
/Users/lanser/code/hermes/hermes-agent/tools/mcp_tool.py:2832
/Users/lanser/code/hermes/hermes-agent/tools/mcp_tool.py:2833
```

这支持 TasteMate 工具以类似 `mcp_tastemate_rank_candidates` 的形式被 Hermes 识别。

### 3. Hermes 会发现并注册 MCP 工具

`discover_mcp_tools()` 会加载配置、连接 MCP server 并注册工具。

证据：

```text
/Users/lanser/code/hermes/hermes-agent/tools/mcp_tool.py:3284
/Users/lanser/code/hermes/hermes-agent/tools/mcp_tool.py:3285
/Users/lanser/code/hermes/hermes-agent/tools/mcp_tool.py:3300
/Users/lanser/code/hermes/hermes-agent/tools/mcp_tool.py:3312
```

### 4. Hermes 是多轮工具调用循环

Hermes conversation loop 会在迭代预算内持续执行模型调用和工具调用。

证据：

```text
/Users/lanser/code/hermes/hermes-agent/agent/conversation_loop.py:644
/Users/lanser/code/hermes/hermes-agent/agent/conversation_loop.py:656
```

工具执行完成后，Hermes 会继续进入下一轮模型响应。

证据：

```text
/Users/lanser/code/hermes/hermes-agent/agent/conversation_loop.py:3427
/Users/lanser/code/hermes/hermes-agent/agent/conversation_loop.py:3505
/Users/lanser/code/hermes/hermes-agent/agent/conversation_loop.py:3506
```

### 5. 工具结果会写回消息上下文

工具结果会 append 到 `messages`，并在下一轮模型调用中可见。

证据：

```text
/Users/lanser/code/hermes/hermes-agent/agent/tool_executor.py:860
/Users/lanser/code/hermes/hermes-agent/agent/tool_executor.py:861
/Users/lanser/code/hermes/hermes-agent/agent/tool_executor.py:864
/Users/lanser/code/hermes/hermes-agent/agent/tool_executor.py:865
/Users/lanser/code/hermes/hermes-agent/agent/tool_executor.py:866
```

这支持 TasteMate 返回 `needs_more_candidates` 后，Hermes 下一轮理论上可以继续搜索。

### 6. Hermes 有后续可用的 pre_llm_call hook

Hermes 支持 `pre_llm_call`，该 hook 可注入 context 到用户消息。

证据：

```text
/Users/lanser/code/hermes/hermes-agent/agent/conversation_loop.py:535
/Users/lanser/code/hermes/hermes-agent/agent/conversation_loop.py:536
/Users/lanser/code/hermes/hermes-agent/agent/conversation_loop.py:537
/Users/lanser/code/hermes/hermes-agent/agent/conversation_loop.py:538
/Users/lanser/code/hermes/hermes-agent/website/docs/user-guide/features/hooks.md:378
```

这支持迭代二的“搜索前轻量偏好注入”作为可行增强方向。

## 四、Assumption

```text
1. Hermes 在用户使用 @taste 时，会稳定按工具说明调用 mcp_tastemate_rank_candidates。
2. Hermes 看到 needs_more_candidates 后，会根据 suggested_search_hints 继续搜索。
3. LLM 能以足够稳定的方式对 query_relevance、preference_fit、feedback_score 做结构化评分。
4. 用户会通过明确选择、追问、否定或评价提供可学习反馈。
```

这些假设不阻塞进入设计，但必须在迭代一 Build / Verify 阶段验证。

## 五、Unknown

```text
1. 不同模型对 @taste 触发词和工具调用说明的遵循稳定性。
2. Hermes 在真实使用中传给 rank_candidates 的候选结构是否稳定。
3. DeepSeek-V4-Flash 或其他低成本模型在候选评分上的一致性。
4. 用户反馈是否足够频繁，能在短期内形成有意义的偏好画像。
```

这些未知项不阻塞当前 Design，因为迭代一目标是验证闭环，而不是保证长期推荐质量。

## 六、证据来源

本轮使用的证据来源：

```text
Hermes MCP 客户端源码
Hermes conversation loop 源码
Hermes tool executor 源码
Hermes MCP 用户文档
Hermes hooks 用户文档
TasteMate 当前项目级设计文档
```

未使用未验证的聊天结论作为 Confirmed。

## 七、对设计的影响

Confirmed 结论支持：

```text
TasteMate 迭代一可以作为外部 MCP server 接入 Hermes。
迭代一可以不修改 Hermes 源码。
rank_candidates 可以作为后置候选重排工具。
needs_more_candidates 可以作为工具结果反馈给 Hermes。
pre_llm_call 可作为迭代二搜索前偏好注入方向。
```

Assumption 和 Unknown 带来的设计约束：

```text
迭代一必须使用 @taste 显式触发，降低误触发和成本。
迭代一不能承诺 Hermes 会 100% 强制调用 TasteMate。
迭代一必须把工具调用稳定性列为验收重点。
评分结果必须带解释，便于人工判断是否合理。
偏好学习必须先写 evidence，避免一次反馈直接污染 stable_preferences。
```

