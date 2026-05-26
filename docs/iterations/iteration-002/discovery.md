# Iteration 002 Discovery：真实候选排序穿刺结论

## 一、当前结论

```text
方案 1 可作为迭代二主路径：
Hermes 主动整理 candidates，再调用 TasteMate 排序。
```

但该结论有边界：

```text
默认不应让 Hermes 做开放式外网调研。
外网补全会引入明显延迟和安全拦截风险。
```

## 二、已验证路径

### 1. 用户给候选

输入形态：

```text
用户给出 CrewAI、LangGraph、AutoGen、OpenAI Agents SDK、Smolagents。
要求 Hermes 不访问外网，只整理 candidates 并调用 TasteMate。
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

### 2. 不给候选，不访问外网

输入形态：

```text
用户只给推荐目标。
要求 Hermes 不访问外网、不写文件、不做完整调研。
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

### 3. 允许一次外网补全

输入形态：

```text
允许最多 1 次外网查询。
候选达到 3 个后立即停止。
外网失败时用已有候选继续。
```

结果：

```text
部分 PASS
```

证据：

```text
Hermes 尝试 terminal 外网补全。
terminal 被安全策略阻断并耗时约 60s。
Hermes 最终 fallback 到已有候选并调用 mcp_tastemate_rank_candidates。
TasteMate 调用耗时约 0.01s。
```

结论：

```text
外网补全可以作为后续扩展，但不适合进入迭代二默认主路径。
```

## 三、候选来源判断

迭代二采用：

```text
explicit_candidates：用户或 Hermes 明确整理后传入的候选。
```

迭代二不采用：

```text
observed_tool_candidates：从 Hermes 工具结果中自动抽取的候选。
```

原因：

```text
observed_tool_candidates 需要验证插件是否能看到工具结果或上下文，属于后续迭代。
```

## 四、风险

### R-001 Hermes 过度调研

现象：

```text
Hermes 为了真实候选访问多个国外站点，导致长时间等待。
```

应对：

```text
迭代二默认不访问外网。
如后续启用外网补全，必须设置硬超时和候选数量上限。
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
