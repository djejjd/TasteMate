# Iteration 003 Development Spec：反馈画像增强与有限排序生效

## 适用阶段

```text
Development Spec
```

本文件在 Iteration 003 Design 通过后、Plan 之前编写，用于约束后续开发计划和实现。

本文件不是代码实现，也不是开发计划。后续 `plan.md` 必须引用本文件。

## 一、开发原则

迭代三只解决本地可验证闭环内的反馈画像增强：

```text
record_feedback 继续沿用现有输入协议。
有效或可归档的 feedback 先写 evidence_log；完全 invalid 的 feedback 不写 evidence_log。
长期画像只允许受控 feature 白名单进入。
rank_candidates 在现有相关性排序上应用有限、可解释的画像修正。
get_profile 必须能解释画像来源、证据数量和当前状态。
本轮阻塞验收只收本地闭环，不把远端 feedback/evidence 主路径纳入阻塞范围。
```

当前阶段禁止实现：

```text
Hermes 源码修改。
远端 feedback/evidence 主路径验收。
搜索前偏好注入。
observed_tool_candidates。
Obsidian 偏好底座。
开放式自由文本 feature 升级。
复杂衰减模型。
高级冲突求解。
UI、多用户、人工编辑画像界面。
```

## 二、技术形态

TasteMate 继续作为本地 stdio MCP server 运行。

迭代三只增强本地 feedback、profile、ranker 和 get_profile 逻辑，不修改 Hermes 侧输入协议：

```text
Hermes -> mcp_tastemate_record_feedback -> FeedbackProcessor -> profile.json
Hermes -> mcp_tastemate_rank_candidates -> Ranker -> 读取 profile.json
Hermes -> mcp_tastemate_get_profile -> Profile Summary
```

远端 Hermes 侧 `feedback/evidence` 主路径不进入本轮阻塞验收；如需验证，必须单独形成验证记录。

## 三、目录结构

迭代三预计影响范围：

```text
tastemate/
  core/
    feedback.py
    ranker.py
    scoring.py
  tools/
    record_feedback.py
    get_profile.py
    rank_candidates.py
  storage/
    json_store.py
tests/
  test_record_feedback.py
  test_rank_candidates.py
  test_get_profile.py
docs/iterations/iteration-003/
  development.md
  plan.md
  verification.md
  review.md
```

如 Plan 发现无需修改某个文件，必须说明原因。不得因为迭代三顺手重构无关模块。

## 四、核心模块

### core.feedback

职责：

```text
接收现有 feedback 输入协议。
将反馈分类为 strong_positive、strong_negative、normal_positive、normal_negative、invalid。
先写 evidence_log，再从候选快照和反馈文本中抽取白名单 feature。
按升级规则写入 stable_preferences、negative_preferences、current_focus。
保持白名单外 feature 只留在 evidence_log。
```

不得做：

```text
修改 Hermes 输入协议。
引入模型调用或外部分类器。
对开放式自由文本做长期画像升级。
执行复杂冲突求解。
```

### storage.json_store

职责：

```text
读取和写回 profile.json。
兼容旧 profile 缺少 stable_preferences、negative_preferences、current_focus 等字段的情况。
为新增字段补齐默认结构。
保留 evidence_log 历史记录。
```

不得做：

```text
引入 SQLite 或其他新存储。
因为旧 schema 缺字段而直接失败。
在存储层决定排序逻辑。
```

### core.ranker

职责：

```text
继续计算 query_relevance、preference_fit、feedback_score 等基础信号。
读取 stable_preferences、negative_preferences、current_focus。
仅对相关候选做有限画像修正。
输出 ranked_candidates、reasons、risks。
当未命中画像或画像无效时，退化为现有基础排序逻辑。
```

不得做：

```text
把画像修正变成排序唯一依据。
让明显低相关候选仅凭画像反超高相关候选。
写 profile。
处理 record_feedback 持久化。
```

### core.scoring

职责：

```text
承载画像相关的加减分规则。
区分 stable_preferences、negative_preferences、current_focus 的权重层级。
为 ranker 提供可解释分数构成。
```

不得做：

```text
混入 profile 持久化。
引入当前迭代不需要的复杂时序衰减。
```

### tools.record_feedback

职责：

```text
暴露 mcp_tastemate_record_feedback。
保持输入协议兼容。
返回结构化处理结果，包括 feedback 类型、命中特征、是否发生升级和写入摘要。
```

不得做：

```text
要求调用方新增必填字段。
把无效反馈伪装成已升级长期偏好。
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
生成候选。
修改 Hermes 配置。
把画像增强写成搜索前偏好注入。
```

### tools.get_profile

职责：

```text
暴露 mcp_tastemate_get_profile。
汇总长期正向偏好、长期负向偏好、当前关注、证据数量和来源摘要。
对旧 schema 返回兼容降级结构。
```

不得做：

```text
修改画像。
省略来源和证据数量解释。
```

## 五、接口约定

### record_feedback 输入

继续沿用现有输入协议，不新增必填字段：

```json
{
  "query": "@taste 推荐适合我长期使用的本地知识库工具",
  "user_feedback": "我明确更喜欢本地优先、开源的工具，这个方向以后优先。",
  "selected_candidate_ids": ["obsidian-local"],
  "rejected_candidate_ids": ["hosted-only"],
  "candidates_snapshot": [
    {
      "id": "obsidian-local",
      "title": "Obsidian Local Stack",
      "summary": "本地优先、可离线使用的知识库工具组合。",
      "metadata": {
        "features": ["local_first", "open_source"]
      }
    }
  ]
}
```

字段约束：

```text
query：必填，字符串。
user_feedback：必填，字符串，可为空字符串但会影响有效性判定。
selected_candidate_ids：可选，字符串数组。
rejected_candidate_ids：可选，字符串数组。
candidates_snapshot：可选，数组；若存在，其元素结构沿用当前候选协议。
```

### record_feedback 输出

```json
{
  "feedback_valid": true,
  "signal_strength": 0.9,
  "extracted_signals": ["local_first", "open_source"],
  "profile_updates": [
    "stable_preferences.local_first upsert",
    "stable_preferences.open_source upsert",
    "current_focus.local_first upsert"
  ],
  "accepted": true,
  "feedback_type": "strong_positive",
  "applied_features": ["local_first", "open_source"],
  "profile_update_details": {
    "stable_preferences": ["local_first", "open_source"],
    "negative_preferences": [],
    "current_focus": ["local_first", "open_source"]
  },
  "evidence_written": true,
  "reason": "强显式正向反馈命中白名单特征，已升级长期偏好"
}
```

输出约束：

```text
feedback_valid、signal_strength、extracted_signals 必须继续保留，供旧调用方兼容使用。
feedback_type 只能是 strong_positive、strong_negative、normal_positive、normal_negative、invalid。
applied_features 只包含白名单特征。
invalid 时不得声称已升级长期画像。
profile_updates 继续保留旧的数组摘要；如需结构化详情，应新增独立字段，例如 profile_update_details。
```

### rank_candidates 输入

迭代三保持现有输入兼容：

```json
{
  "query": "@taste 推荐适合我长期使用的本地知识库工具",
  "taste_mode": "force",
  "candidates": [
    {
      "id": "obsidian-local",
      "title": "Obsidian Local Stack",
      "summary": "本地优先、可离线使用的知识库工具组合。",
      "metadata": {
        "features": ["local_first", "open_source"]
      }
    }
  ]
}
```

本轮不新增输入字段；画像增强仅发生在内部评分逻辑。

### rank_candidates 输出：排序成功

```json
{
  "ranking_needed": true,
  "mode": "recommendation",
  "action": "ranked",
  "ranked_candidates": [
    {
      "id": "obsidian-local",
      "title": "Obsidian Local Stack",
      "final_score": 0.76,
      "query_relevance": 0.66,
      "preference_fit": 0.82,
      "feedback_score": 0.45,
      "reasons": [
        "命中长期正向偏好: local_first",
        "命中当前关注: open_source"
      ],
      "risks": []
    }
  ]
}
```

输出约束：

```text
reasons 必须能区分长期正向、长期负向或当前关注。
未命中画像时不得伪造画像相关 reasons。
当前关注只能表现为轻量修正，不得替代 query_relevance 主导。
```

### get_profile 输出

`get_profile` 可以做兼容扩展，但不能改变已有字段语义或基础类型：

```json
{
  "stable_preferences": {
    "local_first": {
      "feature": "local_first",
      "label": "本地优先",
      "strength": "strong",
      "evidence_count": 2,
      "source": "feedback",
      "last_updated": "2026-06-08T12:00:00Z"
    }
  },
  "negative_preferences": {
    "hosted_only": {
      "feature": "hosted_only",
      "label": "纯托管方案",
      "strength": "normal",
      "evidence_count": 2,
      "source": "feedback",
      "last_updated": "2026-06-08T12:05:00Z"
    }
  },
  "current_focus": {
    "open_source": {
      "feature": "open_source",
      "label": "开源优先",
      "evidence_count": 1,
      "last_updated": "2026-06-08T12:00:00Z"
    }
  },
  "evidence_summary": {
    "total_count": 6
  },
  "summary": "当前偏好摘要"
}
```

兼容要求：

```text
stable_preferences、negative_preferences、current_focus 继续保持对象形态。
旧调用方即使忽略新增字段，也不能影响旧行为。
缺字段 profile 读取时，必须返回可用的默认空结构。
```

## 六、配置说明

迭代三不新增必需配置项。

如果实现阶段需要白名单配置，Plan 必须明确采用以下两种之一：

```text
方案 A：代码内固定白名单常量。
方案 B：项目内本地配置文件，但默认随仓库提供安全默认值。
```

本轮不得引入依赖远端环境的动态配置中心。

## 七、数据结构

profile.json 在迭代三至少应兼容以下结构：

```json
{
  "stable_preferences": {
    "local_first": {
      "feature": "local_first",
      "label": "本地优先",
      "strength": "strong",
      "evidence_count": 2,
      "source": "feedback",
      "last_updated": "2026-06-08T12:00:00Z"
    }
  },
  "negative_preferences": {
    "hosted_only": {
      "feature": "hosted_only",
      "label": "纯托管方案",
      "strength": "normal",
      "evidence_count": 2,
      "source": "feedback",
      "last_updated": "2026-06-08T12:05:00Z"
    }
  },
  "current_focus": {
    "open_source": {
      "feature": "open_source",
      "label": "开源优先",
      "evidence_count": 1,
      "last_updated": "2026-06-08T12:00:00Z"
    }
  },
  "evidence_log": []
}
```

升级规则必须写死为可测行为：

```text
strong_positive：命中白名单特征后，1 次即可写入 stable_preferences。
strong_negative：命中白名单特征后，1 次即可写入 negative_preferences。
normal_positive：同一白名单特征累计 2 次同向证据后，写入 stable_preferences。
normal_negative：同一白名单特征累计 2 次同向证据后，写入 negative_preferences。
invalid：不得污染 stable_preferences、negative_preferences、current_focus。
白名单外特征：只保留在 evidence_log，不得升级为长期画像。
```

排序权重约束：

```text
stable_preferences 权重高于 current_focus。
negative_preferences 为显式减分，但不能让完全不相关候选仅凭画像因素主导排序。
current_focus 只做轻量修正，避免一次短期任务污染长期偏好。
```

## 八、错误处理

```text
profile 缺字段：按空集合处理，并在写回时补齐默认结构。
evidence_log 存在脏数据：跳过无法识别项，不得污染长期画像。
无法抽取白名单 feature：允许只写 evidence_log，不升级长期画像。
feedback_type=invalid：不得写入 stable_preferences、negative_preferences、current_focus。
候选未命中任何画像 feature：退化为现有基础排序逻辑，不伪造画像 reasons。
正负偏好同时命中：按当前简单规则执行，并在 reasons 中可解释；不做复杂冲突求解。
get_profile 读取异常或旧 schema 不完整：返回兼容降级结构，不让调用方崩溃。
```

## 九、测试策略

阻塞验收标准以本地闭环证明，不以远端链路为前提。

```text
A-001 强显式反馈可一次升级 -> 单元测试固定样例验证 strong_positive / strong_negative 1 次升级。
A-002 普通反馈需两次同向升级 -> 单元测试验证第 1 次不升级、第 2 次升级。
A-003 白名单外 feature 不污染长期画像 -> 单元测试验证只写 evidence_log。
A-004 长期正向偏好会对后续排序产生有限正向影响 -> 排序测试验证相关候选前移。
A-005 长期负向偏好会对后续排序产生有限负向影响 -> 排序测试验证相关候选后移。
A-006 current_focus 只做轻量修正，不替代相关性主导 -> 排序测试验证低相关候选不会异常反超。
A-007 get_profile 能解释偏好来源、证据数和当前状态 -> get_profile 测试验证结构化摘要。
A-008 不修改 Hermes 输入协议，不修改 Hermes 源码 -> 文档和实现审查确认接口兼容，代码影响范围不进入 Hermes 源码。
A-009 固定候选集下反馈前后排序变化符合指定样例 -> 本地样例测试验证 local-first 候选前移、cloud-required 候选后移。
A-010 单次反馈不会把长期画像推得过高 -> profile 阈值测试验证 weight、confidence、单次增量不超过 design.md 规定阈值。
```

至少覆盖以下测试类型：

```text
record_feedback 规则测试。
invalid feedback 不写 evidence_log / stable_preferences / negative_preferences / current_focus 的失败路径测试。
旧 profile schema 兼容读写测试。
rank_candidates 排序前后变化测试。
rank_candidates 未命中画像时的退化测试。
单次 strong feedback 的长期画像阈值测试。
get_profile 输出兼容与解释测试。
```

## 十、本地运行方式

Plan 阶段应在项目实际结构基础上确认最终命令；迭代三本地验证至少需要覆盖：

```bash
python -m pytest tests/test_record_feedback.py -q
python -m pytest tests/test_rank_candidates.py -q
python -m pytest tests/test_get_profile.py -q
python -m pytest -q
```

如 `test_get_profile.py` 最终并入其他测试文件，Plan 必须更新命令和原因。

## 十一、禁止事项

```text
禁止修改 Hermes 源码。
禁止把远端 feedback/evidence 主路径写成本轮已完成能力。
禁止开放白名单外 feature 直接升级为长期画像。
禁止把 current_focus 当长期稳定偏好使用。
禁止让画像修正掩盖 query_relevance 主导。
禁止未命中画像却伪造画像 reasons。
禁止以复杂衰减、复杂冲突求解或新基础设施扩大本轮范围。
禁止顺手重构无关模块。
```
