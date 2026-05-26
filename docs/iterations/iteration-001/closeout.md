# Iteration 001 Closeout：显式 @taste 后置重排闭环

## 一、变更摘要

```text
本轮完成 TasteMate MCP server 的迭代一实现，并完成 Hermes 接入验证。
新增 tastemate-route Hermes 用户插件，用 pre_gateway_dispatch 检测显式 @taste 推荐类消息。
推荐类消息通过 mcp_tastemate_rank_candidates 完成后置重排；普通消息和事实类 @taste 消息不强制进入排序。
明确反馈通过 mcp_tastemate_record_feedback 写入 evidence_log。
```

## 二、验证摘要

```text
本地插件测试：python -m pytest tests/test_hermes_route_plugin.py -q，8 passed。
本地全量测试：python -m pytest -q，25 passed。
Hermes registry 主动 dispatch 穿刺通过。
远程 pre_gateway_dispatch hook 级验证通过。
Weixin 形态 MessageEvent 模拟通过。
CLI 真实入口普通消息通过，未触发 mcp_tastemate_*。
CLI 真实入口 @taste 推荐消息通过，调用 mcp_tastemate_rank_candidates。
CLI 真实入口 @taste 事实消息通过，未调用 mcp_tastemate_rank_candidates。
CLI 真实入口明确反馈通过，调用 mcp_tastemate_record_feedback，返回 evidence_log count=2。
```

## 三、审核摘要

```text
最终审核结论：PASS。
BLOCK：无。
FOLLOW_UP：fixed_probe_candidates 只证明通道；微信客户端外部投递链路仍可补充实测；route_decision 复杂表达覆盖有限。
```

## 四、已知风险

```text
风险：当前 tastemate-route 使用 fixed_probe_candidates。
影响：只能证明 Hermes/TasteMate 编排闭环，不能证明真实候选来源或推荐质量。
应对：候选来源设计进入后续迭代，explicit_candidates 和 observed_tool_candidates 不混入当前验收。

风险：微信客户端外部投递链路未作为最终渠道验收。
影响：不能证明微信客户端到 Hermes 的传输层稳定性。
应对：后续按渠道验证单独验收；当前已完成 Weixin 形态 MessageEvent 模拟和 CLI 真实入口验收。

风险：route_decision 使用固定 marker。
影响：复杂自然语言推荐意图覆盖有限。
应对：后续 gate 规则或意图识别优化，不阻塞迭代一显式 @taste 验收。
```

## 五、后续事项

```text
1. 设计候选来源：explicit_candidates 和 observed_tool_candidates。
2. 评估 gateway send API 直发路线。
3. 补充微信客户端外部投递链路渠道验证。
4. 优化 @taste 推荐意图 gate。
```

## 六、文档同步

```text
已同步：
- docs/iterations/iteration-001/status.md
- docs/iterations/iteration-001/verification.md
- docs/iterations/iteration-001/review.md
- docs/iterations/iteration-001/closeout.md

未同步：无。
原因：不适用。
```

## 七、发布或提交建议

```text
是否需要 commit / tag / release：建议先提交当前迭代分支，再由用户决定是否合并。
建议：提交前确认未跟踪文件中 .obsidian/、tasteMateHermesPersonalAssistant.md 是否属于本轮提交范围。
```
