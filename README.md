# SpreadsheetBench 首周预跑

本仓库提供 SpreadsheetBench v0.1 的数据集适配器、实验配置和首周五题预跑报告。研究主框架来自 [LDlornd/research](https://github.com/LDlornd/research)，适配代码基于上游 `e52531b` 版本。本仓库不复制主框架、原始数据包、trace、工作簿或密钥。

- [实验结果与问题分析](REPORT.md)
- [适配器与运行说明](datasets/SPREADSHEETBENCH.md)

## 代码接入

按 `research` 的 README 将 `agent-session-analyzer` 放在相邻目录，再将本仓库的 `config/`、`datasets/` 和 `.gitattributes` 中同名路径复制到 `research` 根目录。需要 Python 3.12、`uv` 和 Docker Linux 引擎；Windows 上按[适配器说明](datasets/SPREADSHEETBENCH.md)使用 Linux 宿主容器。

官方 SpreadsheetBench v0.1 资源包保存在 `research/data/spreadsheetbench/raw/`，其中应有原始 `dataset.json` 和 `spreadsheet/`。从 `research` 根目录执行：

```sh
uv run python -m datasets.spreadsheetbench_package data/spreadsheetbench
```

这会生成主框架读取的 `data/spreadsheetbench/dataset.json` 和 `index.json`。原始 912 题、工作簿和生成的资源包均不入 Git。当前配置选择 `12307`、`15380`、`15829`、`13-1`、`17-35`，每题一次，条件为 `no-skill`。运行前在本机被 Git 忽略的 `research/.env` 中配置 `THINGO_UNI_API_KEY`、`RESEARCH_PROJECT_ID` 和 `RESEARCH_USER_ID`；执行实验会调用付费模型。

五题均产生了 Agent 输出和 trace；其中三题在原始 trial 中有有效评分，另两题因评分器异常保留 `reward=null`，随后使用保存的输出工作簿离线复评。另用 `dsh-spreadsheetbench.toml` 对 `12307` 做了一次 DSH 连通性实验。详细结果见[报告](REPORT.md)。正式的 10 题 × 3 轮 × 2 模型 × 2 harness 矩阵尚未运行。
