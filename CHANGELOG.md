# Changelog

## 0.5.1 — 2026-11-13

- 项目改名 **tripple-signals → triple-sigma**（仓库由 Dai 在 GitHub Settings 改名，旧地址自动重定向；token 按仓库 ID 授权，不受影响）：仓库内全部标识同步更换——README/ROADMAP、plugin 与技能目录 `skills/triple-sigma`、MCP server 名、抓取器 User-Agent、pyproject 包名、横幅 SVG/PNG 的字标、站点标题与 feed 标题。历史条目与期次内容不改。
- 站点 canonical 地址改回 `https://daiyanze.github.io/triple-sigma`：daiyanze.com 的 DNS 在 Cloudflare（个人站），GitHub 账号侧残留的同名自定义域名配置会把 github.io 的访问重定向过去并 404；该残留配置的清理（或改用子域名）待 Dai 决定，见仓库设置说明。

## 0.5.0 — 2026-11-13

继续借鉴 new-term-radar 还没借的三件（其付费部分——AIsa 链接图谱、DataForSEO 关键词量——不借）：

- **新词词汇表**（`radar/vocab.py`）：new-term-radar 的核心机制是维护滚动词汇表、只认「第一次被说出口」的名字。本仓库没有 X 火箭筒，改为落在实体型源上（GitHub / HF / HF Spaces / OpenRouter / Civitai / Product Hunt / 目录站 / App Store）：名字在 `vocab.window_days`（默认 60）内没在候选流出现过 → 候选打 `"novel": true`，状态存 `state/vocab.json`。第一次运行只建基线、不打标。实测：基线 268 个名字，第二轮即标出 2 个新名字（OpenRouter 新模型、Product Hunt 新品）。
- **sitemap 快照 diff**：从「lastmod 时间窗口」改为快照比对（`state/sitemap-seen.json` 按目录留档全部见过的工具页 URL，90 天未现自动遗忘），只报新 URL，同一工具永不重复播报。第一次运行每个目录只建基线（note 里列出各目录基线量）。实测 12 家基线共约 6 万个 URL；对照实验中人为从快照删掉的 3 个 URL 被精确地作为新条目报回。
- **目录站 3 → 12 家**：新增 Glama、mcp.so、LobeHub MCP、LobeHub Skills、Aixploria、OpenTools、Clipfly、aitoptools、ai-bot.cn（逐个实测结构后定 pattern）。索引分片解析泛化：支持多组 shard_patterns（Glama 的 servers + remote-servers）、非数字分片按文档顺序（OpenTools 的命名分片）、`?section=…&page=N` 分页（mcp.so）。顺带修三个实测发现的问题：无时区 lastmod 与带时区的混排会崩（已统一补 UTC 并加回归测试）；Toolify 最新分片含多语言路径（`/de/tool/…`）导致同一工具多语言重复（pattern 改锚定域名，与 LobeHub 的处理一致）；slug 里的百分号编码统一解码再生成名字。
- 注意：升级后第一次扫描，sitemap 组不出条目（建基线）、vocab 不打标，属预期行为，报告 note 与候选文件里都有说明。测试增至 44 个，全过。

## 0.4.0 — 2026-11-13

- 配置迁 YAML：新增 `config.example.yaml`（带注释），加载顺序 config.yaml > config.yml > config.json > config.example.*，旧 JSON 配置照常可读；`config.example.json` 改为由 YAML 生成的镜像（文件内有标注）。解析优先用 PyYAML（装了的话），否则用内置子集解析器 `radar/yamlmini.py`——零依赖不变，两个解析器对示例配置的输出经测试逐字节一致（结构相等）。
- 用户可控选项（抓取后、共振分组前由代码执行，分级仍归 agent）：`keywords.mute` 屏蔽词（命中丢弃）、`keywords.boost` 关注词（打标，单源可升一级）、`keywords.alert` 必看词（打标并汇入候选文件 `keyword_alerts`）；`topics` 主题权重（取代平铺的相关性列表，旧写法兼容）；每源 `enabled: false` 关源（状态单列 disabled，不算缺失、不补扫）与 `max_items` 抓后截断（避开与各源既有 `limit` 抓取参数重名）；`filters.max_age_hours` 新鲜度窗口（只过滤带可解析时间戳的候选）。
- 一键 CLI：`python -m radar` 无参即扫描（按本地钟点自动选期次），`scan --edition` 改为可选；新增 `pyproject.toml`，`pip install -e .` 后可用 `radar` 命令（零依赖）。`--config` 在子命令前后均可传。
- 实测演示（临时配置）：mute/boost/alert + max_age_hours=72 + 关 Civitai + arXiv max_items=5 一轮跑通——stale 丢弃 94 条、boost 打标 3 条、alert 命中 22 条（Gemini 发布周）、关源与截断均按预期生效。测试增至 38 个，全过。

## 0.3.1 — 2026-11-13

- 新增 3 个英文免费源（22 个源，21 个免 key）：HF Daily Papers（L1，HF 社区票选论文，arXiv 的已筛选版）、Bluesky（L1，配置账号的公开 RSS——搜索 API 要鉴权，账号 RSS 是免 key 的路；默认 7 个账号均逐个实测有帖才收录，含 Simon Willison、Karpathy、Greg Brockman 与 4 家媒体）、Wikipedia 热读榜（L2，英文维基昨日浏览 Top，过滤元页面；大众注意力确认 + 社会观察供稿）。
- 本轮按使用者选择只接英文源：实测可用的中文源（Bilibili 热门、V2EX、少数派）暂不接，记录在方法论第八节。
- 测试增至 31 个，全过；实测 22 个源 21 个出数，仅 X 缺失。

## 0.3.0 — 2026-11-13

- 信息源从 7 个扩到 19 个，新增 12 个抓取器，全部免费、免 key（参考 new-term-radar 与 AIHOT 的信源设计，逐个实测可用后才接）：
  - L1 新增：官方博客 RSS 组（9 家实验室/公司，仿 AIHOT 的 T1 分级）、Show HN、HF Spaces、OpenRouter 最新模型、Civitai 最新模型、arXiv 最新论文。
  - L2 新增：科技媒体 RSS 组（5 家媒体 + 3 位独立作者，AIHOT 的 T2 分级）、DEV、Lobsters、Mastodon 趋势、目录站 sitemap 组（Futurepedia/Toolify/dang.ai，借鉴 new-term-radar 的 sitemap 信号）、App Store 美区双榜。
  - Product Hunt 不再依赖 token：无 token 时走公开 Atom feed（无票数，结果里注明）。
- 防假共振：RSS 组与 sitemap 组整组只算 1 个源（方法论与 SKILL 同步写明）。
- 共振分组降噪：停用词扩充（英文虚词与泛动词）、单 token 条目上限 12、按源数排序后只保留最强的 60 组——候选约 600 条时 junk 组从 292 降到可用量级。
- 健壮性：common 层透明解 gzip（DeepMind 的 feed 按 UA 返回 gzip 导致解析失败，已修）；App Store 营销工具接口 502 时自动降级旧版 iTunes feed。
- 实测（2026-11-13）：19 个源 18 个实时出数，仅 X 缺失（无 token，仍由 agent 网页扫补位）；测试从 13 增至 28 个，全过。
- 没接的（实测不可用，记录在方法论第八节）：Stack Exchange API（出口 IP 被限流）、Bluesky 公开搜索（403）、Microsoft Research RSS（403）。
- 顺手清掉 plugin.json 描述里写死的 "Twice-daily"（频度由使用者定义，不写进产品文案）。

## 0.2.1 — 2026-11-12

- Renamed the project from hot-news-radar to tripple-signals: repository, plugin name, skill folder (`skills/tripple-signals/`), MCP server name and fetcher user-agent now all carry the new name. No behaviour changes.

## 0.2.0 — 2026-11-12

- 抓取层落地：`radar/fetchers/`（GitHub 爆发仓+Trending、HN、Hugging Face、Reddit JSON/RSS、Google News RSS 为实抓；Product Hunt 与 X 需 token，未配置时如实报缺失、由 agent 网页扫补位）。
- `python -m radar scan --edition morning|evening`：跑全部抓取器，候选写入 `state/candidates-<日期>-<期次>.json`，附初步跨源共振分组（只提示可能性，分级仍归 agent）。
- MCP server 从占位变成最小可用实现（stdio、仅标准库）：`radar_scan` / `radar_review` 两个工具，冒烟测试通过。
- 测试增至 13 个（解析函数 + 存储），全部通过；实测 scan：7 个源中 5 个实时出数。

## 0.1.0 — 2026-11-11

- 骨架：方法论（methodology.md）、agent 指令（skills/hot-news-radar/SKILL.md）、配置示例、状态存储（radar/store.py）、14 天复盘 CLI、GitHub Actions 骨架。
- 未包含：各信息源抓取器、MCP server 实现（见 README 路线图）。
