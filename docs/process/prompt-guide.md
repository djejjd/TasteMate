# 项目工作流提问指南

## 一、用途

这份文档用于减少人与 agent 的沟通成本。

后续你可以直接使用这里的固定术语触发某个阶段，agent 应按 `AGENTS.md` 和 `docs/process/` 中的规则执行。

---

## 二、总入口

### 按完整项目工作流处理

```text
按项目工作流处理：<需求>
```

含义：

```text
从 Intake 开始判断当前应该进入哪个阶段。
如果需要调研，先做 Discovery。
如果需要设计，先写 Design。
不应直接跳到代码实现。
```

### 限制当前阶段

```text
按项目工作流处理：<需求>
当前只到 Design，不进入 Development Spec 和 Plan。
```

含义：

```text
允许完成 Intake、Discovery、Design。
不允许继续写开发约定、开发计划或代码。
```

### 只讨论，不改文件

```text
按项目工作流讨论：<问题>
只讨论，不改文件。
```

含义：

```text
可以给建议、梳理方案、指出风险。
不得修改文档、代码、git 状态。
```

---

## 三、阶段触发语

### Intake：需求接收

```text
进入 Intake：<需求>
```

或：

```text
按项目工作流，先做需求接收。
```

agent 应输出或更新：

```text
原始需求
当前理解
目标
非目标
约束
当前阶段
需要调研的问题
输出产物
```

适合在需求还不清楚时使用。

---

### Discovery：调研确认

```text
进入 Discovery：确认 <问题>
```

或：

```text
按项目工作流做调研确认，结论区分 Confirmed / Assumption / Unknown。
```

agent 应输出或更新：

```text
调研问题
调研范围
Confirmed
Assumption
Unknown
证据来源
对设计的影响
```

适合确认源码能力、外部工具、价格、协议、开源项目参考。

---

### Design：方案设计

```text
进入 Design：基于当前调研设计方案。
```

或：

```text
按项目工作流进入 Design，不进入 Development Spec 和 Plan。
```

agent 应输出或更新：

```text
当前结论
背景与问题
目标
非目标
数据流
模块边界
接口设计
错误与降级
成本与性能
风险与应对
验收标准
后续迭代
```

适合确定“做什么”和“为什么这样做”。

---

### Development Spec：开发约定

```text
进入 Development Spec：基于设计文档补开发约定。
```

或：

```text
按项目工作流进入 Development Spec，不写代码。
```

agent 应输出或更新：

```text
目录结构
核心模块
接口 schema
配置说明
数据结构
错误处理
测试策略
本地运行方式
禁止事项
```

适合在写开发计划之前，先固定代码结构和接口约定。

---

### Plan：开发计划

```text
进入 Plan：基于 design 和 development 写开发计划。
```

或：

```text
按项目工作流进入 Plan，不写代码。
```

agent 应输出或更新：

```text
文件影响范围
实现步骤
测试计划
不做事项
风险处理
回滚或降级思路
分支或 worktree 隔离策略
```

适合在准备编码前使用。

---

### Build：实现

```text
进入 Build：按已确认的 plan 实现。
```

或：

```text
按项目工作流进入 Build，完成后执行 Verify。
```

agent 应：

```text
按计划修改文件
不得扩大范围
不得处理 FOLLOW_UP
遇到设计冲突必须停下来
完成后进入验证
```

适合开始写代码或正式改文档时使用。

---

### Verify：验证

```text
进入 Verify：按验收标准验证当前实现。
```

或：

```text
按项目工作流做验证，记录命令、结果和未验证项。
```

agent 应输出或更新：

```text
验证范围
测试命令
测试结果
手工验证
未验证项
结论
```

适合检查“是否真的完成”。

---

### Multi-Agent Review：多 agent 审核

```text
启动 Multi-Agent Review。
```

或：

```text
按项目工作流启动多 agent 审核，用 docs/process/agents 下的角色。
```

agent 应：

```text
按角色启动或模拟审核
只输出 PASS / BLOCK / FOLLOW_UP
汇总 BLOCK
只修复 BLOCK
最多两轮审核
第二轮仍有 BLOCK 时交给用户决策
```

适合进入验收审核时使用。

---

### Fix Review BLOCK：修复审核阻塞

```text
按 review-loop 规则修复 Round 1 的 BLOCK。
```

或：

```text
只修复 BLOCK，不处理 FOLLOW_UP。
```

agent 应：

```text
只处理审核中明确列出的 BLOCK
不新增功能
不顺手重构
不扩大范围
修复后只做 Round 2 复查
```

---

### Closeout：收尾归档

```text
进入 Closeout：归档本轮结果。
```

或：

```text
按项目工作流做 Closeout。
```

agent 应输出或更新：

```text
变更摘要
验证摘要
审核摘要
已知风险
后续事项
文档同步
提交或发布建议
```

适合一轮迭代完成后使用。

---

## 四、常用限定语

### 限制不要写代码

```text
先不要写代码。
```

含义：

```text
最多进行 Intake / Discovery / Design / Development Spec / Plan。
不得进入 Build。
```

### 限制不要改文件

```text
只讨论，不改文件。
```

含义：

```text
不得修改文档、代码、git 状态。
```

### 允许先继续，后续补确认

```text
拿不准但不阻塞的，标为 Assumption 或 Unknown，继续向下。
```

含义：

```text
不要卡住流程。
但不能把未确认内容写成 Confirmed。
```

### 限制范围

```text
只处理当前迭代范围，FOLLOW_UP 不处理。
```

含义：

```text
不得把后续事项混入当前实现。
```

### 强制验收依据

```text
按设计文档和验收标准判断，不按临时聊天结论判断。
```

含义：

```text
验收必须回到文档和证据。
```

---

## 五、推荐组合句式

### 从新需求开始

```text
按项目工作流处理：<需求>
先完成 Intake 和 Discovery，结论区分 Confirmed / Assumption / Unknown。
```

### 只做设计

```text
按项目工作流处理：<需求>
当前只到 Design，不进入 Development Spec 和 Plan。
```

### 准备开发但不写代码

```text
按项目工作流进入 Development Spec 和 Plan。
基于当前 design，先不要写代码。
```

### 开始实现

```text
按项目工作流进入 Build。
严格按已确认 plan 实现，完成后进入 Verify。
```

### 启动审核

```text
启动 Multi-Agent Review。
使用 docs/process/agents 下的角色，只输出 PASS / BLOCK / FOLLOW_UP。
```

### 修复审核问题

```text
按 review-loop 规则，只修复 Round 1 的 BLOCK，不处理 FOLLOW_UP。
修复后只做 Round 2 复查。
```

