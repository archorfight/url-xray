# Contributing to url-xray

Thanks for your interest in contributing! Here's how to help.

## Bug Reports & Feature Requests

- Open a [GitHub Issue](https://github.com/archorfight/url-xray/issues)
- Include the URL you tried to analyze and the error/output
- For feature requests, describe the use case

## Development Setup

```bash
git clone https://github.com/archorfight/url-xray.git
cd url-xray
pip install -e ".[dev]"
pytest tests/ -v
```

## Adding New URL Types

Want to support a new URL type (e.g., YouTube videos, App Store pages)?

1. Add the type to `detect_type()` in `fetcher.py`
2. Add a prompt template in `llm.py` (both `PROMPTS_ZH` and `PROMPTS_EN`)
3. Add any type-specific data fetching logic in `fetcher.py`
4. Add tests in `tests/test_url_xray.py`
5. Update README

## Improving Prompts

The analysis quality depends on prompt engineering. If you find a prompt that produces better results:

1. Edit the template in `llm.py`
2. Run against the same URL to compare output
3. Submit a PR with before/after comparison

## Pull Request Process

1. Fork the repo and create your branch from `main`
2. Run `pytest tests/ -v` — all tests must pass
3. Keep changes focused — one feature/fix per PR
4. Write clear commit messages

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
