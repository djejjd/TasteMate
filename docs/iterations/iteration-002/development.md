# Iteration 002 Development Spec：真实候选排序

## 适用阶段

```text
Development Spec
```

本文件在 Iteration 002 Design Review 通过后、Plan 之前编写，用于约束后续开发计划和实现。

本文件不是代码实现，也不是开发计划。后续 `plan.md` 必须引用本文件。

## 一、开发原则

迭代二只解决真实候选排序：

```text
用户或 Hermes 明确整理 candidates。
Hermes 调用 mcp_tastemate_rank_candidates。
TasteMate 校验 candidates 最小协议。
TasteMate 对真实 candidates 排序或降级。
fixed_probe_candidates 退出真实候选主路径。
```

当前阶段禁止实现：

```text
observed_tool_candidates 自动抽取。
Hermes 工具结果自动解析。
搜索前偏好注入。
feedback 画像增强。
Obsidian 偏好底座。
gateway send API。
Hermes 源码修改。
```

## 二、技术形态

TasteMate 继续作为本地 stdio MCP server 运行。

Hermes 通过 MCP 工具调用把真实 candidates 显式传给 TasteMate：

```text
Hermes -> mcp_tastemate_rank_candidates -> TasteMate Ranker
```

`tastemate-route` 插件在迭代二中只保留为迭代一通道回归路径，不作为真实候选主路径。

## 三、目录结构

迭代二预计影响范围：

```text
tastemate/
  schemas/
    candidates.py
  core/
    ranker.py
  tools/
    rank_candidates.py
tests/
  test_rank_candidates.py
  test_server_tools.py
  test_hermes_route_plugin.py
docs/iterations/iteration-002/
  development.md
  plan.md
  verification.md
  review.md
```

如 Plan 发现无需修改某个文件，必须说明原因。不得因为迭代二顺手重构其他模块。

## 四、核心模块

### schemas.candidates

职责：

```text
定义 Candidate 最小协议。
校验候选是否包含 id、title、summary、metadata。
保留 url、source 作为推荐字段。
保留 metadata 为开放对象。
返回规范化候选和字段缺失信息。
```

不得做：

```text
搜索候选。
从 Hermes 工具结果抽取候选。
根据 title/url 自动伪造已满足协议的真实候选。
```

### core.ranker

职责：

```text
接收已规范化的 candidates。
在候选为空、数量不足、缺少必填字段、缺少 summary 时返回降级结果。
对满足协议的真实 candidates 计算 query_relevance、preference_fit、feedback_score、final_score。
返回 ranked_candidates、reasons、risks。
```

不得做：

```text
写 profile。
处理 record_feedback。
调用搜索或外部工具。
把 fixed_probe_candidates 当真实候选来源。
```

### tools.rank_candidates

职责：

```text
暴露 mcp_tastemate_rank_candidates。
读取 profile。
调用 Ranker。
保持输入输出为结构化 JSON。
```

不得做：

```text
补全候选。
生成候选。
修改 Hermes 配置。
```

### tastemate-route 插件

职责：

```text
保留迭代一 @taste -> fixed_probe_candidates -> rewrite 回归路径。
在日志中继续标注 candidate_source=fixed_probe_candidates。
```

不得做：

```text
冒充真实候选主路径。
声称 fixed_probe_candidates 来自 Hermes 搜索结果。
实现 observed_tool_candidates。
```

## 五、接口约定

### rank_candidates 输入

```json
{
  "query": "@taste 推荐适合个人开发者优先尝试的 AI agent 框架",
  "taste_mode": "force",
  "candidates": [
    {
      "id": "smolagents",
      "title": "Smolagents",
      "summary": "Hugging Face 的轻量 agent 框架，适合本地和实验型 agent。",
      "metadata": {
        "language": "Python",
        "open_source": true,
        "complexity": "Very Low",
        "best_for": "Minimal setups and research experiments"
      },
      "url": "https://github.com/huggingface/smolagents",
      "source": "github"
    }
  ]
}
```

字段约束：

```text
query：必填，字符串。
taste_mode：可选，迭代二继续使用 force。
candidates：必填，数组，可为空。
candidate.id：必填，非空字符串。
candidate.title：必填，非空字符串。
candidate.summary：必填，非空字符串。
candidate.metadata：必填，对象，可以为空对象。
candidate.url：推荐字段，缺失不阻塞验收。
candidate.source：推荐字段，缺失不阻塞验收。
```

### rank_candidates 输出：排序成功

```json
{
  "ranking_needed": true,
  "mode": "recommendation",
  "action": "ranked",
  "ranked_candidates": [
    {
      "id": "smolagents",
      "title": "Smolagents",
      "final_score": 0.7025,
      "query_relevance": 0.65,
      "preference_fit": 0.9,
      "feedback_score": 0.5,
      "reasons": ["符合开源偏好", "符合本地优先偏好"],
      "risks": []
    }
  ]
}
```

### rank_candidates 输出：候选缺少必填字段

```json
{
  "ranking_needed": true,
  "mode": "recommendation",
  "action": "invalid_candidates",
  "reason": "候选缺少必填字段，无法按真实候选协议排序",
  "missing_fields": [
    {
      "candidate_index": 0,
      "fields": ["id", "metadata"]
    }
  ],
  "ranked_candidates": [],
  "risks": ["候选字段不足"]
}
```

如果实现阶段复用 `low_confidence` 作为等价降级结果，Plan 必须明确映射关系，并保证 Hermes 不伪造已完成排序。

### rank_candidates 输出：候选不足

```json
{
  "ranking_needed": true,
  "mode": "recommendation",
  "action": "needs_more_candidates",
  "reason": "候选数量不足或缺少关键方向",
  "suggested_search_hints": []
}
```

### rank_candidates 输出：事实类或无候选 passthrough

```json
{
  "ranking_needed": false,
  "mode": "factual",
  "action": "passthrough",
  "reason": "确定性事实问题或没有可排序候选集合"
}
```

## 六、配置说明

迭代二不新增配置项。

继续使用已有环境变量：

```text
TASTEMATE_PROFILE_PATH
```

继续使用已有 Hermes MCP 配置方式。不得要求用户修改 Hermes 源码。

## 七、数据结构

### Candidate

```json
{
  "id": "candidate-id",
  "title": "候选标题",
  "summary": "候选摘要",
  "metadata": {},
  "url": "https://example.com",
  "source": "github"
}
```

### CandidateValidationResult

实现可使用等价结构，但必须能表达：

```json
{
  "valid_candidates": [],
  "invalid_candidates": [
    {
      "candidate_index": 0,
      "candidate_id": null,
      "missing_fields": ["id", "metadata"]
    }
  ]
}
```

## 八、错误处理

### candidates 为空

```text
返回 passthrough 或 needs_more_candidates。
Hermes 不伪造排序结果。
```

### candidates 少于 2 个

```text
返回 needs_more_candidates。
Hermes 说明候选不足。
```

### candidate 缺少 summary

```text
返回 low_confidence 或 invalid_candidates。
Hermes 说明候选信息不足。
```

### candidate 缺少 id、title 或 metadata

```text
返回 invalid_candidates 或等价降级结果。
结果必须包含缺失字段信息。
Hermes 不伪造 TasteMate 排序结果。
```

### Hermes 未调用 TasteMate

```text
验收失败。
最终回复不得声称 TasteMate 已完成排序。
```

## 九、测试策略

### A-001 用户给候选

测试方式：

```text
本地单元测试覆盖 rank_candidates 对真实 candidates 排序。
手工或集成验证覆盖 Hermes 调用 mcp_tastemate_rank_candidates，参数 candidates 来自用户给定候选。
```

必须验证：

```text
工具调用出现 mcp_tastemate_rank_candidates completed 或等价成功证据。
工具返回结构被 Hermes 接收，action 为 ranked 或明确降级 action。
candidates 为用户给定候选。
每个 candidate 包含 id、title、summary、metadata。
url、source 缺失不阻塞排序。
没有新增 fixed_probe_candidates 主路径记录。
最终回复不得在工具调用失败或未收到排序结果时声称 TasteMate 已排序。
```

### A-002 Hermes 基于已有知识生成候选

测试方式：

```text
手工或集成验证发送 @taste 推荐类问题。
检查工具调用日志和 candidates 参数。
```

必须验证：

```text
Hermes 调用 mcp_tastemate_rank_candidates，并出现 completed 或等价成功证据。
工具返回结构被 Hermes 接收，action 为 ranked 或明确降级 action。
candidates 是 3-5 个真实候选。
每个 candidate 包含 id、title、summary、metadata。
Hermes 不是只生成普通推荐报告。
最终回复不得在工具调用失败或未收到排序结果时声称 TasteMate 已排序。
```

### A-003 fixed_probe_candidates 退出主路径

测试方式：

```text
检查 tastemate-route 日志和工具调用参数。
保留迭代一插件测试作为回归，但不得把它作为迭代二真实候选验收。
```

必须验证：

```text
真实候选验收中没有新增 candidate_source=fixed_probe_candidates 主路径记录。
fixed_probe_candidates 只出现在迭代一回归或插件通道测试中。
```

### A-004 候选最小协议校验

测试方式：

```text
单元测试传入缺少 id、title、summary 或 metadata 的候选。
集成测试或手工验证检查 Hermes 不伪造已完成排序。
```

必须验证：

```text
缺少必填字段时返回 invalid_candidates、low_confidence 或等价降级结果。
降级结果包含缺失字段信息。
ranked_candidates 为空或不被当作成功排序。
```

### 失败路径覆盖

Development Spec 和 Build 必须覆盖：

```text
candidates 为空。
candidates 少于 2 个。
事实类问题 passthrough。
candidate 缺少 summary。
candidate 缺少 id。
candidate 缺少 title。
candidate 缺少 metadata。
Hermes 未调用 TasteMate。
TasteMate 降级后 Hermes 不伪造排序结果。
```

### passthrough 路径

测试方式：

```text
单元测试或集成/手工验证输入事实类 @taste 问题，例如 @taste Hermes 的 MCP 配置文件在哪？
```

必须验证：

```text
TasteMate 返回 action=passthrough。
ranking_needed=false。
Hermes 不声称 TasteMate 已完成候选排序。
```

## 十、本地运行方式

```bash
python -m pytest tests/test_rank_candidates.py -q
python -m pytest tests/test_server_tools.py -q
python -m pytest tests/test_hermes_route_plugin.py -q
python -m pytest -q
```

如需要手工验证 Hermes 真实入口，Plan 必须写明命令、输入、日志位置和通过条件。

## 十一、禁止事项

```text
禁止修改 Hermes 源码。
禁止把 fixed_probe_candidates 写成真实候选能力。
禁止实现 observed_tool_candidates。
禁止从 Hermes 工具结果自动抽取候选。
禁止实现搜索前偏好注入。
禁止扩展 feedback 画像沉淀。
禁止接入 Obsidian。
禁止把普通推荐报告当作 TasteMate 排序验收。
禁止在未调用 mcp_tastemate_rank_candidates 时声称 TasteMate 已排序。
```
