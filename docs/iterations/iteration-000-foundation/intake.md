# Iteration 000 Intake：TasteMate 论证与基础设计归档

## 一、原始需求

用户希望将前期关于 TasteMate 的讨论，按照项目工作流补齐 `Intake -> Discovery -> Design` 三个阶段的文档，并完成审核。

用户明确要求：

```text
当前项目已经完成论证和简易的设计开发方案。
请按照已设计的工作流，完成 Intake -> Discovery -> Design 三个阶段的文档编写及审核。
按顺序进行处理。
有拿不准但不阻塞流程的结果，可以先继续，后续完成后告知。
```

## 二、当前理解

本轮不是进入代码开发，也不是重新设计 TasteMate，而是把已经形成的方向和设计归档为可追溯的迭代文档。

当前要完成的是：

```text
1. 记录本轮需求接收结果。
2. 记录已经确认的技术事实和仍待确认事项。
3. 形成迭代级设计文档，作为后续 Plan / Build 的输入。
4. 对 Intake、Discovery、Design 文档做阶段审核。
```

## 三、目标

```text
建立 iteration-000-foundation 迭代目录。
补齐 intake.md、discovery.md、design.md。
基于已有流程文档完成阶段审核记录。
明确哪些结论已确认，哪些只是后续待验证。
为后续迭代一开发计划提供稳定输入。
```

## 四、非目标

本轮明确不做：

```text
不写 TasteMate 代码。
不实现 MCP server。
不修改 Hermes 源码。
不进入 Plan / Build / Verify 阶段。
不调整已经确认的迭代一主方向，除非审核发现 BLOCK。
```

## 五、约束

项目约束：

```text
文档中文优先。
所有结论必须区分 Confirmed / Assumption / Unknown。
后续能力必须标注所属迭代，不能写成当前已实现。
审核最多两轮；本轮先做 Round 1。
```

当前 TasteMate 约束：

```text
迭代一默认不改 Hermes 源码。
迭代一只做显式 @taste 后置候选重排闭环。
搜索前偏好注入属于迭代二。
Hermes plugin/hook 自动编排属于迭代三或后续增强。
```

## 六、当前阶段

```text
当前执行阶段：Intake -> Discovery -> Design
当前不进入：Plan -> Build -> Verify -> Closeout
```

## 七、需要调研的问题

本轮需要确认的问题：

```text
1. Hermes 是否支持外部 MCP server 接入。
2. Hermes MCP 工具是否会以可识别工具名注册。
3. Hermes 工具结果是否会进入下一轮模型上下文。
4. Hermes 是否有 hook 能支持后续搜索前偏好注入。
5. 当前设计中哪些判断仍然依赖模型行为，不能视为硬保证。
```

## 八、输出产物

本轮输出：

```text
docs/iterations/iteration-000-foundation/intake.md
docs/iterations/iteration-000-foundation/discovery.md
docs/iterations/iteration-000-foundation/design.md
docs/iterations/iteration-000-foundation/review.md
```

