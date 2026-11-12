---
name: tripple-signals
description: Run one edition (morning/evening) of the twice-daily web hot-topic radar — scan layered sources, judge signals against fixed thresholds, dedupe against the topic store, and emit the report in the fixed format.
---

# Tripple Signals — 执行指令

完整方法论在仓库根目录 `methodology.md`。本文件是可执行版：照步骤跑，不要自由发挥结构。

## 输入

- `config.json`（没有就用 `config.example.json`）：信息源、门槛、期次、时区都在里面，**不要把门槛硬编码在脑子里**。
- `state/seen-topics.json`：话题台账。先读，再扫。
- 期次：morning（06:00 JST，分工见 config）或 evening（18:00 JST）。

## 步骤

0. **先跑抓取层**：`python -m radar scan --edition <morning|evening>`，读它写出的 `state/candidates-<日期>-<期次>.json` 作为候选底稿；状态为 missing 的源（通常是 X、Product Hunt，以及当期失败的源）再用网页扫补齐，并在报告里如实标注哪些源是代码抓的、哪些是网页扫的。
1. **按层扫源**（顺序不可颠倒，这是方法论的核心）：
   - L1 源头层：X（Trending + config 中账号的新名字）、GitHub（Trending + 爆发仓库）、Hacker News（首页/高分新帖）、Hugging Face（Trending 前 50 新面孔）、Product Hunt（当日新品）。
   - L2 发酵层：Reddit（config 的版块，rising/热帖；留意 “is there a tool that…” 式需求）、Google News（科技/AI 头条）。
   - L3 验证层：Google Trends **只**核对已入选话题的曲线，禁止用它发现话题。
   - 某个源查不到：记入报告「本期缺失」，禁止用其他源内容冒充。
2. **判定信号**（用 config 的门槛）：
   - 同一话题 ≥ `min_sources_for_hotspot` 个独立源 = 热点候选；单源 = 苗头。
   - GitHub：年龄与 stars 增速按 config 的 github 规则；X：按 config 的 x 规则；HN/Reddit：进首页/rising 前列。
   - 只保留「具体的新东西」（新模型/产品/仓库/事件名）；泛词（dashboard、pricing 之类）一律丢弃。
3. **打分分级**：共振度、增速（对比台账里上次等级）、新鲜度、与 config `relevance_topics` 的相关性 → 🔥必看 / 👀关注 / 🌱苗头。全期最多 `max_items_per_report` 条，苗头最多 `max_seedlings` 条。
4. **去重**：台账里已有的话题不重复介绍背景，只报状态变化（升级/降温/消亡）；新话题标 🆕。
5. **写回状态**：每条入选话题用 `radar/store.py` 的 `upsert_topic` 更新台账（首次发现时间、来源、等级轨迹）。
6. **出报告**：严格用下方模板。每个数字必须带出处；禁止「爆火」「刷屏」等无量词形容；建议动作只给判断，不替用户做决定。

## 报告模板

```
📰 热点雷达 · {早报|晚报} {YYYY-MM-DD} {HH:MM} JST

🔥 必看（n 条）
1. {话题一句话} — {为什么热，带关键数字}
   来源：{源列表}（附链接）
   建议动作：写 tweet / 深入研究 / 立项观察 / 仅记录

👀 关注（n 条）
（同上格式）

🌱 苗头（n 条）
- {话题} — {单源信号一句话}

📈 今日变化（仅晚报）
- {老话题}：{涨/平/凉 + 依据}

⚠️ 本期缺失：{查不到的源，没有就写「无」}
```

## 红线

- 只读公开信息；不发帖、不点赞、不互动。
- 不编造数字、链接、账号动态；没查到就写缺失。
- 不改 `config.json` 和门槛来「凑」结果；觉得门槛不合理，在报告末尾提一句建议即可。
