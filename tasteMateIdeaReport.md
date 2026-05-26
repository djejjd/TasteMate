# TasteMate

## AI 个人口味画像与跨内容推荐助手

---

# 一、项目定位

TasteMate 是一个：

> 基于用户长期兴趣与内容消费行为的 AI 私人品味助手。

它不是传统“音乐推荐器”，而是：

```text
跨音乐 / 视频 / 电影 / 书籍 / 文章 / 播客
统一建模的 AI 兴趣画像系统
```

核心目标：

```text
理解用户“为什么喜欢”
而不仅是“喜欢了什么”
```

---

# 二、核心 Idea

## 传统推荐系统的问题

传统推荐系统：

```text
猜你喜欢
```

本质上：

```text
用户A喜欢X
用户B也喜欢X
→ 给A推荐B喜欢的东西
```

但它：

* 不理解“品味”
* 不理解“情绪”
* 不理解“场景”
* 无法跨领域关联

例如：

```text
喜欢周杰伦的人
为什么可能喜欢：
王家卫
深夜咖啡馆
LoFi
赛博朋克电影
```

传统系统很难解释。

---

# 三、TasteMate 的核心方向

## 从“内容推荐”

升级为：

# “Taste AI（品味 AI）”

即：

```text
用户长期兴趣
↓
人格/审美/情绪画像
↓
跨内容关联
↓
个性化推荐与解释
```

---

# 四、系统目标

## 1. 用户兴趣画像

例如：

```text
你的兴趣人格：
- 深夜都市感偏好
- 情绪驱动型
- 科技未来感偏好
- 偏爱强创作者风格
- 喜欢“有氛围感”的内容
```

---

## 2. 跨领域推荐

例如：

用户输入：

```text
喜欢：
周杰伦
王家卫
三体
黑镜
AI 视频
```

系统推荐：

```text
音乐：
电子氛围 / 华语R&B

电影：
银翼杀手2049

书：
你一生的故事

视频：
AI 纪录片

地点：
深夜咖啡馆
```

---

## 3. 场景推荐

例如：

```text
最近压力很大
```

系统：

```text
推荐：
- 低能量音乐
- 放松视频
- 轻阅读
- 夜晚散步路线
```

---

# 五、推荐系统核心理论

推荐系统主要有 3 类。

---

## 1. Content-Based（内容推荐）

根据内容特征推荐。

例如：

```text
喜欢周杰伦
→ 推荐陶喆
```

因为：

```text
R&B
华语
旋律型
怀旧
```

特征相似。

---

## 2. Collaborative Filtering（协同过滤）

根据用户行为推荐。

例如：

```text
与你兴趣相似的人
还喜欢什么
```

Spotify/网易云核心逻辑之一。

---

## 3. Hybrid Recommendation（混合推荐）

现代主流方案：

```text
Content-Based
+
Collaborative Filtering
+
Embedding
+
LLM
```

Spotify 类系统大多采用 Hybrid。

---

# 六、TasteMate 推荐架构

建议采用：

# Hybrid + Embedding + LLM

架构。

---

# 七、推荐技术架构

```text
微信 / Hermes / Web
        ↓
FastAPI Gateway
        ↓
用户兴趣分析
        ↓
Embedding Engine
        ↓
向量数据库 Qdrant
        ↓
推荐召回层
        ↓
LLM解释层
        ↓
推荐结果
```

---

# 八、核心模块设计

## 1. Item 内容库

统一所有内容结构：

```json
{
  "id": "001",
  "type": "music",
  "title": "晴天",
  "creator": "周杰伦",
  "tags": ["华语", "青春", "怀旧"],
  "mood": ["温柔"],
  "scene": ["夜晚"],
  "summary": "青春回忆感强的华语流行歌曲"
}
```

支持：

```text
music
movie
book
video
article
podcast
game
```

---

## 2. User Taste Profile（用户画像）

例如：

```json
{
  "mood_preference": ["怀旧", "都市"],
  "style_preference": ["赛博朋克", "LoFi"],
  "energy_level": "low",
  "creator_bias": ["强个人风格"],
  "favorite_tags": ["科技", "未来感"]
}
```

---

## 3. Embedding 向量层

把：

```text
用户
内容
标签
情绪
场景
```

全部向量化。

例如：

```text
周杰伦 -> [0.22, -0.18, ...]
王家卫 -> [0.20, -0.21, ...]
```

向量越近：

```text
品味越接近
```

---

## 4. 推荐召回层

推荐方式：

| 类型                      | 作用    |
| ----------------------- | ----- |
| Content-Based           | 相似内容  |
| Collaborative Filtering | 相似用户  |
| Trending                | 热门趋势  |
| Mood Recall             | 情绪推荐  |
| Cross-Domain            | 跨领域推荐 |

---

## 5. LLM Explain Layer

这是 TasteMate 最大亮点。

例如：

```text
为什么推荐？

因为你长期偏爱：
- 深夜都市感
- 怀旧
- 强氛围感
- 情绪驱动内容
```

这会让推荐：

# “有灵魂”

---

# 九、推荐技术栈

## 后端

推荐：

| 技术         | 用途    |
| ---------- | ----- |
| FastAPI    | API服务 |
| PostgreSQL | 用户数据  |
| Redis      | 缓存    |
| Qdrant     | 向量数据库 |
| Celery     | 异步任务  |

---

## AI 层

| 技术                    | 用途          |
| --------------------- | ----------- |
| OpenAI Embedding      | 向量化         |
| GPT-5.5               | 画像/解释       |
| DeepSeek              | 低成本推理       |
| sentence-transformers | 本地embedding |

---

## 推荐算法

| 技术                   | 阶段   |
| -------------------- | ---- |
| Cosine Similarity    | MVP  |
| LightFM              | 第二阶段 |
| Matrix Factorization | 第二阶段 |
| Two Tower            | 后期   |
| Graph Recommendation | 高级阶段 |

---

# 十、推荐数据库

## 第一阶段

```text
JSON
SQLite
```

即可。

---

## 第二阶段

建议：

# Qdrant

原因：

* 轻量
* AI Native
* Docker 方便
* 和 Hermes 非常搭

---

# 十一、推荐参考项目

## 1. Microsoft Recommenders

GitHub：
[https://github.com/recommenders-team/recommenders](https://github.com/recommenders-team/recommenders)

推荐系统“教科书级”项目。

包含：

```text
协同过滤
矩阵分解
深度推荐
embedding
ranking
evaluation
```

非常适合作为：

# 技术基座

---

## 2. Hybrid Music Recommendation System

GitHub：
[https://github.com/indranil143/Hybrid-Music-Recommendation-System](https://github.com/indranil143/Hybrid-Music-Recommendation-System)

最适合 MVP 参考。

包含：

```text
Content-Based
Collaborative Filtering
LightFM
Spotify Audio Features
```

已经很接近真实产品结构。

---

## 3. Spotify Recommendation System

GitHub：
[https://github.com/unkletam/Spotify-Recommendation-System](https://github.com/unkletam/Spotify-Recommendation-System)

适合理解：

```text
Embedding
Cosine Similarity
内容推荐
```

---

## 4. Cross Domain Recommendation Topics

GitHub：
[https://github.com/topics/cross-domain-recommendation](https://github.com/topics/cross-domain-recommendation)

非常重要。

因为项目核心：

# 跨领域推荐

---

## 5. Microsoft RecAI

GitHub：
[https://github.com/microsoft/RecAI](https://github.com/microsoft/RecAI)

这是：

# LLM + 推荐系统

方向。

未来一定会走这里。

---

# 十二、商业方向参考

## Qloo（非常重要）

Qloo 做的就是：

# Taste AI

跨领域兴趣关联：

```text
音乐
电影
餐厅
地点
旅行
艺术
```

统一建模。

TasteMate 的长期方向和它非常像。

---

# 十三、系统演进路线

## 第一阶段（1周）

目标：

# 做 MVP

功能：

```text
输入喜欢内容
→ 输出兴趣画像
→ 推荐内容
→ AI解释
```

技术：

```text
FastAPI
JSON
Embedding
Cosine Similarity
```

---

## 第二阶段（2~3周）

加入：

```text
Qdrant
用户历史
反馈机制
向量检索
```

---

## 第三阶段

加入：

```text
微信入口
Hermes Agent
长期记忆
```

---

## 第四阶段

加入：

```text
协同过滤
LightFM
Graph Recommendation
```

---

# 十四、真正核心壁垒

不是模型。

而是：

# 用户长期行为数据

例如：

```text
收藏
跳过
停留时间
深夜偏好
循环播放
```

这些会形成：

# Taste Graph（品味图谱）

---

# 十五、最终产品形态

TasteMate 最终不是：

```text
推荐系统
```

而是：

# AI Taste Companion

AI 品味陪伴助手。

它会：

```text
越来越懂你
越来越理解你的兴趣变化
甚至理解你的情绪状态
```

---

# 十六、为什么这个方向值得做

因为：

## AI 正在改变推荐系统

传统推荐：

```text
猜你喜欢
```

AI 推荐：

```text
理解你为什么喜欢
```

这是非常大的方向变化。

---

# 十七、当前最推荐的落地方向

先做：

```text
MVP + AI画像 + Embedding推荐
```

不要一开始陷进：

```text
大模型训练
复杂推荐算法
工业级架构
```

真正核心：

# “Taste Profile + AI Explainability”

这是 TasteMate 最有价值的地方。
