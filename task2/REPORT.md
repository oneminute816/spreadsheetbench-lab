# 任务二：Skill 注册与动态卸载实验报告

## 目标与实现

任务一的 SpreadsheetBench 原版不随题提供专用 Skill。本次沿用任务一 `with-skill` 已使用的 SkillsBench `xlsx`，在本地 `skill_registry` 注册，并让 `research` 的一个代表性题目通过注册中心工具读取它。另从 SkillsBench 资源包固定选择 50 个名称不冲突、只有 `SKILL.md` 的技能，合计 51 个。选择清单记录名称、相对目录和原文件 SHA-256，不公开技能正文或资源文件。

本次采用的接入标准是目录中存在 `SKILL.md`、其 YAML frontmatter 包含符合小写连字符命名的 `name` 和非空 `description`，且能通过 `skill_registry` 的实际解析与注册。对附带资源的 `xlsx`，还验证 `recalc.py` 可从注册中心读取。其他 50 个技能只验证注册、搜索、正文加载与卸载，不执行各自的脚本或 Agent 任务。

在 `skill_registry` 的本地补丁中，`/add_skill` 与 `/delete_skill` 从原有 501 占位接口接入 `SkillRegistry`。成功响应前发布完整索引；卸载只隐藏索引项，保留源文件，后台刷新不会自动恢复。重复名称和无效元数据返回 HTTP 400，加载已卸载名称返回 HTTP 404。原有 `/search_skills`、`/load_skill` 和资源读取响应保持原协议。

## 运行与稳定性

先运行 `xlsx` 单项烟雾验证：10 项检查全部成功。随后在同一服务进程内连续运行 10 轮，每轮对 51 个技能逐个注册、搜索、加载、卸载，检查卸载后的搜索与加载，并用 8 个并发 worker 再次加载。第一轮另检查重复名称拒绝、缺少描述的技能拒绝、`xlsx/recalc.py` 读取。每轮卸载后等待超过默认 1 秒刷新间隔，确认技能不会被后台重扫恢复。

| 检查 | 成功 / 总数 | p50 / p95 毫秒 |
| --- | ---: | ---: |
| 注册 | 510/510 | 14.64 / 43.64 |
| 搜索 | 510/510 | 10.33 / 26.80 |
| 正文加载 | 510/510 | 4.58 / 26.77 |
| 并发加载 | 510/510 | 9.88 / 39.62 |
| 卸载 | 510/510 | 4.69 / 24.01 |
| 卸载后搜索消失、加载返回 404 | 1020/1020 | 分项见摘要 |
| 原始文件仍在 | 510/510 | 0.11 / 0.20 |
| 跨后台刷新后仍不可见 | 10/10 | 16.03 / 93.31 |

加上首轮的异常与资源检查，共 **4093/4093 项成功**，总耗时 49.12 秒，结束时仍是启动时的同一个注册中心进程。[机器可读摘要](evidence/stability-summary.json)记录完整分母、各阶段延迟和失败列表；本地被忽略的 `logs/task2/stability-raw.json` 保留逐项记录。这里的“稳定性”只指本机短时注册中心协议与热更新运行，不代表长期负载、跨机器部署或 51 个实际 Agent 任务的成功率。

## Spring Boot 集成

在 `rsi-flow-spring-boot` 本地补丁中，`core-integration` 新增调用注册中心的 Java 客户端，`core-web` 新增只读搜索与加载入口，地址从 `skill.registry.url` 读取。项目现有完整应用构建在 `core-common` 的 `com.horsecoder:auth:0.1.15` 依赖处停止：原 POM 指向私有 HTTP 仓库，Maven 3.9 默认拦截该 URL；匿名直连返回 HTTP 401。因此本次在该仓库内增加独立的 `task2-skill-demo`，复用**同一客户端和控制器源码**，按项目的 Spring Boot 2.1.9.RELEASE 版本构建并启动。

经 Spring Boot HTTP 入口实测：初始搜索返回 `xlsx`，加载返回非空正文与 `LICENSE.txt`、`recalc.py` 资源名；在注册中心卸载后搜索为 0、加载为 404；重新注册后搜索恢复为 1。期间 Spring 进程 ID 未改变。[脱敏集成摘要](evidence/spring-summary.json)保留检查结果。该验证覆盖 Spring Web 入口到注册中心的读取链路；完整流程引擎应用尚需课题组私有 Maven 仓库凭据与可用仓库地址，不能将独立模块的成功写成完整应用构建成功。

## Research 代表性 trial

任务二适配层复用任务一的题目准备、工作簿重放和评分，只把技能提供方式改为注册中心读取。`--plan` 确认为 `12307` 一题、`registry-skill` 一条件、一次运行。Windows 原生入口因 BenchFlow 需要 Linux `fcntl` 在环境启动阶段失败，原失败 trial 留在本机，`reward=null`；随后沿任务一既有 Linux 宿主容器方式运行成功。

Linux trial 的环境设置核对了注册中心 `xlsx` 正文与任务一文件一致。原始结果 `status=completed`、`reward=1.0`，三个工作簿用例为 `[1,1,1]`。trace 在第 1 步记录一次成功的 `load_skill(name=xlsx)`，确有正文返回；模型没有调用 `search_skills`。Agent 到达 20 次迭代上限，仍保存了可通过评分的产物。以上只证明该次模型实际读取技能并完成题目，不证明它按技能指导行动，也不能据单次运行推断技能效果。[脱敏 trial 摘要](evidence/agent-summary.json)保留这些区分；完整 trace、工作簿、原始评分和用量留在本地 `research/logs/exp/task2/`。

## 版本与边界

- `skill_registry` 基线 `97015e3d182d83c6297c609cc55160d49ff12b44`；`rsi-flow-spring-boot` 基线 `11b418d3068343d0430e46a58650f97d189159d5`。两处改动以[补丁](patches/README.md)公开，未推送上游仓库。
- `research` 仍在本地任务一实验分支，没有任务二框架核心代码改动；代表性运行使用其既有 recorder、模型调用与用量流程。
- `xlsx` 附带许可证限制复制和分发。公开仓库不包含 SkillsBench 技能正文、资源、原始工作簿、完整 trace、密钥或用量账本。
