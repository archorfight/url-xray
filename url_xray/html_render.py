"""HTML report renderer — document-flow layout, Linear-inspired dark theme.

Design philosophy: whitespace and typography create structure, not nested containers.
No per-section cards. Content flows like a well-typeset document.
"""

import html
import re
from datetime import datetime


def _md_to_html(md: str) -> str:
    """Convert markdown to HTML. No nested containers — flat document flow."""
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
        # Links first (capture before escape)
        link_ph = []
        def _cap_link(m):
            link_ph.append(f'<a href="{esc(m.group(2))}" target="_blank" rel="noopener">{esc(m.group(1))}</a>')
            return f"\x00L{len(link_ph)-1}\x00"
        text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", _cap_link, text)
        text = esc(text)
        text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
        text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", text)
        text = re.sub(r"`([^`]+)`", r'<code>\1</code>', text)
        # Restore links
        text = re.sub(r"\x00L(\d+)\x00", lambda m: link_ph[int(m.group(1))], text)
        # Checkboxes
        text = text.replace("\u2610", '<span class="cb">\u2610</span>')
        text = text.replace("\u2611", '<span class="cb done">\u2611</span>')
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
                out.append('<pre><code>')
                in_code = True
            i += 1
            continue
        if in_code:
            out.append(esc(line))
            i += 1
            continue

        # Table
        if "|" in line and line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if all(re.match(r"^[-:]+$", c) for c in cells):
                i += 1
                continue
            table_rows.append(cells)
            in_table = True
            i += 1
            continue
        elif in_table:
            if table_rows:
                out.append('<table><tbody>')
                for idx, row in enumerate(table_rows):
                    tag = "th" if idx == 0 else "td"
                    out.append("<tr>" + "".join(f"<{tag}>{inline(c)}</{tag}>" for c in row) + "</tr>")
                out.append('</tbody></table>')
            table_rows = []
            in_table = False

        # HR
        if re.match(r"^-{3,}$", line.strip()):
            out.append('<hr>')
            i += 1
            continue

        # Headings
        m = re.match(r"^(#{1,4})\s+(.+)", line)
        if m:
            level = len(m.group(1))
            text = inline(m.group(2))
            if level == 1:
                out.append(f'<h1>{text}</h1>')
            elif level == 2:
                out.append(f'<h2>{text}</h2>')
            elif level == 3:
                out.append(f'<h3>{text}</h3>')
            else:
                out.append(f'<h4>{text}</h4>')
            i += 1
            continue

        # Ordered list
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
            content = m.group(1)
            content = re.sub(r"^\[ \]\s*", "\u2610 ", content)
            content = re.sub(r"^\[x\]\s*", "\u2611 ", content, flags=re.IGNORECASE)
            out.append(f"<li>{inline(content)}</li>")
            i += 1
            continue
        elif in_list:
            out.append("</ul>")
            in_list = False

        # Blockquote
        if line.strip().startswith(">"):
            out.append(f'<blockquote>{inline(line.strip().lstrip(">").strip())}</blockquote>')
            i += 1
            continue

        if not line.strip():
            i += 1
            continue

        out.append(f"<p>{inline(line)}</p>")
        i += 1

    # Flush
    if in_list:
        out.append("</ul>")
    if in_olist:
        out.append("</ol>")
    if in_code:
        out.append("</code></pre>")
    if table_rows:
        out.append('<table><tbody>')
        for idx, row in enumerate(table_rows):
            tag = "th" if idx == 0 else "td"
            out.append("<tr>" + "".join(f"<{tag}>{inline(c)}</{tag}>" for c in row) + "</tr>")
        out.append('</tbody></table>')

    return "\n".join(out)


# Type → accent + emoji
_TYPE_STYLES = {
    "website": {"hue": "#5e6ad2", "emoji": "\U0001f310", "label": "Website"},
    "article": {"hue": "#e2b341", "emoji": "\U0001f4f0", "label": "Article"},
    "product": {"hue": "#8b5cf6", "emoji": "\U0001f680", "label": "Product"},
    "github":  {"hue": "#27a644", "emoji": "\U0001f4e6", "label": "GitHub"},
}
_DEFAULT_STYLE = {"hue": "#62666d", "emoji": "\U0001f517", "label": "URL"}


def render_html(result: dict) -> str:
    """Render analysis result as a clean, document-style HTML page."""
    date = datetime.now().strftime("%Y-%m-%d %H:%M")
    url = html.escape(result.get("url", ""))
    url_type = result.get("type", "unknown")
    title = html.escape(result.get("title", url)[:100])
    report_md = result.get("report", "")
    report_html = _md_to_html(report_md)

    ts = _TYPE_STYLES.get(url_type, _DEFAULT_STYLE)
    hue = ts["hue"]
    is_zh = any(ord(c) > 0x4e00 for c in report_md[:300])
    lang = "zh" if is_zh else "en"

    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg:          #08090a;
    --text:        #f7f8f8;
    --text-2:      #d0d6e0;
    --text-3:      #8a8f98;
    --text-4:      #62666d;
    --border:      rgba(255,255,255,0.06);
    --border-2:    rgba(255,255,255,0.10);
    --accent:      {hue};
    --green:       #27a644;
    --surface:     rgba(255,255,255,0.02);
    --mono:        'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace;
    --sans:        'Inter', system-ui, -apple-system, 'Segoe UI', Roboto, 'Noto Sans SC', sans-serif;
  }}

  *, *::before, *::after {{ margin: 0; padding: 0; box-sizing: border-box; }}
  ::selection {{ background: var(--accent); color: #fff; }}

  body {{
    background: var(--bg);
    color: var(--text-2);
    font-family: var(--sans);
    font-size: 15px;
    font-weight: 400;
    font-feature-settings: 'cv01', 'ss03';
    line-height: 1.7;
    letter-spacing: -0.011em;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }}

  /* ── Container ──────────────────────────────────────────────── */
  .wrap {{
    max-width: 720px;
    margin: 0 auto;
    padding: 48px 32px 80px;
  }}

  /* ── Header ─────────────────────────────────────────────────── */
  .header {{
    margin-bottom: 48px;
  }}
  .header-meta {{
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 20px;
  }}
  .badge {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 3px 10px;
    border-radius: 999px;
    background: {hue}18;
    color: {hue};
    font-size: 12px;
    font-weight: 500;
    letter-spacing: -0.01em;
  }}
  .date {{
    font-family: var(--mono);
    font-size: 12px;
    color: var(--text-4);
  }}
  .copy-btn {{
    margin-left: auto;
    background: transparent;
    color: var(--text-3);
    border: none;
    padding: 4px 8px;
    cursor: pointer;
    font-family: var(--sans);
    font-size: 12px;
    font-weight: 500;
    transition: color 0.15s;
  }}
  .copy-btn:hover {{ color: var(--text); }}
  .copy-btn.copied {{ color: var(--green); }}

  .title {{
    font-size: 28px;
    font-weight: 600;
    line-height: 1.3;
    letter-spacing: -0.03em;
    color: var(--text);
    margin-bottom: 6px;
  }}
  .url {{
    font-family: var(--mono);
    font-size: 13px;
    color: var(--text-3);
  }}
  .url a {{
    color: var(--text-3);
    text-decoration: none;
  }}
  .url a:hover {{ color: var(--accent); }}

  /* ── Document body (THE core change: no card wrappers) ──────── */
  .doc {{
    /* Flat flow — sections separated by margin, not containers */
  }}

  /* Headings — typography creates the hierarchy */
  h1 {{
    font-size: 20px;
    font-weight: 600;
    color: var(--text);
    margin: 0 0 12px;
    letter-spacing: -0.022em;
  }}
  h2 {{
    font-size: 16px;
    font-weight: 600;
    color: var(--text);
    margin: 40px 0 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border);
    letter-spacing: -0.018em;
    position: relative;
  }}
  h2::before {{
    content: '';
    position: absolute;
    left: -14px;
    top: 4px;
    width: 3px;
    height: 14px;
    background: var(--accent);
    border-radius: 2px;
  }}
  h3 {{
    font-size: 14px;
    font-weight: 500;
    color: var(--text-3);
    margin: 24px 0 8px;
    letter-spacing: -0.01em;
  }}
  h4 {{
    font-size: 13px;
    font-weight: 500;
    color: var(--text-3);
    margin: 20px 0 6px;
  }}

  /* Paragraphs */
  p {{
    margin: 10px 0;
    font-size: 14px;
    line-height: 1.7;
    color: var(--text-2);
  }}
  strong {{ color: var(--text); font-weight: 600; }}
  em {{ color: var(--text-3); }}
  a {{
    color: var(--accent);
    text-decoration: none;
    border-bottom: 1px solid transparent;
    transition: border-color 0.15s;
  }}
  a:hover {{ border-bottom-color: var(--accent); }}

  /* Lists — flat, generous spacing */
  ul, ol {{
    padding-left: 20px;
    margin: 10px 0;
  }}
  li {{
    font-size: 14px;
    line-height: 1.7;
    margin: 6px 0;
    color: var(--text-2);
  }}
  li::marker {{ color: var(--text-4); }}
  .cb {{ margin-right: 6px; color: var(--text-4); }}
  .cb.done {{ color: var(--green); }}

  /* Table — no box, no outer border. Just row separators. */
  table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
    margin: 16px 0;
  }}
  th {{
    text-align: left;
    padding: 8px 0;
    font-weight: 500;
    font-size: 12px;
    color: var(--text-3);
    border-bottom: 1px solid var(--border-2);
  }}
  td {{
    padding: 8px 0;
    border-bottom: 1px solid var(--border);
    color: var(--text-2);
  }}
  tr:last-child td, tr:last-child th {{
    border-bottom: none;
  }}
  th:not(:last-child), td:not(:last-child) {{
    padding-right: 24px;
  }}

  /* Code — subtle bg, no heavy border */
  pre {{
    background: rgba(0,0,0,0.3);
    border-radius: 8px;
    padding: 14px 16px;
    overflow-x: auto;
    margin: 12px 0;
    font-family: var(--mono);
    font-size: 13px;
    line-height: 1.55;
    color: var(--text-2);
  }}
  code {{ /* inline */ }}
  p code, li code, td code {{
    font-family: var(--mono);
    font-size: 0.88em;
    background: rgba(255,255,255,0.06);
    padding: 2px 5px;
    border-radius: 3px;
    color: var(--text);
  }}

  /* Blockquote — just a left line, no bg */
  blockquote {{
    border-left: 2px solid var(--accent);
    padding-left: 16px;
    margin: 16px 0;
    color: var(--text-3);
    font-size: 14px;
  }}

  /* HR */
  hr {{
    border: none;
    border-top: 1px solid var(--border);
    margin: 32px 0;
  }}

  /* Footer */
  .footer {{
    margin-top: 64px;
    padding-top: 20px;
    border-top: 1px solid var(--border);
    font-size: 12px;
    color: var(--text-4);
    text-align: center;
  }}
  .footer a {{ color: var(--text-3); }}

  /* Responsive */
  @media (max-width: 640px) {{
    .wrap {{ padding: 32px 20px 60px; }}
    .title {{ font-size: 22px; }}
    h2::before {{ left: -10px; }}
  }}
</style>
</head>
<body>

<div class="wrap">

  <div class="header">
    <div class="header-meta">
      <span class="badge">{ts["emoji"]} {ts["label"]}</span>
      <span class="date">{date}</span>
      <button class="copy-btn" onclick="copyReport()">Copy</button>
    </div>
    <div class="title">{title}</div>
    <div class="url"><a href="{url}" target="_blank" rel="noopener">{url}</a></div>
  </div>

  <div class="doc" id="report-body">
{report_html}
  </div>

  <div class="footer">
    Generated by <a href="https://github.com/archorfight/url-xray" target="_blank" rel="noopener">url-xray</a>
  </div>

</div>

<script>
function copyReport() {{
  navigator.clipboard.writeText(document.getElementById('report-body').innerText).then(() => {{
    const b = document.querySelector('.copy-btn');
    b.textContent = '\u2713 Copied';
    b.classList.add('copied');
    setTimeout(() => {{ b.textContent = 'Copy'; b.classList.remove('copied'); }}, 2000);
  }});
}}
</script>

</body>
</html>"""
