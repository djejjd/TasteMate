# Iteration 002 开发执行提示

本文件不是通用 Developer Agent 模板。

本文件只服务于：

```text
Iteration 002 Build 阶段
```

使用前必须先阅读：

```text
docs/process/agents/developer-agent.md
```

本文件只补充迭代二的专用执行约束。

## 一、迭代二唯一目标

```text
实现真实 candidates 排序。
让 TasteMate 对 Hermes 明确传入的真实 candidates 返回：
passthrough / invalid_candidates / needs_more_candidates / ranked
并保留迭代一 fixed_probe_candidates 回归路径。
```

## 二、迭代二禁止事项

```text
不能修改 Hermes 源码。
不能实现 observed_tool_candidates。
不能做搜索前偏好注入。
不能扩 feedback 画像。
不能接入 Obsidian。
不能把 fixed_probe_candidates 写成真实候选主路径。
```

## 三、迭代二默认写集

```text
tastemate/schemas/candidates.py
tastemate/core/ranker.py
tastemate/tools/rank_candidates.py
tests/test_rank_candidates.py
tests/test_server_tools.py
integrations/hermes/plugins/tastemate-route/__init__.py
tests/test_hermes_route_plugin.py
docs/iterations/iteration-002/verification.md
```

## 四、迭代二固定映射

```text
事实类 query 或 candidates 为空 -> passthrough
缺少 id/title/summary/metadata -> invalid_candidates
有效候选少于 2 个 -> needs_more_candidates
候选满足协议且数量足够 -> ranked
```

补充约束：

```text
candidate.metadata 可以是空对象 {}
url 和 source 缺失不阻塞排序
rank_candidates_tool 只透传结构化结果
Hermes 插件只保留 fixed_probe_candidates 回归路径
```

## 五、迭代二开发顺序

```text
1. 先补 candidates 协议测试。
2. 再实现 schemas/candidates.py。
3. 再补 ranker 的 4 类结果测试。
4. 再实现 core/ranker.py。
5. 再检查 rank_candidates tool 只透传结构化结果。
6. 最后处理 Hermes 插件回归边界。
7. 最后补 verification.md。
```

## 六、迭代二必须交回的证据

```text
本地 pytest 结果
远端 Hermes 验证命令和结果摘要
verification.md 草稿或正文
未完成项和风险
```
