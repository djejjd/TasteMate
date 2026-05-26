# Iteration 001 当前进展

## 适用范围

```text
当前状态索引 / 迭代中间进展 / 后续实验入口
```

## 一句话结论

```text
TasteMate 本体、远程部署和 Hermes MCP 接入已完成；软提示路线已被实验否定，Hermes pre_gateway_dispatch rewrite 编排已从临时 probe 固化为 tastemate-route 插件，并完成远程 hook 级验证、Weixin 形态模拟和 CLI 真实入口端到端验收。
```

## 已完成

- 本地 `tastemate` MCP server 已实现并通过测试。
- 远程 Hermes 容器已接入 `tastemate` MCP server。
- Hermes 能识别并列出 `rank_candidates`、`record_feedback`、`get_profile`。
- 远程依赖安装、启动、重启和 MCP 注册都已验证。
- `@taste` 事实类问题已修正为 passthrough，不再误判为推荐。
- Hermes registry 主动调用 `mcp_tastemate_rank_candidates` 已穿刺通过。
- `pre_gateway_dispatch` 检测 `@taste` 并 rewrite 回 Hermes 自有 agent 回复通道已穿刺通过。
- 以 `Platform.WEIXIN` 构造的伪消息已通过 `GatewayRunner._handle_message` 并触发 rewrite。
- `tastemate-route` 固化插件已完成本地测试和远程 hook 级验证。
- CLI 真实入口普通消息、`@taste` 推荐消息、`@taste` 事实消息和明确反馈写入均已验收。
- 远程 Hermes 当前启用插件为 `tastemate-route`，旧 `tastemate-route-probe` 已退出当前启用配置。

## 已做的穿刺实验

1. **Prompt 强制调用**
   - 结果：失败。
   - 现象：模型输出像是 TasteMate 的排序结果，但日志里没有真实工具调用。

2. **临时 `AGENTS.md` 强规则**
   - 结果：失败。
   - 现象：仍然没有真实的 `mcp_tastemate_rank_candidates` 调用记录。

3. **临时 `pre_llm_call` 插件注入**
   - 结果：失败。
   - 现象：Hermes 仍然返回看似合理的排序文本，但日志没有真实工具调用，`profile.json` 也没有新增反馈证据。

4. **Hermes registry 主动 dispatch**
   - 结果：通过。
   - 现象：显式执行 `discover_mcp_tools()` 后，`handle_function_call("mcp_tastemate_rank_candidates", args)` 返回 `structuredContent.action=ranked`。

5. **`pre_gateway_dispatch` rewrite 编排**
   - 结果：通过。
   - 现象：普通消息返回 `action=allow`；`@taste` 推荐类消息真实调用 TasteMate 后返回 `action=rewrite`，rewrite 文本包含真实排序结果。

## 当前判断

- Hermes 能看到 TasteMate。
- Hermes 工具调度层能主动调用 TasteMate MCP。
- 仅靠软提示，不能把 `@taste` 变成稳定的真实工具调用。
- `pre_gateway_dispatch` rewrite 是当前不改 Hermes 源码前提下的可行验收补充路径，已完成 hook 级验证。
- Weixin 形态事件模拟已证明消息能从 Hermes gateway 路由到 `pre_gateway_dispatch` 并 rewrite。
- gateway send API 直发能力未验证，列为后续探索，不阻塞当前 rewrite 闭环。
- CLI 真实入口验收已覆盖当前迭代核心闭环；微信客户端外部投递链路列为后续渠道验证，不阻塞当前迭代。

## 下一步工作

- 保持不修改 Hermes 源码。
- 提交前确认 `.obsidian/` 和 `tasteMateHermesPersonalAssistant.md` 是否纳入本轮提交。
- 候选来源和 gateway send API 进入后续设计，不混入当前补充验收。
- 微信客户端外部投递链路作为后续渠道验证，不混入当前验收阻塞项。

## 关键信息入口

- [verification.md](./verification.md)
- [review.md](./review.md)
- [plan.md](./plan.md)
- [orchestration-addendum.md](./orchestration-addendum.md)
- [probes/hermes-plugin-dispatch-probe.md](./probes/hermes-plugin-dispatch-probe.md)
- [docs/design.md](../../design.md)
