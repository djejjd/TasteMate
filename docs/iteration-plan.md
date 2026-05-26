# TasteMate 迭代规划

## 一、当前阶段

当前处于迭代一前的方案论证阶段。

目标是确认：

```text
方向是否合理
数据流是否清楚
是否能不改 Hermes 源码接入
成本是否可控
第一版要验证什么闭环
```

---

## 二、迭代一：显式启用的后置重排闭环

### 目标

实现一个最小可用的 TasteMate MCP server，让 Hermes 在用户显式使用 `@taste` 时，可以调用 TasteMate 对候选结果进行个性化排序。

### 范围

```text
MCP server
rank_candidates
record_feedback
get_profile
本地 profile store
基础评分
基础反馈学习
Hermes 配置接入
```

### 不做

```text
不改 Hermes 源码
不做搜索前偏好注入
不做自动拦截所有搜索结果
不做 UI
不做复杂模型训练
```

### 验收标准

```text
Hermes 能发现 TasteMate MCP 工具
@taste 推荐类问题能触发 rank_candidates
事实类问题能返回 passthrough
推荐类候选能输出 query_relevance、preference_fit、final_score
排序结果能解释为什么更适合我
用户明确反馈能写入 evidence_log
后续排序能体现已有反馈
```

### 主要风险

```text
Hermes 不一定稳定调用 rank_candidates
候选结果格式可能不统一
LLM 评分可能不稳定
早期偏好数据少，个性化效果有限
```

### 风险应对

```text
使用 @taste 明确触发
工具描述中明确调用时机
rank_candidates 兼容松散候选结构
所有评分必须带解释
偏好更新先写 evidence，避免学歪
```

---

## 三、迭代二：搜索前轻量偏好增强

### 目标

在迭代一闭环成立后，让 TasteMate 能在搜索前给 Hermes 提供轻量偏好上下文，提升候选召回质量。

### 可能能力

```text
pre_llm_call hook 注入偏好摘要
get_search_hints 工具
按任务生成轻量偏好关键词
负向偏好过滤提示
current_focus 注入
```

### 设计原则

```text
偏好只轻度影响搜索，不强行收窄召回。
搜索前偏好用于提示方向，最终排序仍由 rank_candidates 完成。
事实类问题不注入偏好。
```

### 验收标准

```text
推荐类问题召回候选更贴近个人偏好
事实类问题不被偏好干扰
搜索结果仍保持足够多样性
整体模型调用成本可控
```

---

## 四、迭代三：更强的 Hermes 外置编排

### 目标

如果仅靠 MCP 工具描述无法稳定触发 TasteMate，则考虑用 Hermes plugin/hook 增强编排，但仍尽量不改 Hermes 源码。

### 可能能力

```text
transform_tool_result 标记搜索结果
post_tool_call 记录候选来源
pre_llm_call 注入本轮 TasteMate 状态
自动判断是否应调用 rank_candidates
```

### 触发条件

只有当迭代一出现明显问题时才进入：

```text
Hermes 经常忘记调用 rank_candidates
候选结果无法稳定传入 TasteMate
需要更可靠地控制预算和调用顺序
```

---

## 五、长期方向

长期可以考虑：

```text
更稳定的偏好画像管理
批处理 profile updater
离线评估推荐质量
多模型成本路由
候选特征抽取缓存
轻量 embedding 检索
可视化偏好画像
```

这些不进入迭代一。

