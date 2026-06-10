#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KodiWulf Dark Index Generator

Erzeugt echte statische GitHub-Pages-Indexdateien:
- Root index.html mit bg.png als Hintergrund
- Root index.md mit echten Links
- index.html in jedem Add-on-Ordner
- keine Fake-ZIP-Links: ZIPs werden nur verlinkt, wenn sie wirklich existieren
"""

from __future__ import annotations

import html
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_BASE_URL = "https://n-e-o-w-u-l-f.github.io/kodiwulf-repo"

EXCLUDED_DIRS = {
    ".git", ".github", "tools", ".build", "build", "dist", "__pycache__",
    "zips", "_incoming", "incoming-zips"
}

TOP_ROOT_FILES = [
    "addons.xml",
    "addons.xml.md5",
    "index.html",
    "index.md",
    ".nojekyll",
    "README.md",
    "CHANGES.md",
    "UPDATE_PROCESS.md",
    "bg.png",
]


def human_size(size: int) -> str:
    units = ["B", "KB", "MB", "GB"]
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.2f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{size} B"


def mtime(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")


def addon_meta(addon_dir: Path) -> tuple[str, str, str]:
    addon_xml = addon_dir / "addon.xml"
    if not addon_xml.is_file():
        return addon_dir.name, "", ""
    try:
        root = ET.fromstring(addon_xml.read_text(encoding="utf-8"))
        return (
            root.attrib.get("id", addon_dir.name),
            root.attrib.get("version", ""),
            root.attrib.get("name", ""),
        )
    except Exception:
        return addon_dir.name, "", ""


def addon_dirs() -> list[Path]:
    found: list[Path] = []
    for child in sorted(ROOT.iterdir()):
        if not child.is_dir() or child.name in EXCLUDED_DIRS:
            continue
        if child.name.startswith(("plugin.", "repository.", "script.", "service.")) or (child / "addon.xml").is_file():
            found.append(child)
    return found


def file_row(path: Path, href: str | None = None, icon: str = "📄") -> str:
    href = href or path.name
    size = "-" if path.is_dir() else human_size(path.stat().st_size)
    modified = mtime(path)
    name = path.name + ("/" if path.is_dir() else "")
    return (
        "<tr>"
        f"<td class=\"ico\">{icon}</td>"
        f"<td><a href=\"{html.escape(href)}\">{html.escape(name)}</a></td>"
        f"<td>{html.escape(modified)}</td>"
        f"<td>{html.escape(size)}</td>"
        "</tr>"
    )


def all_root_entries() -> list[tuple[str, Path, str]]:
    entries: list[tuple[str, Path, str]] = []

    for dirname in addon_dirs():
        entries.append((dirname.name + "/", dirname, "📁"))

    for name in TOP_ROOT_FILES:
        path = ROOT / name
        if path.exists() and path.is_file():
            entries.append((name, path, "📄"))

    for path in sorted(ROOT.iterdir()):
        if path.name in EXCLUDED_DIRS or path.name.startswith(".backup-"):
            continue
        if path.is_file() and path.name not in TOP_ROOT_FILES:
            entries.append((path.name, path, "📦" if path.suffix.lower() == ".zip" else "📄"))

    return entries


def write_addon_index(addon_dir: Path) -> None:
    addon_id, version, addon_name = addon_meta(addon_dir)
    rows: list[str] = []

    parent_row = (
        "<tr><td class=\"ico\">↩</td><td><a href=\"../\">Parent Directory</a></td>"
        "<td>-</td><td>-</td></tr>"
    )
    rows.append(parent_row)

    for path in sorted(addon_dir.iterdir()):
        if path.name.startswith("."):
            continue
        if path.is_file():
            icon = "📦" if path.suffix.lower() == ".zip" else "📄"
            rows.append(file_row(path, path.name, icon))

    if len(rows) == 1:
        rows.append("<tr><td class=\"ico\">⚠</td><td>No files found</td><td>-</td><td>-</td></tr>")

    content = html_shell(
        title=f"Index of /{addon_dir.name}/",
        body=f"""
<header class="hero compact">
  <div>
    <p class="eyebrow">KodiWulf Repository</p>
    <h1>Index of /{html.escape(addon_dir.name)}/</h1>
    <p class="subtitle">{html.escape(addon_name or addon_id)} {html.escape(version)}</p>
  </div>
</header>

<section class="panel">
  <table class="index-table">
    <thead>
      <tr><th></th><th>Name</th><th>Last modified</th><th>Size</th></tr>
    </thead>
    <tbody>
      {''.join(rows)}
    </tbody>
  </table>
</section>
""",
    )
    (addon_dir / "index.html").write_text(content, encoding="utf-8", newline="\n")


def html_shell(title: str, body: str) -> str:
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    return f"""<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    :root {{
      --bg: #050508;
      --panel: rgba(10, 10, 16, 0.84);
      --panel-strong: rgba(14, 14, 22, 0.94);
      --line: rgba(255, 255, 255, 0.13);
      --text: #f1f1f7;
      --muted: #a7a7b5;
      --accent: #ff3030;
      --accent-2: #8be9fd;
      --good: #8cffbf;
      --warn: #ffbf69;
      --shadow: rgba(0, 0, 0, 0.68);
    }}

    * {{ box-sizing: border-box; }}

    html {{
      min-height: 100%;
      background: var(--bg);
    }}

    body {{
      min-height: 100vh;
      margin: 0;
      color: var(--text);
      font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.55;
      background:
        linear-gradient(90deg, rgba(5,5,8,0.96), rgba(5,5,8,0.72), rgba(5,5,8,0.96)),
        linear-gradient(180deg, rgba(0,0,0,0.82), rgba(0,0,0,0.92)),
        url("bg.png");
      background-size: cover;
      background-position: center center;
      background-attachment: fixed;
    }}

    a {{
      color: var(--accent-2);
      text-decoration: none;
      font-weight: 650;
    }}

    a:hover {{
      color: #ffffff;
      text-decoration: underline;
    }}

    main {{
      width: min(1180px, calc(100% - 32px));
      margin: 0 auto;
      padding: 34px 0 56px;
    }}

    .hero {{
      border: 1px solid var(--line);
      border-radius: 26px;
      padding: clamp(26px, 5vw, 54px);
      background:
        radial-gradient(circle at top left, rgba(255,48,48,0.24), transparent 34%),
        radial-gradient(circle at bottom right, rgba(139,233,253,0.13), transparent 34%),
        var(--panel);
      box-shadow: 0 28px 80px var(--shadow);
      backdrop-filter: blur(10px);
      margin-bottom: 22px;
    }}

    .hero.compact {{
      padding: 28px;
    }}

    .eyebrow {{
      margin: 0 0 10px;
      color: var(--accent);
      text-transform: uppercase;
      letter-spacing: 0.16em;
      font-size: 0.78rem;
      font-weight: 800;
    }}

    h1 {{
      margin: 0;
      font-size: clamp(2rem, 7vw, 4.6rem);
      line-height: 0.96;
      letter-spacing: -0.06em;
    }}

    .x {{
      color: var(--accent);
      text-shadow: 0 0 22px rgba(255,48,48,0.65);
    }}

    .subtitle {{
      max-width: 780px;
      margin: 18px 0 0;
      color: var(--muted);
      font-size: 1.04rem;
    }}

    .grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 14px;
      margin: 18px 0;
    }}

    .card, .panel {{
      border: 1px solid var(--line);
      border-radius: 18px;
      background: var(--panel-strong);
      box-shadow: 0 18px 50px var(--shadow);
      backdrop-filter: blur(10px);
    }}

    .card {{
      padding: 18px;
    }}

    .card h2 {{
      margin: 0 0 10px;
      font-size: 1.05rem;
    }}

    .card p {{
      margin: 0;
      color: var(--muted);
    }}

    .panel {{
      overflow: hidden;
      margin-top: 18px;
    }}

    .panel-head {{
      padding: 18px 20px;
      border-bottom: 1px solid var(--line);
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: center;
    }}

    .panel-head h2 {{
      margin: 0;
      font-size: 1.15rem;
    }}

    .pill {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 6px 11px;
      color: var(--muted);
      background: rgba(255,255,255,0.04);
      font-size: 0.82rem;
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
    }}

    th, td {{
      padding: 12px 16px;
      border-bottom: 1px solid rgba(255,255,255,0.09);
      text-align: left;
      vertical-align: middle;
    }}

    th {{
      color: #ffffff;
      font-size: 0.78rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      background: rgba(255,255,255,0.04);
    }}

    td {{
      color: var(--muted);
    }}

    tr:hover td {{
      background: rgba(255,255,255,0.035);
      color: var(--text);
    }}

    .ico {{
      width: 42px;
      text-align: center;
    }}

    .status-ok {{ color: var(--good); }}
    .status-warn {{ color: var(--warn); }}

    .urls {{
      padding: 16px 20px 20px;
      color: var(--muted);
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace;
      white-space: pre-wrap;
      word-break: break-all;
    }}

    footer {{
      margin-top: 22px;
      color: var(--muted);
      font-size: 0.88rem;
      text-align: center;
    }}

    @media (max-width: 820px) {{
      .grid {{ grid-template-columns: 1fr; }}
      th:nth-child(3), td:nth-child(3) {{ display: none; }}
      main {{ width: min(100% - 20px, 1180px); padding-top: 14px; }}
    }}
  </style>
</head>
<body>
<main>
{body}
<footer>Generated by KodiWulf Dark Index Generator · {html.escape(generated)}</footer>
</main>
</body>
</html>
"""


def write_root_index() -> None:
    entries = all_root_entries()
    rows = []

    for display, path, icon in entries:
        href = display
        rows.append(file_row(path, href, icon))

    installed_addons = addon_dirs()
    addon_rows = []
    for addon_dir in installed_addons:
        addon_id, version, addon_name = addon_meta(addon_dir)
        zip_files = sorted(addon_dir.glob("*.zip"))
        zip_html = " ".join(
            f"<a href=\"{html.escape(addon_dir.name + '/' + z.name)}\">{html.escape(z.name)}</a>"
            for z in zip_files
        )
        if not zip_html:
            zip_html = "<span class=\"status-warn\">keine ZIP-Datei im Ordner</span>"
        addon_rows.append(
            "<tr>"
            "<td class=\"ico\">📁</td>"
            f"<td><a href=\"{html.escape(addon_dir.name + '/')}\">{html.escape(addon_id)}</a><br><small>{html.escape(addon_name)}</small></td>"
            f"<td>{html.escape(version)}</td>"
            f"<td>{zip_html}</td>"
            "</tr>"
        )

    if not addon_rows:
        addon_rows.append("<tr><td class=\"ico\">⚠</td><td>No add-on folders found</td><td>-</td><td>-</td></tr>")

    body = f"""
<header class="hero">
  <p class="eyebrow">GitHub Pages Kodi Repository</p>
  <h1><span class="x">x</span>Wulf Repository</h1>
  <p class="subtitle">
    Dunkler statischer Repository-Index nach Directory-Listing-Vorbild.
    Alle Links zeigen auf echte Dateien oder echte Ordner in diesem GitHub-Pages-Repository.
  </p>
</header>

<section class="grid">
  <article class="card">
    <h2>Repository XML</h2>
    <p><a href="addons.xml">addons.xml</a></p>
  </article>
  <article class="card">
    <h2>Checksum</h2>
    <p><a href="addons.xml.md5">addons.xml.md5</a></p>
  </article>
  <article class="card">
    <h2>Kodi Repository Add-on</h2>
    <p><a href="repository.kodiwulf/">repository.kodiwulf/</a></p>
  </article>
</section>

<section class="panel">
  <div class="panel-head">
    <h2>Index of /kodiwulf-repo/</h2>
    <span class="pill">bg.png background active</span>
  </div>
  <table class="index-table">
    <thead>
      <tr><th></th><th>Name</th><th>Last modified</th><th>Size</th></tr>
    </thead>
    <tbody>
      {''.join(rows)}
    </tbody>
  </table>
</section>

<section class="panel">
  <div class="panel-head">
    <h2>Kodi Add-ons</h2>
    <span class="pill">real local scan</span>
  </div>
  <table class="index-table">
    <thead>
      <tr><th></th><th>Add-on</th><th>Version</th><th>ZIP</th></tr>
    </thead>
    <tbody>
      {''.join(addon_rows)}
    </tbody>
  </table>
</section>

<section class="panel">
  <div class="panel-head">
    <h2>Kodi URLs</h2>
    <span class="pill">copy into Kodi repository addon</span>
  </div>
  <div class="urls">{html.escape(PUBLIC_BASE_URL)}/addons.xml
{html.escape(PUBLIC_BASE_URL)}/addons.xml.md5
{html.escape(PUBLIC_BASE_URL)}/repository.kodiwulf/</div>
</section>
"""
    (ROOT / "index.html").write_text(html_shell("KodiWulf Repository", body), encoding="utf-8", newline="\n")


def write_index_md() -> None:
    lines = [
        "# KodiWulf Repository",
        "",
        "GitHub Pages:",
        "",
        f"- {PUBLIC_BASE_URL}/",
        f"- {PUBLIC_BASE_URL}/addons.xml",
        f"- {PUBLIC_BASE_URL}/addons.xml.md5",
        "",
        "## Root index",
        "",
    ]

    for display, path, icon in all_root_entries():
        lines.append(f"- {icon} [{display}]({display})")

    lines.extend(["", "## Add-on folders", ""])

    for addon_dir in addon_dirs():
        addon_id, version, addon_name = addon_meta(addon_dir)
        lines.append(f"- [{addon_id}]({addon_dir.name}/) — {addon_name} {version}".strip())

    lines.append("")
    (ROOT / "index.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")


def main() -> None:
    for addon_dir in addon_dirs():
        write_addon_index(addon_dir)
    write_root_index()
    write_index_md()
    (ROOT / ".nojekyll").touch()
    print("[OK] index.html, index.md, add-on directory indexes and .nojekyll generated.")
    print(f"[OK] Background uses: {ROOT / 'bg.png'}")


if __name__ == "__main__":
    main()
