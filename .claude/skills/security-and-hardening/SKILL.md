---
name: security-and-hardening
description: 对 Python MCP server 代码进行安全检查。Use when 处理外部输入（tool 参数、用户反馈数据）、修改文件 I/O 逻辑、新增依赖、修改 profile 存储结构、或 Hermes 插件边界变更。Use when any change touches the trust boundary between MCP client and server.
---

# 安全检查（Security and Hardening）

## 概述

安全优先的开发实践，适配 Python MCP server 场景。TasteMate 作为 MCP server，接受来自外部 AI agent 的 tool 调用，每一个 tool 参数都是不可信输入。安全不是阶段，是对每行触碰外部数据的代码的约束。

## 何时使用

- 修改 `tastemate/tools/` 中任意 tool 的参数处理逻辑
- 修改 `tastemate/schemas/` 中的校验规则
- 修改 `tastemate/storage/json_store.py` 的文件读写
- 新增或升级 `pyproject.toml` 中的依赖
- 修改 Hermes 插件（`integrations/hermes/plugins/`）的边界逻辑
- 处理用户反馈数据、candidate 数据的外部输入

**不使用的情况：** 纯文档修改、测试新增（不含实现变更）、README 更新。

## 核心流程

### 第一步：识别信任边界

TasteMate 的信任边界只有两条：

```
MCP Client (Hermes) ──[stdio]──▶ MCP Server (TasteMate)
                                      │
                                      ▼
                              ~/.tastemate/profile.json
```

1. **Tool 参数边界** — `rank_candidates`、`record_feedback`、`get_profile` 三个 tool 接收的所有参数来自外部
2. **文件 I/O 边界** — profile.json 被读写，路径可通过环境变量 `TASTEMATE_PROFILE_PATH` 覆盖

### 第二步：按边界检查

#### Tool 参数边界检查

- [ ] 所有 tool 参数在 `schemas/` 中有对应的 normalize/validate 函数
- [ ] candidate 的 `summary` 字段缺失时，系统返回 `low_confidence` 而非崩溃（已实现）
- [ ] 反馈数据中的 feature key 满足允许的字符集，防止路径遍历或注入
- [ ] 所有输入的字符串字段有长度上限
- [ ] 数值字段有合理范围限制

#### 文件 I/O 边界检查

- [ ] profile.json 的路径解析防止目录遍历（不包含 `..`）
- [ ] 写文件使用原子写入（先写临时文件再 rename），防止写一半崩溃导致数据损坏
- [ ] JSON 解析失败时有明确的错误处理，不回退到默认可变数据
- [ ] profile.json 的文件权限应为 600（只允许 owner 读写），防止其他用户读取偏好数据
- [ ] 环境变量 `TASTEMATE_PROFILE_PATH` 的值在使用前做路径合法性校验

#### 依赖安全检查

```bash
# TasteMate 用 pip 管理依赖，检查已知漏洞
pip-audit

# 检查直接依赖是否有未声明的安全更新
pip list --outdated | grep -E "cryptography|certifi|urllib3|requests"
```

- [ ] 新增依赖前审查：维护状态、下载量、是否需要 `postinstall` 等效操作
- [ ] `pyproject.toml` 中的依赖版本固定下限，不固定上限（允许安全补丁）
- [ ] 不引入仅用于"方便"的重量级依赖（每个依赖都是攻击面）

## Python 特有的安全模式

### 参数校验：Pydantic 替代 zod

TasteMate 使用 dataclass + manual validation，等价于 TypeScript 的 zod schema：

```python
# tastemate/schemas/candidates.py — 已在 trust boundary 做校验
def normalize_candidate(raw: dict) -> dict:
    """所有外部 candidate 数据进入系统前经过此函数。"""
    # SHA256 生成稳定 ID
    # 字段默认值填充
    # metadata 规范化
    ...
```

**规则：** 所有从外部进入的数据结构必须在对应的 `schemas/*.py` 中有 normalize 函数。不要在 tool 实现中直接操作 raw dict。

### 命令注入防护

```python
# BAD: 拼接外部输入到 shell 命令
import os
os.system(f"cat {user_path}")  # 路径可能是 "; rm -rf /"

# BAD: subprocess 使用 shell=True
import subprocess
subprocess.run(f"echo {user_input}", shell=True)

# GOOD: 避免 shell 调用。TasteMate 当前不调用外部命令，
# 但若后续需要，必须使用 subprocess.run([cmd, arg1, arg2], shell=False)
```

### JSON 文件安全

```python
# BAD: 解析失败时回退到可变默认值
try:
    data = json.load(f)
except json.JSONDecodeError:
    data = {"stable_preferences": {}}  # 可能隐藏存储损坏

# GOOD: 明确报告错误，不做静默回退
try:
    data = json.load(f)
except json.JSONDecodeError as e:
    raise ProfileLoadError(f"Profile JSON is corrupt: {e}") from e
```

### 路径安全

```python
# BAD: 直接使用环境变量路径
profile_path = os.environ.get("TASTEMATE_PROFILE_PATH", "~/.tastemate/profile.json")

# GOOD: 展开 ~ 并做路径规范化校验
profile_path = os.path.expanduser(
    os.environ.get("TASTEMATE_PROFILE_PATH", "~/.tastemate/profile.json")
)
# 解析为绝对路径，检查不包含 .. 遍历
real_path = os.path.realpath(profile_path)
if not real_path.startswith(os.path.expanduser("~")):
    raise ValueError(f"Profile path must be under home directory: {profile_path}")
```

### 日志安全

TasteMate 通过 stdio 与 MCP client 通信，所有 stderr 输出理论上可被 MCP client 看到：

- [ ] 不在日志中输出完整的 profile JSON（包含用户偏好）
- [ ] 错误消息不暴露内部路径或数据结构
- [ ] 使用 Python `logging` 模块，生产环境设为 WARNING 或 ERROR

## 安全检查清单

### 输入校验
- [ ] 所有 tool 参数经过 schema normalize 函数
- [ ] 字符串字段有长度上限
- [ ] 路径参数做目录遍历检查
- [ ] JSON 解析失败有明确错误处理

### 数据保护
- [ ] profile.json 文件权限 600
- [ ] 不记录完整 profile 内容到日志
- [ ] 错误响应不暴露内部路径
- [ ] 环境变量值使用前校验

### 依赖
- [ ] `pip-audit` 无 critical/high 漏洞
- [ ] 新依赖已审查维护状态和必要性
- [ ] 无仅用于便利的重量级依赖引入

### MCP 特定
- [ ] Tool 返回的错误消息不泄露系统内部信息
- [ ] Tool 参数校验失败返回结构化错误（含 error code），而非异常堆栈
- [ ] Hermes 插件收到的排序结果格式变更保持向后兼容

## 常见合理化借口

| 借口 | 现实 |
|---|---|
| "这是本地 MCP server，没有外部攻击面" | MCP client 可能被 prompt injection 诱导发送恶意参数。本地不等于可信。 |
| "参数校验后面再加" | 数据一旦进入系统，污染范围随时间扩散。在边界拦截成本最低。 |
| "profile.json 只是一些偏好标记" | 偏好数据反映用户行为模式，可被用于推断用户习惯。文件权限 600 是最低成本的防护。 |
| "Python 依赖没有 npm 那么乱" | Python 也有 typo-squatting（`requests` vs `requsts`），pip-audit 同样重要。 |
| "这点改动有什么安全问题" | 五分钟的威胁建模可以阻止事后无法补救的设计缺陷。 |

## 红旗

- Tool 参数直接用于文件路径操作
- 新增 `os.system()` 或 `subprocess.run(..., shell=True)` 调用
- profile.json 的路径拼接使用了用户可控的字符串片段
- 日志中出现了完整的字典或 JSON dumps
- 错误消息中包含了 `__file__` 或绝对路径
- `pyproject.toml` 新增了维护状态不明的依赖

## 验证

完成安全相关代码变更后：

- [ ] `pip-audit` 无 critical 或 high 漏洞
- [ ] 所有外部输入在 trust boundary 经过 normalize 函数
- [ ] profile.json 的路径使用场景没有目录遍历风险
- [ ] 错误消息不暴露内部路径或数据结构
- [ ] 新增的文件 I/O 使用了原子写入
- [ ] 敏感操作的日志级别为 DEBUG（生产环境不可见）
