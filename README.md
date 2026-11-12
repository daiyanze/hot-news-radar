# hot-news-radar

每天两扫的全网热点雷达：早 06:00 / 晚 18:00（JST），在热点到达大众搜索之前，从源头层抓到它。

方法论见 [methodology.md](methodology.md)（写给人看的完整版）。本仓库把它拆成 agent 能直接用的四层：

| 层 | 文件 | 作用 |
|---|---|---|
| 指令 | `skills/hot-news-radar/SKILL.md` | agent 照着跑的执行步骤、判定规则、报告模板 |
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

给 agent 用：把 `skills/hot-news-radar/` 装进你的 agent（Claude Code / Codex 等），或直接让 agent 读 SKILL.md 按步骤执行。定时运行有两种方式：

- 本机/常驻 agent：用 agent 自己的调度（如 Muse 的 cron），早晚各一次——当前 Dai 的实际运行方式。
- GitHub Actions：`.github/workflows/radar.yml` 已备好骨架，设仓库变量 `RADAR_ENABLED=true` 后生效（需要先补上抓取层，见路线图）。

## 路线图（骨架之后）

1. **抓取层**：每个源一个 fetcher（GitHub / HN 有公开 API，Reddit 走公开页/RSS，X 走搜索），输出统一结构给 agent 判断。
2. **MCP server**：`radar/mcp_server.py` 是占位入口，抓取层就绪后把 `scan` / `report` / `review` 包成 MCP 工具，任何支持 MCP 的 agent 可调。
3. **复盘自动化**：review 结果按源统计命中率，自动调整各源权重。

## 边界

只读公开信息，不发帖、不互动；密钥只走环境变量，不进仓库。见 [PRIVACY.md](PRIVACY.md)。
