"""Core analyzer — ties fetcher + LLM together, generates reports."""

from datetime import datetime

from .fetcher import (
    detect_type,
    fetch_page,
    fetch_github_info,
    build_tech_info,
    extract_source_name,
)
from .llm import PROMPTS, call_llm


def teardown(url: str, api_key: str, base_url: str, model: str) -> dict:
    """
    Analyze a URL end-to-end.

    Returns:
        {
            "url": str,
            "type": str,
            "title": str,
            "report": str,       # markdown report
            "tech_info": str,    # raw tech data for debugging
            "error": str | None,
        }
    """
    result = {
        "url": url,
        "type": "",
        "title": "",
        "report": "",
        "tech_info": "",
        "error": None,
    }

    # Step 1: Detect type
    url_type = detect_type(url)
    result["type"] = url_type

    # Step 2: Fetch data
    if url_type == "github":
        page_data = fetch_github_info(url)
    else:
        page_data = fetch_page(url)

    if page_data.get("error"):
        result["error"] = f"Fetch failed: {page_data['error']}"
        # Still try with whatever data we have

    title = page_data.get("title", url) or url
    result["title"] = title
    content = page_data.get("body_text", "")
    result["content_preview"] = content[:500]

    # Step 3: Build tech info
    tech_info = build_tech_info(page_data, url_type)
    result["tech_info"] = tech_info

    # Step 4: Pick prompt template
    template = PROMPTS.get(url_type, PROMPTS["website"])

    source = extract_source_name(url)

    # Step 5: Format prompt
    prompt = template.format(
        title=title[:200],
        content=content[:5000],
        tech_info=tech_info,
        source=source,
    )

    # Step 6: Call LLM
    try:
        report = call_llm(prompt, api_key=api_key, base_url=base_url, model=model)
        result["report"] = report
    except Exception as e:
        result["error"] = f"LLM call failed: {e}"
        result["report"] = _fallback_report(url, url_type, page_data, tech_info)

    return result


def _fallback_report(url: str, url_type: str, page_data: dict, tech_info: str) -> str:
    """Generate a basic report without LLM (fallback when API fails)."""
    date = datetime.now().strftime("%Y-%m-%d")
    title = page_data.get("title", url)

    return f"""# {title}

> 分析日期：{date} | URL: {url}
> ⚠️ LLM 分析失败，以下为基础数据（无 AI 分析）

## 基础数据

{tech_info}

## 页面文本预览

{page_data.get("body_text", "无内容")[:2000]}
"""


def save_report(result: dict, output_dir: str = ".") -> str:
    """Save report to file. Returns file path."""
    import os

    date = datetime.now().strftime("%Y-%m-%d")

    # Generate filename
    from urllib.parse import urlparse
    host = urlparse(result["url"]).netloc.replace("www.", "")

    type_suffix = {
        "website": "analysis",
        "article": "teardown",
        "product": "landing",
        "github": "github-eval",
    }.get(result["type"], "analysis")

    # Clean host for filename
    clean_host = host.replace("/", "_").replace(":", "_")[:40]
    filename = f"{clean_host}-{type_suffix}-{date}.md"
    filepath = os.path.join(output_dir, filename)

    # Add header
    header = f"> URL: {result['url']} | Type: {result['type']} | Date: {date}\n\n"
    full_report = header + result["report"]

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(full_report)

    return filepath
