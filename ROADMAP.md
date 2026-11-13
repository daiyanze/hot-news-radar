# Roadmap：从内部雷达工具到可订阅的公开站点

## 目标

把现在只发回聊天的早晚报，变成一个任何人都能打开、能用 RSS/Atom 订阅的静态站点：

- 站点首页：最新一期 + 历史归档
- 每期一个独立页面（永久链接，可分享）
- 订阅源：`/feed.xml`（RSS 2.0）和 `/atom.xml`（Atom 1.0），每期一条，全文入源，订阅者在阅读器里直接读完
- 后期：每个话题一页（利用台账里已有的等级变化历史，看一个话题怎么从 🌱 苗头涨成 🔥 必看）

## 终局架构

```
agent 扫描（现有早晚两次运行）
  → 写结构化期次文件 editions/YYYY-MM-DD-{morning,evening}.json（唯一事实源）
  → radar/publish.py 静态生成（Python，无框架）
  → site/（index、期次页、归档、feed.xml、atom.xml）
  → GitHub Actions 部署到 GitHub Pages
```

设计原则不变：判断留给 agent，确定性工作交给代码。期次文件就是代码与 agent 之间的新合同——聊天里的报告今后也从同一份期次文件渲染，避免站点和聊天两套文本漂移。

## 关键决策

1. **托管先用 GitHub Pages**：仓库已在 GitHub、Actions 已有骨架、零新增账号零成本；产物是纯静态文件，将来迁 Cloudflare Pages 只是换部署目标，内容不用动。Cloudflare 的优势（CDN 速度、边缘能力）在这个体量用不上。
2. **生成器自己写，不用 Hugo/Jekyll**：全仓库只有 Python 一门语言，`radar/publish.py` 读期次文件 + 模板出 HTML 和 feed，几百行可控；不引入第二套工具链。
3. **feed 出两份**：RSS 2.0 兼容性最好，Atom 规范更干净，成本只是多一个模板。每期一个条目，`guid` 用期次日期+早晚，永久不变；正文全文放进 `content:encoded` / Atom `content`。
4. **站点 URL 先用默认域名** `daiyanze.github.io/triple-sigma`；自定义域名（如 signals.grant-dai.com）等有读者再绑，GitHub Pages 支持随时加，feed 里用配置项 `base_url` 生成绝对链接，换域名只改一处配置。

## 分阶段

### P0 决策（已在本文件定稿，只等 Dai 确认托管）

- 托管：GitHub Pages（推荐）或 Cloudflare Pages
- 域名：先默认，后自定义

### P1 站点 MVP（约 1 次构建）

- 定 `editions/*.json` 期次格式：日期、期次、标题、各等级条目（标题/数字/出处链接/建议动作）、缺失源说明
- 写 `radar/publish.py`：生成首页、期次页、归档页、feed.xml、atom.xml
- 极简样式：报纸感排版（衬线标题、等级色点），无 JS 依赖
- 把已有的两期报告回填成期次文件（2026-11-11 试跑、2026-11-12 早报），站点上线即有内容
- GitHub Actions：push 到 main 且 `editions/` 有变化时构建并部署 Pages
- 完成标准：手机和桌面能打开最新一期；feed 通过 W3C 校验器；用任意 RSS 阅读器订阅能收到全文

### P2 自动化闭环（约 1 次构建）

- 早晚报 agent 运行结束时，按格式写期次文件并更新台账，走现有 token 通道提交（一次提交，无批准卡），Actions 自动部署——从扫描到上线全自动，Dai 不介入
- 公开文本清洗：分级标准里的内部措辞（如"与 Dai 相关性"）在公开版改为中性表述，agent 出报时区分聊天版与公开版字段
- 完成标准：连续 3 天 6 期自动上线，零手工操作

### P3 体验完善（按读者反馈再排）

- 话题页：从 `state/seen-topics.json` 的等级历史生成，每页一条时间线
- 按等级/来源筛选、站内搜索（静态索引，无后端）
- OG 分享图与 meta、sitemap.xml、robots.txt
- 合订 feed：一份"全部"、一份"只推 🔥 必看"

### P4 可选项（有明确需求才做）

- 自定义域名 + Cloudflare Pages 迁移（需要速度或边缘功能时）
- 基于 feed 的邮件订阅（用第三方 feed-to-email，仍不自建后端）

## 明确不做

- 不做动态后端、账号、评论、点赞——静态站点全部解决
- 不为这个项目新开付费服务
- 不动本地运行结构：扫描仍在现有定时任务里跑，本地文件夹与台账路径不变

## 风险与注意

- GitHub Pages 要求仓库公开（已经是公开的）；站点内容即报告全文，发布前确认没有内部信息混入期次文件（P2 的清洗就是为此）
- feed 里的链接必须是绝对 URL 且长期稳定：期次页 URL 一旦发布不改名、不删除
- 仓库若再改名，GitHub Pages 默认域名会跟着变，旧 feed 地址失效——改名请先绑自定义域名
