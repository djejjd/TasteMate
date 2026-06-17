# TasteMate 项目暂停总结：Iteration 004 统一偏好信号摄取

## 当前结论

```text
项目暂时终止，代码与文档按阶段性成果备份。
Iteration 004 没有 Closeout。
原因不是 record_preference_signal 工具不可用，而是真实 Telegram 反馈链路暴露了候选上下文不一致的问题。
```

## 已完成进展

```text
1. 新增统一偏好信号入口 record_preference_signal。
2. record_preference_signal 当前支持 candidate_feedback 与 interest。
3. record_interest 不作为正式工具设计，普通兴趣直接进入 record_preference_signal 的 interest 类型。
4. record_feedback 保留为兼容入口，内部走统一偏好信号核心逻辑。
5. tastemate-route 插件新增推荐上下文保存和反馈识别逻辑。
6. MCP server 暴露 record_preference_signal，并保留 record_feedback。
7. 本地测试覆盖统一工具、兼容入口、插件反馈路由和失败 fail-open。
8. 远端服务器已部署过 TasteMate MCP 服务和 tastemate-route 插件更新。
```

## 已验证结果

```text
本地测试：
- pytest -q：通过。

远端 / Hermes CLI：
- interest 主动兴趣记录可以调用 mcp_tastemate_record_preference_signal。
- CLI 中 taste 推荐后的候选反馈已能优先调用 mcp_tastemate_record_preference_signal。
- profile 会写入 evidence / current_focus。
- 再推荐可以消费 profile 中的偏好。

Telegram 外部入站：
- @taste 推荐消息可以命中 tastemate-route。
- 插件可以触发后置重排 rewrite。
```

## 未通过验证

```text
Telegram 外部入站反馈未通过。

用户实际发送：
我更喜欢 Logseq，以后优先。不要 Obsidian。

观测结果：
- gateway 收到 Telegram 入站消息。
- tastemate-route 日志记录 route_reason=feedback_candidate_unmatched。
- 未调用 mcp_tastemate_record_preference_signal。
- Hermes 后续没有调用 TasteMate 工具。
- profile 没有新增 2026-06-17 的反馈 evidence。
```

## 根因

```text
当前插件保存的推荐上下文仍来自 fixed_probe_candidates。
该上下文中的候选是：
- Local-first KB
- Cloud KB
- MCP Assistant

但 Telegram 中用户实际看到并反馈的候选是：
- Logseq
- Obsidian

反馈识别逻辑按候选 id/title 保守匹配。
Logseq / Obsidian 不在当前 candidate_index 中，因此插件正确 fail-open，没有误写 profile。
```

## 当前局限性

```text
1. fixed_probe_candidates 只能证明穿刺链路，不代表真实候选主路径。
2. Telegram 推荐阶段的用户可见候选与插件保存的 candidate context 不一致。
3. 反馈路由依赖候选名匹配，无法记录不在 context 中的候选反馈。
4. 真实渠道反馈闭环不能声明通过。
5. Multi-Agent Review 中已有文档审核 BLOCK：设计/计划对“真实端到端”的承诺高于当时证据。
6. 当前没有完成 Closeout。
```

## 不是问题的部分

```text
1. record_preference_signal 工具本身可用。
2. Hermes CLI 可以选择 record_preference_signal。
3. record_feedback 兼容 wrapper 可以走统一核心逻辑。
4. Telegram 推荐入站可以触发 tastemate-route。
5. 失败时 fail-open 没有误写 profile，这是当前设计预期。
```

## 后续恢复时的优先事项

```text
P0：统一用户可见候选与插件保存候选上下文。
P0：重新定义真实端到端验收口径，必须包含 Telegram 反馈写入 profile 的证据。
P1：移除或隔离 fixed_probe_candidates，不把穿刺资产伪装成真实候选能力。
P1：补充 Telegram 外部入站反馈回归测试和远端验证脚本。
P2：再讨论普通兴趣、候选反馈、未来信号类型的长期协议演进。
```

## 暂停时的建议状态

```text
可以保留当前代码作为备份分支。
不要把 Iteration 004 标记为完成。
不要声称 Telegram 反馈链路已通过。
后续恢复时，应从真实候选上下文设计开始，而不是继续调 record_preference_signal 本身。
```
