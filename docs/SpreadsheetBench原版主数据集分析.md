# SpreadsheetBench 原版主数据集分析

## 六个问题

### 1. 这个数据集是想要测试什么的？

它测试 Agent 将自然语言电子表格要求转成具体工作簿修改的能力，包括理解结构、定位单元格或工作表、计算与保存。原版 v0.1 资源包有 912 题。本周五题是办公场景定点样本，不代表总体分布。

### 2. 这个数据集的任务输入输出是什么？给出一到两个示例。

每题有指令、`answer_position` 和三个编号输入/答案工作簿。本实验让 Agent 看用例 1 的输入，生成工作簿和可重用脚本，再在评估阶段处理用例 2、3。`12307` 统计公司在清单国家中雇员数大于零的数量，写 `I12:I13`；`15380` 从 `A3:A14` 提取月份代码并查表，将月份名写 `B3:B14`。输入、修改要求、输出与原生评分的逐项说明见《实验任务相关问题回答》。

### 3. 这个数据集在什么环境下运行？现有 research 框架能否支持？如何支持？

本周使用 Linux Docker 容器、Python 3.12、`openpyxl` 和 LibreOffice。`research` 已提供资源包、trial、环境、harness、trace 和评分接口，个人仓库的 SpreadsheetBench 适配器完成原版工作簿格式转换、首例隔离、后两例重放和逐格比较。Windows 宿主因 `fcntl` 无法直接运行 BenchFlow，使用 Linux 宿主容器。

### 4. 这个数据集为模型提供了哪些工具？能否尽量只用现有工具完成任务？

原版不附本实验专用 skill。OpenHands 用 `terminal`、`think`、`finish`，DSH 用 `terminal`；表格操作通过终端内的现有 Python 与 LibreOffice 完成。`with-skill` 额外注入 SkillsBench 通用 `xlsx` skill，仍通过终端读取，因此无需修改框架工具接口。需在 trace 核对模型是否真的读取技能。

### 5. 这个数据集采用了哪些评价指标？如何评估任务完成质量？

本实验按原题 `answer_position` 比较三个输出与参考工作簿的重算值，记录逐例通过、逐例通过率和三例全对严格分。另记录有效评分覆盖率、有效结果严格通过率、token 和耗时。评分仅覆盖指定区域；缺失评分、合法零分和环境失败分开报告。这是基于原版评分位置与数值规则的本实验适配结果，不是官方榜单复现。

### 6. 现有 harness 和模型在这些任务上为什么会失败？（skill 角度，harness 指标）

四组运行中，`15380` 始终是有效零分，但用例 2、3 的输入与同编号答案可能错配；旧 OpenHands `no-skill` 的 `13-1`、`17-35` 因评分器异常缺失原始分数；OpenHands `with-skill` 的 `17-35` 虽读取 skill，却在 20 次迭代内未生成脚本，三例输出缺失，得到有效零分。早期 `12307` 的 CRLF 和 DSH profile 插件缺失属于接入问题。报告分别列出 skill 提供、实际读取、原始评分及失败步骤；这些证据仍不足以判断模型内部为何没及时写出脚本，或得出稳定的 harness 优劣结论。

## 两个真实任务与任务素材

核查对象是本地 [官方 v0.1、912 题资源包](https://github.com/RUCKBReasoning/SpreadsheetBench/blob/main/data/spreadsheetbench_912_v0.1.tar.gz)中的原始 `dataset.json` 和 `spreadsheet/<题号>/`，不是本组转换后的资源包索引。两题各有编号 1、2、3 的输入和参考答案工作簿；下表文件名中的 `n` 分别取 `1`、`2`、`3`，六个对应文件均已在本地资源包核对存在。

| 原始任务 | 输入与参考答案（每题三组） | 修改要求与应产生的结果 | 原始评分位置和规则 |
| --- | --- | --- | --- |
| `12307`，单元格级 | `spreadsheet/12307/n_12307_input.xlsx` 与 `n_12307_answer.xlsx`；输入有公司、国家清单和雇员数 | 统计各公司在清单国家中雇员数大于 0 的国家数量，填写工作簿的 `I12:I13`；每组输入应产生一份修改后的输出工作簿 | `answer_position = I12:I13`，逐例对比输出与同编号答案在该区域的值 |
| `15380`，单元格级 | `spreadsheet/15380/n_15380_input.xlsx` 与 `n_15380_answer.xlsx`；输入含 `A3:A14` 的文本及 `codes2`、`month` 对照范围 | 从文本提取月份代码并查表，将对应月份写入 `B3:B14`；例如 `2014_09_Drop2_Reminder` 对应 `SEP` | `answer_position = B3:B14`，逐例对比输出与同编号答案在该区域的值 |

原版 [评分代码](https://github.com/RUCKBReasoning/SpreadsheetBench/blob/main/evaluation/evaluation.py)对这两道单元格级题使用 `answer_position` 指定区域，读取重算后的单元格值作比较；三个用例的通过比例是 `soft_restriction`，三例全对才使 `hard_restriction = 1`。本组 Agent 只看到用例 1 的输入，需交付 `output.xlsx` 和可重用的 `solution.py`；评估阶段才用同一脚本生成用例 2、3 的输出并读取答案。这是本组接入协议，不是原始题目自带的输出接口。`15380` 的用例 2、3 存在同编号输入与答案的 `A3` 内容不一致疑点，原始评分结果和待核查证据见 [实验报告](../REPORT.md#失败轨迹记录)。

## 公开性、复用来源与缺口

| 要素 | 已核对的来源与公开情况 | 本组使用方式或缺口 |
| --- | --- | --- |
| 数据版本与任务素材 | [官方仓库](https://github.com/RUCKBReasoning/SpreadsheetBench)公开 SpreadsheetBench；本地包标记 `v0.1`、共 912 题，含原始 `dataset.json` 和两题各三组输入/答案工作簿 | 工作簿位于独立资源包，未提交进个人代码仓库；本组转换程序生成 `research` 所需索引，不改写原题 |
| 现成 skill | 上述 SpreadsheetBench 原始包未随题提供 `SKILL.md` 或两题专用 skill；本地另有 **SkillsBench 独立资源包**中的通用 `xlsx` skill，路径 `data/skillsbench/skills/xlsx-recover-data/xlsx/`。已核对本地文件，未核实其独立公开下载地址 | `with-skill` 复用这份通用 skill，`no-skill` 不提供；它不是 SpreadsheetBench 原生素材。缺口是没有经这两题验证的专用步骤指引，提供 skill 也不等于模型实际读取或正确使用 |
| 工具与执行环境 | 官方仓库公开[推理与执行说明](https://github.com/RUCKBReasoning/SpreadsheetBench#inference)；`research` 已有 Docker、OpenHands/DSH、终端和文件操作能力 | 两题可用终端内的 Python、`openpyxl` 与 LibreOffice 处理，无须新增工具接口；本组适配器负责把原始工作簿接入 trial |
| 评分规则与代码 | 官方公开 [`evaluation/evaluation.py`](https://github.com/RUCKBReasoning/SpreadsheetBench/blob/main/evaluation/evaluation.py) 和[重算说明](https://github.com/RUCKBReasoning/SpreadsheetBench#evaluation)，按指定区域比较并计算软、硬分 | 官方脚本当前将待评分 `proc_path` 指向 `*_input.xlsx`，输出工作簿路径只在注释中；直接照此运行不能评估 Agent 输出。本组 verifier 显式比较 `*_output.xlsx` 与同编号答案，并保留逐例证据 |

因此，原版题目、工作簿和评分方法有公开来源，但并不存在随题公开且可直接用于本实验的专用 skill；评分脚本也需要指定实际输出文件。本组评分沿用原版的单元格值与三例软、硬分思想，加入首例隔离、后两例重放及本地重算流程，结果不能称为官方榜单复现。

## 样本与局限

本周固定五题，一题一轮。它覆盖单元格填值、条件汇总、查找计算、整表合并和日期筛选，但不足以估计 912 题的整体完成率。正式对照应固定题目、模型、工具能力、预算、skill 条件和重复次数，再分析失败类型的比例。
