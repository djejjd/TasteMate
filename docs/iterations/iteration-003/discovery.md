# Iteration 003 Discovery：反馈画像增强与有限排序生效

## 一、调研问题

```text
1. 当前代码是否已经具备 feedback -> evidence_log 的基础能力。
2. 当前代码中 stable_preferences / negative_preferences / current_focus 的边界是什么。
3. 当前排序逻辑是否已经消费 feedback 相关信号，以及消费深度如何。
4. iteration-003 是否可以在不改 feedback 输入协议的前提下完成。
5. 哪些问题必须留在本轮范围外。
```

## 二、调研范围

```text
源码路径：
- tastemate/core/feedback.py
- tastemate/core/ranker.py
- tastemate/core/scoring.py
- tastemate/tools/record_feedback.py
- tastemate/tools/get_profile.py
- tastemate/storage/json_store.py
- tests/test_record_feedback.py
- tests/test_rank_candidates.py

项目文档：
- docs/design.md
- docs/development.md
- docs/iteration-plan.md
- docs/iterations/iteration-002/closeout.md
- docs/process/acceptance.md
- docs/process/documentation.md

其他来源：
- 本轮用户确认：iteration-003 以本地验证为主，远端 feedback/evidence 单独验证。
```

## 三、Confirmed

```text
C-001 iteration-001 已具备 record_feedback 写 evidence_log 的基础能力。

C-002 当前 FeedbackProcessor 已使用现有输入协议：
query、user_feedback、selected_candidate_ids、rejected_candidate_ids、candidates_snapshot。

C-003 当前 FeedbackProcessor 已能抽取少量 feature，并对已有 stable_preferences 做保守更新；但不会系统沉淀 negative_preferences，也没有明确的 strong / normal 分类层。

C-004 当前排序逻辑仍以 query_relevance、preference_fit、feedback_score 为主，长期画像与临时画像还没有形成清晰分层消费。

C-005 iteration-002 已完成真实 candidates 排序主路径，iteration-003 不需要再解决 fixed_probe_candidates 主路径问题。

C-006 项目规则要求：验收标准必须可判断、可验证、可失败；设计文档必须包含数据流、模块边界、接口设计、错误与降级、成本与性能、风险与应对、验收标准、后续迭代。

C-007 本轮用户已确认：iteration-003 阻塞验收只收本地闭环；远端 feedback/evidence 不进入本轮阻塞验收。
```

## 四、Assumption

```text
A-001 iteration-003 第一版只在受控 feature 白名单内升级长期画像，就足以支撑本地可验证闭环。

A-002 强显式反馈可以用规则文本判定，不需要引入模型或外部分类器。

A-003 get_profile 与 rank_candidates 的输出可以做兼容扩展，而不需要 Hermes 输入协议变化。

A-004 current_focus 只做轻量修正即可满足本轮目标，不需要复杂时间衰减。
```

## 五、Unknown

```text
U-001 强显式反馈关键词集合在真实用户表达中的覆盖率。

U-002 白名单 feature 在真实长期使用中是否过窄。

U-003 远端 feedback/evidence 主路径在 Hermes 真实运行中的稳定性。

U-004 冲突 feedback 在真实使用中出现频率是否足以要求更复杂的冲突求解。
```

## 六、证据来源

```text
E-001 docs/design.md：项目级设计已把反馈学习定义为 TasteMate 核心数据流之一。
E-002 docs/iteration-plan.md：iteration-003 当前定位为“反馈画像增强”。
E-003 docs/iterations/iteration-002/closeout.md：iteration-002 已完成真实 candidates 排序闭环，后续事项明确提到 feedback/evidence 远端链路可单独补实验。
E-004 tastemate/core/feedback.py：当前已写 evidence_log，并仅对已有 stable_preferences 做保守更新。
E-005 docs/process/acceptance.md：验收标准必须可判断、可验证、可失败。
E-006 docs/process/documentation.md：设计文档必需章节约束。
```

## 七、对设计的影响

```text
1. iteration-003 可以复用现有 feedback 输入协议，不新增输入字段。
2. 设计必须补上 strong / normal 分类层，以及 stable / negative / current_focus 的清晰分工。
3. 设计必须把“输出兼容扩展”写清，避免接口边界争议。
4. 本轮验收应完全落在本地固定样例和本地 profile 变化上，不把远端链路混成阻塞项。
5. 白名单 feature 机制应作为受控升级路径，白名单外 feedback 只保留在 evidence_log。
```
