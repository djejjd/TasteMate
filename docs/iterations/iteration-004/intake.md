# Iteration 004 Intake：统一偏好信号摄取

## 一、原始需求

```text
当前已经通过最小穿刺实验确认两条偏好写入路径可行：
1. 推荐后显式反馈可以通过 Hermes 插件转成候选选择/排除，并调用 TasteMate 写入 profile。
2. 普通自然语言兴趣表达可以抽取白名单特征，并写入 current_focus。

本轮不应只做 record_feedback 的临时补丁，也不单独设计 record_interest。
需要正式设计一个统一偏好信号接口，首版支持推荐后候选反馈和普通兴趣表达，同时保留后续扩展 signal_type 的空间。
```

## 二、当前理解

```text
TasteMate 已有 record_feedback 正式工具，并已在 iteration-003 完成本地画像沉淀和排序消费。
工作区中的 record_interest 属于穿刺代码，证明普通兴趣记录可行，但尚未进入正式接口设计。

如果继续把推荐后反馈和普通兴趣记录做成两套独立工具，后续会在特征抽取、profile 更新语义、日志、验收和 Hermes 编排上重复改造。
因此本轮正式方向应是新增统一工具 record_preference_signal。

record_feedback 保留为兼容 wrapper，内部转成统一偏好信号。
record_interest 不作为正式工具设计；普通兴趣记录直接进入 record_preference_signal 的 interest 类型。
```

## 三、目标

```text
1. 设计统一偏好信号接口 record_preference_signal，作为后续偏好摄取的稳定入口。
2. 首版只实现 candidate_feedback 和 interest 两类 signal_type。
3. 协议保留扩展空间，未来可新增 correction、temporary_context、manual_profile_edit 等类型，但未知类型必须 fail-soft，不写 profile。
4. 将 record_feedback 保留为兼容入口，内部转换为 candidate_feedback 信号。
5. 不设计独立 record_interest 工具；现有穿刺代码只作为可行性证据。
6. 明确 profile 更新语义，避免普通兴趣一次写入就污染 stable_preferences。
7. 将远端真实端到端验收作为阻塞验收：必须实际更新服务器插件/服务，并验证真实消息、工具调用、profile 变化和再推荐效果。
```

## 四、非目标

```text
1. 不修改 Hermes 源码。
2. 不废除 record_feedback；本轮只做兼容 wrapper。
3. 不把 record_interest 作为正式 MCP 工具发布。
4. 不实现开放式自然语言偏好理解。
5. 不支持“第一个 / 第二个 / 上面那个”这类相对指代作为阻塞能力。
6. 不实现多用户隔离、UI 编辑画像、人工审核界面。
7. 不实现搜索前偏好注入。
8. 不升级 fixed_probe_candidates 为真实候选系统。
9. 不把 future signal_type 写成当前已支持能力。
```

## 五、约束

```text
技术约束：
- 不修改 Hermes 主程序源码。
- TasteMate 新增统一 MCP 工具时必须保持 record_feedback 旧输入协议兼容。
- profile 写入必须继续使用现有 JSON profile 存储和白名单 feature 体系。

范围约束：
- 当前实现只支持 candidate_feedback 和 interest。
- candidate_feedback 必须绑定候选快照和 selected/rejected candidate ids。
- interest 必须命中显式偏好词和白名单 feature，首版只写 evidence_log 与 current_focus，不直接升级 stable_preferences。

产品约束：
- 本轮必须以真实用户路径成立为判断标准，不能只以本地工具可调用作为完成依据。
- 验收必须包含远端服务器实际更新和真实 Hermes 消息链路。

流程约束：
- 先完成 Intake / Discovery / Design / Development Spec / Plan，再进入 Build。
- 验证记录必须引用设计和验收标准，不得无依据声称已完成。
```

## 六、当前阶段

```text
Intake / Discovery / Design
```

## 七、需要调研的问题

```text
1. 当前 record_feedback 的输入、输出和 profile 更新契约有哪些必须兼容。
2. record_interest 穿刺代码验证了哪些能力，哪些不能作为正式结论。
3. 统一 PreferenceSignal 最小字段应如何设计，才能支持当前两类信号并保留扩展空间。
4. candidate_feedback 与 interest 的 profile 更新语义应如何区分，避免误写长期偏好。
5. Hermes tastemate-route 插件如何保存推荐上下文并路由到 record_preference_signal。
6. 远端端到端验收需要哪些证据才能证明真实用户路径成立。
```

## 八、输出产物

```text
docs/iterations/iteration-004/intake.md
docs/iterations/iteration-004/discovery.md
docs/iterations/iteration-004/design.md
docs/iterations/iteration-004/development.md
docs/iterations/iteration-004/plan.md

后续 Build 完成后必须补充：
- docs/iterations/iteration-004/verification.md
- docs/iterations/iteration-004/review.md
- docs/iterations/iteration-004/status.md
```
