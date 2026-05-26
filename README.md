# TasteMate

TasteMate 是一个面向 Hermes 的外置个人偏好层。当前版本聚焦迭代一：在用户显式使用 `@taste` 时，对 Hermes 已形成的候选结果做后置重排，并把用户反馈记录为可解释的偏好证据。

## 当前状态

```text
阶段：迭代一已完成
范围：显式 @taste 后置候选重排闭环
验证：本地测试、Hermes 插件 hook、CLI 真实入口、反馈写入链路均已验证
仓库建议：public，已移除或占位化环境敏感信息
```

## 已实现能力

- `mcp_tastemate_rank_candidates`：对候选内容进行偏好重排。
- `mcp_tastemate_record_feedback`：记录用户选择、追问、否定或明确评价。
- `mcp_tastemate_get_profile`：读取当前偏好画像摘要。
- Hermes `tastemate-route` 插件：在显式 `@taste` 消息中追加 TasteMate 工具调用指令。
- 项目流程文档：覆盖设计、开发、验证、验收和多 agent 审核流程。

## 当前不做

- 不修改 Hermes 源码。
- 不做搜索前偏好注入。
- 不做 Hermes gateway send API 直发。
- 不做 UI、多用户系统、账号体系。
- 不把 `fixed_probe_candidates` 当成正式候选来源；它只用于穿刺和端到端通道验证。

## 快速开始

```bash
python -m pip install -e '.[dev]'
python -m pytest -q
python -m tastemate.server
```

## 主要目录

```text
tastemate/                              TasteMate MCP 服务、工具、画像和排序逻辑
integrations/hermes/plugins/            Hermes 插件集成
tests/                                  自动化测试
docs/design.md                          总体设计
docs/development.md                     总体开发说明
docs/iteration-plan.md                  迭代规划
docs/iterations/iteration-001/          迭代一文档、验证记录和收尾记录
docs/process/                           项目流程、文档、验收和审核规则
```

## 文档上传说明

本仓库当前按 public GitHub 仓库发布。公开版本保留项目设计、实现、验证结论和流程文档，但环境敏感信息使用占位符表示。

公开仓库发布时，以下内容必须保持脱敏：

- 远端服务器 IP、SSH 用户、容器路径和日志路径。
- Hermes 运行环境细节。
- 临时穿刺验证记录中的原始消息、时间戳和本地路径。
- 任何个人知识库、草稿或 Obsidian 工作区内容。

## 关键文档

- [总体设计](docs/design.md)
- [开发说明](docs/development.md)
- [迭代一状态](docs/iterations/iteration-001/status.md)
- [迭代一验证](docs/iterations/iteration-001/verification.md)
- [迭代一收尾](docs/iterations/iteration-001/closeout.md)
- [项目工作流](docs/process/workflow.md)
- [审核流程](docs/process/review-loop.md)
