#!/usr/bin/env python3
"""Rebuild archive index and inject 今日/往期 + prev/next nav into dated briefings."""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WEEKDAYS = "星期一 星期二 星期三 星期四 星期五 星期六 星期日".split()

NAV_CSS = """
    .site-nav {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      gap: 1rem;
      margin: 0 0 1.15rem;
      font-size: 0.82rem;
    }
    .site-nav a {
      color: var(--muted);
      text-decoration: none;
    }
    .site-nav a:hover { color: var(--accent); }
    .site-nav .here { color: var(--ink); font-weight: 650; }
    .site-nav .links { display: flex; gap: 1.1rem; }
    .day-nav {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 0.8rem;
      margin: 2.1rem 0 0;
      padding-top: 1.05rem;
      border-top: 1px solid var(--line);
      font-size: 0.88rem;
    }
    .day-nav a { text-decoration: none; }
    .day-nav .gone { color: var(--faint); }
    .archive-list {
      list-style: none;
      padding: 0;
      margin: 1.4rem 0 0;
    }
    .archive-list li {
      margin: 0 0 0.7rem;
    }
    .archive-list a.row {
      display: block;
      padding: 0.95rem 1.05rem 0.9rem;
      background: var(--paper-2);
      border: 1px solid var(--line);
      border-radius: 10px;
      text-decoration: none;
      color: inherit;
      box-shadow: var(--shadow);
    }
    .archive-list a.row:hover { border-color: var(--line-strong); }
    .archive-list .when {
      margin: 0;
      color: var(--accent);
      font-size: 0.72rem;
      font-weight: 650;
      letter-spacing: 0.14em;
    }
    .archive-list .blurb {
      margin: 0.35rem 0 0;
      color: var(--ink);
      font-size: 0.95rem;
      line-height: 1.55;
    }
"""

SITE_NAV_RE = re.compile(r'\n    <nav class="site-nav"[\s\S]*?</nav>\n', re.M)
DAY_NAV_RE = re.compile(r'\n    <nav class="day-nav"[\s\S]*?</nav>\n', re.M)


def dates() -> list[str]:
    found = sorted({p.stem for p in ROOT.glob("20[0-9][0-9]-[0-9][0-9]-[0-9][0-9].html")})
    return found


def label(iso: str) -> str:
    d = datetime.strptime(iso, "%Y-%m-%d")
    return f"{d.month}月{d.day}日"


def weekday(iso: str) -> str:
    d = datetime.strptime(iso, "%Y-%m-%d")
    return WEEKDAYS[d.weekday()]


def long_label(iso: str) -> str:
    d = datetime.strptime(iso, "%Y-%m-%d")
    return f"{d.year}年{d.month}月{d.day}日 {weekday(iso)}"


def extract_lede(html: str) -> str:
    m = re.search(r'<p class="lede">(.*?)</p>', html, re.S)
    if not m:
        return ""
    text = re.sub(r"<[^>]+>", "", m.group(1))
    return re.sub(r"\s+", " ", text).strip()


def site_nav_html(current: str) -> str:
    today_cls = ' class="here"' if current == "today" else ""
    arch_cls = ' class="here"' if current == "archives" else ""
    return f"""    <nav class="site-nav" aria-label="站点">
      <a href="index.html"{today_cls}>今日</a>
      <div class="links">
        <a href="archives.html"{arch_cls}>往期</a>
      </div>
    </nav>
"""


def day_nav_html(iso: str, all_dates: list[str]) -> str:
    i = all_dates.index(iso)
    prev = all_dates[i - 1] if i > 0 else None
    nxt = all_dates[i + 1] if i + 1 < len(all_dates) else None
    left = (
        f'<a href="{prev}.html">← {label(prev)}</a>'
        if prev
        else '<span class="gone">← 没有更早</span>'
    )
    right = (
        f'<a href="{nxt}.html">{label(nxt)} →</a>'
        if nxt
        else '<span class="gone">已是最新</span>'
    )
    return f"""    <nav class="day-nav" aria-label="相邻日期">
      {left}
      <a href="archives.html">全部往期</a>
      {right}
    </nav>
"""


def ensure_css(html: str) -> str:
    if ".site-nav" in html:
        html = re.sub(
            r"\n    \.site-nav \{[\s\S]*?\.archive-list \.blurb \{[\s\S]*?\}\n",
            "\n",
            html,
            count=1,
        )
    html = html.replace("  </style>", NAV_CSS + "  </style>", 1)
    if "nav.toc { display: none" in html and ".site-nav, .day-nav" not in html:
        html = html.replace(
            "nav.toc { display: none !important; }",
            "nav.toc, .site-nav, .day-nav { display: none !important; }",
        )
    return html


def inject_page(path: Path, iso: str, all_dates: list[str]) -> None:
    html = path.read_text()
    html = SITE_NAV_RE.sub("\n", html)
    html = DAY_NAV_RE.sub("\n", html)
    html = ensure_css(html)
    html = html.replace(
        '  <div class="page">\n',
        '  <div class="page">\n' + site_nav_html("today" if iso == all_dates[-1] else "day"),
        1,
    )
    html = html.replace(
        "    <footer>",
        day_nav_html(iso, all_dates) + "    <footer>",
        1,
    )
    path.write_text(html)


def write_archives(all_dates: list[str]) -> None:
    items = []
    for iso in reversed(all_dates):
        lede = extract_lede((ROOT / f"{iso}.html").read_text())
        items.append(
            f"""        <li>
          <a class="row" href="{iso}.html">
            <p class="when">{long_label(iso)}</p>
            <p class="blurb">{lede}</p>
          </a>
        </li>"""
        )
    body = "\n".join(items)
    latest = all_dates[-1]
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>往期 · 世界新闻简报</title>
  <style>
    :root {{
      --paper: #f6f1e8;
      --paper-2: #fbf7f0;
      --ink: #1c1814;
      --muted: #5e574f;
      --faint: #8a8278;
      --line: #ddd3c4;
      --line-strong: #cfc3b2;
      --accent: #8b2420;
      --accent-soft: #f1e4dc;
      --shadow: 0 1px 0 rgba(28, 24, 20, 0.04), 0 8px 24px rgba(28, 24, 20, 0.04);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background:
        radial-gradient(1200px 400px at 50% -80px, rgba(139, 36, 32, 0.05), transparent 60%),
        var(--paper);
      color: var(--ink);
      font-family: system-ui, "PingFang SC", "Noto Sans SC", "Hiragino Sans GB", sans-serif;
      font-size: 16px;
      line-height: 1.7;
      -webkit-font-smoothing: antialiased;
    }}
    a {{ color: var(--accent); text-underline-offset: 0.18em; }}
    .page {{
      width: min(720px, 100%);
      margin: 0 auto;
      padding: 1.5rem 1.15rem 3.75rem;
    }}
    .masthead {{
      padding: 0.35rem 0 1.2rem;
      border-bottom: 1px solid var(--line);
    }}
    .kicker {{
      display: flex;
      align-items: center;
      gap: 0.7rem;
      margin: 0 0 0.7rem;
      color: var(--accent);
      font-size: 0.68rem;
      font-weight: 650;
      letter-spacing: 0.32em;
    }}
    .kicker::after {{
      content: "";
      flex: 1;
      height: 1px;
      background: var(--accent);
      opacity: 0.28;
    }}
    h1 {{
      margin: 0;
      font-size: clamp(1.85rem, 5.5vw, 2.55rem);
      font-weight: 700;
      letter-spacing: -0.03em;
      line-height: 1.12;
    }}
    .dateline {{
      margin: 0.7rem 0 0;
      color: var(--muted);
      font-size: 0.92rem;
    }}
    footer {{
      margin-top: 2.4rem;
      color: var(--faint);
      font-size: 0.78rem;
    }}
{NAV_CSS}
    @media (min-width: 640px) {{
      .page {{ padding: 2.1rem 1.5rem 4.25rem; }}
    }}
  </style>
</head>
<body>
  <div class="page">
{site_nav_html("archives")}    <header class="masthead">
      <p class="kicker">ARCHIVE</p>
      <h1>往期简报</h1>
      <p class="dateline">共 {len(all_dates)} 期 · 最新 {label(latest)}</p>
    </header>
    <main>
      <ul class="archive-list">
{body}
      </ul>
    </main>
    <footer>由 dihua 整理</footer>
  </div>
</body>
</html>
"""
    (ROOT / "archives.html").write_text(html)


def main() -> None:
    all_dates = dates()
    if not all_dates:
        raise SystemExit("no dated html")
    for iso in all_dates:
        inject_page(ROOT / f"{iso}.html", iso, all_dates)
    latest = all_dates[-1]
    (ROOT / "index.html").write_text((ROOT / f"{latest}.html").read_text())
    write_archives(all_dates)
    print("updated", ", ".join(all_dates), "+ index + archives")


if __name__ == "__main__":
    main()
