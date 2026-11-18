# SpreadsheetBench 单题基线

这是 SpreadsheetBench 接入实验的交付仓库，包含相对研究主框架的新增代码、配置和第一道题的实验报告。研究主框架来自 [LDlornd/research](https://github.com/LDlornd/research)，本次使用的上游提交为 `6c6131b10b4ec4e108dbaf0e4e53b96f199c0608`。本仓库不复制主框架、原始数据包、trace、工作簿或密钥。

- [实验结果与问题分析](REPORT.md)
- [适配器与运行说明](datasets/SPREADSHEETBENCH.md)

## 代码接入

先克隆上述 `research` 提交，并按其 README 将 `agent-session-analyzer` 放在相邻目录。将本仓库的 `config/` 和 `datasets/` 中同名路径复制到 `research` 根目录。所需环境是 Python 3.12、`uv`、Docker Desktop 的 Linux 引擎；Windows 上需要按适配器说明使用 Linux 宿主容器。

官方 SpreadsheetBench v0.1 资源包保存在 `research/data/spreadsheetbench/raw/`，其中应有原始 `dataset.json` 和 `spreadsheet/`。从 `research` 根目录执行：

```sh
uv run python -m datasets.spreadsheetbench_package data/spreadsheetbench
```

这会生成主框架读取的 `data/spreadsheetbench/dataset.json` 和 `index.json`。原始 912 题、工作簿和生成的资源包均不入 Git。实验只选 `12307`、`no-skill`、一次重复；运行命令、容器入口、费用查询见[运行说明](datasets/SPREADSHEETBENCH.md)。实际运行会调用付费模型，需先在 `research/.env` 配置自己的 `DEEPSEEK_API_KEY`、`RESEARCH_PROJECT_ID=research`、`RESEARCH_USER_ID=your-id`。费用查询时使用相同的用户标识。

原始 trace、费用记录和生成的工作簿保留在本机，用于核对与费用报销；公开仓库只提供整理后的实验报告。开发用的本地 `research` 分支已撤销本次基线提交，没有推送到研究组仓库。
