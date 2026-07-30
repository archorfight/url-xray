"""HTML report renderer — dark theme card-style report with copy button."""

import html
from datetime import datetime


def _md_to_html(md: str) -> str:
    """Minimal markdown-to-HTML converter (no external deps).

    Handles: headings, bold, italic, code blocks, inline code,
    tables, blockquotes, bullet lists, numbered lists, checkboxes, hr.
    """
    import re

    lines = md.split("\n")
    out = []
    in_table = False
    in_code = False
    in_list = False
    in_olist = False
    table_rows = []

    def esc(text):
        return html.escape(text)

    def inline(text):
        text = esc(text)
        # Bold
        text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
        # Italic (avoid matching ** by requiring non-* before)
        text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", text)
        # Inline code
        text = re.sub(r"`([^`]+)`", r'<code class="inline-code">\1</code>', text)
        # Links [text](url)
        text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2" target="_blank">\1</a>', text)
        # Checkbox
        text = text.replace("- [ ]", '<span class="checkbox">☐</span>')
        text = text.replace("- [x]", '<span class="checkbox checked">☑</span>')
        return text

    i = 0
    while i < len(lines):
        line = lines[i]

        # Code block
        if line.strip().startswith("```"):
            if in_code:
                out.append("</code></pre>")
                in_code = False
            else:
                lang = line.strip().lstrip("`").strip()
                out.append(f'<pre class="code-block"><code class="language-{lang}">')
                in_code = True
            i += 1
            continue

        if in_code:
            out.append(esc(line))
            i += 1
            continue

        # Table detection
        if "|" in line and line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            # Skip separator rows
            if all(re.match(r"^[-:]+$", c) for c in cells):
                i += 1
                continue
            table_rows.append(cells)
            in_table = True
            i += 1
            continue
        elif in_table:
            # Flush table
            if table_rows:
                out.append('<div class="table-wrap"><table>')
                out.append("<thead><tr>")
                for c in table_rows[0]:
                    out.append(f"<th>{inline(c)}</th>")
                out.append("</tr></thead><tbody>")
                for row in table_rows[1:]:
                    out.append("<tr>")
                    for c in row:
                        out.append(f"<td>{inline(c)}</td>")
                    out.append("</tr>")
                out.append("</tbody></table></div>")
            table_rows = []
            in_table = False

        # Horizontal rule / section separator
        if re.match(r"^-{3,}$", line.strip()) or re.match(r"^---+$", line.strip()):
            out.append('<hr class="section-sep">')
            i += 1
            continue

        # Headings
        m = re.match(r"^(#{1,4})\s+(.+)", line)
        if m:
            level = len(m.group(1))
            text = inline(m.group(2))
            # Map ## to card sections
            if level == 2:
                out.append(f'<div class="card"><h2 class="card-title">{text}</h2>')
            elif level == 3:
                out.append(f'<h3 class="sub-title">{text}</h3>')
            elif level == 1:
                out.append(f'<h1 class="report-title">{text}</h1>')
            else:
                out.append(f'<h{level}>{text}</h{level}>')
            i += 1
            continue

        # Numbered list
        m = re.match(r"^(\d+)\.\s+(.+)", line)
        if m:
            if not in_olist:
                out.append("<ol>")
                in_olist = True
            in_list = False
            out.append(f"<li>{inline(m.group(2))}</li>")
            i += 1
            continue
        elif in_olist:
            out.append("</ol>")
            in_olist = False

        # Bullet list
        m = re.match(r"^[-*]\s+(.+)", line)
        if m:
            if not in_list:
                out.append("<ul>")
                in_list = True
            in_olist = False
            out.append(f"<li>{inline(m.group(1))}</li>")
            i += 1
            continue
        elif in_list:
            out.append("</ul>")
            in_list = False

        # Blockquote
        if line.strip().startswith(">"):
            text = inline(line.strip().lstrip(">").strip())
            out.append(f'<blockquote>{text}</blockquote>')
            i += 1
            continue

        # Empty line
        if not line.strip():
            i += 1
            continue

        # Normal paragraph
        out.append(f"<p>{inline(line)}</p>")
        i += 1

    # Flush remaining
    if in_list:
        out.append("</ul>")
    if in_olist:
        out.append("</ol>")
    if in_code:
        out.append("</code></pre>")
    if table_rows:
        out.append('<div class="table-wrap"><table>')
        out.append("<thead><tr>")
        for c in table_rows[0]:
            out.append(f"<th>{inline(c)}</th>")
        out.append("</tr></thead><tbody>")
        for row in table_rows[1:]:
            out.append("<tr>")
            for c in row:
                out.append(f"<td>{inline(c)}</td>")
            out.append("</tr>")
        out.append("</tbody></table></div>")

    return "\n".join(out)


def render_html(result: dict) -> str:
    """Render analysis result as a styled HTML page."""
    date = datetime.now().strftime("%Y-%m-%d %H:%M")
    url = html.escape(result.get("url", ""))
    url_type = result.get("type", "unknown")
    title = html.escape(result.get("title", url)[:80])
    report_md = result.get("report", "")
    report_html = _md_to_html(report_md)

    type_colors = {
        "website": "#3b82f6",
        "article": "#f59e0b",
        "product": "#8b5cf6",
        "github": "#10b981",
    }
    type_color = type_colors.get(url_type, "#6b7280")
    type_emoji = {"website": "🌐", "article": "📰", "product": "🚀", "github": "📦"}.get(url_type, "🔗")

    return f"""<!DOCTYPE html>
<html lang="{('en' if 'English' in report_md[:200] else 'zh')}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>URL X-Ray Report — {title}</title>
<style>
  :root {{
    --bg: #0f172a;
    --card-bg: #1e293b;
    --card-border: #334155;
    --text: #e2e8f0;
    --text-dim: #94a3b8;
    --accent: #3b82f6;
    --green: #10b981;
    --red: #ef4444;
    --yellow: #f59e0b;
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans SC", sans-serif;
    line-height: 1.7;
    padding: 24px 16px;
    max-width: 900px;
    margin: 0 auto;
  }}

  /* Header */
  .report-header {{
    background: linear-gradient(135deg, {type_color}15, transparent);
    border: 1px solid {type_color}40;
    border-radius: 16px;
    padding: 24px 28px;
    margin-bottom: 24px;
  }}
  .header-top {{
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 12px;
    flex-wrap: wrap;
  }}
  .type-badge {{
    background: {type_color}25;
    color: {type_color};
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 13px;
    font-weight: 600;
    border: 1px solid {type_color}50;
  }}
  .header-meta {{
    font-size: 13px;
    color: var(--text-dim);
  }}
  .header-title {{
    font-size: 20px;
    font-weight: 700;
    margin: 8px 0 4px;
    line-height: 1.4;
  }}
  .header-url {{
    font-size: 13px;
    color: var(--accent);
    word-break: break-all;
  }}
  .header-url a {{
    color: var(--accent);
    text-decoration: none;
  }}

  /* Copy button */
  .copy-btn {{
    background: var(--card-border);
    color: var(--text);
    border: none;
    padding: 8px 16px;
    border-radius: 8px;
    cursor: pointer;
    font-size: 13px;
    font-weight: 500;
    transition: all 0.2s;
    margin-left: auto;
  }}
  .copy-btn:hover {{
    background: var(--accent);
    color: white;
  }}
  .copy-btn.copied {{
    background: var(--green);
    color: white;
  }}

  /* Cards */
  .card {{
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: 12px;
    padding: 24px 28px;
    margin-bottom: 16px;
  }}
  .card-title {{
    font-size: 16px;
    font-weight: 700;
    margin-bottom: 16px;
    padding-bottom: 10px;
    border-bottom: 1px solid var(--card-border);
    color: var(--text);
  }}
  .sub-title {{
    font-size: 14px;
    font-weight: 600;
    margin: 16px 0 8px;
    color: var(--text-dim);
  }}

  /* Content */
  p {{ margin: 8px 0; color: var(--text); font-size: 14px; }}
  strong {{ color: #f8fafc; font-weight: 600; }}
  em {{ color: var(--text-dim); font-style: italic; }}
  a {{ color: var(--accent); text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}

  /* Lists */
  ul, ol {{ margin: 8px 0 8px 20px; }}
  li {{ margin: 4px 0; font-size: 14px; }}
  .checkbox {{ margin-right: 6px; color: var(--text-dim); }}
  .checkbox.checked {{ color: var(--green); }}

  /* Tables */
  .table-wrap {{ overflow-x: auto; margin: 12px 0; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th {{
    background: var(--card-border);
    padding: 8px 12px;
    text-align: left;
    font-weight: 600;
    border-radius: 6px 6px 0 0;
  }}
  td {{
    padding: 8px 12px;
    border-bottom: 1px solid var(--card-border);
  }}
  tr:last-child td {{ border-bottom: none; }}

  /* Code */
  .code-block {{
    background: #0d1117;
    border: 1px solid var(--card-border);
    border-radius: 8px;
    padding: 14px 16px;
    overflow-x: auto;
    margin: 12px 0;
    font-size: 13px;
    line-height: 1.5;
  }}
  .inline-code {{
    background: var(--card-border);
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 13px;
    font-family: "SF Mono", "Fira Code", monospace;
  }}

  /* Blockquote */
  blockquote {{
    border-left: 3px solid {type_color};
    padding: 8px 16px;
    margin: 12px 0;
    background: {type_color}10;
    border-radius: 0 8px 8px 0;
    color: var(--text-dim);
  }}

  /* Separator */
  .section-sep {{
    border: none;
    border-top: 1px solid var(--card-border);
    margin: 20px 0;
  }}

  /* Report title */
  .report-title {{
    font-size: 22px;
    font-weight: 800;
    margin-bottom: 16px;
    color: #f8fafc;
  }}

  /* Footer */
  .footer {{
    text-align: center;
    padding: 20px;
    color: var(--text-dim);
    font-size: 12px;
  }}
  .footer a {{ color: var(--accent); }}

  @media (max-width: 600px) {{
    body {{ padding: 12px 8px; }}
    .card, .report-header {{ padding: 16px; border-radius: 10px; }}
  }}
</style>
</head>
<body>

<div class="report-header">
  <div class="header-top">
    <span class="type-badge">{type_emoji} {url_type}</span>
    <span class="header-meta">{date}</span>
    <button class="copy-btn" onclick="copyReport()">Copy Report</button>
  </div>
  <div class="header-title">{title}</div>
  <div class="header-url"><a href="{url}" target="_blank">{url}</a></div>
</div>

<div class="report-body" id="report-body">
{report_html}
</div>

<div class="footer">
  Generated by <a href="https://github.com/archorfight/url-xray" target="_blank">url-xray</a> · X-ray any URL
</div>

<script>
function copyReport() {{
  const text = document.getElementById('report-body').innerText;
  navigator.clipboard.writeText(text).then(() => {{
    const btn = document.querySelector('.copy-btn');
    btn.classList.add('copied');
    btn.textContent = '✓ Copied!';
    setTimeout(() => {{
      btn.classList.remove('copied');
      btn.textContent = 'Copy Report';
    }}, 2000);
  }});
}}
</script>

</body>
</html>"""
