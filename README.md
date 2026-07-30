# url-xray 🔍

Tear down any URL — websites, articles, landing pages, GitHub repos — into structured analysis reports.

**[中文说明](#中文) | [English](#english)**

---

<a id="english"></a>
## What it does

Give it a URL. It auto-detects the type and runs the right analysis:

| Type | What it analyzes |
|------|-----------------|
| 🌐 **Website** | Tech stack, content audit, business model, SEO, competitive score (0-5) |
| 📰 **Article** | Topic type, structure teardown, emotional + practical value, virality factors |
| 🚀 **Landing page** | Positioning, conversion elements checklist, copy quality |
| 📦 **GitHub repo** | Activity, tech stack, commercial potential, what to learn |

### Skill vs CLI

This repo contains two complementary things:

- **`skill/url-xray/`** — An agent skill (operation manual for AI agents like Hermes). Uses headless browser, terminal, and other agent tools for deep analysis. Handles SPAs, login walls, visual assessment.
- **`url_xray/`** (Python CLI) — A standalone pip package. Automated httpx-based fetching + LLM analysis. Simpler, but cannot render JavaScript by default; install SPA dependency to enable. When it can't fetch content (SPA), it says so honestly instead of fabricating analysis.

The skill is the source of truth for analysis framework. The CLI follows it.

## Quick Start

```bash
# Install
pip install git+https://github.com/archorfight/url-xray.git

# Set your API key (any OpenAI-compatible API works)
export LLM_API_KEY=your-key-here

# Analyze
url-xray https://example.com
```

## Usage

```bash
# Basic — save report to current directory (Chinese output)
url-xray https://example.com

# English report
url-xray https://example.com --lang en

# Override URL type detection
url-xray https://somesite.com --type product

# Specify output directory
url-xray https://example.com -o ./reports

# Print to stdout instead of saving
url-xray https://example.com --stdout

# Use DeepSeek
url-xray https://example.com \
  --base-url https://api.deepseek.com/v1 \
  --model deepseek-chat

# Use any OpenAI-compatible provider
url-xray https://example.com \
  --base-url https://openrouter.ai/api/v1 \
  --model anthropic/claude-sonnet-4
```

## Configuration

All config via environment variables or `.env` file (see `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_API_KEY` | *(required)* | Your API key |
| `LLM_BASE_URL` | `https://api.openai.com/v1` | API base URL |
| `LLM_MODEL` | `gpt-4o` | Model name |

### Supported providers

Any OpenAI-compatible API:
- OpenAI (`gpt-4o`, `gpt-4o-mini`)
- DeepSeek (`deepseek-chat`)
- OpenRouter (100+ models)
- Zhipu/GLM (`glm-4`)
- Local LLMs via LM Studio / Ollama (OpenAI compat mode)

### Optional: SPA rendering support

For JavaScript-rendered sites (Next.js, React, etc.), install with the optional SPA dependency:

```bash
pip install "url-xray[spa]"
playwright install chromium
```

Without this, the tool falls back to static HTML parsing (works for most SSR sites).

### Scoring

Each applicable dimension is scored 0-5 (0=none, 1=terrible, 3=adequate, 5=excellent).
Each score includes a one-line reason and one piece of evidence.
Missing evidence is marked N/A.
Total is a simple average of scored dimensions.

### Output language

```bash
url-xray https://example.com --lang zh  # Chinese (default)
url-xray https://example.com --lang en  # English
```

## Examples

See the [`examples/`](examples/) directory for a sample HTML report:
- [Hyper3D](examples/hyper3d.ai-analysis-2026-07-30.html) — website analysis (current version)

## How it works

```
URL → type detection → page fetch + tech probe → LLM analysis → structured report
```

1. **Detect** URL type from domain/path patterns (or override with `--type`)
2. **Fetch** page HTML, extract metadata, probe headers/sitemap/routes
3. **Analyze** via LLM with type-specific prompt templates
4. **Output** a structured markdown or HTML report

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## License

MIT

---

<a id="中文"></a>
## 中文说明

给一个 URL，自动识别类型并输出结构化拆解报告。

| 类型 | 分析内容 |
|------|----------|
| 🌐 **网站/工具站** | 技术栈、内容审计、商业模式、SEO、竞争力评分(0-5) |
| 📰 **自媒体内容** | 选题类型、结构拆解、双价值检查、传播因子 |
| 🚀 **产品/落地页** | 定位分析、转化元素清单、文案质量 |
| 📦 **GitHub项目** | 活跃度、技术栈、商业潜力、可借鉴点 |

### Skill 与 CLI 的区别

- **skill/url-xray/**：AI Agent 的操作手册（如 Hermes）。使用浏览器、终端等工具做深度分析，能处理 SPA、登录墙、视觉评估。
- **url_xray/**（Python CLI）：独立 pip 包。基于 httpx 自动抓取 + LLM 分析。更简单，但无法渲染 JavaScript 或做视觉评估。抓不到内容时会如实说明，不编造分析。

Skill 是分析框架的唯一真源，CLI 跟随它。

### 快速开始

```bash
# 安装
pip install git+https://github.com/archorfight/url-xray.git

# 设置 API Key
export LLM_API_KEY=your-key-here

# 支持任何 OpenAI 兼容 API（OpenAI / DeepSeek / 智谱GLM / OpenRouter / 本地模型）
```

### 评分规则

每个适用维度打 0-5 分（0=无，1=极差，3=及格，5=优秀）。
每个分数附带一句话理由和一条证据。
证据不足标 N/A。
总分为已评分维度的简单平均值。

### 示例报告

见 [`examples/`](examples/) 目录。

## License

MIT
