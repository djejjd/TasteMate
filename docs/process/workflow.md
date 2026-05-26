# AI 多 Agent 开发工作流

## 一、定位

这套流程先服务于 TasteMate，但设计为项目无关的通用工作流，后续可以迁移到其他 AI 主导开发项目。

整体分三层：

```text
Global Workflow：通用工作流，所有项目复用。
Project Rules：项目规则，由 AGENTS.md 和项目文档定义。
Iteration Contract：当前迭代契约，由迭代规划和开发计划定义。
```

项目规则可以收紧通用流程，但不应绕过通用流程中的验证和审核要求。

---

## 二、阶段总览

```text
0. Intake 需求接收
1. Discovery 调研确认
2. Design 方案设计
3. Development Spec 开发约定
4. Plan 开发计划
5. Build 实现
6. Verify 验证
7. Multi-Agent Review 多 agent 审核
8. Closeout 收尾归档
```

每个阶段都有明确产物和退出条件。未满足退出条件，不进入下一阶段。

---

## 三、0. Intake 需求接收

目标：把用户想法变成清晰任务。

默认产物是轻量 Intake 记录。小任务可以写在开发计划开头；中大型任务应单独落文档。

建议路径：

```text
docs/iterations/iteration-<n>/intake.md
```

必须明确：

```text
问题是什么
目标是什么
非目标是什么
当前阶段是什么
是否需要写代码
是否需要修改文档
是否需要调研外部事实
```

退出条件：

```text
任务边界明确。
知道本次是讨论、调研、写文档、写计划还是写代码。
如果进入 Design 或 Plan，必须已有可追溯的 Intake 记录。
```

---

## 四、1. Discovery 调研确认

目标：确认事实，不靠猜。

默认产物是 Discovery 记录。只要涉及源码确认、外部 API、价格、协议、第三方工具能力，就必须记录确认来源和结论状态。

建议路径：

```text
docs/iterations/iteration-<n>/discovery.md
```

适用于：

```text
源码能力确认
第三方工具能力确认
API、价格、协议确认
开源项目参考
现有文档一致性检查
```

输出必须区分：

```text
Confirmed：已确认事实
Assumption：合理假设
Unknown：未确认风险
```

退出条件：

```text
关键技术路径已确认。
未确认点不会阻塞进入设计。
Confirmed / Assumption / Unknown 已明确记录。
```

---

## 五、2. Design 方案设计

目标：定义应该做什么。

每轮迭代如果产生新的设计结论，应优先写入当前迭代目录，再视情况同步到项目级设计文档。

建议路径：

```text
docs/iterations/iteration-<n>/design.md
```

设计文档必须包含：

```text
目标
非目标
数据流
模块边界
接口
错误与降级
成本与性能
风险
验收标准
```

文档写法必须遵循：

```text
docs/process/documentation.md
```

退出条件：

```text
用户确认设计。
验收标准明确可测。
当前迭代边界清楚。
```

---

## 六、3. Development Spec 开发约定

目标：在进入具体开发计划前，明确代码层面的长期实现约定。

Development Spec 不等同于 Plan：

```text
Development Spec：项目结构、模块职责、接口 schema、配置、存储、错误处理、测试策略。
Plan：当前迭代具体改哪些文件、按什么步骤做、如何验证。
```

建议路径：

```text
docs/iterations/iteration-<n>/development.md
```

如果开发约定已经稳定，应同步到项目级：

```text
docs/development.md
```

Development Spec 必须包含：

```text
目录结构
核心模块
接口 schema
配置
数据结构
错误处理
测试策略
本地运行方式
禁止事项
```

退出条件：

```text
代码结构和接口约定明确。
测试策略能覆盖设计文档中的验收标准。
没有把后续迭代能力写成当前实现。
Development Spec Review 无 BLOCK。
用户确认可以进入 Plan。
```

### Development Spec Review

进入 Plan 前必须完成轻量前置审核。

默认审核角色：

```text
Architecture Reviewer
Documentation Reviewer
Verification Reviewer
```

如 Development Spec 包含复杂实现细节、异常处理策略或数据结构，也可以增加：

```text
Implementation Reviewer
```

前置审核只判断是否允许进入 Plan，不做实现后验收。

---

## 七、4. Plan 开发计划

目标：定义怎么做。

每轮迭代都应有独立开发计划，不直接覆盖历史计划。

建议路径：

```text
docs/iterations/iteration-<n>/plan.md
```

开发计划必须包含：

```text
文件影响范围
实现步骤
测试计划
不做事项
风险处理
回滚或降级思路
分支或 worktree 隔离策略
```

Plan 必须引用：

```text
当前迭代 design.md
当前迭代 development.md 或项目级 docs/development.md
当前迭代验收标准
```

退出条件：

```text
计划可执行。
没有超出当前迭代范围。
Development Spec 已存在或已有等价开发约定。
已判断是否需要独立分支或 worktree。
Plan Review 无 BLOCK。
用户确认可以进入实现。
```

### Plan Review

进入 Build 前必须完成轻量前置审核。

默认审核角色：

```text
Design Reviewer
Architecture Reviewer
Verification Reviewer
Documentation Reviewer
```

如果计划包含复杂实现步骤，也可以增加：

```text
Implementation Reviewer
```

前置审核只判断是否允许进入 Build。

审核执行要求：

```text
每个审核角色必须指派独立 agent 执行。
主 agent 只负责分发审核任务、汇总结论和处理 BLOCK。
无法为每个角色指派独立 agent 时，不得产出审核结论，必须交给用户决策。
具体指派规则见 docs/process/review-loop.md 和 docs/process/roles.md。
```

---

## 八、5. Build 实现

目标：按计划实现。

约束：

```text
多文件代码变更、功能开发、需要审核循环的任务，默认使用独立分支或 worktree。
不得顺手重构。
不得扩大范围。
不得混入后续迭代能力。
遇到设计冲突必须停下来更新设计或询问用户。
不得修改外部源码，除非设计和用户明确批准。
```

退出条件：

```text
实现完成。
主 agent 自检通过。
必要文档已同步。
```

---

## 九、6. Verify 验证

目标：证明实现有效。

建议路径：

```text
docs/iterations/iteration-<n>/verification.md
```

必须记录：

```text
测试命令
测试结果
手工验证步骤
未验证项
失败项
```

退出条件：

```text
核心验收标准都有证据。
不能验证的项已明确说明原因。
```

---

## 十、7. Multi-Agent Review 多 agent 审核

目标：分角色审查当前迭代是否可验收。

建议路径：

```text
docs/iterations/iteration-<n>/review.md
```

默认角色：

```text
Design Reviewer
Architecture Reviewer
Implementation Reviewer
Verification Reviewer
Documentation Reviewer
```

执行要求：

```text
每个角色必须由独立 agent 担任。
主 agent 不得自行扮演审核角色给出 PASS、BLOCK 或 FOLLOW_UP。
review.md 必须记录每个角色的 Assigned Agent。
无法为每个角色指派独立 agent 时，不得产出审核结论，必须交给用户决策。
```

每个角色只允许输出：

```text
PASS
BLOCK
FOLLOW_UP
```

退出条件：

```text
没有 BLOCK。
FOLLOW_UP 已记录到后续事项。
```

审核轮次规则见：

```text
docs/process/review-loop.md
```

---

## 十一、8. Closeout 收尾归档

目标：把本次迭代变成可追溯资产。

必须输出：

```text
变更摘要
验证摘要
审核摘要
已知风险
后续事项
是否需要 commit、tag 或 release
```

如果本次修改改变了设计、接口、验收标准或项目约束，必须同步更新对应文档。

每轮迭代收尾建议写入：

```text
docs/iterations/iteration-<n>/closeout.md
```

退出条件：

```text
用户知道当前完成了什么。
用户知道哪些没有做。
用户知道后续怎么推进。
```
