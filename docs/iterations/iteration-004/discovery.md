# Iteration 004 Discovery：统一偏好信号摄取

## 一、调研问题

```text
1. 当前 record_feedback 是否已经是正式兼容入口，必须保留哪些契约。
2. 推荐后自然语言反馈为什么没有在远端真实路径写入 profile。
3. 最小穿刺实验是否证明 Hermes 插件可以编排推荐后反馈。
4. 最小穿刺实验是否证明普通兴趣表达可以写入 current_focus。
5. 统一 record_preference_signal 的设计边界应放在哪里。
6. 远端端到端验收需要验证哪些证据，才能避免“本地通过、真实路径不可用”的问题。
```

## 二、调研范围

```text
源码路径：
- tastemate/server.py
- tastemate/tools/record_feedback.py
- tastemate/tools/record_interest.py
- tastemate/core/feedback.py
- integrations/hermes/plugins/tastemate-route/__init__.py
- tests/test_record_feedback.py
- tests/test_server_tools.py
- tests/test_hermes_route_plugin.py

项目文档：
- docs/design.md
- docs/development.md
- docs/iterations/iteration-003/status.md
- docs/iterations/iteration-003/verification.md
- docs/process/documentation.md
- docs/process/acceptance.md

远端运行证据：
- 2026-06-10 远端 Hermes 推荐 / 反馈 / 再推荐 session 观察
- /opt/data/logs/tastemate-route.jsonl
- /opt/data/tastemate/profile.json

穿刺实验代码：
- 工作区中未提交的 tastemate-route 反馈编排改动
- 工作区中未提交的 record_interest_tool 改动
```

## 三、Confirmed

```text
C-001 record_feedback 已是 TasteMate 的正式工具入口。
证据：tastemate/server.py 暴露 record_feedback；tests/test_record_feedback.py 和 tests/test_server_tools.py 已覆盖其基本写入与兼容输出。

C-002 record_feedback 的输入依赖 query、user_feedback、selected_candidate_ids、rejected_candidate_ids、candidates_snapshot。
证据：tastemate/tools/record_feedback.py。

C-003 iteration-003 已完成本地 feedback 画像沉淀和排序消费，本轮不需要重做排序核心。
证据：docs/iterations/iteration-003/status.md 记录 pytest -q 58 passed，并说明 Build / Verify / Multi-Agent Review 已完成。

C-004 远端旧真实路径中，推荐后自然语言反馈没有触发 mcp_tastemate_record_feedback，profile.json 在反馈前后没有变化。
证据：docs/iterations/iteration-004 原 discovery 中记录的 2026-06-10 远端 session、日志和 profile 对比。

C-005 问题不是 TasteMate record_feedback 本地写入失败，而是 Hermes 集成层没有在推荐后反馈轮调用该工具。
证据：record_feedback 本地测试通过；远端反馈 session 无 record_feedback 工具调用。

C-006 推荐后反馈编排穿刺已在本地代码中验证可行。
证据：工作区 tests/test_hermes_route_plugin.py 已覆盖推荐后保存上下文、显式反馈触发 mcp_tastemate_record_feedback、无上下文/未命中候选/调度异常 fail-open；当前本地运行 pytest tests/test_hermes_route_plugin.py -q 为 14 passed。

C-007 普通兴趣记录穿刺已在本地代码中验证可行。
证据：工作区 tastemate/tools/record_interest.py 可从“本地优先 / 开源 / SaaS / 企业”等显式文本中抽取白名单 feature，写入 evidence_log 和 current_focus；tests/test_server_tools.py 中 record_interest_tool 样例通过。

C-008 record_interest 仍是穿刺代码，不是已批准的正式工具。
证据：该文件为工作区未跟踪文件；现有 iteration-004 正式文档尚未批准独立 record_interest 接口。

C-009 统一接口的外部兼容要求是保留 record_feedback。
证据：现有测试、文档和 Hermes 编排历史都引用 record_feedback；直接废弃会破坏兼容。
```

## 四、Assumption

```text
A-001 新增 record_preference_signal，并让 record_feedback 转调统一逻辑，可以同时降低后续 record_interest 独立演进成本和当前兼容风险。

A-002 首版 record_preference_signal 只支持 candidate_feedback 与 interest，足以覆盖已穿刺的两类真实需求。

A-003 signal_type 采用开放扩展设计，但运行时只接受当前白名单类型；未知类型 fail-soft，不写 profile。

A-004 interest 首版只写 evidence_log 与 current_focus，不直接升级 stable_preferences，可以避免普通兴趣表达一次性污染长期画像。

A-005 Hermes tastemate-route 插件可以继续通过 pre_gateway_dispatch 保存最近一次推荐上下文，并在后续显式反馈轮调用统一工具。
```

## 五、Unknown

```text
U-001 远端 Hermes 当前 hook 参数和本地 FakeContext 的 dispatch_tool 行为是否完全一致。

U-002 远端更新插件后，pre_gateway_dispatch 是否能在反馈轮稳定读取上一次推荐上下文文件。

U-003 真实用户消息中候选 title/id 匹配覆盖率是否足够，尤其是中文别名、简称和中英混写。

U-004 普通兴趣表达由 Hermes 直接调用 record_preference_signal，还是由 tastemate-route 插件自动路由，哪种线上稳定性更高。

U-005 未来新增 signal_type 时，是否需要 schema 版本字段和迁移策略。
```

## 六、证据来源

```text
E-001 tastemate/server.py：当前正式 MCP server 暴露 rank_candidates / record_feedback / get_profile；工作区穿刺改动临时加入了 record_interest。
E-002 tastemate/tools/record_feedback.py：record_feedback_tool 的正式输入与输出兼容逻辑。
E-003 tastemate/tools/record_interest.py：普通兴趣记录穿刺实现，但文件未提交，不能视为正式接口。
E-004 integrations/hermes/plugins/tastemate-route/__init__.py：工作区穿刺改动证明推荐上下文保存和反馈调度可本地测试。
E-005 tests/test_hermes_route_plugin.py：本地穿刺测试覆盖 feedback -> record_feedback 编排。
E-006 tests/test_server_tools.py：本地穿刺测试覆盖 interest -> current_focus 写入。
E-007 docs/iterations/iteration-003/status.md：iteration-003 本地反馈画像增强已完成。
E-008 docs/process/acceptance.md：验收标准必须可判断、可验证、有失败条件。
E-009 docs/process/documentation.md：设计文档必须区分 Confirmed、Assumption、Unknown。
```

## 七、对设计的影响

```text
1. 本轮设计不应只补 tastemate-route 到 record_feedback 的胶水层，否则后续普通兴趣记录会重复改核心摄取逻辑。
2. 本轮也不应把 record_interest 作为第二个正式工具发布，否则接口会过早分叉。
3. 正式设计应以 record_preference_signal 为统一入口，当前只实现 candidate_feedback 与 interest 两个 handler。
4. record_feedback 必须保留，并作为 candidate_feedback 的兼容 wrapper。
5. 未知 signal_type 必须结构化拒绝，不写 profile。
6. 普通 interest 与候选 feedback 必须共享 evidence_log 追溯机制，但 profile 升级语义不同。
7. 验收必须包含远端真实端到端路径；本地 pytest 只能证明基础逻辑，不足以 Closeout。
```
