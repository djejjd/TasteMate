# 验收标准规则

## 一、验收依据

验收不能基于临时聊天结论，也不能基于模型自我判断。

验收依据按优先级为：

```text
1. 已确认的设计文档
2. 当前迭代规划
3. Development Spec 开发约定
4. 开发计划
5. 测试和手工验证记录
6. 多 agent 审核结论
```

设计文档决定方向，迭代规划决定当前边界，Development Spec 决定实现约定，验证记录证明是否完成。

---

## 二、验收标准写法

每条验收标准必须：

```text
可判断
可验证
有通过条件
有失败条件
不依赖主观感觉
```

禁止写法：

```text
排序效果较好
代码结构合理
用户体验不错
性能可以接受
```

推荐写法：

```text
A-001 未使用 @taste 时 TasteMate 不介入。
验证方式：运行普通问题，观察无 mcp_tastemate_* 工具调用。
通过条件：没有 TasteMate 工具调用。
失败条件：出现任何 TasteMate 工具调用。
```

---

## 三、标准模板

```text
ID：
描述：
验证方式：
通过条件：
失败条件：
适用阶段：
```

示例：

```text
A-002
描述：@taste 推荐类问题必须触发 rank_candidates。
验证方式：输入 @taste 推荐几个适合我的本地知识库工具。
通过条件：Hermes 调用 mcp_tastemate_rank_candidates，并返回 ranked 或 needs_more_candidates。
失败条件：Hermes 直接回答且未调用 TasteMate。
适用阶段：迭代一。
```

---

## 四、TasteMate 迭代一验收基线

迭代一至少包含：

```text
A-001 未使用 @taste 时 TasteMate 不介入。
A-002 @taste 推荐类问题必须触发 rank_candidates。
A-003 事实类问题必须返回 passthrough。
A-004 候选不足时必须返回 needs_more_candidates 和 suggested_search_hints。
A-005 推荐类候选必须输出 query_relevance、preference_fit、final_score。
A-006 用户明确反馈必须写入 evidence_log。
A-007 单次反馈必须先写 evidence_log，不得新增 stable_preferences 条目；任一 stable_preferences 权重提升不得超过 0.10；任一 stable_preferences confidence 不得设置到 0.70 以上。
A-008 不修改 Hermes 源码。
```

每条验收标准必须在开发计划或验证记录中给出对应验证方式。

---

## 五、验收结论

验收结论只能是：

```text
ACCEPTED：全部阻塞验收标准通过。
BLOCKED：存在未通过的阻塞验收标准。
ACCEPTED_WITH_FOLLOW_UP：阻塞标准通过，但存在后续事项。
```

如果存在未验证项，不能输出 `ACCEPTED`。
