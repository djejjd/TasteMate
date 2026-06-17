# Iteration 004 Plan：统一偏好信号摄取

## 一、当前结论

```text
Iteration 004 的 Build 目标是新增统一工具 record_preference_signal。
首版实现 candidate_feedback / interest 两类 handler。
record_feedback 保留兼容 wrapper。
record_interest 不作为正式工具发布，现有穿刺代码必须并入统一接口或移除。

本轮完成标准不是本地测试通过，而是本地测试 + 远端真实端到端验收均通过。
```

## 二、文件影响范围

预计修改：

```text
tastemate/server.py
tastemate/tools/record_feedback.py
integrations/hermes/plugins/tastemate-route/__init__.py
tests/test_record_feedback.py
tests/test_get_profile.py
tests/test_server_tools.py
tests/test_hermes_route_plugin.py
docs/iterations/iteration-004/verification.md
docs/iterations/iteration-004/review.md
docs/iterations/iteration-004/status.md
```

预计新增：

```text
tastemate/tools/record_preference_signal.py
tastemate/core/preference_signal.py
tastemate/schemas/preference_signal.py
tests/test_record_preference_signal.py
```

预计删除或不纳入正式交付：

```text
tastemate/tools/record_interest.py
```

如最终保留文件名，必须改为内部 helper，并不得暴露 mcp_tastemate_record_interest。

## 三、不做事项

```text
1. 不修改 Hermes 主程序源码。
2. 不删除 record_feedback。
3. 不发布 record_interest MCP 工具。
4. 不实现相对指代反馈。
5. 不实现 LLM 偏好理解。
6. 不实现多用户隔离。
7. 不实现搜索前偏好注入。
8. 不把 fixed_probe_candidates 升级为真实候选系统。
```

## 四、实现步骤

### Task 0：设计评审门禁

目标：

```text
在进入 Build 前确认 design.md 和 development.md 被用户认可。
```

验收：

```text
用户明确批准进入 Build。
```

### Task 1：建立统一 PreferenceSignal 结构和 processor

目标：

```text
新增 PreferenceSignal 规范、handler registry 和统一输出结构。
```

TDD：

```text
1. 写失败测试：未知 signal_type 返回 accepted=false，profile 不变。
2. 写失败测试：空 user_signal 返回 accepted=false。
3. 实现最小 schema / processor / result builder。
```

### Task 2：candidate_feedback handler

目标：

```text
让 record_preference_signal 能处理候选绑定反馈，并复用现有 FeedbackProcessor。
```

TDD：

```text
1. 写失败测试：candidate_feedback 有效输入写入 evidence_log。
2. 写失败测试：selected/rejected/candidates_snapshot 缺失时不写 profile。
3. 实现 candidate_feedback handler。
4. 验证 profile_update_details 与 iteration-003 兼容。
```

### Task 3：record_feedback 兼容 wrapper

目标：

```text
保持旧 record_feedback 输入和输出字段不破坏，内部转调统一 processor。
```

TDD：

```text
1. 运行既有 record_feedback / get_profile / server_tools 测试，确认先能暴露兼容缺口。
2. 实现 wrapper。
3. 确认旧字段 feedback_valid / signal_strength / extracted_signals / profile_updates / profile_update_details 仍存在。
```

### Task 4：interest handler

目标：

```text
把普通兴趣记录并入 record_preference_signal，不发布 record_interest。
```

TDD：

```text
1. 写失败测试：interest 写 current_focus 和 evidence_log。
2. 写失败测试：interest 单次不写 stable_preferences。
3. 写失败测试：没有显式兴趣词或白名单 feature 时 accepted=false。
4. 将 record_interest 穿刺逻辑迁入 interest handler 或删除穿刺文件。
```

### Task 5：MCP server 暴露统一工具

目标：

```text
tastemate/server.py 暴露 record_preference_signal。
record_feedback 保留。
record_interest 不暴露。
```

验证：

```text
tests/test_server_tools.py 覆盖 mcp app 可导入，并覆盖工具函数层。
```

### Task 6：Hermes 插件调用统一工具

目标：

```text
tastemate-route 推荐后反馈路由调用 mcp_tastemate_record_preference_signal。
```

TDD：

```text
1. 写失败测试：推荐成功后保存推荐上下文。
2. 写失败测试：显式候选反馈触发 mcp_tastemate_record_preference_signal，signal_type=candidate_feedback。
3. 写失败测试：无上下文 / 未命中 / 歧义 / MCP 失败 fail-open。
4. 实现插件上下文保存、候选索引、反馈路由和日志。
```

### Task 7：本地验证

目标：

```text
确认统一工具、兼容入口、Hermes 插件和全量测试通过。
```

命令：

```bash
pytest tests/test_record_preference_signal.py -q
pytest tests/test_record_feedback.py tests/test_get_profile.py tests/test_server_tools.py -q
pytest tests/test_hermes_route_plugin.py -q
pytest -q
```

### Task 8：远端部署和端到端验收

目标：

```text
在服务器真实 Hermes 环境中证明 candidate_feedback 和 interest 两条路径都成立。
```

步骤：

```text
1. 备份远端当前 TasteMate MCP 服务代码、Hermes tastemate-route 插件和 profile.json。
2. 更新远端 TasteMate MCP 服务代码。
3. 更新远端 tastemate-route 插件。
4. 重启或 reload Hermes / MCP 服务，使新工具和插件生效。
5. 验证 mcp_tastemate_record_preference_signal 已可被 Hermes 发现。
6. 发送 @taste 推荐消息，记录 session id、工具调用和插件日志。
7. 发送推荐后显式反馈，记录 session id、统一工具调用和 profile diff。
8. 再发送 @taste 推荐消息，记录排序或 reasons 对画像变化的体现。
9. 发送普通兴趣表达，记录 session id、统一工具调用和 profile diff。
10. 再发送 @taste 推荐消息，记录 current_focus 被消费的证据。
11. 将命令、session id、日志摘录和 profile diff 写入 verification.md。
```

通过条件：

```text
candidate_feedback：
- 反馈轮真实调用 mcp_tastemate_record_preference_signal。
- signal_type=candidate_feedback。
- profile.json 出现对应 evidence/profile 更新。
- 再推荐体现画像变化。

interest：
- 普通兴趣轮真实调用 mcp_tastemate_record_preference_signal。
- signal_type=interest。
- profile.json current_focus 出现对应 feature。
- stable_preferences 未因单次 interest 直接新增。
- 再推荐体现 current_focus。
```

失败处理：

```text
任一远端阻塞验收失败时，Iteration 004 不得 Closeout。
必须记录失败证据和修复计划。
```

### Task 9：Multi-Agent Review

目标：

```text
按 docs/process/review-loop.md 执行最多两轮审核。
```

审核重点：

```text
Documentation Reviewer：文档是否清楚区分穿刺事实、设计结论和后续能力。
Architecture Reviewer：统一接口是否过度抽象或破坏兼容。
Implementation Reviewer：record_feedback 兼容和 handler 边界是否正确。
Verification Reviewer：远端端到端证据是否足以支撑验收。
```

### Task 10：Closeout

目标：

```text
只有本地验证、远端验收和多 agent review 均通过后，才更新 status.md 并进入 Closeout。
```

## 五、验收映射

```text
A-001 -> Task 2 / Task 7
A-002 -> Task 4 / Task 7
A-003 -> Task 3 / Task 7
A-004 -> Task 1 / Task 7
A-005 -> Task 6 / Task 7
A-006 -> Task 6 / Task 7
A-007 -> Task 8
A-008 -> Task 8
A-009 -> Task 8 / Task 9
```

## 六、提交策略

```text
1. 设计文档通过后再进入 Build。
2. 本地实现和测试通过后提交代码。
3. 远端验收通过后补 verification.md / review.md / status.md。
4. 不把未通过远端验收的实现标记为完成。
```
