# CLAUDE.md

本文件为 Claude Code（claude.ai/code）在此仓库中工作时提供指引。

## 项目概览

TasteMate 是一个本地 MCP server，为 Hermes（AI 助手）提供外置个人偏好层。用户显式使用 `@taste` 时，TasteMate 通过规则评分系统对 Hermes 的候选结果做后置重排，并将用户反馈记录为持久化偏好画像。

当前阶段：迭代一已完成（固定候选穿刺验证），迭代二进行中（真实候选排序）。

## 核心约束

**不修改 Hermes 源码。** TasteMate 是外部 MCP server 和 Hermes 插件，不触碰 Hermes 内部。

## 常用命令

```bash
python -m pip install -e '.[dev]'   # 安装及开发依赖
python -m pytest -q                  # 运行全部测试
python -m tastemate.server           # 启动 MCP server（stdio）
```

测试框架为 pytest，配置文件在 `pyproject.toml`（`[tool.pytest.ini_options]`）。

## 架构

```
tastemate/
  server.py              # FastMCP 入口 — 定义 3 个工具，薄封装
  tools/                 # 工具实现：加载 profile → 调用 core → 持久化
    rank_candidates.py   #   从 ~/.tastemate/profile.json 读取画像
    record_feedback.py   #   读取画像，经 FeedbackProcessor 修改后保存
    get_profile.py       #   读取画像，返回摘要
  core/                  # 纯逻辑，无 I/O
    ranker.py            #   Ranker：分类查询（事实 vs 推荐），评分候选
                         #     （0.55×相关性 + 0.30×偏好匹配 + 0.15×反馈）
    scoring.py           #   无状态评分函数：query_relevance、preference_fit、feedback_score
    feedback.py          #   FeedbackProcessor：从选择/拒绝中抽取特征，写入 evidence_log
    profile.py           #   summarize_profile：画像转可读字符串
  schemas/               # 数据规范化与校验
    candidates.py        #   normalize_candidate：SHA256 生成稳定 ID，字段默认值
    feedback.py          #   make_evidence、now_iso
    profile.py           #   default_profile、normalize_profile
  storage/
    json_store.py        #   JsonProfileStore：加载/保存 ~/.tastemate/profile.json
integrations/hermes/plugins/tastemate-route/
  __init__.py            #   Hermes 插件：pre_gateway_dispatch hook
                         #   检测 @taste + 推荐标记，调用 mcp_tastemate_rank_candidates，
                         #   用排序结果改写 gateway 文本
  plugin.yaml            #   插件清单
tests/                   # pytest 测试，覆盖工具和 Hermes 插件
```

### 数据流

1. 用户发送含 `@taste` 的消息 → Hermes `pre_gateway_dispatch` hook 触发
2. 插件检测 `@taste` + 推荐标记 → 匹配则调用 `mcp_tastemate_rank_candidates`
3. `Ranker.rank()` 分类查询、评分候选，返回排序结果（或 passthrough / needs_more_candidates / low_confidence）
4. 插件用排序结果改写 gateway 文本，Hermes 据此回复用户
5. 用户反馈（选择/拒绝）时，`mcp_tastemate_record_feedback` 将 evidence 写入画像

### 评分公式

```
final_score = query_relevance × 0.55 + preference_fit × 0.30 + feedback_score × 0.15
```

所有分数截断至 [0, 1]。相关性作为门槛：低于 0.35 时，preference_fit 上限为 0.35。

### Profile 存储

`~/.tastemate/profile.json`（可通过 `TASTEMATE_PROFILE_PATH` 环境变量覆盖）。结构：

```json
{
  "stable_preferences": {},
  "negative_preferences": {},
  "current_focus": {},
  "evidence_log": []
}
```

### 关键设计决策

- **规则评分，非 LLM。** 评分使用关键词匹配和 metadata 标记（`open_source`、`local_first`、`supports_mcp`、`cloud_required`、`enterprise_oriented`）。LLM 是后续允许的增强方向，当前实现不依赖 LLM。
- **保守的反馈更新。** 单次反馈权重上限很小（最大 delta 0.10），且 `_conservatively_update_existing_stable_preference` 只调整已存在的偏好，不会从单次反馈创建新偏好。
- **事实问题旁路。** 包含事实标记（在哪、是什么、配置文件等）且不含推荐标记的查询，直接跳过排序。
- **候选必须有 summary。** 缺少 `summary` 字段的候选返回 `low_confidence` 结果。

## 项目技能

项目在 `.claude/skills/` 下有 3 个自定义技能，在特定阶段由 Agent 按需激活：

| 技能 | 激活阶段 | 触发条件 |
|---|---|---|
| `idea-refine` | Intake 前 | 需求模糊、范围不清、多方案需要权衡；功能请求缺乏具体范围 |
| `doubt-driven-development` | Build / Design | 修改评分公式、profile 结构、feedback 逻辑、Hermes 插件边界；任何不可逆变更或跨模块决策 |
| `security-and-hardening` | Verify 前 | 修改 tool 参数处理、文件 I/O、依赖变更、profile 存储结构变更 |

### 与工作流的对应关系

```
idea-refine          → 需求精炼完成 → Intake
doubt-driven-dev     → 高风险决策经对抗性审查 → Design / Build
security-and-hardening → 安全检查清单通过 → Verify
```

技能文件位于：
- `.claude/skills/idea-refine/SKILL.md`
- `.claude/skills/doubt-driven-development/SKILL.md`
- `.claude/skills/security-and-hardening/SKILL.md`

## 开发工作流

所有开发遵循：Intake → Discovery → Design → Development Spec → Plan → Build → Verify → Multi-Agent Review → Closeout。

每个迭代的文档位于 `docs/iterations/iteration-<n>/`。当前迭代文档在 `docs/iterations/iteration-002/`。

关键规则：
- 不得扩大当前迭代范围。
- 不得顺手重构无关模块。
- 文档中文优先，先结论后细节。
- 迭代关闭前必须完成多 agent 审核——每个审核角色有严格边界，只能输出 PASS、BLOCK 或 FOLLOW_UP。

完整工作流见 `docs/process/workflow.md`，项目级 agent 规则见 `AGENTS.md`。
