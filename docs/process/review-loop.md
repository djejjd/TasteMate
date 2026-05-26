# 审核与打回规则

## 一、核心原则

多 agent 审核是验收机制，不是持续改进机制。

```text
第一轮发现问题。
修复后第二轮只复查第一轮 BLOCK。
第二轮仍有 BLOCK，必须交给用户决策。
```

不允许无限循环：

```text
审核 -> 打回 -> 修改 -> 审核 -> 打回 -> 修改
```

审核必须由独立 agent 执行：

```text
主 agent 只能组织、分发、汇总和执行修复。
主 agent 不得冒充 Design Reviewer、Architecture Reviewer、Implementation Reviewer、Verification Reviewer 或 Documentation Reviewer 给出审核结论。
每个审核角色必须指派独立 agent 按对应角色文档审查。
无法为每个角色指派独立 agent 时，不得产出审核结论；必须记录原因并交给用户决定等待、缩小审核范围或调整流程。
```

---

## 二、审核轮次

默认最多两轮审核。

### 前置审核

Development Spec Review 和 Plan Review 属于进入 Build 前的前置审核。

规则：

```text
前置审核默认一轮。
发现 BLOCK 时，只修复 BLOCK。
修复后只由提出 BLOCK 的角色复查。
复查仍有 BLOCK 时，必须交给用户决策。
FOLLOW_UP 不阻塞进入下一阶段。
```

前置审核不允许重新设计已批准方案，也不允许把后续能力塞进当前迭代。

### Round 1

目标：发现当前迭代是否存在阻塞问题。

每个被指派的审核 agent 输出：

```text
PASS
BLOCK
FOLLOW_UP
```

主 agent 汇总后只处理 `BLOCK`。

指派要求：

```text
一个审核 agent 只能担任一个审核角色。
审核 agent 必须只读取本轮 Scope 和 Inputs Assigned，不继承主 agent 的口头判断作为事实。
审核 agent 必须基于文档、代码、测试输出或日志证据给出结论。
```

### Triage

主 agent 必须对所有 BLOCK 去重和归类。

每个 BLOCK 必须满足：

```text
有证据
有定位
有影响说明
有必须修复的理由
```

不满足条件的 BLOCK，主 agent 必须在 Triage 中标记为“不进入 Fix 队列”，并说明处理结论是 FOLLOW_UP 或 NOTE。
原审核 agent 的 Decision 和原始问题必须保留，不得改写。

### Fix

只允许修复 BLOCK。

允许：

```text
修复 BLOCK
补充对应测试
更新与 BLOCK 直接相关的文档
```

不允许：

```text
新增功能
顺手重构
处理 FOLLOW_UP
扩大当前迭代范围
重新设计已批准方案
```

### Round 2

目标：确认 Round 1 的 BLOCK 是否已修复。

Round 2 不重新全量审查。

Round 2 必须由提出对应 BLOCK 的同一角色 agent 或同等独立角色 agent 复查。

第二轮不得新增问题，除非满足以下条件之一：

```text
修复 BLOCK 引入新的严重 bug
新问题破坏核心验收标准
新问题属于安全、数据破坏或不可恢复错误
```

否则新发现的问题必须归为 FOLLOW_UP。

---

## 三、第二轮仍有 BLOCK

如果 Round 2 仍有 BLOCK，主 agent 不得继续自动修复。

必须交给用户选择：

```text
1. 允许第三轮审核和修复
2. 缩小当前迭代范围
3. 修改设计或验收标准
4. 接受风险并记录 waiver
5. 放弃当前实现，重新规划
```

没有用户确认，不进入第三轮。

---

## 四、问题分级

### BLOCK

当前迭代不能通过，必须修。

要求：

```text
可定位
可复现或可证明
影响核心目标、验收标准、数据安全、稳定性或设计边界
```

### FOLLOW_UP

真实问题，但不阻塞当前迭代。

要求：

```text
说明为什么不阻塞
建议进入哪个后续迭代或事项
```

### NOTE

说明性观察，不要求动作。

NOTE 不进入修复队列。

---

## 五、禁止模糊意见

禁止直接输出：

```text
建议优化
可以考虑
需要注意
最好加强
可能存在问题
```

如果确实要提出，必须改写为：

```text
BLOCK / FOLLOW_UP / NOTE
```

并说明原因。
