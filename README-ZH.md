<p align="center">
  <img src="frontend/public/icon.png" alt="My Own Researcher 图标" width="88" height="88">
</p>

<h1 align="center">My Own Researcher</h1>

<p align="center">
  <strong>带来一份文档，提出一个问题，探索可能发生的事。</strong><br>
  你的个人研究工作台：构建知识图谱、模拟不同观点、生成研究报告。
</p>

<p align="center">
  <a href="#看看实际效果">查看演示</a> ·
  <a href="#安装与运行">开始使用</a> ·
  <a href="#选择推理提供方">选择 AI</a> ·
  <a href="#通过其他-ai-助手使用">连接 AI 助手</a> ·
  <a href="#myownstack-的一部分">MyOwnStack</a> ·
  <a href="README.md">English</a>
</p>

<p align="center">
  <strong>使用自己的 AI 订阅</strong> &nbsp; / &nbsp;
  <strong>本地图谱存储</strong> &nbsp; / &nbsp;
  <strong>浏览器 + MCP</strong>
</p>

---

一份提案摆在面前，事实散落在各处，相关各方诉求不同，下一步却不明确。**My Own Researcher 将这些材料变成可探索的情景**：关联事实，让模拟参与者表达观点，再通过报告查看讨论过程与结果。

**📄 源材料 → 🕸️ 知识图谱 → 👥 模拟讨论 → 📝 报告 → 💬 后续追问**

上传 PDF、Markdown 或文本文件，然后提出问题：*我们遗漏了哪些假设？哪些地方可能存在分歧？要让这个方案可行，需要满足什么条件？*

本项目属于 **MyOwnStack**，为使用你自己的 AI 账号运行本地服务而构建。订阅推理由共享 npm 包 **[MyOwnLlmIntegrator](https://www.npmjs.com/package/myown-llm-integrator)** 提供，安装应用依赖时会自动安装该包。

这是 **[MiroFish](https://github.com/666ghj/MiroFish)** 的独立分支，采用 [AGPL-3.0](LICENSE) 许可证。

> [!NOTE]
> 模拟用于探索假设与可能的情景。输出是由模型生成、需要进一步核实的材料，不代表真实世界一定会出现相同结果。

## 看看实际效果

**认识 LoopLunch：一个午餐创业计划、两个定价方案，以及暂缓试点的理由。**

一家虚构的新加坡办公午餐创业团队，应该定价 **S$12**、定价 **S$14**，还是推迟试点？从原始简报出发，查看知识图谱、7 位模拟参与者、他们的讨论，以及保存下来的报告。

[![LoopLunch 演示：研究问题、三个决策选项与已保存运行的覆盖范围](docs/images/looplunch-demo.png)](#体验演示)

*虚构情景，已录制的运行结果：7 位参与者 · 102 次行为 · 完成计划中 336 轮的 37 轮。报告中说明了这一有限覆盖范围。*

### 体验演示

演示使用项目内置的示例数据，**无需后端、Docker 或 AI 账号。** 安装 Node.js 22.12+ 后运行：

```sh
git clone https://github.com/Handriantog/My-Own-Researcher.git
cd My-Own-Researcher
npm ci --prefix frontend
npm run frontend
```

打开 **[localhost:4317/demo](http://localhost:4317/demo)**，或在首页选择 **Demo**。浏览演示不会发起后端或 AI 请求。

也可以直接阅读[原始简报](frontend/public/demo/looplunch-brief.pdf)和[已保存的报告](frontend/src/demo/looplunch-report.md)。

## 此分支增加了什么

| | 你可以获得 |
| --- | --- |
| 🔑 **使用自己的 AI 账号** | 使用已通过 ChatGPT 登录的 Codex CLI，或选择其他 14 种 Agent CLI。默认本地模式无需 LLM API 密钥，也不会自动回退到付费 API。 |
| 🕸️ **将图谱保存在本地** | Graphiti + Neo4j 在你的电脑上存储图谱。本地模式无需 Zep 账号或密钥。 |
| 🎛️ **运行前确认设置** | 选择模型、并行请求上限、研究深度和模拟平台。开始前查看工作量估算，运行中跟踪进度与提供方返回的用量。 |
| 🧩 **复用 AI 接入能力** | [MyOwnLlmIntegrator](https://github.com/Handriantog/My-Own-LLM-Integrator) 为本应用和其他本地服务提供共享的订阅推理引擎。 |
| 🔄 **恢复未完成的工作** | 图谱导入、Agent 准备、记忆保存和报告章节均支持检查点，并提供可见的重试状态与手动恢复操作。 |
| 📄 **导出研究报告** | 支持下载 Markdown 和 PDF。PDF 根据已保存的报告在本地生成，无需再次调用 AI。 |
| 🤝 **通过 AI 助手操作** | MCP 工具通过 Streamable HTTP 或 stdio 暴露同一套项目、图谱、模拟和报告功能。 |
| 🌐 **默认英文界面** | 界面默认使用英文，并保留上游的语言选择器。 |

> [!IMPORTANT]
> **本地存储不等于离线 AI。** 文档文本和模拟对话会发送到所选 CLI 的模型服务（默认 Codex 配置使用 OpenAI）。其认证方式、计费规则以及账号和模型限制仍然适用；推理并非免费或无限量。

<details>
<summary><strong>与继承的 MiroFish 配置相比，有哪些变化？</strong></summary>

### 与继承的 MiroFish 配置对比

此表描述本分支最初继承的上游基线，不代表所有当前上游版本。

| 方面 | 继承的 MiroFish 基线 | 本分支的本地配置 |
| --- | --- | --- |
| 研究流程 | 源文档、图谱、OASIS 模拟、报告、交互 | 保留此流程 |
| 语言模型推理 | OpenAI 兼容 API 配置 | Codex 或其他支持的 Agent CLI；保留可选 API 模式 |
| 图谱服务 | Zep Cloud 凭据 | 本地 Graphiti + Neo4j；无需 Zep 账号 |
| 界面 | 上游多语言界面 | 默认英文，采用本分支的名称与标识 |
| 中断处理 | 原有任务与运行管理 | 增加检查点、可见的重试状态和手动恢复 |
| 运行控制 | 计划模拟轮数 | Quick / Moderate / Full 运行档位，以及带提示的提前停止与部分报告 |
| 报告导出 | 下载 Markdown 报告 | 增加本地生成的 PDF 下载 |

</details>

## 安装与运行

### 1. 准备运行环境

| 要求 | 所需条件 |
| --- | --- |
| 操作系统 | macOS、Linux 或 WSL |
| 运行时 | Node.js **22.12+** 和 Python **3.11–3.12** |
| Python 包管理 | [uv](https://docs.astral.sh/uv/) |
| 图数据库 | 支持 Compose 的 Docker，且 Docker 已启动 |
| AI 推理 | 已安装的 Agent CLI，以及可用于登录的账号 |

以下快速开始使用 [Codex CLI](https://learn.chatgpt.com/docs/cli) 和你的 ChatGPT 账号。使用其他 CLI 时，请按[选择推理提供方](#选择推理提供方)中的说明配置并登录。

### 2. 配置工作台

克隆 Researcher 并安装依赖。npm 会下载已发布的 Integrator 包，无需单独克隆 Integrator 仓库：

```sh
mkdir -p MyOwnStack
cd MyOwnStack
git clone https://github.com/Handriantog/My-Own-Researcher.git MyOwnResearcher
cd MyOwnResearcher
npm ci
npm ci --prefix frontend
uv sync --project backend --frozen
uv sync --project graph_platform --frozen
python3 scripts/configure_local_graph.py
codex login
```

**从同级本地包配置迁移？** 先运行 `npm ci`，再按[迁移命令](docs/llm-integrator.md#updating-an-existing-checkout)刷新两个 Python 环境中的引擎。现在不再需要同级的 Integrator 仓库。

登录时选择 **Sign in with ChatGPT**。配置脚本会在已被 Git 忽略的 `.env` 中创建私有凭据，保留已有密钥和提供方选择，并启用本地 Graphiti 存储。每个 CLI 自行管理登录信息，请勿将其登录凭据写入 `.env`。

### 3. 启动并开始探索

```sh
npm run graph:up
npm run dev
```

打开 **[localhost:4317/?lang=en](http://localhost:4317/?lang=en)**，等待图谱服务就绪后再上传文件。首次启动图谱服务时会下载本地嵌入模型和重排序模型。

**下次启动**：再次运行以上两条命令。**停止服务**：按 Ctrl+C，再运行 `npm run graph:down` 停止 Neo4j，数据会保留。如果之前启动了仅演示用的前端，请先停止它，再启动完整应用。

<details>
<summary><strong>各服务运行在哪里？配置与端口</strong></summary>

Docker 通过 `compose.local-graph.yml` **仅运行 Neo4j**。前端、后端、图谱服务、MCP 适配器和所选 Agent CLI 均直接在宿主机运行。

| 服务 | 默认地址 |
| --- | --- |
| 浏览器界面 | `http://localhost:4317` |
| MCP 端点 | `http://127.0.0.1:4318/mcp` |
| 后端 | `http://127.0.0.1:5001` |
| 图谱服务 | `http://127.0.0.1:5002` |

带注释的 [`.env.example`](.env.example) 说明了提供方设置、本地凭据和超时配置。可在根目录 `.env` 中按需覆盖 `FRONTEND_PORT`、`MCP_PORT` 或 `FLASK_PORT`。Web 服务遇到端口占用时会报错，不会悄悄改用其他端口。

配置脚本默认使用 `LLM_PROVIDER=codex`，保留已有选择，支持 `--provider` 参数，并设置 `GRAPH_PROVIDER=graphiti`。

</details>

## 开始一次研究

1. **提供背景材料。** 在首页上传一份简短的 PDF、Markdown 或文本文件，并描述你想探索的问题。
2. **确认研究设置。** 选择 **Review settings**（检查设置），查看已连接的提供方、模型、并行请求上限、平台和预估 token 范围。
3. **选择研究深度。** 决定执行多少比例的计划模拟轮数：

   | Quick · 新运行的默认档位 | Moderate | Full |
   | --- | --- | --- |
   | 计划轮数的 25% | 计划轮数的 50% | 计划轮数的 100% |

4. **开始研究。** 选择 **Start research**，后端会依次执行分析、图谱构建、Agent 准备、模拟、记忆保存和报告生成。可在浏览器中跟踪进度，关闭页面不会停止运行。
5. **阅读、追问、导出。** 查看报告中的证据与覆盖范围说明，下载 Markdown 或 PDF，并在相关功能可用时继续与 Agent 或报告交互。

> [!TIP]
> 建议从简短材料和 Quick 深度开始。新运行默认使用 **2 个并行 AI 请求**和 **Reddit** 平台。提高并行度可以缩短等待时间，但不会减少总工作量。估算值表示工作量范围，并非账号剩余额度或强制 token 上限。

<details>
<summary><strong>运行停止或失败时怎么办？</strong></summary>

- **Stop research**（停止研究）会取消当前工作并阻止后续阶段。请等待模拟记忆保存完成；有可用结果时，需要主动选择 **Generate partial report**（生成部分报告）。
- **Resume**（恢复）会复用已完成的图谱、准备、记忆和报告检查点。中断的模拟会从第 1 轮重新开始，不会在某一轮中途恢复 OASIS 进程。
- **恢复需要主动操作。** 后端重启后，中断的研究不会自动重新开始推理。请检查状态，再决定何时继续。

运行控制详见[研究设置与恢复指南](docs/research-settings.md)；存储和服务诊断详见[工作台指南](docs/my-own-researcher.md)。

</details>

## 选择推理提供方

**默认使用 Codex。** [MyOwnLlmIntegrator](https://github.com/Handriantog/My-Own-LLM-Integrator) 提供全部 15 种提供方适配器，包括 Claude Code、Gemini CLI 和 Cursor。请使用运行本应用的同一个操作系统用户安装并登录所选 CLI。

例如，安装并登录 Claude Code 后运行：

```sh
python3 scripts/configure_local_graph.py --provider claude-code
uv run --project backend python backend/scripts/check_agent.py --provider claude-code
```

此检查仅验证配置和可执行文件是否可用，**不会执行推理**。更换提供方后请重启应用。

<details>
<summary><strong>全部 15 种提供方：ID、可执行文件与 MCP 配置</strong></summary>

`LLM_PROVIDER` 和 MCP 配置生成器均使用下表中的提供方 ID。

| Agent | 提供方 ID | 推理可执行文件 | MCP 配置位置 |
| --- | --- | --- | --- |
| Codex | `codex` | `codex` | `~/.codex/config.toml` |
| Claude Code | `claude-code` | `claude` | `.mcp.json` |
| Antigravity | `antigravity` | `agy`（需要 CLI） | `.agents/mcp_config.json` |
| Cursor | `cursor` | `agent` | `.cursor/mcp.json` |
| Devin CLI | `devin` | `devin` | `.devin/mcp_config.json` |
| Factory Droid | `factory-droid` | `droid` | `.factory/mcp.json` |
| Gemini CLI | `gemini` | `gemini` | `.gemini/settings.json` |
| GitHub Copilot CLI | `copilot` | `copilot` | `~/.copilot/mcp-config.json` |
| Grok Build CLI | `grok` | `grok` | `~/.grok/config.toml` |
| Kimi Code | `kimi` | `kimi`（当前 Node.js CLI） | `.kimi-code/mcp.json` |
| OpenCode | `opencode` | `opencode`（v2） | `opencode.json` |
| Pi | `pi` | `pi`（当前支持原生 MCP 的版本） | `.pi/mcp.json` |
| Qwen Code | `qwen` | `qwen` | `.qwen/settings.json` |
| Hermes Agent | `hermes` | `hermes` | `~/.hermes/config.yaml` |
| Muse | `muse` | `muse`（Meta Muse Code） | `~/.config/muse/settings.json` |

</details>

<details>
<summary><strong>可选设置与实际账号兼容性检查</strong></summary>

对于非 Codex Agent，可在根目录 `.env` 中使用以下可选设置：

```dotenv
LLM_PROVIDER=claude-code
GRAPH_PROVIDER=graphiti
# AGENT_BIN=/absolute/path/to/claude
# AGENT_MODEL=an-exact-model-id-available-to-your-account
AGENT_TIMEOUT_SECONDS=600
AGENT_QUEUE_TIMEOUT_SECONDS=600
```

文档分析、角色生成、配置生成、模拟、报告、访谈，以及**本地 Graphiti 信息提取**，都会使用你选择的提供方。选择其他 CLI 提供方时无需登录 Codex。

可通过 `GRAPH_LLM_PROVIDER` 为图谱选择不同的 CLI。当 `LLM_PROVIDER=openai` 时，除非另行覆盖，图谱提取仍保留原有的 Codex 默认设置。`AGENT_MODEL` 用于非 Codex 请求；Codex 继续使用 `CODEX_*` 设置。API 和 boost 密钥不会触发自动回退。

要验证登录、文本和 JSON 输出、模拟行为及图谱兼容性，可以主动运行小规模实际调用检查。**以下命令会消耗你的账号额度。** 请将 `claude-code` 替换为所选提供方 ID。

```sh
uv run --project backend python backend/scripts/check_agent.py --provider claude-code --live
# 可选：在临时 OASIS 模拟中运行两个 Agent
uv run --project backend python backend/scripts/check_agent.py --provider claude-code --live --oasis
```

</details>

新增的原生预设属于**实验性功能，且依赖 CLI 版本**。命令构建、解析器和请求路由已通过模拟可执行文件测试；真实账号兼容性仍需在你的安装环境中检查。CLI 工具限制并非操作系统沙箱：客户端可能保留原生工具、用户配置、钩子或 MCP 自动发现行为。

安装步骤、版本要求、工具控制限制和 `AGENT_COMMAND_JSON` 包装器详见[推理提供方配置指南](docs/agent-providers.md)。

## 通过其他 AI 助手使用

你的 AI 助手可以通过 **MCP** 操作工作台，无需打开浏览器。推理与 MCP 相互独立：例如，可以让 Cursor 操作研究流程，同时由 Claude Code 执行底层推理。

完成安装后，启动服务：

```sh
npm run graph:up
npm run dev:agent
```

如果 `npm run dev` 已经运行，MCP 也已可用。请只运行一个后端。在后端和图谱服务单独运行时，`npm run mcp` 可以只启动适配器。

**Streamable HTTP 连接地址**：`http://127.0.0.1:4318/mcp` · **工具超时**：至少 **900 秒**。

使用上表中的提供方 ID，为客户端生成设置：

```sh
python3 scripts/agent_mcp.py --provider claude-code
python3 scripts/agent_mcp.py --provider gemini
python3 scripts/agent_mcp.py --provider cursor --transport stdio
python3 scripts/agent_mcp.py --list
```

生成器**只打印配置**。将其中的 `my-own-researcher` 条目合并到客户端设置中，保留已有服务器，然后重启或重新加载 Agent。可以让它调用 `get_status`，在不执行推理的情况下检查连接。

### 给 AI 助手的第一个任务

> 使用 my-own-researcher MCP 工具研究提供的材料。先检查服务是否就绪，用唯一的 upload_id 创建项目，构建图谱，并准备仅使用 Reddit 的模拟。先运行两轮试验，等待模拟和记忆保存完成，再生成并获取报告。保留证据与覆盖范围限制的说明。阅读 research://workflow，了解调用顺序和恢复规则。

服务器提供带类型定义的工具和 `research://workflow` 资源。Agent 可以通过 `create_project` 提交文本或 Markdown、构建和搜索图谱、运行模拟、轮询进度，并通过 `get_report` 获取报告 Markdown。通过浏览器上传的项目（包括 PDF）同样可用。推理工具会使用所选提供方并消耗账号额度。

<details>
<summary><strong>通用 stdio 配置与自定义连接</strong></summary>

对于接受通用 stdio 设置的客户端，请将以下两处 `/absolute/path/My-Own-Researcher` 替换为你的实际项目路径：

```json
{
  "mcpServers": {
    "my-own-researcher": {
      "command": "uv",
      "args": [
        "run", "--project", "/absolute/path/My-Own-Researcher/backend", "--frozen",
        "python", "/absolute/path/My-Own-Researcher/backend/mcp_server.py"
      ]
    }
  }
}
```

stdio 会启动一个适配器；后端和图谱服务仍需处于运行状态。如果 Agent 的 `PATH` 中找不到 `uv`，请使用其绝对路径。客户端的工具超时需要单独设置，具体配置字段因客户端而异。

生成器的 stdio 输出会自动使用项目的绝对路径，并在可用时解析 `uv` 路径。自定义 HTTP 端口时使用 `--url http://127.0.0.1:YOUR_PORT/mcp`。如果 Hermes 的调用可能超过其 HTTP 空闲时间限制，请使用 stdio。

各客户端的配置位置、格式、超时单位和兼容性说明详见[逐 Agent MCP 配置指南](docs/agent-mcp.md)；工具、轮询、重试和通过 SSH 远程访问的说明详见 [MCP 使用指南](docs/mcp.md)。

</details>

## 存储与运行限制

| 注意事项 | 说明 |
| --- | --- |
| **单用户、单后端** | 这是面向单用户的本地应用。服务应绑定到回环地址；不支持多个后端 worker 或共享的公网部署。 |
| **同时备份两部分数据** | 项目和检查点位于 `backend/uploads/`；Neo4j 数据位于其 Docker 卷中。请一起备份。 |
| **数据本地保存，推理调用远程服务** | 本地文件和图谱保留在你的电脑上。推理所需内容会发送到所选 CLI 的模型提供方。 |
| **现有图谱保留原提供方** | 修改配置不会迁移项目数据。图谱层满足本应用的需求，并未实现 Zep 的全部功能。 |

## MyOwnStack 的一部分

**共享 AI 接入能力，构建实用的本地服务。** MyOwnStack 将一组应用连接起来，让它们在你的电脑上保存工作数据，并使用你已有的 AI 账号。

| 项目 | 职责 |
| --- | --- |
| **[MyOwnResearcher](https://github.com/Handriantog/My-Own-Researcher)** | 将文档和问题转化为知识图谱、模拟观点与研究报告。 |
| **[MyOwnLlmIntegrator](https://github.com/Handriantog/My-Own-LLM-Integrator)** | 为本地应用提供可复用的 npm 接口，调用已登录的 Agent CLI。包含 Python 引擎、JavaScript API 和提供方预设。 |

```text
MyOwnStack/
└── MyOwnResearcher/
    └── node_modules/
        └── myown-llm-integrator/   # 从 npm 安装的共享引擎
```

Researcher 负责研究流程、运行设置、并发控制和用量历史。Integrator 负责 CLI 执行、提供方响应解析和进程清理。Python 服务从已安装的 npm 包中加载其引擎。仅在开发 Integrator 包本身时，才需要它的源代码仓库。

想构建其他本地服务？可以从 **[Integrator 快速开始](https://github.com/Handriantog/My-Own-LLM-Integrator#quickstart)** 入手。Python 依赖布局详见 [Researcher 集成指南](docs/llm-integrator.md)。

## 接下来做什么

| 我想…… | 查看这里 |
| --- | --- |
| 在其他应用中复用订阅推理引擎 | [MyOwnLlmIntegrator](https://github.com/Handriantog/My-Own-LLM-Integrator) |
| 更新共享 npm 依赖 | [集成指南](docs/llm-integrator.md) |
| 了解模型、并行度、用量估算或自动研究 | [研究设置指南](docs/research-settings.md) |
| 配置存储或恢复运行 | [工作台指南](docs/my-own-researcher.md) |
| 调整默认 Codex 配置 | [Codex 提供方指南](docs/codex-provider.md) |
| 使用其他 CLI 进行推理 | [Agent 推理提供方指南](docs/agent-providers.md) |
| 连接我的 AI 助手 | [逐 Agent MCP 配置指南](docs/agent-mcp.md) |
| 了解研究工具与工作流程 | [MCP 使用指南](docs/mcp.md) |
| 阅读英文说明 | [English README](README.md) |

以上详细指南目前使用英文。

## 致谢与许可证

本项目基于 MiroFish 团队的 **[MiroFish](https://github.com/666ghj/MiroFish)**，原始界面和研究模拟流程由其贡献者创建。本独立分支保留 **[GNU Affero General Public License v3.0](LICENSE)**。原项目说明见[上游文档](https://github.com/666ghj/MiroFish#readme)；上游的安装步骤不能直接替代本分支的本地安装说明。

模拟功能由 CAMEL-AI 的 **[OASIS](https://github.com/camel-ai/oasis)** 提供；本地图谱处理使用 **[Graphiti](https://github.com/getzep/graphiti)** + **[Neo4j](https://github.com/neo4j/neo4j)**。依赖与模型保留各自的许可证。独立维护不代表获得上述项目或 OpenAI 的认可。

---

<p align="center"><strong>下一次研究，从一个好问题开始。</strong><br><a href="#安装与运行">搭建你的工作台 →</a></p>
