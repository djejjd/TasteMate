# Iteration 002 Closeout：真实候选排序

## 一、变更摘要

```text
本轮完成真实 candidates 排序闭环，把 iteration-001 中 fixed_probe_candidates 的主路径替换为 Hermes 主动整理真实 candidates 后调用 TasteMate 排序。
TasteMate 侧新增 candidates 最小协议校验，并统一 rank_candidates 的四类输出：passthrough、invalid_candidates、needs_more_candidates、ranked。
tastemate-route 插件保留为 iteration-001 回归资产，不再作为 iteration-002 真实候选主路径。
```

## 二、验证摘要

```text
本地 rank_candidates 测试：.venv/bin/python -m pytest tests/test_rank_candidates.py -q，14 passed。
本地 server_tools 测试：.venv/bin/python -m pytest tests/test_server_tools.py -q，4 passed。
本地 Hermes 插件回归测试：.venv/bin/python -m pytest tests/test_hermes_route_plugin.py -q，9 passed。
本地全量测试：.venv/bin/python -m pytest -q，32 passed。
远端 Hermes 容器、MCP 注册和 CLI 主路径已复验。
远端 A-001 用户给定真实 candidates 路径通过，实际调用 mcp_tastemate_rank_candidates，structuredContent.action=ranked。
远端 A-002 Hermes 基于已有知识整理真实 candidates 路径通过，实际调用 mcp_tastemate_get_profile -> mcp_tastemate_rank_candidates，structuredContent.action=ranked。
远端 tastemate-route 默认入口已下线，真实 candidates 验收期间无新增 fixed_probe_candidates 主路径记录。
```

## 三、审核摘要

```text
最终审核结论：PASS。
BLOCK：无。
FOLLOW_UP：如需更强业务侧证据，可再补真实平台入口烟测；feedback/evidence 远端链路仍可单独补实验并核对 profile.json。
```

## 四、已知风险

```text
风险：Hermes 调用 mcp_tastemate_rank_candidates 时的 candidates 质量仍取决于 Hermes 侧提示和整理质量。
影响：真实候选路径已建立，但排序效果仍可能受 Hermes 候选整理质量波动影响。
应对：当前验收只要求真实 candidates 调用与结构化排序闭环成立；后续如要提升质量，应进入独立迭代优化候选整理提示或候选来源。

风险：feedback/evidence 远端链路未作为 iteration-002 阻塞验收项完成复验。
影响：当前不能把远端 feedback 写入效果表述为已验收事实。
应对：deployment / usage 文档中仅保留工具层口径与实验建议；若要确认远端反馈链路，应单独补实验并核对 profile.json。

风险：tastemate-route 插件 low_confidence 分支在当前 Ranker 结果集合中已不再产出，形成保留型 dead code。
影响：不影响 iteration-002 主路径，但后续阅读成本略增。
应对：后续如清理该分支，需单独验证不影响 iteration-001 回归资产。
```

## 五、后续事项

```text
1. 如需更强业务侧证据，补一次真实平台入口烟测并沉淀截图或会话摘录。
2. 单独设计并验证 feedback/evidence 远端链路，确认 profile.json 变化与排序反馈闭环。
3. 进入下一迭代前，先做 iteration-003 intake，明确是否优先做反馈画像增强。
4. 后续按需要清理 tastemate-route 中仅用于旧口径兼容的 dead code。
```

## 六、文档同步

```text
已同步：
- docs/iterations/iteration-002/status.md
- docs/iterations/iteration-002/verification.md
- docs/iterations/iteration-002/review.md
- docs/iterations/iteration-002/closeout.md
- README.md

未同步：无。
原因：不适用。
```

## 七、发布或提交建议

```text
是否需要 commit / tag / release：建议先提交当前 iteration-002 分支收口文档，再由用户决定是否合并或发布。
建议：提交前复核 iteration-002 未跟踪文档是否全部纳入本轮交付范围，并确认 README 对外口径已切换到 iteration-002。
```
