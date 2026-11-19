# 逐题产物与本机原始记录索引

本目录的 `trials/<harness>/<condition>/<task>/` 是公开证据副本，只含可公开的 `solution.py`、`replay.json`、`cases.json`。三者分别对应 Agent 生成脚本、用例 2/3 的脚本重放记录、原始 verifier 逐例评分。生成的 `output.xlsx`、`2_output.xlsx`、`3_output.xlsx` 和原始参考工作簿只在本机保存，避免把大型工作簿资源包提交到代码仓库。

| Harness / 条件 | 本机实验名 | 公开证据 | 缺失说明 |
| --- | --- | --- | --- |
| OpenHands / no-skill | `spreadsheetbench-12307-thingo-openhands-fixed` | [12307](trials/openhands/no-skill/12307/) | 无 |
| OpenHands / no-skill | `spreadsheetbench-week1-four-thingo-openhands` | [15380](trials/openhands/no-skill/15380/) · [15829](trials/openhands/no-skill/15829/) · [13-1](trials/openhands/no-skill/13-1/) · [17-35](trials/openhands/no-skill/17-35/) | `13-1`、`17-35` 原始 verifier 崩溃，没有 `cases.json`；离线复评仅写在报告 |
| DSH / no-skill | `spreadsheetbench-12307-thingo-dsh-smoke-2` | [12307](trials/dsh/no-skill/12307/) | 无 |
| DSH / no-skill | `spreadsheetbench-week1-dsh-noskill-four` | [15380](trials/dsh/no-skill/15380/) · [15829](trials/dsh/no-skill/15829/) · [13-1](trials/dsh/no-skill/13-1/) · [17-35](trials/dsh/no-skill/17-35/) | 无 |
| OpenHands / with-skill | `spreadsheetbench-week1-openhands-xlsx-12307` | [12307](trials/openhands/with-skill/12307/) | 无 |
| OpenHands / with-skill | `spreadsheetbench-week1-openhands-xlsx-four` | [15380](trials/openhands/with-skill/15380/) · [15829](trials/openhands/with-skill/15829/) · [13-1](trials/openhands/with-skill/13-1/) · [17-35](trials/openhands/with-skill/17-35/) | `17-35` 在迭代上限前未生成 `solution.py`；`replay.json` 和 `cases.json` 均保留 |
| DSH / with-skill | `spreadsheetbench-week1-dsh-xlsx-12307` | [12307](trials/dsh/with-skill/12307/) | 无 |
| DSH / with-skill | `spreadsheetbench-week1-dsh-xlsx-four` | [15380](trials/dsh/with-skill/15380/) · [15829](trials/dsh/with-skill/15829/) · [13-1](trials/dsh/with-skill/13-1/) · [17-35](trials/dsh/with-skill/17-35/) | 无 |

本机原始 trial 目录按 `research/logs/exp/spreadsheetbench/<harness>/<model>/<实验名>/trials/<task>__<condition>__001/` 组织。每个目录包含配置快照、`result.json`、`agent/trace/`、`agent/usage.jsonl`、`agent/usage-config.json`、生成工作簿和 verifier 日志；旧失败记录也保留。公开的[轨迹摘录](TRACE_EXCERPTS.md)按步骤描述关键事件，不复制完整会话正文。任务包的 `data/spreadsheetbench` 与 `data/skillsbench` 由使用者单独准备。
