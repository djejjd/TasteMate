# Iteration 004 Design：统一偏好信号摄取

## 一、当前结论

```text
Iteration 004 推荐采用统一偏好信号接口 record_preference_signal。
首版只实现 candidate_feedback 与 interest 两类 signal_type，但协议和内部模型保留 future signal_type 扩展空间。

record_feedback 保留为兼容 wrapper，内部转换为 candidate_feedback。
record_interest 不作为正式工具设计，普通兴趣记录直接进入 record_preference_signal 的 interest 类型。

本轮验收必须包含远端真实端到端验证：实际更新服务器插件/服务，发送真实 Hermes 消息，确认工具调用、profile 变化和再推荐效果。
```

## 二、背景与问题

```text
iteration-003 已完成本地 record_feedback 画像沉淀和排序消费。
后续穿刺发现，真实用户路径仍有两个缺口：

1. 推荐后自然语言反馈没有被 Hermes 编排为 TasteMate 工具调用，profile 不会变化。
2. 普通兴趣表达可以被抽取为 current_focus，但如果单独设计 record_interest，会形成第二套偏好摄取接口。

如果本轮只补 record_feedback 的插件胶水，后续开发普通兴趣记录时仍要重构：
- profile 写入语义
- evidence_log 结构
- feature 抽取规则
- MCP 工具接口
- Hermes 编排提示
- 远端验收方式

因此本轮正式设计应统一偏好信号入口，而不是固化两条平行工具路径。
```

## 三、目标

```text
1. 新增 record_preference_signal，作为偏好信号摄取的统一 MCP 工具。
2. 当前实现 candidate_feedback：
   - 来源：推荐后用户对候选的显式选择/排除。
   - 输入：query、user_signal、selected_candidate_ids、rejected_candidate_ids、candidates_snapshot。
   - 写入：沿用 iteration-003 FeedbackProcessor 规则，更新 evidence_log / current_focus / stable_preferences / negative_preferences。
3. 当前实现 interest：
   - 来源：普通自然语言中的显式兴趣或偏好表达。
   - 输入：user_signal、source、可选 context。
   - 写入：evidence_log 和 current_focus；首版不直接升级 stable_preferences。
4. 保留 record_feedback 兼容入口，内部转换为 candidate_feedback。
5. 协议保留扩展字段和 handler 分发机制，未来新增 signal_type 不需要重做 MCP 主入口。
6. 远端真实端到端验收作为阻塞条件。
```

## 四、非目标

```text
1. 不修改 Hermes 源码。
2. 不删除 record_feedback。
3. 不发布独立 record_interest 工具。
4. 不实现开放式偏好理解或 LLM 语义解析。
5. 不支持相对指代反馈作为阻塞能力，例如“第一个”“第二个”“上面那个”。
6. 不实现多用户隔离、账号系统、UI 编辑画像。
7. 不实现搜索前偏好注入。
8. 不把 fixed_probe_candidates 升级为真实候选系统。
9. 不让未知 signal_type 自动写 profile。
```

## 五、数据流

### 1. 推荐后候选反馈

```text
用户发送 @taste 推荐请求
  ↓
Hermes / tastemate-route 调用 mcp_tastemate_rank_candidates
  ↓
记录最近一次 TasteMate 推荐上下文：
- query
- candidates_snapshot
- ranked_candidates
- candidate id/title 索引
  ↓
用户发送显式反馈，例如“我更喜欢 Logseq，不要 Trilium”
  ↓
tastemate-route 判断：
- 存在最近一次推荐上下文
- 命中显式正/负反馈词
- 命中候选 id/title
  ↓
调用 mcp_tastemate_record_preference_signal
signal_type=candidate_feedback
  ↓
record_preference_signal 分发给 candidate_feedback handler
  ↓
handler 转用现有 FeedbackProcessor
  ↓
写入 profile.json
  ↓
Hermes 再推荐时，rank_candidates 读取更新后的 profile
```

### 2. 普通兴趣表达

```text
用户表达普通兴趣，例如“我最近更关注本地优先和开源工具”
  ↓
Hermes 调用 mcp_tastemate_record_preference_signal
signal_type=interest
  ↓
interest handler 做显式词与白名单 feature 抽取
  ↓
写入：
- evidence_log：记录原始兴趣信号
- current_focus：记录短期关注
  ↓
不直接新增 stable_preferences
  ↓
后续 rank_candidates 可消费 current_focus
```

### 3. 兼容 record_feedback

```text
旧调用方调用 mcp_tastemate_record_feedback
  ↓
record_feedback wrapper 保持原输入协议
  ↓
构造 PreferenceSignal：
signal_type=candidate_feedback
source=tastemate_recommendation
  ↓
调用统一 processor
  ↓
返回保持 record_feedback 兼容的输出字段
```

## 六、模块边界

### tastemate.server

职责：

```text
1. 暴露 mcp_tastemate_record_preference_signal。
2. 保留 mcp_tastemate_record_feedback。
3. 不暴露 mcp_tastemate_record_interest 作为正式工具。
4. MCP 层只做参数适配，不直接写 profile。
```

### tastemate.tools.record_preference_signal

职责：

```text
1. 接收统一偏好信号输入。
2. 校验 signal_type 是否有已注册 handler。
3. 加载和保存 profile。
4. 调用对应 handler。
5. 返回统一输出结构。
```

不负责：

```text
1. Hermes 上下文判断。
2. 候选 title/id 匹配。
3. 搜索前偏好注入。
```

### PreferenceSignal handlers

职责：

```text
candidate_feedback handler：
- 校验候选反馈必需字段。
- 调用现有 FeedbackProcessor。
- 保持 iteration-003 profile 更新语义。

interest handler：
- 校验显式兴趣表达。
- 抽取白名单 feature。
- 写 evidence_log 与 current_focus。
- 不直接升级 stable_preferences。
```

### tastemate-route Hermes 插件

职责：

```text
1. 推荐阶段保存最近一次 TasteMate 推荐上下文。
2. 推荐后反馈阶段做保守候选匹配。
3. 调用 mcp_tastemate_record_preference_signal，而不是直接调用 record_feedback。
4. 记录可定位日志。
5. 失败时 fail-open，不阻断 Hermes 主流程。
```

不负责：

```text
1. 生成长期画像。
2. 判断普通 interest 是否应该写 profile，除非后续设计明确由插件路由。
3. 复杂自然语言解析。
```

## 七、接口设计

### 1. record_preference_signal 输入

```json
{
  "signal_type": "candidate_feedback",
  "user_signal": "我更喜欢 Logseq，以后优先。不要 Trilium。",
  "source": "tastemate_recommendation",
  "query": "@taste 推荐几个适合我的知识库工具",
  "candidate_feedback": {
    "selected_candidate_ids": ["logseq"],
    "rejected_candidate_ids": ["trilium"],
    "candidates_snapshot": [
      {
        "id": "logseq",
        "title": "Logseq",
        "summary": "开源、本地优先的知识库工具",
        "metadata": {
          "open_source": true,
          "local_first": true
        }
      }
    ]
  },
  "context": {
    "session_id": "optional",
    "route": "tastemate-route"
  },
  "metadata": {}
}
```

```json
{
  "signal_type": "interest",
  "user_signal": "我最近更关注本地优先和开源工具。",
  "source": "normal_conversation",
  "query": "",
  "interest": {
    "direction": "positive",
    "features": []
  },
  "context": {},
  "metadata": {}
}
```

字段规则：

```text
signal_type：
- 开放扩展字段。
- 当前只接受 candidate_feedback / interest。
- 未知类型返回 accepted=false，不写 profile。

user_signal：
- 用户原始表达。
- 必填。

source：
- 信号来源。
- 当前建议值：tastemate_recommendation、normal_conversation、compat_record_feedback。

query：
- candidate_feedback 必填。
- interest 可为空。

candidate_feedback：
- signal_type=candidate_feedback 时必填。
- 必须包含 selected_candidate_ids / rejected_candidate_ids / candidates_snapshot。

interest：
- signal_type=interest 时可选。
- features 为空时由 handler 从 user_signal 抽取。
- 首版只接受白名单 feature。

context / metadata：
- 保留扩展空间。
- 当前不作为写入 profile 的必要依据。
```

### 2. record_preference_signal 输出

```json
{
  "accepted": true,
  "signal_type": "candidate_feedback",
  "signal_id": "sha256-prefix",
  "applied_features": ["local_first", "open_source"],
  "profile_updates": [
    {
      "section": "evidence_log",
      "count": 2
    },
    {
      "section": "current_focus",
      "features": ["local_first"]
    }
  ],
  "profile_update_details": {
    "stable_preferences": ["local_first"],
    "negative_preferences": [],
    "current_focus": ["open_source"]
  },
  "reason": "accepted_candidate_feedback"
}
```

拒绝输出：

```json
{
  "accepted": false,
  "signal_type": "future_type",
  "signal_id": "",
  "applied_features": [],
  "profile_updates": [],
  "profile_update_details": {
    "stable_preferences": [],
    "negative_preferences": [],
    "current_focus": []
  },
  "reason": "unsupported_signal_type"
}
```

### 3. record_feedback 兼容输出

```text
record_feedback 必须继续返回 iteration-003 兼容字段：
- feedback_valid
- signal_strength
- extracted_signals
- profile_updates
- profile_update_details

内部可以额外包含 accepted / signal_type，但不得移除旧字段。
```

## 八、错误与降级

### unsupported_signal_type

条件：

```text
signal_type 没有已注册 handler。
```

处理：

```text
返回 accepted=false。
不写 profile。
记录 reason=unsupported_signal_type。
```

### candidate_feedback 缺少候选上下文

条件：

```text
缺少 query、candidates_snapshot，或 selected/rejected 均为空。
```

处理：

```text
返回 accepted=false。
不写 profile。
reason=invalid_candidate_feedback_payload。
```

### interest 未命中显式兴趣

条件：

```text
user_signal 为空，或没有显式兴趣/偏好词，或没有命中白名单 feature。
```

处理：

```text
返回 accepted=false。
不写 profile。
reason=missing_explicit_interest_signal。
```

### Hermes 插件匹配失败

条件：

```text
推荐后反馈没有上下文、没有命中候选、或候选匹配歧义。
```

处理：

```text
不调用 record_preference_signal。
按普通 Hermes 流程 allow。
日志记录具体 reason。
```

### 远端工具调用失败

条件：

```text
MCP 工具不存在、返回 parse_error、structuredContent 缺失、dispatch_tool 抛异常。
```

处理：

```text
Hermes 插件 fail-open。
不得回复“已记录偏好”。
日志记录 dispatch_ok=false 和 error_type。
远端验收结论为 BLOCKED，直到工具调用真实可用。
```

## 九、成本与性能

```text
模型调用：
- 本轮不新增 LLM 调用。
- interest 与 candidate_feedback 首版均使用规则和白名单 feature。

存储：
- 继续使用现有 profile.json。
- 不新增数据库。
- 推荐上下文可由 tastemate-route 写入小型 JSON 文件。

运行成本：
- record_preference_signal 每次最多一次 profile load/save。
- Hermes 插件反馈路由只做字符串匹配和一次 MCP 调用。
```

## 十、风险与应对

### R-001 统一接口过度抽象

```text
影响：接口变成万能自然语言偏好入口，导致实现和验收失控。
应对：当前只注册 candidate_feedback / interest 两个 handler；未知类型必须拒绝，不写 profile。
```

### R-002 普通 interest 污染长期偏好

```text
影响：用户一次临时兴趣表达被写入 stable_preferences，后续排序被长期误导。
应对：interest 首版只写 evidence_log 与 current_focus，不直接升级 stable_preferences。
```

### R-003 record_feedback 兼容破坏

```text
影响：已有测试、文档和调用方失效。
应对：record_feedback 保持原输入和旧输出字段，新增统一逻辑只能作为内部实现。
```

### R-004 远端插件本地通过但线上不可用

```text
影响：再次出现“本地开发完成，但真实用户路径没有工具调用”的问题。
应对：远端端到端验收设为阻塞项；没有 session/log/profile 证据时不得 Closeout。
```

### R-005 推荐上下文读取不稳定

```text
影响：反馈轮拿不到上一轮候选快照，无法构造 candidate_feedback。
应对：插件保存最小推荐上下文；无上下文时 fail-open，不写 profile；远端验收必须覆盖推荐后反馈。
```

## 十一、验收标准

### A-001 record_preference_signal 支持 candidate_feedback

```text
描述：统一工具能处理候选绑定反馈，并产生与 record_feedback 兼容的 profile 更新。
验证方式：本地调用 record_preference_signal，传入 query、user_signal、selected/rejected ids 和 candidates_snapshot。
通过条件：accepted=true；profile evidence_log 增加；profile_update_details 可定位更新区域。
失败条件：工具拒绝有效输入，或 profile 没有变化。
适用阶段：本地 Verify。
```

### A-002 record_preference_signal 支持 interest

```text
描述：统一工具能处理普通显式兴趣表达。
验证方式：本地调用 record_preference_signal，输入“我最近更关注本地优先和开源工具”。
通过条件：accepted=true；evidence_log 增加；current_focus 写入 local_first / open_source；stable_preferences 不新增。
失败条件：未写 current_focus，或直接新增 stable_preferences。
适用阶段：本地 Verify。
```

### A-003 record_feedback 兼容入口不破坏

```text
描述：旧 record_feedback 输入协议和旧输出字段保持兼容。
验证方式：运行既有 tests/test_record_feedback.py、tests/test_get_profile.py、tests/test_server_tools.py。
通过条件：既有测试通过；返回字段包含 feedback_valid / signal_strength / extracted_signals / profile_updates / profile_update_details。
失败条件：旧测试失败，或旧字段缺失。
适用阶段：本地 Verify。
```

### A-004 未知 signal_type 不写 profile

```text
描述：协议保留扩展空间，但当前未实现类型必须拒绝。
验证方式：调用 record_preference_signal，signal_type=future_type。
通过条件：accepted=false；reason=unsupported_signal_type；profile.json 无变化。
失败条件：未知类型写入 profile，或静默成功。
适用阶段：本地 Verify。
```

### A-005 Hermes 推荐后反馈调用统一工具

```text
描述：推荐后显式候选反馈必须调用 mcp_tastemate_record_preference_signal，而不是直接调用 record_feedback。
验证方式：本地插件测试先触发 @taste 推荐，再发送“我更喜欢 X，不要 Y”。
通过条件：dispatch_tool 最后一次调用为 mcp_tastemate_record_preference_signal；参数 signal_type=candidate_feedback；selected/rejected ids 准确。
失败条件：未调用统一工具，或参数无法构造 candidate_feedback。
适用阶段：本地 Verify。
```

### A-006 Hermes 插件失败路径不误写

```text
描述：无推荐上下文、未命中候选、候选歧义、MCP 调用失败时不得写 profile。
验证方式：本地插件测试覆盖四类失败路径。
通过条件：返回 allow 或 accepted=false；不调用写入工具或 profile 无变化；日志包含可定位 reason。
失败条件：失败路径调用写入工具并造成 profile 变化，或回复“已记录偏好”。
适用阶段：本地 Verify。
```

### A-007 远端 candidate_feedback 端到端通过

```text
描述：服务器真实 Hermes 路径中，推荐后反馈能更新 profile，并影响后续推荐。
验证方式：
1. 部署更新后的 TasteMate MCP 服务和 tastemate-route 插件到远端服务器。
2. 发送 @taste 推荐消息，记录 session id、工具调用和推荐上下文日志。
3. 发送显式反馈消息，记录 session id 和 mcp_tastemate_record_preference_signal 调用。
4. 对比 /opt/data/tastemate/profile.json 前后变化。
5. 再发送 @taste 推荐消息，记录排序或 reasons 体现反馈后的画像变化。
通过条件：
- 反馈轮出现 mcp_tastemate_record_preference_signal 调用。
- profile.json 前后存在对应 evidence/current/stable/negative 变化。
- 再推荐结果或 reasons 可观察到更新画像被消费。
失败条件：
- 反馈轮没有统一工具调用。
- profile.json 没有变化。
- 再推荐无法证明画像被读取。
适用阶段：远端 Verify，阻塞 Closeout。
```

### A-008 远端 interest 端到端通过

```text
描述：服务器真实 Hermes 路径中，普通兴趣表达能通过统一工具写入 current_focus。
验证方式：
1. 部署更新后的 TasteMate MCP 服务到远端服务器。
2. 发送普通兴趣表达，例如“我最近更关注本地优先和开源工具”。
3. 记录 session id 和 mcp_tastemate_record_preference_signal 调用。
4. 对比 /opt/data/tastemate/profile.json 前后变化。
5. 再发送 @taste 推荐消息，检查 reasons 或排序体现 current_focus。
通过条件：
- 普通兴趣轮出现 mcp_tastemate_record_preference_signal 调用，signal_type=interest。
- current_focus 写入对应 feature。
- stable_preferences 未因单次 interest 直接新增。
- 再推荐 reasons 或排序体现 current_focus。
失败条件：
- Hermes 没有调用统一工具。
- profile 没有写入 current_focus。
- 单次 interest 直接污染 stable_preferences。
适用阶段：远端 Verify，阻塞 Closeout。
```

### A-009 不修改 Hermes 源码

```text
描述：本轮只允许修改 TasteMate 仓库和 Hermes 用户插件，不触碰 Hermes 主程序源码。
验证方式：检查 git diff 和远端部署记录。
通过条件：无 Hermes 主程序源码改动。
失败条件：出现 Hermes 主程序源码改动。
适用阶段：Build / Verify。
```

## 十二、后续迭代

```text
1. 废弃 record_feedback：
   触发条件：record_preference_signal 在远端稳定通过 candidate_feedback 验收，且 Hermes 侧调用方全部切换完成。

2. 新增 signal_type=correction：
   触发条件：用户需要纠正已记录偏好，且有明确回滚/抵消语义设计。

3. 新增 signal_type=temporary_context：
   触发条件：需要表达“这次任务临时偏好”，且能保证不污染长期画像。

4. 支持相对指代反馈：
   触发条件：推荐上下文能稳定保存候选顺序，且远端测试证明“第一个/第二个”解析可靠。

5. 多用户隔离：
   触发条件：TasteMate 进入多用户或多账号部署。

6. 搜索前偏好注入：
   触发条件：统一偏好信号写入和后置排序消费在远端稳定通过验收。
```
