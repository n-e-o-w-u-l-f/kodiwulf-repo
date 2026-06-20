#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KodiWulf Dark Index Generator.

Dieses Modul erzeugt die dunkle root/index.html aus der aktuellen ZIP-Struktur:
  ZIPs/REPOSITORY/
  ZIPs/VIDEO/
  ZIPs/PROGRAMM/

Die Funktion write_dark_index(repo_root) ist absichtlich eigenständig, damit
mehrere Build-Skripte sie nach ihrem normalen Build-Schritt aufrufen können.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from urllib.parse import quote
from zipfile import BadZipFile, ZipFile
import argparse
import html
import xml.etree.ElementTree as ET


CATEGORY_ORDER = ["REPOSITORY", "VIDEO", "PROGRAMM"]

CATEGORY_LABEL = {
    "REPOSITORY": "Repository-ZIPs",
    "VIDEO": "Video-Add-ons",
    "PROGRAMM": "Programm-Add-ons",
    "SONSTIGE": "Sonstige ZIPs",
}

CATEGORY_HINT = {
    "REPOSITORY": "Externe Kodi-Repository-Pakete und Repository-Add-ons.",
    "VIDEO": "Video-Add-ons, Mediatheken und Streaming-Erweiterungen.",
    "PROGRAMM": "Programm-, Wizard- und Werkzeug-Add-ons.",
    "SONSTIGE": "ZIP-Dateien außerhalb der erwarteten ZIPs-Struktur.",
}

PUBLIC_BASE_URL = "https://n-e-o-w-u-l-f.github.io/kodiwulf-repo"


def esc(value: object) -> str:
    """Maskiert Text sicher für HTML-Ausgabe."""
    return html.escape("" if value is None else str(value), quote=True)


def href(raw: str) -> str:
    """Erzeugt einen URL-sicheren relativen Link."""
    return quote(raw, safe="/._-~")


def human_size(size: int | None) -> str:
    """Formatiert Dateigrößen lesbar."""
    if size is None:
        return "-"
    if size >= 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024 * 1024):.2f} GB"
    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):.2f} MB"
    if size >= 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size} B"


def mtime(path: Path) -> str:
    """Gibt die lokale Änderungszeit einer Datei aus."""
    try:
        return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    except OSError:
        return "-"


def read_zip_meta(zip_path: Path) -> dict[str, object]:
    """Liest Add-on-Metadaten aus addon.xml innerhalb einer ZIP-Datei."""
    meta: dict[str, object] = {
        "addon_id": zip_path.stem,
        "name": zip_path.stem,
        "version": "",
        "provider": "",
        "points": [],
        "status": "OK",
        "note": "",
    }

    try:
        with ZipFile(zip_path, "r") as zf:
            candidates = []
            for name in zf.namelist():
                clean = name.strip("/")
                if clean == "addon.xml" or clean.endswith("/addon.xml"):
                    candidates.append(clean)

            if not candidates:
                meta["status"] = "WARN"
                meta["note"] = "Keine addon.xml gefunden"
                return meta

            candidates.sort(key=lambda item: (item.count("/"), item))
            addon_xml_name = candidates[0]
            raw = zf.read(addon_xml_name).decode("utf-8", errors="replace")
            root = ET.fromstring(raw)

            addon_id = root.attrib.get("id", "").strip()
            name = root.attrib.get("name", "").strip()
            version = root.attrib.get("version", "").strip()
            provider = root.attrib.get("provider-name", "").strip()

            points = []
            for ext in root.findall("extension"):
                point = ext.attrib.get("point", "").strip()
                if point:
                    points.append(point)

            meta["addon_id"] = addon_id or meta["addon_id"]
            meta["name"] = name or addon_id or meta["name"]
            meta["version"] = version
            meta["provider"] = provider
            meta["points"] = points
            meta["addon_xml"] = addon_xml_name
            return meta

    except BadZipFile:
        meta["status"] = "ERROR"
        meta["note"] = "Defekte ZIP-Datei"
        return meta
    except ET.ParseError as exc:
        meta["status"] = "ERROR"
        meta["note"] = f"addon.xml XML-Fehler: {exc}"
        return meta
    except Exception as exc:
        meta["status"] = "ERROR"
        meta["note"] = f"{type(exc).__name__}: {exc}"
        return meta


def category_for_zip(repo_root: Path, zip_path: Path) -> str:
    """Bestimmt die sichtbare Kategorie aus ZIPs/<Kategorie>/datei.zip."""
    zip_root = repo_root / "ZIPs"

    try:
        rel_parts = zip_path.relative_to(zip_root).parts
    except ValueError:
        return "SONSTIGE"

    if len(rel_parts) >= 2:
        category = rel_parts[0].upper()
        if category in CATEGORY_ORDER:
            return category

    return "SONSTIGE"


def collect_zip_items(repo_root: Path) -> list[dict[str, object]]:
    """Sammelt alle ZIPs rekursiv unter ZIPs/."""
    zip_root = repo_root / "ZIPs"
    items: list[dict[str, object]] = []

    if not zip_root.is_dir():
        return items

    for zip_path in sorted(zip_root.rglob("*.zip")):
        rel = zip_path.relative_to(repo_root).as_posix()
        category = category_for_zip(repo_root, zip_path)
        meta = read_zip_meta(zip_path)
        items.append({
            "path": zip_path,
            "rel": rel,
            "category": category,
            "size": zip_path.stat().st_size,
            "mtime": mtime(zip_path),
            "meta": meta,
        })

    def sort_key(item: dict[str, object]) -> tuple[int, str, str]:
        category = str(item["category"])
        meta = item["meta"]
        assert isinstance(meta, dict)
        cat_index = CATEGORY_ORDER.index(category) if category in CATEGORY_ORDER else 99
        return (
            cat_index,
            str(meta.get("addon_id", "")).lower(),
            str(item["rel"]).lower(),
        )

    return sorted(items, key=sort_key)


def root_listing_rows(repo_root: Path, items: list[dict[str, object]]) -> str:
    """Rendert die obere Directory-Listing-Tabelle."""
    rows: list[str] = []
    known_paths = [
        repo_root / "ZIPs",
        repo_root / "ZIPs" / "REPOSITORY",
        repo_root / "ZIPs" / "VIDEO",
        repo_root / "ZIPs" / "PROGRAMM",
        repo_root / "addons.xml",
        repo_root / "addons.xml.md5",
        repo_root / "repository.kodiwulf",
        repo_root / "bg.png",
        repo_root / "README.md",
        repo_root / "CHANGES.md",
        repo_root / "UPDATE_PROCESS.md",
        repo_root / "index.md",
        repo_root / ".nojekyll",
    ]

    for path in known_paths:
        if not path.exists():
            continue

        rel = path.relative_to(repo_root).as_posix()
        if path.is_dir():
            rows.append(
                f'<tr><td class="type">DIR</td>'
                f'<td><a href="{href(rel)}/">{esc(rel)}/</a></td>'
                f'<td>{esc(mtime(path))}</td><td>-</td></tr>'
            )
        else:
            rows.append(
                f'<tr><td class="type">FILE</td>'
                f'<td><a href="{href(rel)}">{esc(rel)}</a></td>'
                f'<td>{esc(mtime(path))}</td><td>{esc(human_size(path.stat().st_size))}</td></tr>'
            )

    if not rows:
        rows.append('<tr><td class="type warn">WARN</td><td>Keine Dateien gefunden</td><td>-</td><td>-</td></tr>')

    return "\n".join(rows)


def addon_rows(items: list[dict[str, object]]) -> str:
    """Rendert die Gesamttabelle aller Add-ons."""
    rows: list[str] = []

    for item in items:
        meta = item["meta"]
        assert isinstance(meta, dict)

        status = str(meta.get("status", "OK"))
        note = str(meta.get("note", ""))
        provider = str(meta.get("provider", ""))
        addon_id = str(meta.get("addon_id", ""))
        version = str(meta.get("version", ""))
        category = str(item["category"])
        points = meta.get("points", [])

        points_text = ", ".join(str(point) for point in points) if isinstance(points, list) and points else "kein Extension-Point erkannt"
        status_class = "ok" if status == "OK" else "warn" if status == "WARN" else "bad"
        note_html = f'<br><small class="warn">{esc(note)}</small>' if note else ""
        provider_html = f'<br><small>{esc(provider)}</small>' if provider else ""
        points_html = f'<br><small>{esc(points_text)}</small>'
        rel = str(item["rel"])

        rows.append(
            "<tr>"
            f'<td class="type">{esc(category[:4])}</td>'
            f'<td><a href="{href(rel)}">{esc(addon_id)}</a>{provider_html}{points_html}{note_html}</td>'
            f'<td>{esc(version or "nicht erkannt")}</td>'
            f'<td><span class="badge {status_class}">{esc(status)}</span></td>'
            f'<td><a href="{href(rel)}">{esc(Path(rel).name)}</a><br><small>{esc(human_size(int(item["size"])))}</small></td>'
            "</tr>"
        )

    if not rows:
        rows.append('<tr><td class="type warn">WARN</td><td>Keine ZIPs in ZIPs/ gefunden</td><td>-</td><td>-</td><td>-</td></tr>')

    return "\n".join(rows)


def grouped_panels(items: list[dict[str, object]]) -> str:
    """Rendert je Kategorie eine Download-Tabelle."""
    grouped: dict[str, list[dict[str, object]]] = {key: [] for key in CATEGORY_ORDER}
    grouped["SONSTIGE"] = []

    for item in items:
        category = str(item["category"])
        grouped.setdefault(category, []).append(item)

    panels: list[str] = []
    panel_categories = CATEGORY_ORDER + (["SONSTIGE"] if grouped.get("SONSTIGE") else [])

    for category in panel_categories:
        category_items = grouped.get(category, [])
        rows: list[str] = []

        for item in category_items:
            meta = item["meta"]
            assert isinstance(meta, dict)
            rel = str(item["rel"])

            rows.append(
                "<tr>"
                f'<td class="type">ZIP</td>'
                f'<td><a href="{href(rel)}">{esc(meta.get("addon_id", ""))}</a><br><small>{esc(meta.get("name", ""))}</small></td>'
                f'<td>{esc(meta.get("version", "") or "nicht erkannt")}</td>'
                f'<td>{esc(str(item["mtime"]))}</td>'
                f'<td>{esc(human_size(int(item["size"])))}</td>'
                f'<td><a href="{href(rel)}">Download</a></td>'
                "</tr>"
            )

        if not rows:
            rows.append('<tr><td class="type">-</td><td>Keine ZIPs vorhanden</td><td>-</td><td>-</td><td>-</td><td>-</td></tr>')

        panels.append(f'''
<section class="panel" id="{esc(category.lower())}">
  <div class="panel-head">
    <div>
      <h2>{esc(CATEGORY_LABEL.get(category, category))}</h2>
      <small>{esc(CATEGORY_HINT.get(category, ""))}</small>
    </div>
    <span class="pill">{len(category_items)} ZIPs</span>
  </div>
  <div class="table-wrap">
    <table>
      <thead><tr><th></th><th>Add-on</th><th>Version</th><th>Last modified</th><th>Size</th><th>ZIP</th></tr></thead>
      <tbody>
        {''.join(rows)}
      </tbody>
    </table>
  </div>
</section>
''')

    return "\n".join(panels)


def build_document(repo_root: Path, items: list[dict[str, object]]) -> str:
    """Baut das komplette dunkle HTML-Dokument."""
    counts = {key: 0 for key in CATEGORY_ORDER}
    counts["SONSTIGE"] = 0
    for item in items:
        counts[str(item["category"])] = counts.get(str(item["category"]), 0) + 1

    bg_status = "bg.png background active" if (repo_root / "bg.png").exists() else "bg.png nicht gefunden"
    repo_addon_link = "repository.kodiwulf/" if (repo_root / "repository.kodiwulf").is_dir() else "ZIPs/REPOSITORY/"
    generated_at = "deterministic build"

    return f'''<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>KodiWulf Repository</title>
<meta name="description" content="Dunkler KodiWulf Repository Index für Kodi 21 Omega">
<style>
:root {{
  --bg: #050506;
  --panel: rgba(9, 9, 13, 0.88);
  --panel2: rgba(14, 14, 21, 0.95);
  --line: rgba(255,255,255,0.14);
  --text: #f4f4f8;
  --muted: #aaaab8;
  --red: #ff3030;
  --cyan: #8be9fd;
  --green: #98ffbb;
  --yellow: #ffcc66;
  --shadow: rgba(0,0,0,0.72);
}}

* {{ box-sizing: border-box; }}
html {{ min-height: 100%; background: var(--bg); }}

body {{
  min-height: 100vh;
  margin: 0;
  color: var(--text);
  font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  line-height: 1.55;
  background:
    radial-gradient(circle at 20% 10%, rgba(255,48,48,0.20), transparent 34%),
    radial-gradient(circle at 85% 25%, rgba(139,233,253,0.13), transparent 30%),
    linear-gradient(90deg, rgba(5,5,6,0.98), rgba(5,5,6,0.76), rgba(5,5,6,0.98)),
    linear-gradient(180deg, rgba(0,0,0,0.84), rgba(0,0,0,0.95)),
    url("bg.png");
  background-size: cover;
  background-position: center center;
  background-attachment: fixed;
}}

a {{ color: var(--cyan); text-decoration: none; font-weight: 700; }}
a:hover {{ color: #fff; text-decoration: underline; }}

main {{
  width: min(1180px, calc(100% - 32px));
  margin: 0 auto;
  padding: 34px 0 58px;
}}

.hero {{
  border: 1px solid var(--line);
  border-radius: 28px;
  padding: clamp(28px, 5vw, 58px);
  background:
    linear-gradient(135deg, rgba(255,48,48,0.16), transparent 42%),
    linear-gradient(315deg, rgba(139,233,253,0.10), transparent 42%),
    var(--panel);
  box-shadow: 0 30px 90px var(--shadow);
  backdrop-filter: blur(10px);
  margin-bottom: 18px;
}}

.eyebrow {{
  margin: 0 0 12px;
  color: var(--red);
  text-transform: uppercase;
  letter-spacing: .18em;
  font-size: .78rem;
  font-weight: 900;
}}

h1 {{
  margin: 0;
  font-size: clamp(2.2rem, 7vw, 5rem);
  line-height: .95;
  letter-spacing: -.065em;
}}

.x {{ color: var(--red); text-shadow: 0 0 24px rgba(255,48,48,.72); }}
.subtitle {{ max-width: 900px; margin: 18px 0 0; color: var(--muted); font-size: 1.04rem; }}

.nav {{
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 22px;
}}

.nav a {{
  display: inline-flex;
  align-items: center;
  min-height: 38px;
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 7px 13px;
  color: var(--text);
  background: rgba(255,255,255,.045);
}}

.nav a:hover {{
  border-color: rgba(139,233,253,.45);
  background: rgba(139,233,253,.10);
  text-decoration: none;
}}

.grid {{
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin: 18px 0;
}}

.card,
.panel {{
  border: 1px solid var(--line);
  border-radius: 18px;
  background: var(--panel2);
  box-shadow: 0 18px 55px var(--shadow);
  backdrop-filter: blur(10px);
}}

.card {{ padding: 18px; }}
.card h2 {{ margin: 0 0 10px; font-size: 1.05rem; }}
.card p {{ margin: 0; color: var(--muted); }}
.card strong {{ display: block; color: var(--green); font-size: 2rem; line-height: 1; }}

.panel {{ overflow: hidden; margin-top: 18px; }}

.panel-head {{
  padding: 18px 20px;
  border-bottom: 1px solid var(--line);
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
}}

.panel-head h2 {{ margin: 0; font-size: 1.15rem; }}

.pill {{
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 6px 11px;
  color: var(--muted);
  background: rgba(255,255,255,.04);
  font-size: .82rem;
  white-space: nowrap;
}}

.table-wrap {{ width: 100%; overflow-x: auto; }}
table {{ width: 100%; border-collapse: collapse; }}

th,
td {{
  padding: 12px 16px;
  border-bottom: 1px solid rgba(255,255,255,.09);
  text-align: left;
  vertical-align: middle;
}}

th {{
  color: #fff;
  font-size: .78rem;
  text-transform: uppercase;
  letter-spacing: .08em;
  background: rgba(255,255,255,.045);
}}

td {{ color: var(--muted); }}
tr:hover td {{ background: rgba(255,255,255,.04); color: var(--text); }}

.type {{
  width: 78px;
  text-align: center;
  color: var(--yellow);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  white-space: nowrap;
}}

.warn {{ color: var(--yellow); font-weight: 800; }}
.bad {{ color: #ff9090; }}

.badge {{
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 4px 9px;
  font-size: .74rem;
  font-weight: 900;
  letter-spacing: .07em;
}}

.badge.ok {{ color: #04120a; background: var(--green); }}
.badge.warn {{ color: #1c1300; background: var(--yellow); }}
.badge.bad {{ color: #210000; background: #ff6b6b; }}

.urls {{
  padding: 16px 20px 20px;
  color: var(--muted);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  white-space: pre-wrap;
  word-break: break-all;
}}

small {{ color: var(--muted); }}

footer {{
  margin-top: 22px;
  color: var(--muted);
  font-size: .88rem;
  text-align: center;
}}

@media (max-width: 920px) {{
  .grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
  th:nth-child(4), td:nth-child(4) {{ display: none; }}
}}

@media (max-width: 640px) {{
  main {{ width: min(100% - 20px, 1180px); padding-top: 14px; }}
  .grid {{ grid-template-columns: 1fr; }}
  .panel-head {{ align-items: flex-start; flex-direction: column; }}
}}
</style>
</head>
<body>
<main>
  <header class="hero">
    <p class="eyebrow">GitHub Pages Kodi Repository</p>
    <h1><span class="x">x</span>Wulf Repository</h1>
    <p class="subtitle">
      Dunkler statischer Repository-Index nach Directory-Listing-Vorbild.
      Diese Seite verlinkt die aktuelle ZIP-Struktur aus <strong>ZIPs/REPOSITORY</strong>,
      <strong>ZIPs/VIDEO</strong> und <strong>ZIPs/PROGRAMM</strong>.
    </p>
    <nav class="nav" aria-label="Repository Navigation">
      <a href="#repository">Repository-ZIPs</a>
      <a href="#video">Video-Add-ons</a>
      <a href="#programm">Programm-Add-ons</a>
      <a href="addons.xml">addons.xml</a>
      <a href="addons.xml.md5">addons.xml.md5</a>
      <a href="{esc(repo_addon_link)}">Repository Add-on</a>
    </nav>
  </header>

  <section class="grid" aria-label="Repository Übersicht">
    <article class="card"><h2>ZIPs gesamt</h2><p><strong>{len(items)}</strong>aus ZIPs/ rekursiv gelesen</p></article>
    <article class="card"><h2>Repository</h2><p><strong>{counts.get("REPOSITORY", 0)}</strong>ZIPs/REPOSITORY</p></article>
    <article class="card"><h2>Video</h2><p><strong>{counts.get("VIDEO", 0)}</strong>ZIPs/VIDEO</p></article>
    <article class="card"><h2>Programm</h2><p><strong>{counts.get("PROGRAMM", 0)}</strong>ZIPs/PROGRAMM</p></article>
  </section>

  <section class="grid">
    <article class="card"><h2>Repository XML</h2><p><a href="addons.xml">addons.xml</a></p></article>
    <article class="card"><h2>Checksum</h2><p><a href="addons.xml.md5">addons.xml.md5</a></p></article>
    <article class="card"><h2>Kodi Repository Add-on</h2><p><a href="{esc(repo_addon_link)}">{esc(repo_addon_link)}</a></p></article>
    <article class="card"><h2>ZIP Root</h2><p><a href="ZIPs/">ZIPs/</a></p></article>
  </section>

  <section class="panel">
    <div class="panel-head">
      <h2>Index of /kodiwulf-repo/</h2>
      <span class="pill">{esc(bg_status)}</span>
    </div>
    <div class="table-wrap">
      <table>
        <thead><tr><th></th><th>Name</th><th>Last modified</th><th>Size</th></tr></thead>
        <tbody>
          {root_listing_rows(repo_root, items)}
        </tbody>
      </table>
    </div>
  </section>

  <section class="panel">
    <div class="panel-head">
      <h2>Kodi Add-ons</h2>
      <span class="pill">real ZIP scan</span>
    </div>
    <div class="table-wrap">
      <table>
        <thead><tr><th></th><th>Add-on</th><th>Version</th><th>Status</th><th>ZIP</th></tr></thead>
        <tbody>
          {addon_rows(items)}
        </tbody>
      </table>
    </div>
  </section>

  {grouped_panels(items)}

  <section class="panel">
    <div class="panel-head">
      <h2>Kodi URLs</h2>
      <span class="pill">for repository.kodiwulf</span>
    </div>
    <div class="urls">{esc(PUBLIC_BASE_URL)}/
{esc(PUBLIC_BASE_URL)}/addons.xml
{esc(PUBLIC_BASE_URL)}/addons.xml.md5
{esc(PUBLIC_BASE_URL)}/{esc(repo_addon_link)}</div>
  </section>

  <footer>Generated by KodiWulf Dark Index Builder - {esc(generated_at)}</footer>
</main>
</body>
</html>
'''


def write_dark_index(repo_root: Path | str = ".") -> Path:
    """Schreibt die dunkle index.html in das angegebene Repository-Root."""
    root = Path(repo_root).resolve()
    index_path = root / "index.html"
    items = collect_zip_items(root)
    document = build_document(root, items)
    document = "\n".join(line.rstrip() for line in document.splitlines()).rstrip() + "\n"
    if not index_path.exists() or index_path.read_text(encoding="utf-8", errors="replace") != document:
        index_path.write_text(document, encoding="utf-8", newline="\n")
    return index_path


def main() -> int:
    """CLI-Einstiegspunkt für manuelle Aktualisierung."""
    parser = argparse.ArgumentParser(description="KodiWulf dark index.html generator")
    parser.add_argument("--repo", default=".", help="Pfad zum kodiwulf-repo Root")
    args = parser.parse_args()

    index_path = write_dark_index(Path(args.repo))
    print(f"[OK] Dark index geschrieben: {index_path}")
    return 0



def force_public_plugin_links(html_text: str) -> str:
    """Ersetzt lokale ZIPs/-Quellpfade durch öffentliche plugin/*-Links."""
    replacements = {
        "ZIPs/VIDEO/": "plugin/video/",
        "ZIPs/PROGRAMM/": "plugin/program/",
        "ZIPs/REPOSITORY/": "plugin/repository/",
        "ZIPs/VIDEO": "plugin/video",
        "ZIPs/PROGRAMM": "plugin/program",
        "ZIPs/REPOSITORY": "plugin/repository",
        'href="ZIPs/"': 'href="plugin/"',
        ">ZIPs/<": ">plugin/<",
        "aus ZIPs/ rekursiv gelesen": "aus plugin/* gespiegelt",
        "ZIP Root": "Plugin Root",
    }
    for old, new in replacements.items():
        html_text = html_text.replace(old, new)
    return html_text


if __name__ == "__main__":
    raise SystemExit(main())
