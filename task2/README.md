# 任务二运行说明

从[实验报告](REPORT.md)看结果、局限和证据。`build_manifest.py` 固定候选技能，`verify_registry.py` 执行热更新验证，`registry_spreadsheetbench.py` 复用任务一适配器并让 Agent 通过注册中心读取 `xlsx`。`patches/` 保存两个上游仓库的本地接入改动，`config/` 是代表性 trial 的组件配置，`evidence/` 只保存脱敏摘要。

## 前置目录与版本

将 `research`、`skill_registry`、`rsi-flow-spring-boot`、本仓库放在同一工作区。SkillsBench 独立资源包保存在 `research/data/skillsbench/`，SpreadsheetBench 原始工作簿及转换资源包保存在 `research/data/spreadsheetbench/`。使用报告中的上游基线版本并应用 `patches/` 中对应补丁；保留原始资源包在本机。

在 Windows PowerShell 中，从各上游仓库根目录先执行 `git apply --check <本仓库>/task2/patches/<补丁名>`，再执行 `git apply <本仓库>/task2/patches/<补丁名>`。补丁没有包含技能正文和工作簿。

## 批量验证

以下示例从本仓库根目录运行。`python` 使用已有的 Python 3.12 环境，需安装 `skill_registry/pyproject.toml` 声明的 FastAPI、Pydantic、PyYAML 和 Uvicorn 等依赖。此工作区已用 `research/.venv/Scripts/python.exe` 验证。脚本自行在本机回环地址启动和关闭注册中心，不调用模型。

```powershell
$workspace = (Resolve-Path ..).Path
$python = Join-Path $workspace 'research/.venv/Scripts/python.exe'
& $python task2/build_manifest.py (Join-Path $workspace 'skillsbench/skills') task2/skills-manifest.json
& $python task2/verify_registry.py `
  --registry-project (Join-Path $workspace 'skill_registry') `
  --skills-root (Join-Path $workspace 'skillsbench/skills') `
  --rounds 10 --concurrency 8 `
  --summary logs/task2/stability-summary.json --raw logs/task2/stability-raw.json
```

预期选择 51 个名称，验证输出 `Checks: 4093; failures: 0; same process alive: True`。实际时间随机器变化，验证应以输出 JSON 的分母、错误和进程状态为准。若需要先检查 `xlsx`，追加 `--limit 1 --rounds 1 --concurrency 1` 并使用不同的输出文件名。

## Spring Boot 验证

完整 `rsi-flow-spring-boot` 仍依赖私有 Maven 仓库；`task2-skill-demo` 是可独立构建的同版本验证模块，直接编译 `core-integration` 客户端和 `core-web` 控制器。需要 JDK 8 或更高版本和 Maven 3.9；本工作区的 Maven 位于 `../tools/apache-maven-3.9.11/`。从 Spring 仓库根目录运行：

```powershell
& '../tools/apache-maven-3.9.11/bin/mvn.cmd' -B -ntp -f task2-skill-demo/pom.xml -DskipTests package
java --add-opens=java.base/java.lang=ALL-UNNAMED -jar task2-skill-demo/target/task2-skill-demo-1.0.0.jar
```

上面的启动命令适用于本机 JDK 21；JDK 8 运行时去掉 `--add-opens`。在另一个终端将注册中心的 `SKILLS_DIR` 指向本机 `research/data/skillsbench/skills/xlsx-recover-data/xlsx`，设 `HOST=127.0.0.1`、`PORT=5000` 后启动 patched `skill_registry`。Spring 默认只监听 `127.0.0.1:18080`；访问 `/api/engine/skills` 和 `/api/engine/skills/xlsx` 可查元数据与正文。通过注册中心 `/delete_skill` 卸载 `xlsx` 后，这两个入口分别返回空列表和 404；调用 `/add_skill` 可恢复。

## Research 代表性运行

按任务一 [Linux 宿主容器说明](../datasets/SPREADSHEETBENCH.md)准备 Docker 与 `research` 的锁定依赖。容器内将 `PYTHONPATH` 同时包含本仓库根目录和 patched `skill_registry/src`，在回环地址启动扫描 `xlsx` 目录的注册中心。从 `research` 根目录先运行：

```sh
python -m evaluation \
  --dataset ../spreadsheetbench-lab-public/task2/config/dataset.toml \
  --environment ../spreadsheetbench-lab-public/task2/config/environment.toml \
  --agent ../spreadsheetbench-lab-public/task2/config/agent.toml \
  --evaluation ../spreadsheetbench-lab-public/task2/config/evaluation.toml \
  --name task2-registry-xlsx-check --plan
```

预期 `tasks=["12307"]`、`planned_trials=1`。核对后移除 `--plan` 并使用新的实验名正式运行。正式运行会启动 Docker、调用付费模型，并通过 `research` 的既有流程写 trace、评分和用量到本机忽略目录。不要在 Windows 原生 Python 中执行正式 trial，BenchFlow 需要 Linux 的 `fcntl`。
