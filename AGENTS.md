# TasteMate Agent 工作守则

本文件是项目级 agent 入口规则。所有参与 TasteMate 的主 agent、实现 agent、审核 agent 都必须优先遵循。

## 一、基本原则

```text
先论证，再设计。
先设计，再计划。
先计划，再实现。
实现后必须验证。
验收必须基于文档和证据。
```

没有用户明确要求时，不要直接进入代码实现。

## 二、当前项目约束

TasteMate 当前阶段是方案与流程建设阶段。

项目约束：

```text
文档中文优先。
不修改 Hermes 源码，除非用户明确批准。
迭代一只做显式 @taste 的后置候选重排闭环。
搜索前偏好注入、Hermes plugin 编排、UI、多用户系统都属于后续迭代。
```

## 三、工作流

所有开发任务默认遵循：

```text
Intake -> Discovery -> Design -> Development Spec -> Plan -> Build -> Verify -> Multi-Agent Review -> Closeout
```

详细规则见：

```text
docs/process/workflow.md
docs/process/documentation.md
docs/process/acceptance.md
docs/process/review-loop.md
docs/process/prompt-guide.md
```

## 四、审核规则

多 agent 审核是验收机制，不是头脑风暴。

硬规则：

```text
每个审核 agent 只能按自己的角色边界审查。
审核结论只能是 PASS、BLOCK、FOLLOW_UP。
BLOCK 必须可定位、可复现、可修复。
FOLLOW_UP 不阻塞当前迭代。
审核最多两轮；第二轮只复查第一轮 BLOCK。
第二轮仍有 BLOCK 时，必须交给用户决策。
```

角色文档见：

```text
docs/process/agents/
```

## 五、禁止事项

```text
禁止无依据声称已验证。
禁止把推测写成事实。
禁止在当前迭代混入后续能力。
禁止顺手重构无关模块。
禁止用“建议优化”“可以考虑”作为阻塞意见。
禁止在审核和修复之间无限循环。
```

## 六、文档规则

所有项目文档必须遵循：

```text
中文优先。
先结论后细节。
必须写清适用阶段。
设计文档必须包含目标、非目标、数据流、边界、验收标准。
开发文档必须包含实现结构、接口、测试、禁止事项。
迭代文档必须包含范围、不做事项、验收标准、风险。
后续能力必须标注所属迭代，不能写成当前已实现。
```

详细规则见：

```text
docs/process/documentation.md
```
