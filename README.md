![tripple-signals · 全网热点信号](assets/banner.png)

# tripple-signals

全网热点雷达：在热点到达大众搜索之前，从源头层抓到它。扫描频度由使用者自行定义，程序也可自行发现并更新。

方法论见 [methodology.md](methodology.md)（写给人看的完整版）。公开站点与订阅（RSS/Atom）的计划见 [ROADMAP.md](ROADMAP.md)。本仓库把它拆成 agent 能直接用的四层：

| 层 | 文件 | 作用 |
|---|---|---|
| 指令 | `skills/tripple-signals/SKILL.md` | agent 照着跑的执行步骤、判定规则、报告模板 |
| 配置 | `config.example.json` | 信息源清单、量化门槛、时区与期次——调参只动这里 |
| 工具 | `radar/` | 确定性工作交给代码：状态存储、去重、14 天复盘（抓取器见路线图） |
| 状态 | `state/seen-topics.json` | 话题台账（机器版）；`seen-topics.md` 是给人看的视图 |

设计参考 [zhuyansen/new-term-radar](https://github.com/zhuyansen/new-term-radar)：热点有传播顺序（X/HF 首发 → GitHub 爆发 → 目录/媒体 → Google Trends），雷达读前两步，Trends 只用来事后验证。

## 快速开始

```bash
cp config.example.json config.json   # 按需改源和门槛，config.json 不进 git
python -m radar review               # 列出到期该复盘的话题（14 天规则）
python -m pytest -q tests            # 逻辑测试，不碰网络
```

给 agent 用：把 `skills/tripple-signals/` 装进你的 agent（Claude Code / Codex 等），或直接让 agent 读 SKILL.md 按步骤执行。定时运行有两种方式：

- 本机/常驻 agent：用 agent 自己的调度（如 Muse 的 cron），早晚各一次——当前 Dai 的实际运行方式。
- GitHub Actions：`.github/workflows/radar.yml` 已备好骨架，设仓库变量 `RADAR_ENABLED=true` 后生效（需要先补上抓取层，见路线图）。

## 抓取层（0.3.0 扩源）

`python -m radar scan --edition morning` 跑全部抓取器，候选写入 `state/candidates-<日期>-<期次>.json`。共 19 个源，全部免费、免 key（唯一的例外是 X）：

- L1 源头层（11）：官方博客 RSS 组（OpenAI/DeepMind/Google Research/HF/Mistral/NVIDIA/AWS/GitHub Blog/BAIR，仿 [AIHOT](https://github.com/KKKKhazix/AIHOT) 的 T1 分级）、GitHub（爆发仓 Search API + Trending 页）、Hacker News（Algolia）、Show HN、Hugging Face models、HF Spaces、OpenRouter（最新上架模型）、Civitai（最新社区模型）、arXiv（最新论文）、Product Hunt（公开 Atom feed；有 `PRODUCTHUNT_TOKEN` 时走 GraphQL 取票数）、X（需 `X_BEARER_TOKEN` 且 config 里配账号，未配置时如实报缺失、由 agent 网页扫补位）。
- L2 发酵层（8）：Reddit（JSON，失败自动降级 RSS——无分数）、科技媒体 RSS 组（TechCrunch/The Verge/Ars Technica/MIT TR/The Decoder/Simon Willison/Import AI/Latent Space，AIHOT 的 T2 分级）、DEV、Lobsters、Mastodon 趋势、目录站 sitemap 组（Futurepedia/Toolify/dang.ai，借鉴 [new-term-radar](https://github.com/zhuyansen/new-term-radar) 的 sitemap 信号）、App Store 美区双榜（营销工具接口不稳时自动降级旧版 iTunes feed）、Google News（RSS）。
- **组源只算一个源**：RSS 组和 sitemap 组内部再多家，跨源共振时整组计 1——通稿被十家转述、工具被五个目录抄录，都不算多源共振。
- 2026-11-13 实测：19 个源 18 个实时出数（约 600 条候选），仅 X 缺失（无 token）。
- MCP server 已可用（`python -m radar.mcp_server`，仅标准库）：工具 `radar_scan`、`radar_review`。

## 路线图

1. **复盘自动化**：review 结果按源统计命中率，自动调整各源权重。
2. **GitHub Actions 实跑**：workflow 文件补齐后，把 scan 接进定时任务（当前雷达由 agent 侧 cron 驱动）。

## 边界

只读公开信息，不发帖、不互动；密钥只走环境变量，不进仓库。见 [PRIVACY.md](PRIVACY.md)。
