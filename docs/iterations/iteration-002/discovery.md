# Iteration 002 Discovery：真实候选排序穿刺结论

## 一、调研问题

```text
1. Hermes 是否能把用户给定候选整理为 candidates 并调用 TasteMate。
2. 用户不给候选时，Hermes 是否能基于已有知识整理真实 candidates 并调用 TasteMate。
3. 补全查询失败或耗时时，Hermes 是否能 fallback 到已有候选并继续调用 TasteMate。
4. 迭代二应采用 explicit_candidates 还是 observed_tool_candidates。
```

## 二、调研范围

```text
范围内：
- 显式 @taste 推荐类问题。
- Hermes 主动整理 candidates。
- mcp_tastemate_rank_candidates 工具调用。
- fixed_probe_candidates 是否退出真实候选主路径。

范围外：
- 从 Hermes 工具结果自动抽取 observed_tool_candidates。
- 搜索前偏好注入。
- feedback 画像增强。
- Obsidian 偏好底座。
```

## 三、Confirmed

### C-001 用户给候选可以进入 TasteMate 排序

输入形态：

```text
用户给出 CrewAI、LangGraph、AutoGen、OpenAI Agents SDK、Smolagents。
要求 Hermes 整理 candidates 并调用 TasteMate。
```

结果：

```text
PASS
```

证据：

```text
Hermes 调用 mcp_tastemate_rank_candidates。
调用耗时约 0.00s。
candidates 为用户给定的 5 个真实框架。
tastemate-route 没有新增 fixed_probe_candidates 日志。
```

结论：

```text
Hermes 可以把用户给定候选结构化后主动传给 TasteMate。
```

### C-002 用户不给候选时，Hermes 可以基于已有知识生成候选

输入形态：

```text
用户只给推荐目标。
要求基于已有知识列出 3-5 个真实候选并调用 TasteMate。
```

结果：

```text
PASS
```

证据：

```text
Hermes 调用 mcp_tastemate_rank_candidates。
调用耗时约 0.01s。
candidates 包含 CrewAI、LangGraph、Smolagents、AutoGen、OpenAI Agents SDK。
没有新增 tastemate-route fixed_probe_candidates 日志。
```

结论：

```text
Hermes 可以基于已有知识生成候选并主动传给 TasteMate。
```

### C-003 补全查询失败时可以 fallback 到已有候选

输入形态：

```text
允许最多 1 次补全查询。
候选达到 3 个后立即停止。
补全失败时用已有候选继续。
```

结果：

```text
部分 PASS
```

证据：

```text
Hermes 尝试 terminal 补全查询。
terminal 被安全策略阻断并耗时约 60s。
Hermes 最终 fallback 到已有候选并调用 mcp_tastemate_rank_candidates。
TasteMate 调用耗时约 0.01s。
```

结论：

```text
补全查询可以作为后续扩展，但不适合作为迭代二的必需路径。
```

## 四、Assumption

```text
A-001 Hermes 在后续真实使用中仍能按提示整理 3-5 个 candidates。
A-002 不同推荐主题下，id/title/summary/metadata 仍是足够稳定的最小协议。
A-003 缺少 url 或 source 不应阻塞排序；这些字段只作为推荐字段和证据补充。
```

## 五、Unknown

```text
U-001 Hermes 插件是否能稳定观察搜索或工具结果，并自动抽取 observed_tool_candidates。
U-002 不同模型对“先整理 candidates，再调用 TasteMate”的遵循稳定性。
U-003 真实用户问题中 candidates metadata 字段的分布是否足以支撑稳定排序。
```

## 六、证据来源

```text
E-001 用户给候选穿刺：Hermes 工具调用日志显示 mcp_tastemate_rank_candidates，候选为 5 个真实框架。
E-002 Hermes 基于已有知识生成候选穿刺：工具调用日志显示 candidates 包含 5 个真实框架。
E-003 补全查询穿刺：terminal 补全被安全策略阻断约 60s 后，Hermes fallback 到已有候选并调用 TasteMate。
E-004 tastemate-route 日志：上述真实候选穿刺没有新增 fixed_probe_candidates 记录。
```

## 七、对设计的影响

```text
1. 迭代二采用 explicit_candidates：用户或 Hermes 明确整理后传入的候选。
2. 迭代二不采用 observed_tool_candidates；自动抽取进入后续迭代。
3. 迭代二必须定义 candidates 最小协议，并允许 metadata 扩展。
4. url 和 source 是推荐字段，不是阻塞排序的必填字段。
5. 验收必须检查工具调用参数和 tastemate-route 日志，不能只看最终回复文本。
6. Hermes 候选整理必须服务于 TasteMate 排序，不能只生成普通推荐报告。
```

## 八、风险

### R-001 Hermes 过度调研

现象：

```text
Hermes 为了真实候选扩展成长报告或长链路调研，导致长时间等待。
```

应对：

```text
迭代二提示应要求 Hermes 尽快形成 3-5 个 candidates 并调用 TasteMate。
如后续启用补全查询，必须设置硬超时和候选数量上限。
```

### R-002 Hermes 只生成报告，不调用 TasteMate

现象：

```text
普通推荐请求可能让 Hermes 只做调研报告，而不是调用 mcp_tastemate_rank_candidates。
```

应对：

```text
@taste 流程必须明确要求最终调用 mcp_tastemate_rank_candidates。
验收以工具调用日志为准，不以回复文本为准。
```

### R-003 candidates 字段不稳定

现象：

```text
不同主题下 Hermes 生成的 metadata 字段可能不一致。
```

应对：

```text
定义最小必填字段和允许扩展字段。
TasteMate 只依赖稳定字段排序，扩展字段作为加分证据。
```
