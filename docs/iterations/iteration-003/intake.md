# Iteration 003 Intake：反馈画像增强与有限排序生效

## 一、原始需求

```text
规划 iteration-003。
目标不是只做画像框架而没有效果，而是让画像和排序都有效果。
本轮先做本地验证；远端 feedback/evidence 作为单独验证项目。
强显式反馈应支持一次生效；feature 第一版限制在受控集合内，后续再演进。
```

## 二、当前理解

```text
iteration-001 已验证 feedback 能写入 evidence_log。
iteration-002 已验证真实 candidates 排序主路径。
iteration-003 要解决的问题是：让 feedback 从“只写 evidence”进入“沉淀为可解释画像，并对排序产生有限但明确的影响”。
本轮不追求完整远端链路，也不追求开放式画像系统，只做本地可验证闭环。
```

## 三、目标

```text
1. 定义 evidence_log -> stable_preferences / negative_preferences / current_focus 的沉淀规则。
2. 定义强显式反馈 1 次升级、普通 feedback 2 次同向升级的规则。
3. 让 rank_candidates 消费长期正向偏好、长期负向偏好和 current_focus。
4. 让 get_profile 能解释偏好来源、证据数量和当前关注。
5. 用本地固定样例验证反馈前后排序变化。
```

## 四、非目标

```text
1. 不修改 Hermes 源码。
2. 不把远端 feedback/evidence 主路径纳入本轮阻塞验收。
3. 不做搜索前偏好注入。
4. 不做 observed_tool_candidates。
5. 不做 Obsidian 偏好底座。
6. 不做 UI、多用户、人工编辑画像界面。
7. 不做复杂衰减模型和高级冲突求解。
8. 不允许白名单外 feature 升级为长期偏好。
```

## 五、约束

```text
技术约束：继续沿用现有 feedback 工具输入协议；只做本地规则逻辑，不引入模型调用。
范围约束：本轮阻塞验收只收本地闭环；远端 feedback/evidence 另立验证项目。
成本约束：只允许受控 feature 白名单进入长期画像；避免开放式自由文本 feature 污染 schema。
时间约束：先完成 Intake / Discovery / Design，再进入 Development Spec 和 Plan。
```

## 六、当前阶段

```text
Intake
```

## 七、需要调研的问题

```text
1. 现有 feedback、profile、ranker 代码边界是否支持 iteration-003 的本地闭环演进。
2. 哪些 feature 适合作为 iteration-003 第一版白名单。
3. 强显式反馈、普通 feedback、无效 feedback 的可测判定边界如何定义。
4. current_focus 对排序的影响边界怎样写成可验收条款。
5. 输入不变、输出兼容扩展的接口边界如何写清。
```

## 八、输出产物

```text
docs/iterations/iteration-003/intake.md
docs/iterations/iteration-003/discovery.md
docs/iterations/iteration-003/design.md
后续进入 development spec 和 plan。
```
