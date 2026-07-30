"""CLI interface for url-xray."""

import sys
import os

import httpx
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from .analyzer import teardown, save_report
from .fetcher import detect_type

console = Console()

BANNER = r"""
 _   _ ___ _   _ ___
| | | / __| | | / __|
| |_| \__ \ |_| \__ \
 \__,_|___/\__,_|___/

  X-ray any URL into structured analysis.
"""


def main():
    import argparse

    load_dotenv()  # Load .env if present

    parser = argparse.ArgumentParser(
        prog="url-xray",
        description="Tear down any URL — websites, articles, landing pages, GitHub repos — into structured analysis.",
        epilog="""
Examples:
  url-xray https://example.com
  url-xray https://mp.weixin.qq.com/s/xxxxx --output ./reports
  url-xray https://github.com/user/repo --model gpt-4o
  url-xray https://example.com --base-url https://api.deepseek.com/v1 --model deepseek-chat

Environment variables (or .env file):
  LLM_API_KEY    Required. Your API key.
  LLM_BASE_URL   Default: https://api.openai.com/v1
  LLM_MODEL      Default: gpt-4o
        """.strip(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("url", help="URL to analyze")
    parser.add_argument("-o", "--output", default=".", help="Output directory (default: current dir)")
    parser.add_argument(
        "--api-key",
        default=os.environ.get("LLM_API_KEY", ""),
        help="LLM API key (or set LLM_API_KEY env var)",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1"),
        help="LLM API base URL (or set LLM_BASE_URL env var)",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("LLM_MODEL", "gpt-4o"),
        help="LLM model name (or set LLM_MODEL env var)",
    )
    parser.add_argument("--lang", choices=["zh", "en"], default="zh", help="Report language: zh (default) or en")
    parser.add_argument("--format", choices=["md", "html"], default="html", help="Output format: html (default, styled) or md (plain markdown)")
    parser.add_argument("--stdout", action="store_true", help="Print report to stdout instead of saving file")
    parser.add_argument("-q", "--quiet", action="store_true", help="Minimal output")

    args = parser.parse_args()

    if not args.api_key:
        console.print("[red]Error: No API key provided.[/red]")
        console.print("Set LLM_API_KEY environment variable, create a .env file, or use --api-key.")
        console.print("\nExample .env:")
        console.print("  LLM_API_KEY=sk-xxxx")
        console.print("  LLM_BASE_URL=https://api.openai.com/v1")
        console.print("  LLM_MODEL=gpt-4o")
        sys.exit(1)

    # Validate URL
    if not args.url.startswith(("http://", "https://")):
        args.url = "https://" + args.url

    if not args.quiet:
        console.print(BANNER, style="cyan")

    url_type = detect_type(args.url)
    type_emoji = {
        "website": "🌐",
        "article": "📰",
        "product": "🚀",
        "github": "📦",
    }.get(url_type, "🔗")

    if not args.quiet:
        console.print(f"\n{type_emoji} Detected type: [bold]{url_type}[/bold]")
        console.print(f"🔗 URL: {args.url}\n")

    # Run analysis
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Fetching page data...", total=None)

        progress.update(task, description="Fetching page data...")
        progress.advance(task)

        progress.update(task, description="Probing tech stack...")
        result = teardown(
            url=args.url,
            api_key=args.api_key,
            base_url=args.base_url,
            model=args.model,
            lang=args.lang,
        )

        progress.update(task, description="Generating report...")

    # Handle errors
    if result.get("error") and not result.get("report"):
        console.print(f"\n[red]❌ Error: {result['error']}[/red]")
        sys.exit(1)

    if result.get("error"):
        console.print(f"\n[yellow]⚠️ Warning: {result['error']}[/yellow]")

    # Output
    if args.stdout:
        console.print()
        console.print(result["report"], style="white")
    else:
        filepath = save_report(result, args.output, fmt=args.format)
        if not args.quiet:
            console.print(f"\n[green]✅ Report saved:[/green] {filepath}")
            console.print(f"\n[dim]Report preview (first 30 lines):[/dim]\n")
            lines = result["report"].split("\n")[:30]
            console.print(Panel("\n".join(lines), border_style="dim"))
        else:
            print(filepath)


if __name__ == "__main__":
    main()
