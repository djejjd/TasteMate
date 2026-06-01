# Iteration 002 部署与使用指南

## 适用阶段

```text
Build 完成后 / Verify 前后 / 线上联调
```

## 一句话结论

```text
Iteration 002 的线上关键点只有两个：
1. 让 Hermes 能发现 tastemate MCP server
2. 不要再启用 tastemate-route 的 fixed_probe_candidates 默认入口
```

## 一、目标

```text
让 Hermes 在收到 @taste 推荐请求时，走“真实 candidates -> mcp_tastemate_rank_candidates”主路径。
```

## 二、不做事项

```text
不修改 Hermes 源码。
不删除 Hermes 原有数据。
不把 tastemate-route 固定候选插件当成 iteration-002 默认入口。
```

## 三、前提

远端 Hermes 数据目录约定如下：

```text
/opt/data/config.yaml
/opt/data/tastemate/
/opt/data/sessions/
/opt/data/logs/
```

TasteMate 代码与虚拟环境约定如下：

```text
/opt/data/tastemate/.venv/bin/python
/opt/data/tastemate/tastemate/server.py
```

## 四、部署步骤

### 1. 确认 tastemate MCP server 已配置

`/opt/data/config.yaml` 中至少应包含：

```yaml
mcp_servers:
  tastemate:
    command: /opt/data/tastemate/.venv/bin/python
    args:
      - -m
      - tastemate.server
    enabled: true
    env:
      TASTEMATE_PROFILE_PATH: /opt/data/tastemate/profile.json
```

### 2. 确认 Hermes CLI 能发现 tastemate

执行：

```bash
docker exec hermes sh -lc 'cd /opt/hermes && HERMES_HOME=/opt/data /opt/hermes/.venv/bin/hermes mcp list'
```

通过标准：

```text
MCP Servers 列表中出现 tastemate，且状态为 enabled。
```

### 3. 下线 tastemate-route 默认入口

原因：

```text
该插件是 iteration-001 的 fixed_probe_candidates 回归路径。
它会在 pre_gateway_dispatch 直接构造固定候选，阻断 iteration-002 的真实 candidates 主路径。
```

处理方式：

```text
保留插件文件，不删除。
只从 /opt/data/config.yaml 的 plugins.enabled 中移除 tastemate-route。
```

本次线上实际状态：

```yaml
plugins:
  enabled: []
  disabled: []
```

### 4. 重启 Hermes

执行：

```bash
docker restart hermes
```

### 5. 确认不再命中 fixed probe 日志

执行：

```bash
docker exec hermes sh -lc 'tail -n 10 /opt/data/logs/tastemate-route.jsonl 2>/dev/null'
```

通过标准：

```text
不再出现新的 candidate_source=fixed_probe_candidates 记录。
```

## 五、为了更稳定看到效果的使用建议

### 1. 推荐类请求尽量写清 3 个元素

建议同时给出：

```text
1. 任务对象：你要推荐什么
2. 选择维度：你最在意什么
3. 明确约束：哪些不要
```

推荐写法：

```text
@taste 推荐几个适合我的本地知识库工具。
我更看重：本地优先、开源、低维护成本。
我不想要：强团队协作导向、重 SaaS 依赖。
```

原因：

```text
当前 iteration-002 的排序效果高度依赖 Hermes 整理 candidates 的质量。
请求越具体，Hermes 给 TasteMate 的候选越稳定，排序结果越可解释。
```

### 2. 如果你已经有候选，优先走 A-001

更稳的实验方式是：

```text
先自己给出 3 到 5 个候选，再让 @taste 排序。
```

例如：

```text
@taste 请基于以下候选帮我排序：Obsidian、Logseq、Anytype、Joplin。
我更看重：本地优先、开源、移动端可用。
```

原因：

```text
A-001 的不确定性最低。
它主要验证 TasteMate 的排序逻辑，而不是 Hermes 的候选发现质量。
```

### 3. A-002 更适合测“整体体验”，不适合先测精度

如果你要观察：

```text
Hermes 能不能自己整理真实候选，再交给 TasteMate 排序
```

就用 A-002。

如果你要观察：

```text
TasteMate 对同一组候选能不能稳定体现偏好差异
```

优先用 A-001。

### 4. 同一类实验不要一次塞太多偏好

推荐一次只给 2 到 3 个高优先级偏好，例如：

```text
本地优先
开源优先
不要企业 SaaS 风格
```

不要一轮里同时塞入 8 到 10 个偏好维度。

原因：

```text
当前 profile 仍是保守画像，不适合承载过多细碎偏好。
过多约束会让实验结果更难解释，到底是候选问题还是偏好冲突问题也会变得不清楚。
```

## 六、是否需要先补录基础偏好信息

一句话结论：

```text
不是必须，但建议做一轮轻量预热，比直接手工改 profile.json 更合适。
```

### 不建议的方式

```text
直接手工编辑 stable_preferences / negative_preferences
```

原因：

```text
当前 iteration-001 / iteration-002 的画像更新口径是“先写 evidence_log，再保守影响排序”。
直接手改 profile.json 会让后续实验难以区分：
到底是自然反馈形成的偏好，还是人工注入的结果。
```

### 更推荐的方式

做 3 轮以内的小样本预热，每轮都给明确反馈。

推荐顺序：

```text
1. 先发一个 A-001 请求，给出 3 到 5 个你熟悉的候选
2. 看排序结果
3. 再补一句明确反馈
```

推荐反馈样式：

```text
这次我更倾向第一个，因为我更看重本地优先和低维护。
排除第三个，因为它太像团队 SaaS，不符合我的使用习惯。
```

当前实现下，更容易沉淀成 evidence 的反馈要满足两个条件：

```text
1. 明确选中或排除某个候选
2. 反馈文本里带出偏好原因
```

原因：

```text
record_feedback 当前只有在同时拿到 user_feedback + selected_candidate_ids/rejected_candidate_ids 时才会判定 feedback_valid=true。
如果只有“还不错”“一般般”这类泛反馈，没有明确选中/排除对象，evidence 很可能不会成立。
```

### 推荐优先补录的基础偏好

如果你确实要做预热，优先只测这些高价值维度：

```text
1. 本地优先 vs 云依赖
2. 开源优先 vs 闭源可接受
3. 个人工具 vs 团队/企业 SaaS
4. 低维护成本 vs 高可定制性
5. 移动端需要 vs 仅桌面可接受
```

这些维度的好处是：

```text
它们容易映射到 candidate metadata 和 summary，
也更容易在排序理由里观察到差异。
```

### 什么时候值得补录

满足任一情况就值得做一轮预热：

```text
1. 你要连续做同一类推荐实验
2. 你已经知道自己有几个非常稳定的长期偏好
3. 你希望 A-002 的结果更快体现“像你”的排序倾向
```

### 什么时候没必要补录

```text
1. 你只是验证链路是否打通
2. 你只是比较候选协议和排序输出结构
3. 你当前还没想清自己的长期偏好是什么
```

这种情况下，直接跑 A-001 / A-002 即可。

## 七、实验建议

推荐按这个顺序做实验：

```text
第一步：A-001，无画像预热
第二步：A-001，同类请求 + 明确反馈 1 到 2 次
第三步：A-002，观察 Hermes 自发现候选时是否开始体现偏好
```

这样能把问题拆开：

```text
1. 排序器本身是否工作
2. feedback 是否开始起作用
3. Hermes 候选整理质量是否影响最终效果
```

## 八、反馈与 evidence 操作指南

先说明边界：

```text
本节主要用于实验指导。
其中关于 feedback_valid、关键词抽取和 profile 写入的描述，来自当前 TasteMate record_feedback 工具实现。
这不等于 iteration-002 已经把“上一轮 @taste 结果 -> Hermes 自动识别反馈 -> 远端写入 evidence”整条链路做成阻塞验收项。
如果你要验证这条反馈链路，建议单独做实验并直接检查 profile.json。
```

### 1. 反馈要在上一轮 @taste 结果之后立刻给

推荐方式：

```text
上一条是 @taste 排序结果
下一条立刻补反馈
```

示例：

```text
用户：@taste 请基于以下候选帮我排序：Obsidian、Logseq、Anytype
Hermes：返回排序结果
用户：我选 Logseq，主要因为我更看重开源和本地优先；Anytype 我先不选，因为我不想要这种半开源方案。
```

原因：

```text
工具层面要求明确，但是否真正触发远端 feedback 链路，还依赖 Hermes 能否识别“这是上一轮 @taste 推荐的后续反馈”。
隔太久、换太多话题、跨太多轮之后，再补反馈，实验成功率会下降。
```

### 2. 最有效的反馈结构

推荐按这个句式给：

```text
我选 <候选名>，因为 <偏好原因>。
我排除 <候选名>，因为 <排除原因>。
```

比“感觉不错”“这个不太行”更有效。

### 3. 当前最容易被识别的偏好关键词

当前 `FeedbackProcessor` 工具实现里，规则抽取最稳的是这几类：

```text
本地 / local -> local_first
开源 / open source -> open_source
cloud / SaaS -> cloud_required
```

所以更推荐写成：

```text
我选 Logseq，因为我更看重开源和本地优先。
我不选 Notion，因为我不想依赖 SaaS。
```

而不是：

```text
这个气质更对。
那个感觉不太搭。
```

### 4. 可直接复制的反馈示例

#### 示例 1：本地优先 + 开源优先

```text
我选 Logseq，因为我更看重本地优先和开源。
Obsidian 我先不选，因为核心闭源。
```

#### 示例 2：排除企业 SaaS

```text
我不要这种团队协作 / 企业 SaaS 风格的工具。
如果必须联网、强依赖云服务，我会降权。
```

#### 示例 3：低维护成本优先

```text
我更倾向第一个，因为我希望低维护、少折腾。
需要复杂自建和持续配置的方案，对我吸引力会下降。
```

#### 示例 4：移动端是硬约束

```text
我会优先选移动端体验完整的候选。
如果只有桌面端可用，我一般不会选。
```

### 5. 当前不太推荐的反馈写法

```text
第一个不错。
这个更顺眼。
第二个差点意思。
都还行。
```

问题是：

```text
1. 没明确说选中/排除谁
2. 没说偏好原因
3. 很难形成稳定 feature evidence
```

### 6. 怎么判断 evidence 有没有写进去

先看轻量信号：

```text
1. get_profile 的 summary / current_focus 出现最新反馈内容
2. 后续同类排序里，可能开始出现“历史反馈对 xxx 有正向/负向信号”
```

说明：

```text
第 2 条更适合当观察信号，不建议把它当成唯一证明。
当前最直接的核对方式仍然是查看 profile.json。
```

如果要看更硬的证据，直接检查 profile 文件：

```bash
docker exec hermes sh -lc 'cat /opt/data/tastemate/profile.json'
```

重点看：

```text
evidence_log
current_focus.last_feedback
current_focus.last_query
```

说明：

```text
当前 get_profile 返回 stable_preferences / negative_preferences / current_focus / summary，
不会直接把 evidence_log 全量吐出来。
如果你要核对每条 evidence，还是看 profile.json 最直接。
```

### 7. 一个最小可行的 evidence 预热流程

推荐按下面 4 步执行：

```text
1. 发一个 A-001 请求，给出 3 到 5 个候选
2. 读取排序结果
3. 立刻补一条“我选谁 / 我排除谁 / 为什么”的反馈
4. 再跑一次同类 A-001 或 A-002，看排序理由是否出现历史反馈信号
```

如果这一轮只是想确认 feedback 是否真的写入，推荐额外执行：

```bash
docker exec hermes sh -lc 'cat /opt/data/tastemate/profile.json'
```

## 九、可直接复制的实验话术

### 话术 1：链路验证

```text
@taste 请基于以下候选帮我排序：Obsidian、Logseq、Anytype、Joplin。
我更看重：本地优先、开源、低维护成本。
```

### 话术 2：A-001 预热 + 反馈

第一轮：

```text
@taste 请基于以下候选帮我排序：Obsidian、Logseq、Anytype。
我更看重：本地优先、开源。
```

第二轮反馈：

```text
我选 Logseq，因为我更看重开源和本地优先。
Anytype 我先不选，因为我不想要这种半开源方案。
```

第三轮复测：

```text
@taste 再帮我比较一下 Logseq、Anytype、Joplin。
我还是更看重：本地优先、开源、低维护。
```

### 话术 3：A-002 整体体验实验

```text
@taste 推荐几个适合我的本地知识库工具。
我更看重：本地优先、开源、低维护。
我不想要：企业 SaaS 风格、强团队协作导向。
```

### 话术 4：排除云依赖

```text
@taste 推荐几个适合我的工具。
我更看重：本地优先、可离线使用。
我不想要：强依赖 cloud / SaaS 的方案。
```

## 十、A-001：用户显式给候选

示例：

```text
@taste 请基于以下候选帮我排序：Obsidian、Logseq、Anytype。我的诉求是本地优先、开源优先。
```

期望行为：

```text
Hermes 明确整理 candidates 数组，并调用 mcp_tastemate_rank_candidates。
```

## 十一、A-002：Hermes 自己整理真实候选

示例：

```text
@taste 推荐几个适合我的本地知识库工具，要求本地优先、隐私友好。
```

期望行为：

```text
Hermes 先整理 3 到 5 个真实候选，再调用 mcp_tastemate_rank_candidates。
```

## 十二、验收命令

推荐至少执行以下检查：

```bash
docker exec hermes sh -lc 'cd /opt/hermes && HERMES_HOME=/opt/data /opt/hermes/.venv/bin/hermes mcp list'
docker exec hermes sh -lc 'ls -1t /opt/data/sessions/session_*.json | head -n 3'
docker exec hermes sh -lc 'tail -n 10 /opt/data/logs/tastemate-route.jsonl 2>/dev/null'
```

验收证据应至少包含：

```text
1. session 中出现 mcp_tastemate_rank_candidates
2. tool call 参数里包含 candidates
3. structuredContent.action 为 ranked / needs_more_candidates / invalid_candidates 之一
4. 没有新的 fixed_probe_candidates 主路径记录
```

## 十三、回退方案

如果需要临时回退到 iteration-001 固定候选探针：

```text
1. 恢复 /opt/data/config.yaml 备份
2. 把 tastemate-route 加回 plugins.enabled
3. docker restart hermes
```

说明：

```text
这只适用于回归验证，不适合作为 iteration-002 默认线上入口。
```

## 十四、当前已验证结果

```text
A-001:
- session_20260528_002333_9b377c.json
- mcp_tastemate_rank_candidates 已调用
- candidates=3
- action=ranked

A-002:
- session_20260528_002333_46440c.json
- mcp_tastemate_get_profile -> mcp_tastemate_rank_candidates
- candidates=5
- action=ranked
```
