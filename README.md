# case-teardown 🔍

Tear down any URL — websites, articles, landing pages, GitHub repos — into structured analysis reports.

**[中文说明](#中文) | [English](#english)**

---

<a id="english"></a>
## What it does

Give it a URL. It auto-detects the type and runs the right analysis:

| Type | What it analyzes |
|------|-----------------|
| 🌐 **Website** | Tech stack, content audit, business model, SEO, competitive score (1-10) |
| 📰 **Article** | Topic type, structure teardown, emotional + practical value, virality factors |
| 🚀 **Landing page** | Positioning, conversion elements checklist, copy quality |
| 📦 **GitHub repo** | Activity, tech stack, commercial potential, what to learn |

## Quick Start

```bash
# Install
pip install git+https://github.com/archorfight/case-teardown.git

# Set your API key (any OpenAI-compatible API works)
export LLM_API_KEY=*** it
case-teardown https://example.com
```

## Usage

```bash
# Basic — save report to current directory (Chinese output)
case-teardown https://example.com

# English report
case-teardown https://example.com --lang en

# Specify output directory
case-teardown https://example.com -o ./reports

# Print to stdout instead of saving
case-teardown https://example.com --stdout

# Use DeepSeek
case-teardown https://example.com \
  --base-url https://api.deepseek.com/v1 \
  --model deepseek-chat

# Use any OpenAI-compatible provider
case-teardown https://example.com \
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
pip install "case-teardown[spa]"
playwright install chromium
```

Without this, the tool falls back to static HTML parsing (works for most SSR sites).

### Output language

```bash
case-teardown https://example.com --lang zh  # Chinese (default)
case-teardown https://example.com --lang en  # English
```

## Examples

See the [`examples/`](examples/) directory for sample reports:
- [Website analysis (Chinese)](examples/ideafactorys.com-analysis-2026-07-30.md) — tool site teardown
- [Website analysis (English)](examples/stripe.com-analysis-2026-07-30.md) — SaaS site analysis
- [GitHub repo evaluation](examples/github.com-github-eval-2026-07-30.md) — open source project assessment

## How it works

```
URL → type detection → page fetch + tech probe → LLM analysis → markdown report
```

1. **Detect** URL type from domain/path patterns
2. **Fetch** page HTML, extract metadata, probe headers/sitemap/routes
3. **Analyze** via LLM with type-specific prompt templates
4. **Output** a structured markdown report

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
| 🌐 **网站/工具站** | 技术栈、内容审计、商业模式、SEO、竞争力评分(1-10) |
| 📰 **自媒体内容** | 选题类型、结构拆解、双价值检查、传播因子 |
| 🚀 **产品/落地页** | 定位分析、转化元素清单、文案质量 |
| 📦 **GitHub项目** | 活跃度、技术栈、商业潜力、可借鉴点 |

### 快速开始

```bash
# 安装
pip install git+https://github.com/archorfight/case-teardown.git

# 设置 API Key
export LLM_API_KEY=*** it

# 支持任何 OpenAI 兼容 API（OpenAI / DeepSeek / 智谱GLM / OpenRouter / 本地模型）
```

### 示例报告

见 [`examples/`](examples/) 目录。

## License

MIT
