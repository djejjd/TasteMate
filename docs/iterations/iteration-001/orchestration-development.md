# Iteration 001 Development Spec Addendum：Hermes @taste rewrite 编排

## 适用阶段

```text
Development Spec Addendum
```

本文件是 `docs/iterations/iteration-001/orchestration-addendum.md` 的开发规格补充，用于约束后续 `orchestration-plan.md` 和实现。

本文件不替代 `docs/iterations/iteration-001/development.md`。TasteMate MCP server、ranker、feedback、profile store 的开发规格仍以原 Development Spec 为准。

## 一、开发原则

本补充只解决一个问题：

```text
把显式 @taste 推荐类消息稳定转成真实 mcp_tastemate_rank_candidates 调用，并通过 rewrite 交回 Hermes 自有 agent 回复通道。
```

实现必须遵循：

```text
不修改 Hermes 源码。
不依赖 LLM 自主决定是否调用 TasteMate。
不让普通消息触发 TasteMate。
插件异常时 fail-open，不能阻断 Hermes 普通流程。
所有正向结论必须有日志或验证输出支撑。
```

## 二、技术形态

采用 Hermes 用户插件。

推荐插件名：

```text
tastemate-route
```

远程部署目录：

```text
<HERMES_DATA_DIR>/plugins/tastemate-route/
```

本地文档中的临时 probe 名称 `tastemate-route-probe` 只作为实验记录，不作为正式插件名。

Hermes 配置启用：

```yaml
plugins:
  enabled:
    - tastemate-route
```

插件注册：

```text
register(ctx)
  -> ctx.register_hook("pre_gateway_dispatch", on_pre_gateway_dispatch)
```

核心调用：

```text
ctx.dispatch_tool("mcp_tastemate_rank_candidates", args)
```

返回方式：

```text
未命中 @taste gate：return {"action": "allow"}
命中且调用成功：return {"action": "rewrite", "text": rewrite_text}
命中但调用失败：return {"action": "allow"}
```

## 三、目录结构

远程用户插件结构：

```text
<HERMES_DATA_DIR>/plugins/tastemate-route/
  plugin.yaml
  __init__.py
```

项目内文档结构：

```text
docs/iterations/iteration-001/
  orchestration-addendum.md
  orchestration-development.md
  orchestration-plan.md
  probes/
    hermes-plugin-dispatch-probe.md
```

如果后续需要把插件代码纳入 TasteMate 仓库管理，建议新增：

```text
integrations/hermes/plugins/tastemate-route/
  plugin.yaml
  __init__.py
```

该目录是否进入本轮 Build 由 `orchestration-plan.md` 决定。

## 四、核心模块

### plugin.yaml

职责：

```text
声明 Hermes 插件元信息。
声明提供 pre_gateway_dispatch hook。
```

建议内容：

```yaml
name: tastemate-route
version: 0.1.0
description: "Route explicit @taste recommendation requests to TasteMate MCP via gateway rewrite."
author: "TasteMate"
hooks:
  - pre_gateway_dispatch
```

### register(ctx)

职责：

```text
注册 pre_gateway_dispatch hook。
闭包持有 ctx，用于后续 dispatch_tool。
不在 register 阶段主动调用 TasteMate。
```

禁止：

```text
禁止在 register 阶段执行 discover_mcp_tools。
禁止在 register 阶段读取或写入 profile。
禁止在 register 阶段访问用户消息。
```

### on_pre_gateway_dispatch

职责：

```text
读取 event.text。
执行 @taste gate。
未命中时 allow。
命中时调用 TasteMate dispatch wrapper。
根据 TasteMate 结果生成 rewrite text。
写入 probe/operation 日志。
```

输入来自 Hermes：

```text
event：Hermes gateway MessageEvent。
gateway：Hermes GatewayRunner，当前阶段只作为未来 gateway send API 探索入口，不调用。
session_store：当前阶段不使用。
```

输出：

```json
{"action": "allow"}
```

或：

```json
{"action": "rewrite", "text": "TasteMate 已完成真实后置重排..."}
```

### @taste gate

职责：

```text
保守判断当前消息是否应进入 TasteMate 编排。
```

第一版命中条件：

```text
text 包含 @taste。
text 包含至少一个推荐类意图词。
```

推荐类意图词：

```text
推荐
比较
选型
排序
适合
工具
方案
选择
```

非命中示例：

```text
Hermes 的配置在哪？
今天北京天气如何？
```

命中示例：

```text
@taste 推荐几个适合我的本地知识库工具
@taste 比较几个个人可用的 agent 框架
@taste 帮我做一个本地优先方案选型
```

事实类 `@taste` 示例：

```text
@taste Hermes 的 MCP 配置文件在哪？
```

处理口径：

```text
如果 gate 命中但问题实质是事实类，允许进入 rank_candidates，由 TasteMate ranker 返回 passthrough。
后续可在 gate 层增加事实类排除，但当前补充不要求。
```

### TasteMate dispatch wrapper

职责：

```text
构造 rank_candidates 输入。
调用 ctx.dispatch_tool。
解析 Hermes MCP wrapper 返回。
返回标准化结果给 formatter。
```

输入结构：

```json
{
  "query": "@taste 推荐几个适合我的本地知识库工具",
  "candidates": [],
  "taste_mode": "force"
}
```

当前穿刺允许固定候选：

```json
[
  {
    "id": "local",
    "title": "Local-first KB",
    "summary": "Open source local-first self-hosted knowledge base with MCP-friendly integration",
    "metadata": {
      "open_source": true,
      "local_first": true,
      "supports_mcp": true
    }
  },
  {
    "id": "cloud",
    "title": "Cloud KB",
    "summary": "Cloud hosted managed knowledge base with subscription pricing",
    "metadata": {
      "open_source": false,
      "local_first": false
    }
  },
  {
    "id": "assistant",
    "title": "MCP Assistant",
    "summary": "Personal assistant framework with plugin support and low maintenance setup",
    "metadata": {
      "supports_mcp": true
    }
  }
]
```

正式固化时必须显式标注候选来源：

```text
fixed_probe_candidates：仅用于穿刺和端到端通道验证。
explicit_candidates：后续由用户或 Hermes 明确传入候选。
observed_tool_candidates：后续从 Hermes 工具结果中抽取。
```

当前补充只实现 `fixed_probe_candidates`，用于固化已通过的 `@taste -> dispatch -> rewrite` 编排通道验证。

`explicit_candidates` 不进入本轮实现，因为还需要单独设计用户或 Hermes 如何明确传入候选、候选格式如何约束、候选不足如何交互。

`observed_tool_candidates` 不进入本轮实现，因为还需要独立穿刺验证 `post_tool_call` / `transform_tool_result` 是否能稳定观察搜索类工具结果、归一候选结构、判断候选充足时机。

`explicit_candidates` 和 `observed_tool_candidates` 都作为后续候选来源优化方向，不作为 Iteration 001 A-002 验收条件。

### Hermes MCP wrapper 返回解析

`ctx.dispatch_tool` 返回字符串，通常是 JSON 字符串。

可能形态一：

```json
{
  "structuredContent": {
    "ranking_needed": true,
    "mode": "recommendation",
    "action": "ranked",
    "ranked_candidates": []
  },
  "result": "{...}"
}
```

可能形态二：

```json
{
  "result": "{...}"
}
```

可能形态三：

```json
{
  "error": "Unknown tool: mcp_tastemate_rank_candidates"
}
```

解析顺序：

```text
1. json.loads(raw)。
2. 优先读取 parsed["structuredContent"]。
3. 如果 structuredContent 缺失，尝试 json.loads(parsed["result"])。
4. 如果仍无法得到 dict，视为 dispatch_failed。
```

标准化结果：

```json
{
  "ok": true,
  "action": "ranked",
  "structured": {},
  "raw_preview": "..."
}
```

失败结果：

```json
{
  "ok": false,
  "error_type": "unknown_tool",
  "message": "Unknown tool: mcp_tastemate_rank_candidates",
  "raw_preview": "..."
}
```

### rewrite formatter

职责：

```text
把真实 TasteMate structuredContent 转成 Hermes agent 可理解的用户消息。
保留原始请求。
明确禁止 Hermes 再次调用 TasteMate。
要求 Hermes 基于排序结果回复用户。
```

ranked 模板：

```text
TasteMate 已完成真实后置重排。请基于以下排序结果回复用户，不要再次调用 TasteMate。

原始请求：
{original_text}

排序结果：
1. {title} final_score={final_score} reasons={reason1；reason2}
2. ...

请输出简洁推荐结论，并保留 TasteMate 的主要排序理由。
```

needs_more_candidates 模板：

```text
TasteMate 已完成真实判断，当前候选不足。请基于以下 suggested_search_hints 继续说明还需要补充哪些候选，不要伪装成已完成排序。

原始请求：
{original_text}

原因：
{reason}

建议补充候选方向：
- {hint}
```

passthrough 模板：

```text
TasteMate 判断本轮不适合个性化排序。请按普通 Hermes 流程回答用户。

原始请求：
{original_text}

TasteMate reason：
{reason}
```

low_confidence 模板：

```text
TasteMate 判断当前候选信息不足，无法可靠排序。请向用户说明需要更明确的候选或约束，不要给出伪排序。

原始请求：
{original_text}

TasteMate reason：
{reason}
```

格式限制：

```text
rewrite text 必须包含 “TasteMate 已完成真实...” 或 “TasteMate 判断...” 作为来源标记。
rewrite text 不得声称来自 Hermes 搜索结果，除非候选来源确实是 Hermes 搜索结果。
rewrite text 不得隐藏 dispatch 失败。
```

### operation log

日志路径：

```text
<HERMES_DATA_DIR>/logs/tastemate-route.jsonl
```

每条记录一行 JSON。

字段：

```json
{
  "ts": "2026-05-27T00:00:00Z",
  "hook": "pre_gateway_dispatch",
  "matched": true,
  "action": "rewrite",
  "query_hash": "sha256-prefix",
  "query_preview": "@taste 推荐几个适合我的本地知识库工具",
  "candidate_source": "fixed_probe_candidates",
  "candidate_count": 3,
  "dispatch_ok": true,
  "dispatch_action": "ranked",
  "error_type": null
}
```

隐私与安全：

```text
query_preview 最多 200 字符。
raw tool result 最多记录 2000 字符，正式版本默认不记录完整 raw。
不得记录 API key、auth token、完整环境变量。
```

## 五、接口约定

### pre_gateway_dispatch hook

输入：

```python
def on_pre_gateway_dispatch(*, event, gateway=None, session_store=None, **kwargs):
    ...
```

输出：

```json
{"action": "allow"}
```

或：

```json
{"action": "rewrite", "text": "..."}
```

失败时输出：

```json
{"action": "allow"}
```

原因：

```text
插件失败时不能阻断 Hermes 普通回复。
```

### rank_candidates dispatch

调用：

```python
raw = ctx.dispatch_tool("mcp_tastemate_rank_candidates", args)
```

args：

```json
{
  "query": "原始用户消息",
  "candidates": [],
  "taste_mode": "force"
}
```

返回处理：

```text
必须支持 structuredContent。
必须支持 result 中嵌套 JSON 字符串。
必须支持 error。
```

## 六、配置说明

### Hermes plugin 配置

```yaml
plugins:
  enabled:
    - tastemate-route
```

### Hermes MCP 配置

TasteMate MCP server 仍按原 Development Spec 接入：

```yaml
mcp_servers:
  tastemate:
    command: "<HERMES_DATA_DIR>/tastemate/.venv/bin/python"
    args: ["-m", "tastemate.server"]
    env:
      TASTEMATE_PROFILE_PATH: "<HERMES_DATA_DIR>/tastemate/profile.json"
    timeout: 120
```

### 回滚方式

禁用插件：

```yaml
plugins:
  enabled: []
```

或从 enabled 列表移除：

```text
tastemate-route
```

回滚后重启 Hermes gateway。

TasteMate MCP server 可保留，不影响普通 Hermes 流程。

## 七、数据结构

### RouteDecision

```json
{
  "matched": true,
  "reason": "explicit_taste_recommendation",
  "query": "@taste 推荐几个适合我的本地知识库工具"
}
```

### DispatchResult

```json
{
  "ok": true,
  "action": "ranked",
  "structured": {
    "ranking_needed": true,
    "mode": "recommendation",
    "action": "ranked",
    "ranked_candidates": []
  },
  "error_type": null,
  "message": ""
}
```

### RewriteResult

```json
{
  "action": "rewrite",
  "text": "TasteMate 已完成真实后置重排..."
}
```

## 八、错误处理

### MCP 工具未注册

识别：

```text
Unknown tool: mcp_tastemate_rank_candidates
```

处理：

```text
记录 error_type=unknown_tool。
返回 {"action": "allow"}。
不得向用户声称 TasteMate 已介入。
```

### TasteMate MCP server 不可用

识别：

```text
MCP server 'tastemate' is not connected
MCP call failed
timeout
```

处理：

```text
记录 error_type=mcp_unavailable。
返回 {"action": "allow"}。
Hermes 按普通流程回答。
```

### dispatch 返回 error

处理：

```text
记录 error_type=dispatch_error。
返回 {"action": "allow"}。
```

### structuredContent 解析失败

处理：

```text
尝试解析 result。
仍失败时记录 error_type=parse_failed。
返回 {"action": "allow"}。
```

### ranked 为空

处理：

```text
如果 action=ranked 但 ranked_candidates 为空，改用 low_confidence rewrite 模板。
记录 error_type=empty_ranked_candidates。
```

### 插件内部异常

处理：

```text
捕获异常。
记录 error_type=plugin_exception。
返回 {"action": "allow"}。
```

## 九、测试策略

### 单元级 hook 验证

普通消息：

```text
输入：Hermes 的配置在哪？
期望：返回 {"action": "allow"}。
期望：不调用 ctx.dispatch_tool。
```

@taste 推荐消息：

```text
输入：@taste 推荐几个适合我的本地知识库工具
期望：调用 ctx.dispatch_tool("mcp_tastemate_rank_candidates", args)。
期望：返回 {"action": "rewrite", "text": "..."}。
期望：rewrite text 包含 TasteMate 来源标记和排序结果。
```

dispatch 失败：

```text
ctx.dispatch_tool 返回 {"error": "Unknown tool: mcp_tastemate_rank_candidates"}
期望：返回 {"action": "allow"}。
期望：日志记录 error_type=unknown_tool。
```

passthrough：

```text
TasteMate structuredContent.action=passthrough
期望：rewrite text 明确 TasteMate 判断不适合排序。
```

needs_more_candidates：

```text
TasteMate structuredContent.action=needs_more_candidates
期望：rewrite text 包含 suggested_search_hints，且不伪装成已完成排序。
```

### 远程集成验证

命令级验证：

```text
在远程 hermes 容器内执行 hook 验证脚本。
```

通过条件：

```text
普通消息返回 action=allow。
@taste 推荐消息返回 action=rewrite。
rewrite text 来自真实 mcp_tastemate_rank_candidates structuredContent。
日志写入 <HERMES_DATA_DIR>/logs/tastemate-route.jsonl。
```

### 真实端到端验收

通过用户实际入口发送：

```text
Hermes 的配置在哪？
@taste 推荐几个适合我的本地知识库工具
@taste Hermes 的 MCP 配置文件在哪？
```

通过条件：

```text
普通消息不触发 TasteMate。
@taste 推荐消息触发 TasteMate 并由 Hermes 回复排序结果。
@taste 事实类问题不被伪装成推荐排序。
```

## 十、本地运行方式

本地只验证 TasteMate MCP server：

```bash
python -m pytest -q
python -c "from tastemate.server import mcp; print(mcp.name)"
```

Hermes 插件验证需要在 Hermes 运行环境内执行：

```bash
cd <HERMES_APP_DIR>
HERMES_HOME=<HERMES_DATA_DIR> <HERMES_APP_DIR>/.venv/bin/python < probe_script.py
```

远程部署后重启 Hermes gateway：

```bash
docker restart hermes
```

或按实际部署方式：

```bash
docker compose restart hermes
```

## 十一、禁止事项

```text
禁止修改 Hermes 源码。
禁止把 fixed_probe_candidates 写成真实推荐能力。
禁止在 dispatch 失败时伪造 TasteMate 排序结果。
禁止继续用 prompt / AGENTS / pre_llm_call 强化替代真实工具调用。
禁止实现搜索前偏好注入。
禁止实现 gateway send API 直发，除非另开探索并通过审核。
禁止把 record_feedback 自动编排混入本补充。
禁止在日志中写入密钥、token 或完整敏感上下文。
```

## 十二、Plan 输入要求

`orchestration-plan.md` 必须至少包含：

```text
插件目录和 manifest 创建。
gate 函数实现。
dispatch wrapper 实现。
structuredContent/result/error 解析。
rewrite formatter 实现。
operation log 实现。
错误降级实现。
远程部署步骤。
回滚步骤。
hook 级验证。
真实端到端验收。
```
