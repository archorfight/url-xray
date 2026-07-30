# case-teardown 🔍

Tear down any URL — websites, articles, landing pages, GitHub repos — into structured analysis reports.

## What it does

Give it a URL. It auto-detects the type and runs the right analysis:

| Type | What it analyzes |
|------|-----------------|
| 🌐 **Website / Tool site** | Tech stack, content audit, business model, SEO, competitive score (1-10) |
| 📰 **Article / Social media** | Topic type, structure teardown, emotional + practical value, virality factors |
| 🚀 **Product / Landing page** | Positioning, conversion elements checklist, copy quality |
| 📦 **GitHub repo** | Activity, tech stack, commercial potential, what to learn |

## Quick Start

```bash
# Install
pip install -e .

# Set your API key (any OpenAI-compatible API works)
export LLM_API_KEY=*** Or use a .env file (see .env.example)
case-teardown https://example.com
```

## Usage

```bash
# Basic — save report to current directory
case-teardown https://example.com

# Specify output directory
case-teardown https://example.com -o ./reports

# Print to stdout instead of saving
case-teardown https://example.com --stdout

# Use DeepSeek
case-teardown https://example.com \
  --base-url https://api.deepseek.com/v1 \
  --model deepseek-chat

# Use OpenRouter
case-teardown https://example.com \
  --base-url https://openrouter.ai/api/v1 \
  --model anthropic/claude-sonnet-4
```

## Configuration

All config via environment variables or `.env` file:

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

## How it works

```
URL → type detection → page fetch + tech probe → LLM analysis → markdown report
```

1. **Detect** URL type from domain/path patterns
2. **Fetch** page HTML, extract metadata, probe headers/sitemap/routes
3. **Analyze** via LLM with type-specific prompt templates
4. **Output** a structured markdown report

## Output

Reports are saved as `<domain>-<type>-<date>.md`.

Example for a website:
```
# Example Site 深度分析

## 一句话结论
[定性判断]

## 基础情报
[技术数据表格]

## 内容审计
[标称 vs 实际]

## 商业模式
[变现路径分析]

## 竞争力评分
[1-10分，5个维度]

## 可借鉴点
[可以偷的思路 + 不要犯的错]
```

## Development

```bash
# Install in dev mode
pip install -e .

# Run directly
python -m case_teardown https://example.com

# Run tests
pytest tests/
```

## License

MIT
