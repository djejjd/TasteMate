# Iteration 002 验证记录

## 适用阶段

```text
Build / Verify
```

## 一、验证目标

```text
1. 真实 candidates 排序四类输出：passthrough / invalid_candidates / needs_more_candidates / ranked。
2. candidates 最小协议校验（id/title/summary/metadata）。
3. fixed_probe_candidates 只出现在插件回归路径，不作为真实候选主路径。
4. 已有迭代一功能不受影响。
```

## 二、本地验证

### 测试命令

```bash
python -m pytest tests/test_rank_candidates.py -q
python -m pytest tests/test_server_tools.py -q
python -m pytest tests/test_hermes_route_plugin.py -q
python -m pytest -q
```

### Developer Agent 提交结果

```text
tests/test_rank_candidates.py: 14 passed
tests/test_server_tools.py: 4 passed
tests/test_hermes_route_plugin.py: 9 passed
全量: 32 passed
```

### 主 agent 复验结果

```text
首次复验误用外层 pyenv Python 3.10.14，导致当前环境未安装 mcp，出现 ModuleNotFoundError。
切换到项目隔离环境后，主 agent 复验结果如下：

.venv/bin/python -m pytest tests/test_rank_candidates.py -q -> 14 passed
.venv/bin/python -m pytest tests/test_server_tools.py -q -> 4 passed
.venv/bin/python -m pytest tests/test_hermes_route_plugin.py -q -> 9 passed
.venv/bin/python -m pytest -q -> 32 passed

隔离环境信息：
.venv/bin/python -> Python 3.13.12
.venv/bin/python -c "import mcp; print(mcp.__file__)" -> import 成功
```

### 四类输出覆盖

| 测试 | 场景 | action | 状态 |
|---|---|---|---|
| `test_ranker_returns_passthrough_for_empty_candidates` | candidates 为空 | passthrough | PASS |
| `test_rank_candidates_passthrough_for_factual_question` | 事实类问题（无 @taste） | passthrough | PASS |
| `test_rank_candidates_passthrough_for_taste_factual_question` | 事实类问题（有 @taste） | passthrough | PASS |
| `test_ranker_returns_invalid_candidates_for_missing_metadata` | candidate 缺少 metadata | invalid_candidates | PASS |
| `test_ranker_returns_invalid_candidates_for_missing_summary` | candidate 缺少 summary | invalid_candidates | PASS |
| `test_rank_candidates_low_confidence_schema_for_missing_summaries` | 多个 candidate 缺少 summary | invalid_candidates | PASS |
| `test_ranker_returns_needs_more_candidates_for_single_valid_candidate` | 仅 1 个有效候选 | needs_more_candidates | PASS |
| `test_rank_candidates_needs_more_candidates_for_single_recommendation_candidate` | 仅 1 个有效候选（带 metadata） | needs_more_candidates | PASS |
| `test_ranker_returns_ranked_for_valid_candidates` | 2 个有效候选 | ranked | PASS |
| `test_rank_candidates_ranked_schema_for_recommendation_candidates` | 2 个有效候选含评分 | ranked | PASS |

### 固定映射验证

```text
事实类 query 或 candidates 为空 -> passthrough: PASS
缺少 id/title/summary/metadata -> invalid_candidates: PASS
有效候选少于 2 个 -> needs_more_candidates: PASS
候选满足协议且数量足够 -> ranked: PASS
```

### Hermes 插件回归边界

```text
test_operation_log_marks_fixed_probe_candidates_only_for_plugin_regression: PASS
candidate_source=fixed_probe_candidates 标记已记录。
```

### 迭代一已有功能回归

```text
test_rank_candidates_feedback_score_uses_feature_evidence_for_new_candidates: PASS
test_get_profile_tool_returns_summary: PASS
test_record_feedback_tool_persists_evidence: PASS
test_server_exports_mcp_app: PASS
test_operation_log_records_matched_route: PASS
test_needs_more_candidates_rewrite_does_not_fake_ranking: PASS
test_unknown_tool_fails_open: PASS
test_dispatch_exception_fails_open: PASS
```

## 三、远端验证

本阶段由主 agent 复验远端 Hermes 基础状态、插件入口、CLI 主路径与 A-001 / A-002 验收证据。

主 agent 实际执行命令：

```bash
ssh -o BatchMode=yes -o ConnectTimeout=8 ubuntu@124.223.102.241 'docker ps --format "{{.Names}}\t{{.Status}}" | grep ^hermes'
ssh -o BatchMode=yes -o ConnectTimeout=8 ubuntu@124.223.102.241 'docker exec hermes sh -lc "grep -nA3 ^plugins: /opt/data/config.yaml"'
ssh -o BatchMode=yes -o ConnectTimeout=8 ubuntu@124.223.102.241 'docker exec hermes sh -lc "cd /opt/hermes && HERMES_HOME=/opt/data /opt/hermes/.venv/bin/hermes mcp list"'
ssh -o BatchMode=yes -o ConnectTimeout=8 ubuntu@124.223.102.241 'docker exec -i hermes sh -lc "cd /opt/hermes && HERMES_HOME=/opt/data /opt/hermes/.venv/bin/python -"' < /private/tmp/hermes_main_a001_probe.py
ssh -o BatchMode=yes -o ConnectTimeout=8 ubuntu@124.223.102.241 'docker exec -i hermes sh -lc "cd /opt/hermes && HERMES_HOME=/opt/data /opt/hermes/.venv/bin/python -"' < /private/tmp/hermes_main_a002_probe.py
ssh -o BatchMode=yes -o ConnectTimeout=8 ubuntu@124.223.102.241 'docker exec hermes sh -lc "tail -n 10 /opt/data/logs/tastemate-route.jsonl 2>/dev/null"'
```

### 主 agent 复验结果

```text
远端 Hermes 容器正常运行：
hermes    Up About a minute

远端 config.yaml 已从 plugins.enabled 中移除 tastemate-route：
plugins:
  enabled: []
  disabled: []

Hermes CLI 已启用 tastemate MCP server：
Name       Tools   Status
tastemate  all     enabled

gateway 入口验证：
1. 下线 tastemate-route 前，@taste 请求会在 pre_gateway_dispatch 被固定候选改写。
2. 下线 tastemate-route 并重启后，gateway capture probe 记录到的 captured_text 与原始 @taste 输入一致。
3. tastemate-route.jsonl 没有新增 fixed_probe_candidates 记录，最新记录仍停留在 2026-05-27T19:34:08+00:00。

A-001 远端验收：
- session: session_20260528_002333_9b377c.json
- 实际 tool call: mcp_tastemate_rank_candidates
- candidates 参数：3 个，分别为 obsidian / logseq / anytype
- structuredContent.action: ranked
- ranked_candidates 返回：logseq / anytype / obsidian
- 实际 assistant tool_calls 中未出现 execute_code

A-002 远端验收：
- session: session_20260528_002333_46440c.json
- 实际 tool calls: mcp_tastemate_get_profile -> mcp_tastemate_rank_candidates
- candidates 参数：5 个，分别为 obsidian / logseq / anytype / joplin / foam
- structuredContent.action: ranked
- ranked_candidates 返回：obsidian / logseq / anytype / foam / joplin
- 实际 assistant tool_calls 中未出现 execute_code
```

## 四、未验证项

```text
无剩余阻塞型未验证项。
后续可选补充：通过真实微信/生产入口再补一轮业务侧烟测截图或会话摘录。
```

## 五、阻塞结论

```text
PASS
```

说明：

```text
本地实现和 pytest 已通过。
远端 Hermes 已下线 tastemate-route 默认入口，不再劫持 @taste 请求。
远端已取得 A-001 / A-002 的真实 candidates -> mcp_tastemate_rank_candidates 主路径证据。
因此迭代二 Verify 通过，可进入 Multi-Agent Review。
```

## 六、风险

```text
1. Hermes 插件 format_rewrite_text 中的 low_confidence 分支在新 Ranker 中不再产出，属于 dead code。不影响功能，后续迭代可清理。
2. Hermes 调用 mcp_tastemate_rank_candidates 时的 candidates 质量取决于 Hermes prompt 工程，不在 TasteMate 侧控制范围内。
3. 远端 hermes 仍存在 cron.jobs 权限报错，当前不影响 TasteMate 排序主路径，但应作为运维项后续处理。
4. gateway 端到端验证当前通过 capture probe + main 链 session 证据收口；若后续 gateway 生命周期初始化逻辑变化，建议补一次真实平台入口回归。
```

## 七、未完成项

```text
1. 进入 Multi-Agent Review。
2. deployment / usage 文档已产出，待随 Review 一并确认。
3. 如需验证 feedback/evidence 远端链路，单独补实验并核对 profile.json。
4. 后续按需要清理 tastemate-route 旧插件 dead code，前提是不影响 iteration-001 回归资产保留。
```
