"""Fetch and analyze URL data — type detection, content extraction, tech probing."""

import re
import socket
import json
from datetime import datetime
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup


def detect_type(url: str) -> str:
    """Detect URL type from domain and path patterns."""
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.lower()

    # GitHub repo
    if host in ("github.com", "www.github.com") and path.count("/") >= 2:
        return "github"

    # Self-media / article platforms
    article_hosts = {
        "mp.weixin.qq.com": "article",
        "waytoagi.feishu.cn": "article",
        "zhuanlan.zhihu.com": "article",
        "www.zhihu.com": "article",
        "xiaohongshu.com": "article",
        "www.xiaohongshu.com": "article",
        "weibo.com": "article",
        "m.weibo.cn": "article",
        "www.douyin.com": "article",
        "www.bilibili.com": "article",
    }
    if host in article_hosts:
        return article_hosts[host]

    # Product pages
    product_hosts = {
        "www.producthunt.com": "product",
        "producthunt.com": "product",
        "apps.apple.com": "product",
        "play.google.com": "product",
    }
    if host in product_hosts:
        return product_hosts[host]

    # Feishu/Lark wiki
    if "feishu.cn" in host or "larksuite.com" in host:
        return "article"

    # Default: treat as website
    return "website"


def get_domain_age(domain: str) -> str:
    """Try to get domain registration date via whois."""
    try:
        import subprocess
        result = subprocess.run(
            ["whois", domain],
            capture_output=True, text=True, timeout=10
        )
        for line in result.stdout.split("\n"):
            if re.search(r"creation date|created date|registered", line, re.IGNORECASE):
                return line.strip()[:120]
    except Exception:
        pass
    return "unknown"


def fetch_headers(url: str) -> dict:
    """Fetch HTTP headers."""
    headers = {}
    try:
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            resp = client.head(url, headers={"User-Agent": _UA()})
            headers = dict(resp.headers)
    except Exception:
        try:
            with httpx.Client(timeout=15, follow_redirects=True) as client:
                resp = client.get(url, headers={"User-Agent": _UA()})
                headers = dict(resp.headers)
        except Exception:
            pass
    return headers


def check_routes(url: str) -> dict:
    """Check common routes for website type."""
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    routes = {}
    for route in ["login", "register", "pricing", "about", "dashboard"]:
        try:
            with httpx.Client(timeout=10, follow_redirects=False) as client:
                resp = client.get(f"{base}/{route}", headers={"User-Agent": _UA()})
                routes[route] = resp.status_code
        except Exception:
            routes[route] = "error"
    return routes


def check_sitemap(url: str) -> int:
    """Check sitemap and count URLs."""
    parsed = urlparse(url)
    sitemap_url = f"{parsed.scheme}://{parsed.netloc}/sitemap.xml"
    try:
        with httpx.Client(timeout=10, follow_redirects=True) as client:
            resp = client.get(sitemap_url, headers={"User-Agent": _UA()})
            if resp.status_code == 200:
                return resp.text.count("<loc>")
    except Exception:
        pass
    return 0


def _UA() -> str:
    return "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


def _is_spa(html: str) -> bool:
    """Detect if a page is likely a client-side rendered SPA (empty body)."""
    text_len = len(re.sub(r"<[^>]+>", "", html).strip())
    has_spa_markers = any(marker in html for marker in ["__NEXT_DATA__", "__NUXT__", "data-reactroot", "id=\"root\""])
    return text_len < 500 and has_spa_markers


def _fetch_with_playwright(url: str) -> dict:
    """Fallback: fetch SPA pages using playwright (if installed)."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {"error": "Playwright not installed. Run: pip install playwright && playwright install chromium"}

    data = {"url": url, "error": None}
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent=_UA())
            page.goto(url, wait_until="networkidle", timeout=20000)
            page.wait_for_timeout(2000)  # extra wait for dynamic content

            data["status_code"] = 200
            html = page.content()
            data["final_url"] = page.url
            data["title"] = page.title()
            data["html_size_kb"] = round(len(html) / 1024)
            data["body_text"] = page.inner_text("body")[:5000]
            data["body_text_length"] = len(data["body_text"])
            data["rendered_with"] = "playwright"

            # Basic stats from rendered DOM
            data["img_count"] = page.locator("img").count()
            data["link_count"] = page.locator("a").count()
            data["h1_tags"] = [await_el.inner_text() for await_el in []]  # filled below
            data["external_links"] = 0  # approximate

            browser.close()
    except Exception as e:
        data["error"] = str(e)

    return data


def fetch_page(url: str) -> dict:
    """Fetch page HTML and extract structured data."""
    data = {"url": url, "error": None}

    try:
        with httpx.Client(timeout=20, follow_redirects=True) as client:
            resp = client.get(url, headers={"User-Agent": _UA(), "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"})
            html = resp.text
            data["status_code"] = resp.status_code
            data["final_url"] = str(resp.url)
    except Exception as e:
        data["error"] = str(e)
        return data

    soup = BeautifulSoup(html, "html.parser")

    # Check if SPA with empty body — try playwright fallback
    body_text_check = soup.get_text(strip=True)
    if _is_spa(html):
        import os
        # Only try playwright if it's installed
        try:
            import playwright  # noqa
            spa_data = _fetch_with_playwright(url)
            if not spa_data.get("error"):
                # Merge playwright data, keeping httpx headers
                spa_data["status_code"] = data.get("status_code", 200)
                return spa_data
        except ImportError:
            pass  # playwright not installed, continue with what we have

    # Basic metadata
    data["title"] = (soup.title.string or "").strip() if soup.title else ""
    data["html_size_kb"] = round(len(html) / 1024)

    # Meta tags
    for name in ["description", "keywords", "generator", "author"]:
        tag = soup.find("meta", attrs={"name": name})
        if tag:
            data[f"meta_{name}"] = tag.get("content", "")

    # Open Graph
    for prop in ["og:title", "og:description", "og:type", "og:url"]:
        tag = soup.find("meta", attrs={"property": prop})
        if tag:
            data[prop] = tag.get("content", "")

    # Framework detection from HTML
    fw = []
    if soup.find(id="__NEXT_DATA__"):
        fw.append("Next.js")
    if soup.find(id="___gatsby"):
        fw.append("Gatsby")
    if soup.find(id="__nuxt"):
        fw.append("Nuxt")
    data["frameworks_detected"] = fw

    # Laravel/PHP cookie hint (can't read Set-Cookie from JS, infer from HTML)
    if "csrf-token" in html.lower() or "laravel_session" in html.lower():
        fw.append("Laravel")
        data["frameworks_detected"] = fw

    # Content stats
    data["h1_tags"] = [h1.get_text(strip=True) for h1 in soup.find_all("h1")]
    data["h2_count"] = len(soup.find_all("h2"))
    data["img_count"] = len(soup.find_all("img"))
    data["link_count"] = len(soup.find_all("a"))
    data["external_links"] = len([
        a for a in soup.find_all("a", href=True)
        if a["href"].startswith("http") and urlparse(a["href"]).netloc != urlparse(url).netloc
    ])
    data["script_srcs"] = [s.get("src", "") for s in soup.find_all("script", src=True)][:15]
    data["has_jsonld"] = bool(soup.find("script", type="application/ld+json"))

    # Body text extraction
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    body_text = soup.get_text(separator="\n", strip=True)
    data["body_text"] = body_text[:5000]
    data["body_text_length"] = len(body_text)

    # Structured data
    data["lang"] = soup.html.get("lang", "not set") if soup.html else "not set"

    return data


def fetch_github_info(url: str) -> dict:
    """Fetch GitHub repo info via page scraping."""
    data = fetch_page(url)
    # Extract star count, language, etc. from page text
    text = data.get("body_text", "")

    stars = "?"
    star_match = re.search(r"([\d.]+k?)\s*[Ss]tar", text[:2000])
    if star_match:
        stars = star_match.group(1)

    data["github_stars"] = stars
    data["github_url"] = url
    return data


def build_tech_info(page_data: dict, url_type: str) -> str:
    """Format technical info as readable text for the LLM prompt."""
    lines = []
    url = page_data.get("url", "")

    if url_type == "website":
        parsed = urlparse(url)
        domain = parsed.netloc
        domain_age = get_domain_age(domain)
        headers = fetch_headers(url)
        routes = check_routes(url)
        sitemap_count = check_sitemap(url)

        lines.append(f"域名: {domain}")
        lines.append(f"域名注册: {domain_age}")
        lines.append(f"页面体积: {page_data.get('html_size_kb', '?')}KB")
        lines.append(f"图片数: {page_data.get('img_count', 0)}")
        lines.append(f"总链接数: {page_data.get('link_count', 0)} (外链: {page_data.get('external_links', 0)})")
        lines.append(f"H1: {page_data.get('h1_tags', [])}")
        lines.append(f"框架: {', '.join(page_data.get('frameworks_detected', ['未检测到'])) or '未检测到'}")
        lines.append(f"JSON-LD: {'有' if page_data.get('has_jsonld') else '无'}")
        lines.append(f"Sitemap页面数: {sitemap_count}")
        lines.append(f"Server: {headers.get('server', '?')}")
        lines.append(f"路由探测: {json.dumps(routes, ensure_ascii=False)}")
        if page_data.get("meta_description"):
            lines.append(f"Description: {page_data['meta_description'][:150]}")
    else:
        lines.append(f"URL: {url}")
        lines.append(f"页面体积: {page_data.get('html_size_kb', '?')}KB")

    return "\n".join(lines)


def extract_source_name(url: str) -> str:
    """Extract a human-readable source name from URL."""
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    names = {
        "mp.weixin.qq.com": "微信公众号",
        "waytoagi.feishu.cn": "通往AGI",
        "zhuanlan.zhihu.com": "知乎",
        "www.zhihu.com": "知乎",
        "xiaohongshu.com": "小红书",
        "www.xiaohongshu.com": "小红书",
        "weibo.com": "微博",
        "m.weibo.cn": "微博",
    }
    return names.get(host, host)
