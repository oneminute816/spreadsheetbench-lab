# SpreadsheetBench 基线：首题实验报告

## 范围与方法

- 数据：官方 SpreadsheetBench v0.1，共 912 题。本轮仅运行原始顺序中首个有三个完整工作簿用例的单元格级题目 `12307`，目标区域 `I12:I13`。
- 条件：OpenHands SDK、`deepseek/deepseek-flash`、`no-skill`、一次重复。复用 `research` 的 trial 调度、Docker 环境、trace recorder 和 `research-llm` 费用账本。
- 隔离：Agent 只见首个输入工作簿与题目要求，需输出 `solution.py` 和结果工作簿。Agent 结束后，同一脚本处理用例 2、3；参考答案仅在评分阶段上传。
- 评分：LibreOffice 重算输出和参考工作簿，按官方 `answer_position` 比较计算值。逐例通过率为软分，三例全对为严格分。此实现使用可复用 CLI 脚本，提示词和 Agent 结构与官方论文设置不同，不能称为官方榜单结果。

## 运行记录

| 尝试 | 阶段 | 结果 | 模型费用 |
| --- | --- | --- | --- |
| Windows 本机 | 环境 | `benchflow==0.7.8` 导入 Linux 专有的 `fcntl` 失败，未调用模型 | 无模型调用 |
| Linux 宿主首次 | Agent | DeepSeek 返回 HTTP 401，密钥无效；未评分，`reward=null` | 1 次失败请求，用量缺失，费用未知 |
| Linux 宿主第二次 | 完整评分 | 用例 1、2、3 均通过，逐例通过率 `1.0`，严格分 `1.0` | 13 次成功调用，估算 `0.06342848 CNY` |

成功运行的 trial ID 为 `12307__no-skill__001`，状态 `completed`，没有错误。Agent 阶段耗时约 98.49 秒，评分阶段约 28.69 秒。13 次成功调用的记录共计输入 101,248 tokens、输出 11,964 tokens，其中缓存读取 87,424 tokens。上述费用是 `research-llm` 根据 trace 用量和项目价格表计算的估值，不等同平台实际账单；失败的 401 请求未被错误计为零费用。

成功运行的 `result.json`、`cases.json`、`usage.jsonl`、`usage-config.json`、原始 trace、生成的 `solution.py` 和三个结果工作簿均保存在本机；两次失败尝试的完整日志也保存在本机 `research/logs/exp/spreadsheetbench/`。公开仓库只提供汇总报告和代码，原始证据留待费用核对时提供。

## 结论与下一步

这一题证明适配器能完成选题、Agent 作答、后续用例重放、逐例评分、trace 记录和费用估算。样本量只有 1 题，不能据此估计 912 题的总体通过率，也不能判断常见失败类型的比例。下一步应先选一小批不同题型，检查环境、脚本重放与评分错误；保留失败记录并归因后，再扩大到完整数据集统计各类问题占比。

框架改进建议：BenchFlow 在 Windows 上依赖 `fcntl`，应在 `research` 的环境文档中明确 Linux 宿主要求或提供受支持的容器入口；当前本仓库提供了本实验使用的容器入口，没有修改研究主框架。运行后将重放命令结果保存到 `artifacts/spreadsheetbench/replay.json` 的小修只做了静态复核，未再进行付费实验验证。
