# Iteration 004 Verification：统一偏好信号摄取

## 适用阶段

```text
Verify。
本文件记录本地验证、远端部署验证和端到端证据。
```

## 一、当前结论

```text
本地 Build 验证通过。
远端服务器已实际部署更新后的 TasteMate MCP 服务和 tastemate-route 插件。
项目当前暂停；本文件保留已通过证据，同时明确 Telegram 外部入站反馈未通过。

已验证：
1. 远端 TasteMate 暴露 record_preference_signal，且不再暴露 record_interest。
2. 远端 tastemate-route 插件已启用。
3. candidate_feedback 在远端 hook 级闭环中实际调用 mcp_tastemate_record_preference_signal，并写入 /opt/data/tastemate/profile.json。
4. interest 通过远端 Hermes CLI 真实调用 mcp_tastemate_record_preference_signal，并写入 current_focus。
5. 默认候选反馈路径已通过工具描述和注册顺序调整，真实会话优先调用 mcp_tastemate_record_preference_signal。
6. 再推荐读取更新后的 profile，reasons 明确体现长期偏好、当前关注和负向偏好。
7. Telegram 外部入站推荐链路命中 tastemate-route，并完成后置重排 rewrite。

注意：
Telegram 外部入站反馈链路未通过。
实测用户反馈“我更喜欢 Logseq，以后优先。不要 Obsidian。”进入 gateway，但 tastemate-route 返回 feedback_candidate_unmatched，未调用 mcp_tastemate_record_preference_signal，profile 未新增 2026-06-17 的反馈 evidence。
根因是推荐阶段保存的 fixed_probe_candidates 上下文为 Local-first KB / Cloud KB / MCP Assistant，而用户可见回复中的候选为 Logseq / Obsidian。
```

## 二、本地验证

命令：

```bash
pytest tests/test_record_preference_signal.py -q
pytest tests/test_get_profile.py::test_record_feedback_tool_returns_compatible_iteration003_payload -q
pytest tests/test_server_tools.py -q
pytest tests/test_hermes_route_plugin.py -q
pytest tests/test_record_preference_signal.py tests/test_record_feedback.py tests/test_get_profile.py tests/test_server_tools.py tests/test_hermes_route_plugin.py -q
pytest -q
```

结果：

```text
tests/test_record_preference_signal.py：4 passed
record_feedback 兼容测试：1 passed
tests/test_server_tools.py：7 passed
tests/test_hermes_route_plugin.py：14 passed
相关测试集合：47 passed
全量测试：71 passed
```

## 三、远端部署记录

服务器：

```text
ubuntu@124.223.102.241
容器：hermes
TasteMate 路径：/opt/data/tastemate
Hermes 插件路径：/opt/data/plugins/tastemate-route
profile 路径：/opt/data/tastemate/profile.json
```

备份：

```text
代码与插件备份：BACKUP_TS=20260612025207
config 备份：/opt/data/config.yaml.iteration004.20260612031107.bak
profile 初始备份：/opt/data/tastemate/profile.json.iteration004.e2e.before.20260612031326
interest 前备份：/opt/data/tastemate/profile.json.before-interest-e2e.20260612033723
```

部署动作：

```text
1. 上传并解压本地 TasteMate 代码包到 /opt/data/tastemate。
2. 同步 integrations/hermes/plugins/tastemate-route/__init__.py 到 /opt/data/plugins/tastemate-route/__init__.py。
3. 修改 /opt/data/config.yaml，启用 plugins.enabled: [tastemate-route]。
4. docker restart hermes。
```

远端测试：

```bash
docker exec hermes sh -lc "cd /opt/data/tastemate && .venv/bin/python -m pytest tests/test_record_preference_signal.py tests/test_server_tools.py tests/test_get_profile.py tests/test_hermes_route_plugin.py -q"
```

结果：

```text
29 passed in 0.67s
```

远端 MCP 工具注册：

```text
['get_profile', 'rank_candidates', 'record_feedback', 'record_preference_signal']
```

插件状态：

```text
hermes plugins list 显示 tastemate-route enabled。
```

## 四、candidate_feedback 远端验证

验证方式：

```text
在远端容器内加载 /opt/data/plugins/tastemate-route/__init__.py。
使用真实 /opt/data/tastemate 工具函数作为 dispatch 后端：
- mcp_tastemate_rank_candidates -> rank_candidates_tool
- mcp_tastemate_record_preference_signal -> record_preference_signal_tool
profile_path 使用 /opt/data/tastemate/profile.json。
```

输入：

```text
推荐：@taste 推荐几个适合我的本地知识库工具
反馈：我更喜欢 Local-first KB，以后优先。不要 Cloud KB。
```

结果摘要：

```json
{
  "recommendation_action": "rewrite",
  "feedback_action": "rewrite",
  "calls": [
    ["mcp_tastemate_rank_candidates", "..."],
    ["mcp_tastemate_record_preference_signal", "..."]
  ]
}
```

record_preference_signal 参数摘要：

```json
{
  "signal_type": "candidate_feedback",
  "user_signal": "我更喜欢 Local-first KB，以后优先。不要 Cloud KB。",
  "source": "tastemate_recommendation",
  "query": "@taste 推荐几个适合我的本地知识库工具",
  "candidate_feedback": {
    "selected_candidate_ids": ["local"],
    "rejected_candidate_ids": ["cloud"]
  }
}
```

profile 写入证据：

```text
新增 evidence：
- local / local_first / positive
- local / open_source / positive
- cloud / cloud_required / negative

新增 stable_preferences：
- local_first
- open_source

新增 negative_preferences：
- cloud_required
```

插件日志证据：

```text
2026-06-12T03:36:44+00:00
route_reason=explicit_tastemate_feedback
dispatch_ok=true
dispatch_action=record_preference_signal
selected_candidate_ids=["local"]
rejected_candidate_ids=["cloud"]
```

## 五、interest 远端验证

验证方式：

```text
使用远端 Hermes CLI 真实调用：
hermes -z "请使用 TasteMate 的 record_preference_signal 工具记录这个普通兴趣信号：我最近更关注本地优先和开源工具。signal_type=interest，source=normal_conversation。记录后简短回复。"
```

Hermes 输出：

```text
已记录。信号 `81c34728` 已接受，提取了 `local_first` 和 `open_source` 两个特征，加入 `current_focus`。
```

profile 写入证据：

```text
interest 前 evidence_count：5
interest 后 evidence_count：7
stable_unchanged：true
negative_unchanged：true
```

新增 evidence tail：

```text
candidate_id=__interest__, feature=local_first, direction=positive, source=normal_conversation
candidate_id=__interest__, feature=open_source, direction=positive, source=normal_conversation
```

current_focus：

```text
last_feedback=我最近更关注本地优先和开源工具
current_focus 包含 local_first / open_source
```

## 六、默认候选反馈优先入口修正验证

验证方式：

```text
先发送 @taste 推荐消息，再在同一真实 session 中发送候选反馈：
我更喜欢 Logseq，以后优先。不要 Obsidian。
```

Hermes 输出：

```text
记下了。Logseq 优先，Reor 备选，Obsidian 出局。后续知识库相关推荐和方案会按这个排序。
```

session：

```text
20260612_061857_674f3f
```

session export 结果：

```text
TOOLS=['mcp_tastemate_rank_candidates', 'mcp_tastemate_record_preference_signal']
RECORD_PREF=3
RECORD_FEEDBACK=0
RANK=6
```

插件/服务侧变化：

```text
record_preference_signal 已提前注册为优先入口。
record_feedback 保留为 legacy compatibility entrypoint。
远端真实会话在默认候选反馈下已改为调用 mcp_tastemate_record_preference_signal。
```

## 七、再推荐消费画像验证

验证方式：

```text
在远端调用 rank_candidates_tool，读取 /opt/data/tastemate/profile.json。
候选：
- local：Open source local-first knowledge base
- cloud：Cloud hosted SaaS knowledge base
```

结果摘要：

```text
local final_score=0.806
cloud final_score=0.5903
```

local reasons 包含：

```text
命中长期正向偏好: local_first
命中长期正向偏好: open_source
命中当前关注: local_first
命中当前关注: open_source
```

cloud reasons / risks 包含：

```text
命中长期负向偏好: cloud_required
存在云端依赖风险
```

## 八、验收标准映射

```text
A-001 record_preference_signal 支持 candidate_feedback：通过。
A-002 record_preference_signal 支持 interest：通过。
A-003 record_feedback 兼容入口不破坏：通过。
A-004 未知 signal_type 不写 profile：通过。
A-005 Hermes 插件推荐后反馈调用统一工具：远端 hook 级通过。
A-006 Hermes 插件失败路径不误写：本地测试通过。
A-007 远端 candidate_feedback 端到端：Hermes CLI / hook 级通过；Telegram 外部入站反馈未通过。
A-008 远端 interest 端到端：Hermes CLI 真实调用通过。
A-009 不修改 Hermes 源码：通过；本轮只修改 TasteMate 代码、用户插件和远端 config。
```

## 九、剩余风险

```text
R-001 Telegram 外部入站反馈未通过。
影响：当前不能声称真实用户在 Telegram 反馈 Logseq / Obsidian 时会写入 TasteMate profile。
当前判断：阻塞真实渠道反馈闭环 Closeout。

R-002 本轮为验证启用了 tastemate-route 插件。
影响：该插件仍使用 fixed_probe_candidates 作为推荐上下文穿刺资产，不代表真实候选主路径。
当前判断：这是 Telegram 反馈未命中的直接根因之一；后续必须让保存的 candidate context 与用户实际看到的候选一致。
```

## 十、结论

```text
本地 Verify：PASS。
远端 TasteMate MCP 部署验证：PASS。
远端 candidate_feedback hook 级闭环：PASS。
远端 interest 真实 CLI 调用：PASS。
默认候选反馈优先入口修正：PASS。
再推荐画像消费：PASS。
Telegram 外部入站推荐：PASS。
Telegram 外部入站反馈：BLOCK。

当前不进入 Closeout。
项目按阶段性成果暂停，后续恢复时优先处理真实候选上下文一致性。
```
