"""Core analyzer — ties fetcher + LLM together, generates reports."""

from datetime import datetime

from .fetcher import (
    detect_type,
    fetch_page,
    fetch_github_info,
    build_tech_info,
    extract_source_name,
    DEFAULT_SYSTEM_MESSAGE,
)
from .llm import get_prompts, call_llm


def teardown(
    url: str,
    api_key: str,
    base_url: str,
    model: str,
    lang: str = "zh",
    url_type_override: str = None,
) -> dict:
    """
    Analyze a URL end-to-end.

    Returns:
        {
            "url": str,
            "type": str,
            "type_source": str,   # "auto" or "override"
            "fetch_status": str,  # "ok", "partial", or "failed"
            "title": str,
            "report": str,
            "tech_info": str,
            "error": str | None,
        }
    """
    result = {
        "url": url,
        "type": "",
        "type_source": "",
        "fetch_status": "ok",
        "title": "",
        "report": "",
        "tech_info": "",
        "error": None,
    }

    # Step 1: Determine type — override or auto-detect (WP4)
    if url_type_override:
        url_type = url_type_override
        result["type_source"] = "override"
    else:
        url_type = detect_type(url)
        result["type_source"] = "auto"
    result["type"] = url_type

    # Step 2: Fetch data
    if url_type == "github":
        page_data = fetch_github_info(url)
    else:
        page_data = fetch_page(url)

    fetch_error = page_data.get("error")
    if fetch_error:
        result["error"] = f"Fetch failed: {fetch_error}"

    title = page_data.get("title", url) or url
    result["title"] = title
    content = page_data.get("body_text", "")
    result["content_preview"] = content[:500]

    # WP5: If fetch completely failed with no usable content, mark as failed first
    content_len = page_data.get("body_text_length", len(content))
    github_api_data = page_data.get("github_api_data") or {}
    if fetch_error and not content.strip():
        # For github type, API data may still be valid even if page scraping failed
        if url_type == "github" and github_api_data:
            result["fetch_status"] = "partial"
        else:
            result["fetch_status"] = "failed"
            result["report"] = _fallback_report(url, url_type, page_data, "", result["fetch_status"])
            return result

    # WP6: Type-specific thin content check
    is_thin = _check_thin_content(url_type, content_len, page_data)

    # For github type: never thin based on text (WP6)
    if url_type == "github":
        # Skip thin content check entirely for github
        is_thin = False
        # But check for API rate limit → partial
        if page_data.get("github_api_error"):
            result["fetch_status"] = "partial"
            if result["error"] is None:
                result["error"] = page_data["github_api_error"]

    if is_thin:
        result["fetch_status"] = "partial"
        if result["error"] is None:
            result["error"] = f"Content too thin ({content_len} chars). Page is likely a SPA that requires JavaScript rendering."
        else:
            result["error"] += f" | Content too thin ({content_len} chars)."
        result["report"] = _thin_content_report(url, url_type, page_data, result["fetch_status"])
        return result

    # Fetch error but still produced report → partial
    if fetch_error:
        result["fetch_status"] = "partial"

    # Step 3: Build tech info
    tech_info = build_tech_info(page_data, url_type)
    result["tech_info"] = tech_info

    # Step 4: Pick prompt template
    prompts = get_prompts(lang)
    template = prompts.get(url_type, prompts["website"])

    source = extract_source_name(url)

    # Step 5: Format prompt
    prompt = template.format(
        title=title[:200],
        content=f"<UNTRUSTED_PAGE_CONTENT>\n{content[:5000]}\n</UNTRUSTED_PAGE_CONTENT>",
        tech_info=tech_info,
        source=source,
    )

    # Step 6: Call LLM with system message for injection isolation (WP3)
    try:
        report = call_llm(
            prompt,
            api_key=api_key,
            base_url=base_url,
            model=model,
            system_message=DEFAULT_SYSTEM_MESSAGE,
        )
        result["report"] = report
    except Exception as e:
        result["error"] = f"LLM call failed: {e}"
        result["fetch_status"] = "partial"
        result["report"] = _fallback_report(url, url_type, page_data, tech_info, result["fetch_status"])

    return result


def _check_thin_content(url_type: str, content_len: int, page_data: dict) -> bool:
    """WP6: Type-specific thin content detection.

    - website: < 200 chars AND (has SPA markers OR no h1) → thin
    - article: < 100 chars → thin
    - product: < 150 chars AND has SPA markers → thin
    - github: NEVER thin based on text (caller skips this)
    """
    if url_type == "github":
        return False

    if url_type == "article":
        return content_len < 100

    if url_type == "product":
        if content_len < 150:
            html = page_data.get("rendered_with", "")  # playwright-rendered = not thin
            has_spa = _has_spa_markers(page_data)
            return has_spa
        return False

    # website (default)
    if content_len < 200:
        has_spa = _has_spa_markers(page_data)
        has_h1 = bool(page_data.get("h1_tags"))
        return has_spa or not has_h1
    return False


def _has_spa_markers(page_data: dict) -> bool:
    """Check if page data has indicators of being a client-side rendered SPA."""
    fw = page_data.get("frameworks_detected", [])
    spa_frameworks = {"Next.js", "Gatsby", "Nuxt"}
    if spa_frameworks & set(fw):
        return True
    # Also check if rendered_with indicates playwright fallback was used
    if page_data.get("rendered_with") == "playwright":
        return True
    return False


def _thin_content_report(url: str, url_type: str, page_data: dict, fetch_status: str = "partial") -> str:
    """Generate an honest report when page content is too thin to analyze."""
    date = datetime.now().strftime("%Y-%m-%d")
    title = page_data.get("title", url)
    content_preview = page_data.get("body_text", "")[:500]
    html_size = page_data.get("html_size_kb", "?")

    return f"""# {title}

> URL: {url}
> 分析日期：{date}
> ⚠️ 无法生成分析报告：页面内容不足
> 抓取状态：{fetch_status}

## 原因

抓取到的页面有效内容仅 {page_data.get('body_text_length', 0)} 字符（HTML {html_size}KB）。
该网站很可能是纯前端 SPA（单页应用），需要 JavaScript 渲染才能显示内容。

url-xray CLI 使用 httpx 做静态抓取，无法执行 JavaScript。可用的替代方案：

1. 安装 playwright 渲染支持：`pip install url-xray[spa] && playwright install chromium`
2. 使用 Hermes skill 手动分析
3. 使用无头浏览器工具抓取渲染后内容

## 已采集的有限数据

```
标题: {title}
页面体积: {html_size}KB
状态码: {page_data.get('status_code', '?')}
内容预览: {content_preview or '(空)'}
```

注意：以上数据基于未渲染的 HTML，不代表页面真实内容。
"""


def _fallback_report(url: str, url_type: str, page_data: dict, tech_info: str, fetch_status: str = "partial") -> str:
    """Generate a basic report without LLM (fallback when API fails)."""
    date = datetime.now().strftime("%Y-%m-%d")
    title = page_data.get("title", url)

    return f"""# {title}

> 分析日期：{date} | URL: {url}
> ⚠️ LLM 分析失败，以下为基础数据（无 AI 分析）
> 抓取状态：{fetch_status}

## 基础数据

{tech_info}

## 页面文本预览

{page_data.get("body_text", "无内容")[:2000]}
"""


def save_report(result: dict, output_dir: str = ".", fmt: str = "md") -> str:
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

    if fmt == "html":
        from .html_render import render_html
        ext = "html"
        filepath = os.path.join(output_dir, f"{clean_host}-{type_suffix}-{date}.{ext}")
        html_content = render_html(result)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_content)
    else:
        ext = "md"
        filepath = os.path.join(output_dir, f"{clean_host}-{type_suffix}-{date}.{ext}")
        header = f"> URL: {result['url']} | Type: {result['type']} | Date: {date}\n\n"
        full_report = header + result["report"]
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(full_report)

    return filepath
