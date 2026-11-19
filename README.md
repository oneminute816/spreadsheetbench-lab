# SpreadsheetBench 首周预跑

本仓库提供 SpreadsheetBench v0.1 的数据集适配器、实验配置和首周五题预跑报告。研究主框架来自 [LDlornd/research](https://github.com/LDlornd/research)。原始工作簿与完整资源包按框架约定保存在本机 `data/`，不随代码仓库提交。

- [实验结果与问题分析](REPORT.md)
- [逐题产物与轨迹证据](evidence/ARTIFACTS.md)
- [实验任务相关问题回答](docs/实验任务相关问题回答.md)
- [框架流程说明](docs/框架流程说明.md)
- [SpreadsheetBench 原版主数据集分析](docs/SpreadsheetBench原版主数据集分析.md)
- [适配器与运行说明](datasets/SPREADSHEETBENCH.md)

## 代码接入

按 `research` 的 README 将 `agent-session-analyzer` 放在相邻目录，再将本仓库的 `config/`、`datasets/` 和 `.gitattributes` 中同名路径复制到 `research` 根目录。需要 Python 3.12、`uv` 和 Docker Linux 引擎；Windows 上按[适配器说明](datasets/SPREADSHEETBENCH.md)使用 Linux 宿主容器。

官方 SpreadsheetBench v0.1 资源包保存在 `research/data/spreadsheetbench/raw/`，其中应有原始 `dataset.json` 和 `spreadsheet/`。从 `research` 根目录执行：

```sh
uv run python -m datasets.spreadsheetbench_package data/spreadsheetbench
```

这会生成主框架读取的 `data/spreadsheetbench/dataset.json` 和 `index.json`。原始 912 题、工作簿和生成的资源包均不入 Git。当前配置选择 `12307`、`15380`、`15829`、`13-1`、`17-35`，每题一次。`no-skill` 使用 `config/evaluation/spreadsheetbench.toml`；`with-skill` 使用 `config/evaluation/spreadsheetbench-with-skill.toml`，并要求相邻的 `data/skillsbench/skills/xlsx-recover-data/xlsx/` 已存在。运行前在本机被 Git 忽略的 `research/.env` 中配置 `THINGO_UNI_API_KEY`、`RESEARCH_PROJECT_ID` 和 `RESEARCH_USER_ID`；执行实验会调用付费模型。

早期 OpenHands `no-skill` 五题中，三题有原始有效评分，两题因评分器异常保留 `reward=null`，随后使用保存的输出工作簿离线复评。实验报告区分原始评分与复评，并逐项记录两种 harness 的 skill 条件。正式的 10 题 × 3 轮 × 2 模型 × 2 harness 矩阵尚未运行。
