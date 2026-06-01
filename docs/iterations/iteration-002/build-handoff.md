# Iteration 002 Build Handoff

## 适用阶段

```text
Build
```

本文件给后续开发者快速建立上下文，并约束实现边界。开发完成后仍由主 agent 负责 Verify 和 Review。

## 一、先看什么

按以下顺序阅读：

```text
1. docs/iteration-plan.md
2. docs/iterations/iteration-002/status.md
3. docs/iterations/iteration-002/design.md
4. docs/iterations/iteration-002/development.md
5. docs/iterations/iteration-002/plan.md
6. docs/process/acceptance.md
```

读取目标：

```text
iteration-plan.md：确认迭代二只做真实候选排序，不做搜索前偏好注入。
status.md：确认当前处于 Plan 后、Build 前，不要越阶段。
design.md：确认主路径是 Hermes 主动整理 candidates。
development.md：确认候选协议、降级结果、禁止事项。
plan.md：确认实际改哪些文件、先写哪些测试、最后怎么验。
acceptance.md：确认验收必须靠证据，不靠聊天结论。
```

## 二、必须记住的边界

```text
只做真实 candidates 排序。
不修改 Hermes 源码。
不实现 observed_tool_candidates。
不做搜索前偏好注入。
不扩 feedback 画像。
不把 fixed_probe_candidates 写成真实候选主路径。
```

当前主路径必须是：

```text
Hermes 整理真实 candidates
-> mcp_tastemate_rank_candidates
-> TasteMate 校验 candidates
-> ranked / passthrough / invalid_candidates / needs_more_candidates
```

## 三、代码先看哪里

先读这些实现文件：

```text
tastemate/schemas/candidates.py
tastemate/core/ranker.py
tastemate/tools/rank_candidates.py
tests/test_rank_candidates.py
tests/test_server_tools.py
integrations/hermes/plugins/tastemate-route/__init__.py
tests/test_hermes_route_plugin.py
```

理解重点：

```text
schemas/candidates.py：当前是否还在伪造候选字段。
core/ranker.py：当前 factual / recommendation / downgrade 分支是否和开发规格一致。
tools/rank_candidates.py：是否只透传结构化结果。
tastemate-route 插件：只允许保留 fixed_probe_candidates 回归路径，不允许把它当真实候选主路径。
```

## 四、实现顺序

严格按这个顺序做：

```text
1. 先补 candidates 协议校验测试。
2. 再改 schemas/candidates.py。
3. 再补 ranker 的 4 类输出测试：
   passthrough / invalid_candidates / needs_more_candidates / ranked
4. 再改 core/ranker.py 和 tools/rank_candidates.py。
5. 最后只做 Hermes 插件回归边界测试，不把插件混成真实候选主路径。
```

不要跳步。
不要先改实现再补测试。

## 五、实现完成后必须给出的证据

本地证据：

```bash
python -m pytest tests/test_rank_candidates.py -q
python -m pytest tests/test_server_tools.py -q
python -m pytest tests/test_hermes_route_plugin.py -q
python -m pytest -q
```

远端证据：

```bash
ssh -o BatchMode=yes -o ConnectTimeout=8 ubuntu@124.223.102.241 'docker inspect hermes --format "STATUS={{.State.Status}} RESTARTS={{.RestartCount}} IMAGE={{.Config.Image}}"'
ssh -o BatchMode=yes -o ConnectTimeout=8 ubuntu@124.223.102.241 'docker logs hermes --since 10m | rg "mcp_tastemate_rank_candidates|candidate_source|fixed_probe_candidates"'
ssh -o BatchMode=yes -o ConnectTimeout=8 ubuntu@124.223.102.241 'tail -n 50 /home/ubuntu/hermes-data/logs/tastemate-route.jsonl'
```

必须证明：

```text
Hermes 服务在跑。
出现 mcp_tastemate_rank_candidates completed 或等价成功证据。
真实候选主路径没有新增 fixed_probe_candidates 记录。
用户给定候选和 Hermes 已有知识候选两类路径都能返回 ranked 或明确降级 action。
```

## 六、开发者交付给审核的内容

开发完成后，至少交付：

```text
1. 改动文件列表。
2. 本地 pytest 命令和结果。
3. 远端 Hermes 验证命令和结果摘要。
4. verification.md 草稿或等价验证记录。
5. 未完成项和风险列表。
```

主 agent 将据此继续做 Verify 和 Multi-Agent Review。
