# Iteration 004 Development Spec：统一偏好信号摄取

## 适用阶段

```text
Development Spec。
本文件在 Design 通过后作为 Plan 和 Build 的直接约束。
当前只描述建议实现结构和禁止事项，不表示实现已经完成。
```

## 一、开发原则

```text
1. 新增统一工具 record_preference_signal，作为偏好信号摄取主入口。
2. 当前只实现 candidate_feedback 与 interest 两类 handler。
3. signal_type 保留扩展空间，但未知类型必须 accepted=false，不写 profile。
4. record_preference_signal 是新优先入口，面向候选反馈和普通兴趣。
5. record_feedback 保持兼容，内部转为 candidate_feedback。
6. 不发布独立 record_interest 工具。
7. interest 首版只写 evidence_log 与 current_focus，不直接升级 stable_preferences。
8. Hermes 插件只做推荐上下文保存、保守候选匹配和统一工具调度，不做复杂自然语言理解。
9. 远端端到端验证是阻塞验收，不得只用本地 pytest 宣称完成。
```

## 二、技术形态

```text
TasteMate MCP server：
  -> mcp_tastemate_record_preference_signal
  -> unified PreferenceSignal processor
  -> candidate_feedback handler / interest handler
  -> JsonProfileStore 保存 profile.json

兼容路径：
  -> mcp_tastemate_record_feedback
  -> record_feedback wrapper
  -> candidate_feedback handler

Hermes 用户插件：
  -> pre_gateway_dispatch
  -> 推荐阶段保存最近一次 TasteMate 推荐上下文
  -> 反馈阶段调用 mcp_tastemate_record_preference_signal
```

本轮不新增数据库、不新增 LLM 调用、不修改 Hermes 源码。

## 三、目录结构

预计影响范围：

```text
tastemate/
  server.py
  tools/
    record_preference_signal.py
    record_feedback.py
  core/
    preference_signal.py
  schemas/
    preference_signal.py
integrations/
  hermes/
    plugins/
      tastemate-route/
        __init__.py
tests/
  test_record_preference_signal.py
  test_record_feedback.py
  test_server_tools.py
  test_hermes_route_plugin.py
docs/iterations/iteration-004/
  intake.md
  discovery.md
  design.md
  development.md
  plan.md
  verification.md
  review.md
  status.md
```

如实现时发现无需新增某个文件，必须在 Plan 或 verification.md 说明原因。

## 四、核心模块

### tastemate.schemas.preference_signal

职责：

```text
1. 定义 PreferenceSignal 输入规范。
2. 规范化 signal_type、source、user_signal、query、context、metadata。
3. 为 candidate_feedback / interest 提供最小字段校验辅助。
```

不得做：

```text
1. 写 profile。
2. 调用 FeedbackProcessor。
3. 判断 Hermes 上下文。
```

### tastemate.core.preference_signal

职责：

```text
1. 提供 handler registry。
2. 分发 candidate_feedback / interest。
3. 为未知 signal_type 返回结构化拒绝结果。
4. 统一输出 accepted、signal_type、applied_features、profile_updates、profile_update_details、reason。
```

不得做：

```text
1. 绕过 handler 直接写 profile。
2. 对未知类型猜测处理。
```

### tastemate.tools.record_preference_signal

职责：

```text
1. 加载 profile。
2. 调用 core.preference_signal processor。
3. 保存 profile。
4. 返回统一 MCP 输出。
```

### tastemate.tools.record_feedback

职责：

```text
1. 保持旧 record_feedback_tool 输入协议。
2. 将旧参数转换为 signal_type=candidate_feedback。
3. 调用统一 processor。
4. 返回旧兼容字段。
```

不得做：

```text
1. 删除旧字段。
2. 改变旧调用方必须传入的参数。
```

### integrations/hermes/plugins/tastemate-route

职责：

```text
1. @taste 推荐路由继续调用 rank_candidates。
2. rank_candidates 成功后保存最近一次推荐上下文。
3. 推荐后显式反馈命中候选时调用 mcp_tastemate_record_preference_signal。
4. 无上下文、未命中候选、歧义、MCP 失败时 fail-open。
5. 日志必须区分 recommendation_route 与 preference_signal_route。
```

## 五、接口约定

### record_preference_signal

输入：

```json
{
  "signal_type": "candidate_feedback",
  "user_signal": "我更喜欢 Logseq，以后优先。不要 Trilium。",
  "source": "tastemate_recommendation",
  "query": "@taste 推荐几个适合我的知识库工具",
  "candidate_feedback": {
    "selected_candidate_ids": ["logseq"],
    "rejected_candidate_ids": ["trilium"],
    "candidates_snapshot": []
  },
  "interest": {},
  "context": {},
  "metadata": {}
}
```

输出：

```json
{
  "accepted": true,
  "signal_type": "candidate_feedback",
  "signal_id": "abc123",
  "applied_features": ["local_first"],
  "profile_updates": [
    {
      "section": "evidence_log",
      "count": 1
    }
  ],
  "profile_update_details": {
    "stable_preferences": [],
    "negative_preferences": [],
    "current_focus": ["local_first"]
  },
  "reason": "accepted_candidate_feedback"
}
```

### record_feedback 兼容入口

输入保持不变：

```json
{
  "query": "@taste 推荐几个适合我的知识库工具",
  "user_feedback": "我更喜欢 Logseq",
  "selected_candidate_ids": ["logseq"],
  "rejected_candidate_ids": [],
  "candidates_snapshot": []
}
```

输出必须包含：

```json
{
  "feedback_valid": true,
  "signal_strength": 0.7,
  "extracted_signals": [],
  "profile_updates": [],
  "profile_update_details": {
    "stable_preferences": [],
    "negative_preferences": [],
    "current_focus": []
  }
}
```

## 六、配置说明

```text
不新增必需配置项。
继续使用 TASTEMATE_PROFILE_PATH 覆盖 profile 路径。
Hermes 远端部署继续使用现有 mcp_servers.tastemate 配置。
tastemate-route 推荐上下文文件路径可沿用插件内常量，后续如需配置化另开迭代。
```

## 七、数据结构

### PreferenceSignal

```json
{
  "signal_type": "candidate_feedback",
  "user_signal": "原始用户表达",
  "source": "tastemate_recommendation",
  "query": "可选 query",
  "candidate_feedback": {
    "selected_candidate_ids": [],
    "rejected_candidate_ids": [],
    "candidates_snapshot": []
  },
  "interest": {
    "direction": "positive",
    "features": []
  },
  "context": {},
  "metadata": {}
}
```

### handler registry

```text
candidate_feedback -> CandidateFeedbackHandler
interest -> InterestSignalHandler
```

未知 signal_type 不进入 handler。

## 八、错误处理

```text
unsupported_signal_type：
- accepted=false
- reason=unsupported_signal_type
- 不写 profile

invalid_candidate_feedback_payload：
- accepted=false
- 不写 profile

missing_explicit_interest_signal：
- accepted=false
- 不写 profile

dispatch_tool exception：
- Hermes 插件返回 allow
- 不伪装成已记录偏好

parse_failed / missing_structured_content：
- Hermes 插件返回 allow
- 日志记录 error_type
```

## 九、测试策略

```text
A-001 -> tests/test_record_preference_signal.py 覆盖 candidate_feedback 写入。
A-002 -> tests/test_record_preference_signal.py 覆盖 interest 写 current_focus 且不写 stable_preferences。
A-003 -> 既有 tests/test_record_feedback.py / tests/test_get_profile.py / tests/test_server_tools.py 全量兼容。
A-004 -> tests/test_record_preference_signal.py 覆盖 unknown signal_type 不写 profile。
A-005 -> tests/test_hermes_route_plugin.py 覆盖推荐后反馈调用 mcp_tastemate_record_preference_signal。
A-006 -> tests/test_hermes_route_plugin.py 覆盖无上下文、未命中、歧义、MCP 失败。
A-007 -> verification.md 记录远端 candidate_feedback 端到端证据。
A-008 -> verification.md 记录远端 interest 端到端证据。
A-009 -> git diff 与部署记录证明未修改 Hermes 源码。
```

## 十、本地运行方式

```bash
pytest tests/test_record_preference_signal.py -q
pytest tests/test_record_feedback.py tests/test_get_profile.py tests/test_server_tools.py -q
pytest tests/test_hermes_route_plugin.py -q
pytest -q
```

远端验证命令和 session/profile 证据必须写入 verification.md。

## 十一、禁止事项

```text
1. 禁止在本轮删除 record_feedback。
2. 禁止发布独立 record_interest MCP 工具。
3. 禁止未知 signal_type 写 profile。
4. 禁止 interest 单次写入 stable_preferences。
5. 禁止把本地 pytest 通过写成端到端验收完成。
6. 禁止修改 Hermes 主程序源码。
7. 禁止引入 LLM 语义解析作为当前阻塞能力。
8. 禁止顺手改造 fixed_probe_candidates 主路径。
```
