# 文档书写规范

## 一、定位

本规范用于 TasteMate，也作为后续其他项目的通用文档规则基线。

文档的目的不是记录所有讨论，而是沉淀可执行、可验收、可追溯的项目约束。

---

## 二、通用规则

所有项目文档必须遵守：

```text
中文优先。
先结论后细节。
明确适用阶段。
明确目标和非目标。
明确当前做什么、不做什么。
明确哪些是已确认事实、哪些是假设、哪些未知。
后续能力必须标注所属迭代，不能写成当前已实现。
验收标准必须可判断、可验证、可失败。
每轮迭代的 Intake、Discovery、Design、Development、Plan、Verify、Review、Closeout 应可追溯。
```

禁止写法：

```text
可以考虑
建议优化
后续完善
效果较好
结构合理
根据情况处理
```

如果必须表达这类内容，必须归类为：

```text
当前范围
非目标
FOLLOW_UP
风险
待确认问题
```

---

## 三、事实表达规则

文档中的技术结论必须区分：

```text
Confirmed：已经通过源码、官方文档、测试或用户确认。
Assumption：当前采用的合理假设，但尚未验证。
Unknown：未知或待确认事项。
```

示例：

```text
Confirmed：Hermes 支持通过 mcp_servers 配置外部 MCP server。
Assumption：Hermes 会在 @taste 触发时稳定调用 rank_candidates。
Unknown：不同模型对工具调用指令的遵循稳定性。
```

不能把 `Assumption` 或 `Unknown` 写成确定事实。

---

## 四、设计文档规范

设计文档回答：

```text
应该做什么，为什么这样做，边界在哪里，如何验收。
```

必须包含：

```text
1. 当前结论
2. 背景与问题
3. 目标
4. 非目标
5. 数据流
6. 模块边界
7. 接口设计
8. 错误与降级
9. 成本与性能
10. 风险与应对
11. 验收标准
12. 后续迭代
```

硬性要求：

```text
必须有数据流。
必须有不做什么。
必须有错误和降级路径。
必须有明确验收标准。
后续增强必须标注不属于当前迭代。
```

---

## 五、Intake 文档规范

Intake 文档回答：

```text
用户到底要解决什么，本次工作边界在哪里。
```

适用情况：

```text
中大型需求
可能进入设计或开发的需求
存在多个阶段或多个 agent 参与的需求
```

小问题可以不单独建文件，但如果后续进入 Design 或 Plan，必须补一份 Intake 记录。

必须包含：

```text
1. 原始需求
2. 当前理解
3. 目标
4. 非目标
5. 约束
6. 当前阶段
7. 需要调研的问题
8. 输出产物
```

---

## 六、Discovery 文档规范

Discovery 文档回答：

```text
哪些事实已经确认，哪些只是推测，哪些仍未知。
```

只要涉及下面内容，就必须记录 Discovery：

```text
源码能力确认
第三方工具能力
API 或模型价格
协议和许可证
外部服务限制
开源项目参考
```

必须包含：

```text
1. 调研问题
2. 调研范围
3. Confirmed
4. Assumption
5. Unknown
6. 证据来源
7. 对设计的影响
```

---

## 七、开发文档规范

开发文档回答：

```text
怎么实现，项目结构是什么，接口怎么用，如何测试。
```

开发文档应在 Design 通过后、Plan 之前更新。

开发文档分两层：

```text
docs/iterations/iteration-<n>/development.md：当前迭代开发约定。
docs/development.md：项目级稳定开发约定。
```

规则：

```text
新开发约定先写入当前迭代 development.md。
被验证并稳定后，再同步到项目级 docs/development.md。
Plan 必须引用 development.md。
没有 development.md 或等价开发约定，不进入 Build。
```

必须包含：

```text
1. 开发原则
2. 技术形态
3. 目录结构
4. 核心模块
5. 接口约定
6. 配置说明
7. 数据结构
8. 错误处理
9. 测试策略
10. 本地运行方式
11. 禁止事项
```

硬性要求：

```text
接口必须包含输入和输出示例。
测试策略必须对应验收标准。
禁止事项必须明确列出，防止模型扩大范围。
如果实现未开始，必须明确“建议结构”而不是写成已实现结构。
```

---

## 八、迭代规划规范

迭代规划回答：

```text
当前做到哪里，下一步做什么，什么不做。
```

每个迭代必须包含：

```text
目标
范围
不做事项
验收标准
主要风险
风险应对
进入下一迭代的条件
```

硬性要求：

```text
迭代一必须足够小，能验证核心闭环。
后续迭代不能反向污染当前范围。
如果某能力是增强项，必须写清触发条件。
```

---

## 九、迭代文档组织规范

后续每轮迭代应使用独立目录，避免新旧设计混在一起。

推荐结构：

```text
docs/iterations/
  iteration-001/
    intake.md
    discovery.md
    design.md
    development.md
    plan.md
    verification.md
    review.md
    closeout.md
```

项目级文档和迭代级文档的关系：

```text
docs/design.md：当前项目级稳定设计。
docs/development.md：当前项目级开发约定。
docs/iteration-plan.md：整体迭代路线。
docs/iterations/iteration-<n>/：某一轮迭代的具体过程和证据。
```

更新规则：

```text
新想法先进入当前迭代文档。
被验证并成为稳定结论后，再同步到项目级文档。
历史迭代文档不覆盖，除非修正文档错误。
项目级文档不能记录未验证为已实现。
当前迭代 development.md 稳定后，再同步到 docs/development.md。
```

---

## 十、流程文档规范

流程文档回答：

```text
agent 应该怎么工作，什么时候停止，什么时候升级给用户。
```

必须包含：

```text
适用范围
阶段定义
输入
输出
进入条件
退出条件
禁止事项
升级条件
```

流程文档不能只描述理想状态，必须说明失败时怎么办。

---

## 十一、审核角色文档规范

每个审核角色文档必须包含：

```text
身份
输入
只检查什么
BLOCK 条件
FOLLOW_UP 条件
输出格式
```

审核角色不得重新设计方案，除非当前设计不可行或违反已确认约束。

---

## 十二、模板使用规则

新增重要文档时，优先使用：

```text
docs/process/templates/intake.md
docs/process/templates/discovery.md
docs/process/templates/design.md
docs/process/templates/development.md
docs/process/templates/iteration-plan.md
docs/process/templates/review-report.md
docs/process/templates/acceptance-item.md
docs/process/templates/verification.md
docs/process/templates/closeout.md
```

如果模板不适用，可以删减章节，但必须保留：

```text
适用阶段
目标
非目标
验收标准
风险
```

---

## 十三、文档同步规则

如果代码或方案发生以下变化，必须同步更新文档：

```text
数据流变化
接口变化
验收标准变化
迭代范围变化
外部系统边界变化
新增或删除核心模块
```

如果只是内部实现细节变化，但不影响接口、数据流和验收标准，可以只在开发文档或变更摘要中记录。
