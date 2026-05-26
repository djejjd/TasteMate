# 多 Agent 角色总览

## 一、角色原则

多 agent 审核不是让多个模型重新讨论方案，而是让不同角色基于已批准文档进行验收。

角色必须由独立 agent 承担：

```text
主 agent 只能担任流程协调者和汇总者。
主 agent 不得自行扮演审核角色并直接给出角色结论。
每个 Review Role 必须指派一个对应审核 agent。
一个审核 agent 只能担任一个角色。
无法为每个角色指派独立 agent 时，不得产出审核结论；必须记录原因并交给用户决定等待、缩小审核范围或调整流程。
```

每个角色必须遵守：

```text
只审自己的范围。
不重新设计方案。
不扩大当前迭代。
只输出 PASS、BLOCK、FOLLOW_UP。
BLOCK 必须有证据。
FOLLOW_UP 不阻塞当前迭代。
```

---

## 二、默认角色

| 角色 | 目标 | 角色文档 |
| --- | --- | --- |
| Design Reviewer | 判断实现是否符合设计方向和当前迭代目标 | `docs/process/agents/design-reviewer.md` |
| Architecture Reviewer | 判断模块边界、依赖和复杂度是否合理 | `docs/process/agents/architecture-reviewer.md` |
| Implementation Reviewer | 检查代码实现缺陷和维护风险 | `docs/process/agents/implementation-reviewer.md` |
| Verification Reviewer | 检查测试和验证是否足以支撑验收 | `docs/process/agents/verification-reviewer.md` |
| Documentation Reviewer | 检查文档、实现、验收标准是否一致 | `docs/process/agents/documentation-reviewer.md` |

---

## 三、前置审核适用角色

### Development Spec Review

默认角色：

```text
Architecture Reviewer
Documentation Reviewer
Verification Reviewer
```

可选角色：

```text
Implementation Reviewer
```

审核目标：

```text
判断 development.md 是否足以约束后续 plan 和 build。
```

### Plan Review

默认角色：

```text
Design Reviewer
Architecture Reviewer
Verification Reviewer
Documentation Reviewer
```

可选角色：

```text
Implementation Reviewer
```

审核目标：

```text
判断 plan.md 是否可以进入 Build。
```

---

## 四、统一输出格式

每个审核 agent 必须使用：

```text
Review Role:
Assigned Agent:
Scope:
Inputs Assigned:
Inputs Reviewed:
Review Type: Development Spec Review | Plan Review | Implementation Review | Documentation Review | Other
Decision: PASS | BLOCK | FOLLOW_UP

Blocking Issues:
- [B1]
  位置：
  问题：
  影响：
  必须修复：

Follow-up Issues:
- [F1]
  问题：
  为什么不阻塞：
  建议进入：

Non-Issues:
- 明确说明看起来像问题但不阻塞的点。
```

如果没有对应内容，写 `无`。

主 agent 汇总审核时必须保留：

```text
每个角色的 Assigned Agent。
每个角色的 Decision。
BLOCK / FOLLOW_UP / Non-Issues 的原始要点。
主 agent 的 Triage 只能处理 BLOCK 是否进入 Fix 队列、是否重复和修复安排，不得改写角色原始结论。
```
