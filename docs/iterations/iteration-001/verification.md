# Iteration 001 Verification：显式 @taste 后置重排闭环

## 适用阶段

```text
Verify
```

本记录对应 Build 阶段已实现的本地 TasteMate MCP server、规则重排、反馈写入、profile 查询和测试。

## 一、测试命令与结果

### 1. 安装开发依赖

命令：

```bash
python -m pip install -e '.[dev]'
```

结果摘要：

```text
Successfully installed attrs-26.1.0 httpx-sse-0.4.3 jsonschema-4.26.0 jsonschema-specifications-2025.9.1 mcp-1.27.1 python-multipart-0.0.29 referencing-0.37.0 rpds-py-0.30.0 sse-starlette-3.4.4 tastemate-0.1.0
```

退出码：

```text
0
```

### 2. 空测试基线

命令：

```bash
python -m pytest -q
```

结果摘要：

```text
No files were found in testpaths
1 warning in 0.00s
```

退出码：

```text
5
```

说明：

```text
该命令在测试文件创建前执行，只用于确认脚手架基线；exit code 5 符合 Plan 中“无测试时允许”的预期。
```

### 3. Ranker 与 Profile Store 测试

命令：

```bash
python -m pytest tests/test_rank_candidates.py tests/test_profile_store.py -q
```

结果摘要：

```text
10 passed in 0.02s
```

退出码：

```text
0
```

### 4. Feedback Processor 测试

命令：

```bash
python -m pytest tests/test_record_feedback.py -q
```

结果摘要：

```text
3 passed in 0.00s
```

退出码：

```text
0
```

### 5. Tools 与 MCP app 导出测试

命令：

```bash
python -m pytest tests/test_server_tools.py -q
```

结果摘要：

```text
4 passed in 1.35s
```

退出码：

```text
0
```

### 6. 全量单元测试

命令：

```bash
python -m pytest -q
```

结果摘要：

```text
17 passed in 0.22s
```

退出码：

```text
0
```

失败数：

```text
0
```

### 7. Import smoke test

命令：

```bash
python -c "from tastemate.server import mcp; print(mcp.name)"
```

结果摘要：

```text
tastemate
```

退出码：

```text
0
```

### 8. MCP stdio smoke test

命令：

```bash
python -m tastemate.server
```

结果摘要：

```text
进程启动后保持运行并等待 stdio 输入。
测试中通过 Ctrl+C / EOF 结束进程，退出时出现 KeyboardInterrupt traceback。
```

退出码：

```text
1
```

结论：

```text
启动等待 stdio 输入的行为符合 smoke test 预期；退出码 1 来自人工中断，不作为 server 启动失败处理。
```

### 9. Hermes registry 主动 dispatch 穿刺

命令摘要：

```bash
ssh -o BatchMode=yes -o ConnectTimeout=8 <HERMES_SSH_USER>@<HERMES_HOST> 'docker exec -i hermes sh -lc "cd <HERMES_APP_DIR> && HERMES_HOME=<HERMES_DATA_DIR> <HERMES_APP_DIR>/.venv/bin/python -"' < <LOCAL_PROBE_SCRIPT>
```

结果摘要：

```text
DISCOVERED 包含 mcp_tastemate_rank_candidates、mcp_tastemate_record_feedback、mcp_tastemate_get_profile。
handle_function_call("mcp_tastemate_rank_candidates", args) 返回 structuredContent.action=ranked。
```

退出码：

```text
0
```

结论：

```text
Hermes 工具调度层可以主动调用 TasteMate MCP 工具；失败点不是 TasteMate MCP server 或 Hermes registry，而是原先依赖 LLM 自主触发工具不稳定。
```

### 10. `pre_gateway_dispatch` rewrite 穿刺

命令摘要：

```bash
ssh -o BatchMode=yes -o ConnectTimeout=8 <HERMES_SSH_USER>@<HERMES_HOST> 'docker exec -i hermes sh -lc "cd <HERMES_APP_DIR> && HERMES_HOME=<HERMES_DATA_DIR> <HERMES_APP_DIR>/.venv/bin/python -"' < <LOCAL_PROBE_SCRIPT>
```

结果摘要：

```text
普通消息：RESULTS=[{"action": "allow"}]。
@taste 推荐消息：RESULTS=[{"action": "rewrite", "text": "..."}]。
rewrite text 包含 "TasteMate 已完成真实后置重排"，并包含 Local-first KB、Cloud KB、MCP Assistant 的 final_score 和 reasons。
```

退出码：

```text
0
```

结论：

```text
pre_gateway_dispatch 能检测 @taste，并能在真实调用 TasteMate 后通过 rewrite 把排序结果交回 Hermes 自有 agent 回复通道。
```

## 二、变更范围检查

命令：

```bash
git status --short
git diff --name-only
git ls-files --others --exclude-standard
```

结果摘要：

```text
当前分支：feat/iteration-001-tastemate-mcp
已修改的已跟踪文件：tasteMateHermesPersonalAssistant.md
未跟踪文件包含：AGENTS.md、docs/、pyproject.toml、tastemate/、tests/、.gitignore
git diff --name-only 仅显示 tasteMateHermesPersonalAssistant.md
```

说明：

```text
docs/、pyproject.toml、tastemate/、tests/、.gitignore 当前仍为未跟踪文件，因此不会出现在 git diff --name-only 中。
tasteMateHermesPersonalAssistant.md 的修改不是本轮 Build 产生的改动，本轮未触碰 Hermes 源码目录。
```

通过条件：

```text
本轮 Build 新增内容均位于 TasteMate 仓库内。
未发现 /Users/lanser/code/hermes 或 Hermes 源码路径变更。
```

## 三、验收标准映射

| ID | 验收标准 | 证据 | 结果 |
| --- | --- | --- | --- |
| A-001 | 未使用 @taste 时 TasteMate 不介入 | `pre_gateway_dispatch` 穿刺和固化插件远程 hook 验证中普通消息均返回 `action=allow`；CLI 真实入口普通消息 `Hermes 的 MCP 配置文件在哪？` 正常回复，未出现 `mcp_tastemate_*` 工具调用 | 通过 |
| A-002 | @taste 推荐类问题触发 rank_candidates | `tests/test_server_tools.py` 覆盖工具可调用；Hermes registry 主动 dispatch 穿刺通过；`pre_gateway_dispatch` rewrite 穿刺通过；固化插件远程 hook 验证通过；CLI 真实入口 `@taste 推荐几个适合我的本地知识库工具` 调用 `mcp_tastemate_rank_candidates` | 通过 |
| A-003 | 事实类问题返回 passthrough | `tests/test_rank_candidates.py::test_rank_candidates_passthrough_for_factual_question` 和 `tests/test_rank_candidates.py::test_rank_candidates_passthrough_for_taste_factual_question`；CLI 真实入口 `@taste Hermes 的 MCP 配置文件在哪？` 只出现 API call 和 Turn ended，未调用 `mcp_tastemate_rank_candidates` | 通过 |
| A-004 | 候选不足时返回 needs_more_candidates | `tests/test_rank_candidates.py::test_rank_candidates_needs_more_candidates_for_single_recommendation_candidate` | 通过 |
| A-005 | 推荐类候选输出 query_relevance、preference_fit、final_score | `tests/test_rank_candidates.py::test_rank_candidates_ranked_schema_for_recommendation_candidates` | 通过 |
| A-006 | 用户明确反馈写入 evidence_log | `tests/test_record_feedback.py::test_record_feedback_writes_evidence` 和 `tests/test_server_tools.py::test_record_feedback_tool_persists_evidence`；CLI 真实入口反馈 `我选第一个，不要企业 SaaS 那种` 调用 `mcp_tastemate_record_feedback`，返回 `feedback_valid=true` 和 `profile_updates.evidence_log count=2` | 通过 |
| A-007 | 单次反馈写 evidence_log 且限制 stable_preferences | `tests/test_record_feedback.py` 覆盖不新增、权重增量、confidence 上限；CLI 反馈验收返回 `signal_strength=0.7` 且写入 evidence_log | 通过 |
| A-008 | 不修改 Hermes 源码 | 变更范围检查未发现 Hermes 源码路径 | 通过 |

## 四、手工验证步骤

固化插件的远程 hook 级验证已执行；CLI 真实入口端到端手工验收已执行。

已验证项：

```text
V-001 普通消息：Hermes 的 MCP 配置文件在哪？
结果：CLI 会话 20260526_183259_6b8f87 正常回复，未出现 mcp_tastemate_* 调用。

V-002 @taste 推荐类消息：@taste 推荐几个适合我的本地知识库工具
结果：CLI 会话 20260526_183259_6b8f87 调用 mcp_tastemate_rank_candidates。

V-003 @taste 事实类消息：@taste Hermes 的 MCP 配置文件在哪？
结果：CLI 会话 20260526_183259_6b8f87 只出现 API call 和 Turn ended，未调用 mcp_tastemate_rank_candidates。

V-004 明确反馈：我选第一个，不要企业 SaaS 那种
结果：CLI 会话 20260526_183259_6b8f87 调用 mcp_tastemate_record_feedback，返回 feedback_valid=true、signal_strength=0.7、profile_updates.evidence_log count=2。
```

后续渠道验证：

```text
微信客户端外部投递链路仍可单独验收，但不阻塞 Iteration 001。
已完成 Weixin 形态 MessageEvent 模拟，证明 Platform.WEIXIN 事件进入 GatewayRunner._handle_message 后可以触发 rewrite。
```

## 五、编排补充结论

```text
Hermes @taste rewrite 编排属于 Iteration 001 的 A-002 验收补充，不单独拆新迭代。
当前已完成穿刺验证、固化插件远程 hook 级验证、Weixin 形态消息模拟和 CLI 真实入口端到端验收。
gateway send API 直发路线未验证，列为后续探索，不阻塞当前 rewrite 路线。
```

## 六、固化插件本地验证

### 1. Hermes route plugin 测试

命令：

```bash
python -m pytest tests/test_hermes_route_plugin.py -q
```

结果摘要：

```text
8 passed in 0.01s
```

退出码：

```text
0
```

覆盖范围：

```text
插件注册 pre_gateway_dispatch hook。
普通消息返回 allow 且不 dispatch。
@taste 推荐消息调用 mcp_tastemate_rank_candidates。
ranked 结果生成 rewrite。
needs_more_candidates 不伪装成已完成排序。
Unknown tool fail-open。
dispatch 异常 fail-open。
operation log 写入 matched=true、dispatch_ok=true、dispatch_action=ranked。
```

### 2. 全量测试

命令：

```bash
python -m pytest -q
```

结果摘要：

```text
25 passed in 0.24s
```

退出码：

```text
0
```

### 3. Weixin 形态消息模拟

命令摘要：

```bash
ssh -o BatchMode=yes -o ConnectTimeout=8 <HERMES_SSH_USER>@<HERMES_HOST> 'docker exec -i hermes sh -lc "cd <HERMES_APP_DIR> && <HERMES_APP_DIR>/.venv/bin/python -"' < <LOCAL_PROBE_SCRIPT>
```

结果摘要：

```text
构造 Platform.WEIXIN 的 MessageEvent 后送入 GatewayRunner._handle_message。
captured_platform=weixin，captured_chat_type=dm。
captured_text 被 rewrite 成 TasteMate 已完成真实后置重排的排序文本。
operation log 记录 matched=true、action=rewrite、candidate_source=fixed_probe_candidates、dispatch_action=ranked。
```

退出码：

```text
0
```

## 七、固化插件远程 hook 级验证

### 1. 远程部署

动作摘要：

```text
备份旧 <HERMES_DATA_DIR>/plugins/tastemate-route-probe。
上传 integrations/hermes/plugins/tastemate-route/__init__.py 到 <HERMES_DATA_DIR>/plugins/tastemate-route/__init__.py。
上传 integrations/hermes/plugins/tastemate-route/plugin.yaml 到 <HERMES_DATA_DIR>/plugins/tastemate-route/plugin.yaml。
更新 <HERMES_DATA_DIR>/config.yaml，plugins.enabled 只保留 tastemate-route。
重启 hermes 容器。
```

配置确认：

```text
plugins.enabled= ['tastemate-route']
```

### 2. Hook 级验证命令

命令摘要：

```bash
ssh -o BatchMode=yes -o ConnectTimeout=8 <HERMES_SSH_USER>@<HERMES_HOST> 'docker exec -i hermes sh -lc "cd <HERMES_APP_DIR> && HERMES_HOME=<HERMES_DATA_DIR> <HERMES_APP_DIR>/.venv/bin/python -"' < <LOCAL_PROBE_SCRIPT>
```

结果摘要：

```text
MCP_TOOLS 包含 mcp_tastemate_rank_candidates、mcp_tastemate_record_feedback、mcp_tastemate_get_profile。
普通消息 CASE=Hermes 的配置在哪？ 返回 RESULTS=[{"action": "allow"}]。
@taste 推荐消息返回 RESULTS=[{"action": "rewrite", "text": "..."}]。
REWRITE_HAS_TASTEMATE=True。
rewrite preview 包含 Local-first KB、Cloud KB、MCP Assistant 的 final_score 和 reasons。
```

退出码：

```text
0
```

### 3. Operation log 检查

命令：

```bash
ssh -o BatchMode=yes -o ConnectTimeout=8 <HERMES_SSH_USER>@<HERMES_HOST> 'docker exec hermes sh -lc "tail -n 20 <HERMES_DATA_DIR>/logs/tastemate-route.jsonl"'
```

结果摘要：

```text
普通消息日志：matched=false，action=allow，dispatch_ok=null。
@taste 推荐消息日志：matched=true，action=rewrite，candidate_source=fixed_probe_candidates，candidate_count=3，dispatch_ok=true，dispatch_action=ranked。
```

退出码：

```text
0
```

## 八、真实入口端到端验收

已完成：

```text
通过 CLI 真实入口发送普通消息，确认 Hermes 正常回复且 TasteMate 不介入。
通过 CLI 真实入口发送 @taste 推荐消息，确认调用 mcp_tastemate_rank_candidates。
通过 CLI 真实入口发送 @taste 事实类消息，确认不伪装成推荐排序。
通过 CLI 真实入口发送明确反馈，确认调用 mcp_tastemate_record_feedback 并写入 evidence_log。
```

当前状态：

```text
A-001：本地、远程 hook 级和 CLI 真实入口验证通过。
A-002：本地、远程 hook 级和 CLI 真实入口验证通过。
A-006/A-007：本地测试和 CLI 真实入口反馈写入验证通过。
```

后续 FOLLOW_UP：

```text
微信客户端外部投递链路仍可单独验证。
该项验证微信客户端到 Hermes 的传输，不阻塞当前 Iteration 001 的 Hermes/TasteMate 闭环验收。
```

### 服务器 Hermes 验证安排

适用场景：

```text
Hermes 已部署在远程服务器上。
TasteMate 作为外部 stdio MCP server 接入，不修改 Hermes 源码。
验证动作允许修改服务器上的 Hermes 运行配置，但必须可回滚。
```

推荐部署形态：

```text
TasteMate 代码目录：/opt/tastemate 或服务器上已有的项目发布目录。
TasteMate 虚拟环境：/opt/tastemate/.venv。
TasteMate profile：/var/lib/tastemate/profile.json。
Hermes 配置文件：~/.hermes/config.yaml。
Hermes 接入方式：mcp_servers.tastemate 使用 .venv/bin/python -m tastemate.server。
```

服务器准备步骤：

```bash
cd /opt/tastemate
python -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python -m pytest -q
.venv/bin/python -c "from tastemate.server import mcp; print(mcp.name)"
mkdir -p /var/lib/tastemate
```

服务器准备通过条件：

```text
pytest 显示 17 passed。
import smoke test 输出 tastemate。
/var/lib/tastemate 可由运行 Hermes 的系统用户读写。
```

Hermes 配置建议：

```yaml
mcp_servers:
  tastemate:
    command: "/opt/tastemate/.venv/bin/python"
    args: ["-m", "tastemate.server"]
    env:
      TASTEMATE_PROFILE_PATH: "/var/lib/tastemate/profile.json"
    timeout: 120
```

如果 Hermes 配置已有其他 `mcp_servers`，只追加 `tastemate` 项，不覆盖现有 server。

配置生效步骤：

```text
1. 修改服务器上的 ~/.hermes/config.yaml。
2. 重启 Hermes 服务或重新启动运行 Hermes 的会话。
3. 观察 Hermes 启动日志，确认发现 mcp_tastemate_rank_candidates、mcp_tastemate_record_feedback、mcp_tastemate_get_profile。
```

具体重启命令按部署方式选择：

```bash
systemctl restart hermes
```

或：

```bash
docker compose restart hermes
```

或：

```bash
重新启动当前 Hermes CLI / daemon 进程。
```

远程手工验证用例：

```text
V-001 普通问题：
输入：Hermes 的 MCP 配置文件在哪？
通过条件：Hermes 不调用任何 mcp_tastemate_* 工具。
失败条件：出现 mcp_tastemate_* 工具调用。

V-002 @taste 推荐类问题：
输入：@taste 推荐几个适合我的本地知识库工具。
通过条件：Hermes 调用 mcp_tastemate_rank_candidates，工具结果为 ranked 或 needs_more_candidates。
失败条件：Hermes 直接回答且未调用 TasteMate。

V-003 @taste 事实类问题：
输入：@taste Hermes 的 MCP 配置文件在哪？
通过条件：TasteMate 返回 passthrough，或 Hermes 不触发排序。
失败条件：TasteMate 返回 ranked。

V-004 反馈学习：
前置：V-002 已产生推荐结果。
输入：我选第一个，不要企业 SaaS 那种。
通过条件：Hermes 调用 mcp_tastemate_record_feedback，/var/lib/tastemate/profile.json 的 evidence_log 增加记录。
失败条件：没有工具调用，或 profile 未写入 evidence_log。

V-005 profile 查询：
输入：让 Hermes 调用 TasteMate 查看当前 profile。
通过条件：Hermes 调用 mcp_tastemate_get_profile，并返回 stable_preferences、negative_preferences、current_focus、summary。
失败条件：工具不可见或返回结构缺字段。
```

证据记录要求：

```text
记录 Hermes 部署方式：systemd、docker compose、CLI 或其他。
记录 TasteMate 部署目录和 python 路径。
记录 Hermes 配置片段。
记录重启命令和结果。
记录每个验证用例的输入、是否出现 mcp_tastemate_* 工具调用、工具 action、profile evidence_log 变化。
如果无法获取工具调用日志，必须说明观察依据，例如 Hermes 终端输出、debug 日志或最终回答中的工具结果。
```

回滚步骤：

```text
1. 从 ~/.hermes/config.yaml 移除 mcp_servers.tastemate，或临时注释该项。
2. 重启 Hermes 服务或会话。
3. 确认普通 Hermes 问答恢复，不再发现 mcp_tastemate_* 工具。
4. 保留 /var/lib/tastemate/profile.json 作为验证证据；如需删除，必须先备份。
```

## 五、失败项

```text
无单元测试失败。
新增回归测试覆盖 `@taste Hermes 的 MCP 配置文件在哪？` 仍返回 passthrough。
MCP stdio smoke test 由人工中断退出，记录为非阻塞。
固化插件远程 hook 级验证已通过。
CLI 真实入口端到端验收已执行。
```

## 六、Verify 结论

```text
PASS
```

原因：

```text
本地实现、单元测试、远程 hook 级验证、Weixin 形态模拟和 CLI 真实入口端到端验收均通过。
真实入口验收覆盖 A-001、A-002、A-003、A-006、A-007。
微信客户端外部投递链路作为后续渠道验证，不阻塞当前 Iteration 001 验收。
```

## 七、当前进展索引

本轮迭代的最新实验状态已单独整理到：

- [docs/iterations/iteration-001/status.md](./status.md)

阅读顺序建议：

```text
1. status.md：当前进行到哪里、已验证什么、卡在哪里
2. verification.md：正式验证记录和结果证据
3. review.md：审查结论和遗留 Follow-up
```
