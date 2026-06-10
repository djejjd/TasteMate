# TasteMate 开发文档

> 本文件是项目级开发基线，主要描述第一阶段到迭代二之间的通用约束与早期接口草案。
> 当具体迭代目录下存在 `development.md` 时，以迭代级 Development Spec 作为当前 Plan 的直接约束；项目级文档只保留通用原则和历史基线，不再与当前迭代形成并列冲突口径。

## 一、开发原则

第一阶段开发以验证闭环为目标：

```text
显式启用
候选重排
可解释评分
反馈学习
本地持久化
不改 Hermes 源码
```

暂不实现复杂推荐算法、自动搜索前注入、Web UI、多用户能力。

---

## 二、建议技术形态

TasteMate 第一版作为本地 MCP server。

建议能力：

```text
stdio MCP server
本地 profile store
rank_candidates 工具
record_feedback 工具
get_profile 工具
```

Hermes 通过 `~/.hermes/config.yaml` 接入：

```yaml
mcp_servers:
  tastemate:
    command: "python"
    args: ["-m", "tastemate.server"]
    timeout: 120
```

具体命令可在实现阶段根据项目结构调整。

---

## 三、目录建议

后续进入代码阶段时，可以考虑：

```text
tastemate/
  server.py
  tools/
    rank_candidates.py
    record_feedback.py
    get_profile.py
  core/
    ranker.py
    feedback.py
    profile.py
    scoring.py
  storage/
    json_store.py
    sqlite_store.py   # 后续可选，不是当前默认实现
  llm/
    client.py         # 后续可选，不是当前默认实现
    prompts.py        # 后续可选，不是当前默认实现
  schemas/
    candidates.py
    feedback.py
    profile.py
tests/
  test_rank_candidates.py
  test_record_feedback.py
  test_profile_store.py
```

第一版可以先用 JSON 文件持久化，等字段稳定后再迁移 SQLite。
当前迭代若无明确批准，不应把 `sqlite_store.py`、`llm/*` 或真实 LLM 评分作为默认实现边界。

---

## 四、MCP 工具接口

### rank_candidates

输入：

```json
{
  "query": "用户问题",
  "candidates": [
    {
      "id": "candidate-1",
      "title": "候选标题",
      "summary": "候选摘要",
      "url": "https://example.com",
      "metadata": {}
    }
  ],
  "taste_mode": "force"
}
```

输出：

```json
{
  "ranking_needed": true,
  "action": "ranked",
  "ranked_candidates": [],
  "notes": []
}
```

如果不需要排序：

```json
{
  "ranking_needed": false,
  "action": "passthrough",
  "reason": "确定性事实问题"
}
```

### record_feedback

输入：

```json
{
  "query": "上一轮问题",
  "user_feedback": "用户后续反馈",
  "selected_candidate_ids": [],
  "rejected_candidate_ids": [],
  "candidates_snapshot": []
}
```

输出：

```json
{
  "feedback_valid": true,
  "signal_strength": 0.7,
  "extracted_signals": [],
  "profile_updates": [],
  "summary": "本次反馈处理摘要"
}
```

后续迭代如需增强输出，只能在保留 `feedback_valid / signal_strength / extracted_signals / profile_updates` 基础语义的前提下追加字段。

### get_profile

输入：

```json
{}
```

输出：

```json
{
  "stable_preferences": {},
  "negative_preferences": {},
  "current_focus": {},
  "summary": "当前偏好摘要"
}
```

后续迭代可在对象值中追加更细的证据和来源字段，但不应把这三个顶层字段从对象改成其他基础类型。

---

## 五、评分实现细节

第一版评分分两部分：

```text
规则评分
LLM 语义评分
```

说明：

```text
这里描述的是早期可选演进方向，不是当前每个迭代都必须实现的默认路径。
若某个迭代级 Development Spec 明确限定“只做规则逻辑、不接真实 LLM”，则以迭代级文档为准。
```

规则评分可先实现：

```text
open_source
local_first
plugin_friendly
cloud_required
enterprise_oriented
last_updated
license
```

LLM 评分一次性输出：

```text
ranking_needed
query_relevance
preference_fit
reason
risk
```

避免拆成多次模型调用。

---

## 六、反馈学习实现细节

偏好更新不要直接覆盖画像，而是先写 evidence。

建议写入：

```json
{
  "timestamp": "...",
  "event_type": "selected",
  "query": "...",
  "candidate_id": "...",
  "feature": "local_first",
  "direction": "positive",
  "strength": 0.6,
  "source": "explicit_user_feedback"
}
```

画像权重从 evidence 聚合而来。

第一版可以即时更新，后续可改为批处理：

```text
record_feedback 写 evidence_log
profile updater 根据 evidence_log 计算权重
```

权重更新要保守：

```text
强反馈 learning_rate = 0.10
中反馈 learning_rate = 0.04
弱反馈 learning_rate = 0.01
```

---

## 七、测试重点

第一阶段至少覆盖：

```text
无候选时 rank_candidates 返回 passthrough
事实问题返回 ranking_needed=false
推荐问题返回 ranking_needed=true
相关性低的候选不能因偏好高排到前面
明确反馈能生成 evidence
一次反馈不会大幅改变 stable preference
profile store 能读写和恢复
```

Hermes 集成测试可先手工验证：

```text
Hermes 能发现 mcp_tastemate_rank_candidates
Hermes 能把候选传入 TasteMate
TasteMate 返回结构化结果
Hermes 能基于结果生成回答
```

---

## 八、暂不开发项

第一阶段不做：

```text
Hermes 源码改动
Hermes plugin 自动编排
搜索前偏好注入
UI
多用户系统
复杂推荐模型训练
全量内容采集
```
