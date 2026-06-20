#!/usr/bin/env python3
from __future__ import annotations

import html
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

BEGIN = "<!-- DRDEBUG-KODIWULF-INDEX:BEGIN -->"
END = "<!-- DRDEBUG-KODIWULF-INDEX:END -->"


def parse_root(args: list[str]) -> Path:
    for i, arg in enumerate(args):
        if arg == "--root" and i + 1 < len(args):
            return Path(args[i + 1]).expanduser().resolve()
        if arg.startswith("--root="):
            return Path(arg.split("=", 1)[1]).expanduser().resolve()
    return Path.cwd().resolve()


def has_apply(args: list[str]) -> bool:
    return "--apply" in args or any(arg == "--apply=true" for arg in args)


def backup_file(path: Path, label: str) -> Path:
    backup_dir = path.parent.parent / ".drdebug-backups" if path.parent.name in {"Repository", "Videos", "Program"} else path.parent / ".drdebug-backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    backup = backup_dir / f"{path.name}.{label}.{stamp}.bak"
    if path.exists():
        shutil.copy2(path, backup)
    return backup


def normalize_public_index(index_path: Path) -> None:
    if not index_path.exists():
        print(f"[WARN] index.html nicht gefunden: {index_path}", file=sys.stderr)
        return

    text = index_path.read_text(encoding="utf-8")
    original = text

    replacements = {
        "ZIPs/REPOSITORY/": "Repository/",
        "ZIPs/VIDEO/": "Videos/",
        "ZIPs/PROGRAMM/": "Program/",
        "ZIPs/REPOSITORY": "Repository",
        "ZIPs/VIDEO": "Videos",
        "ZIPs/PROGRAMM": "Program",
        "plugin/repository/": "Repository/",
        "plugin/video/": "Videos/",
        "plugin/program/": "Program/",
        "plugin/repository": "Repository",
        "plugin/video": "Videos",
        "plugin/program": "Program",
        "aus ZIPs/ rekursiv gelesen": "aus Repository/, Videos/ und Program/ erzeugt",
        "aus plugin/* gespiegelt": "aus Repository/, Videos/ und Program/ erzeugt",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = text.replace(BEGIN, "").replace(END, "")
    text = re.sub(r"\n{3,}", "\n\n", text)

    if "<main" in text and "</main>" in text:
        text = re.sub(r"(<main\b[^>]*>)", BEGIN + "\n" + r"\1", text, count=1)
        text = re.sub(r"(</main>)", r"\1" + "\n" + END, text, count=1)
    elif "</body>" in text:
        text = text.replace("</body>", BEGIN + "\n" + END + "\n</body>", 1)
    else:
        text = text.rstrip() + "\n" + BEGIN + "\n" + END + "\n"

    if text != original:
        backup = backup_file(index_path, "wrapper-public-index")
        index_path.write_text(text, encoding="utf-8")
        print(f"[OK] public index normalized: {index_path}")
        print(f"[OK] index backup: {backup}")
    else:
        print(f"[OK] public index already normalized: {index_path}")


def human_size(path: Path) -> str:
    size = path.stat().st_size
    units = ["B", "KB", "MB", "GB"]
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} B"
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{size} B"


def write_folder_index(root: Path, folder_name: str, title: str) -> None:
    folder = root / folder_name
    if not folder.exists():
        return

    rows = []
    for f in sorted(folder.iterdir(), key=lambda p: p.name.lower()):
        if not f.is_file():
            continue
        if f.name == "index.html":
            continue
        if not (f.name.endswith(".zip") or f.name.endswith(".zip.md5")):
            continue
        name = html.escape(f.name)
        rows.append(
            f'<tr><td><a href="{name}">{name}</a></td>'
            f'<td>{human_size(f)}</td></tr>'
        )

    body_rows = "\n".join(rows) if rows else '<tr><td colspan="2">Keine Dateien gefunden.</td></tr>'

    content = f"""<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <title>{html.escape(title)}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; background: #111; color: #eee; }}
    a {{ color: #8ab4ff; }}
    table {{ border-collapse: collapse; width: 100%; max-width: 1100px; }}
    th, td {{ border-bottom: 1px solid #333; padding: .55rem; text-align: left; }}
    .up {{ margin-bottom: 1rem; }}
  </style>
</head>
<body>
  <h1>{html.escape(title)}</h1>
  <p class="up"><a href="../">../ Zurück</a></p>
  <table>
    <thead><tr><th>Datei</th><th>Größe</th></tr></thead>
    <tbody>
{body_rows}
    </tbody>
  </table>
</body>
</html>
"""

    index = folder / "index.html"
    old = index.read_text(encoding="utf-8") if index.exists() else None
    if old != content:
        if index.exists():
            backup_file(index, "folder-index")
        index.write_text(content, encoding="utf-8")
        print(f"[OK] folder index written: {index}")
    else:
        print(f"[OK] folder index already current: {index}")


def write_folder_indexes(root: Path) -> None:
    write_folder_index(root, "Repository", "KodiWulf Repository ZIPs")
    write_folder_index(root, "Videos", "KodiWulf Video Add-ons")
    write_folder_index(root, "Program", "KodiWulf Program Add-ons")


def main() -> int:
    here = Path(__file__).resolve().parent
    core = here / "kodiwulf_build_repo_core.py"

    if not core.exists():
        print(f"ERROR: Core generator fehlt: {core}", file=sys.stderr)
        return 2

    args = sys.argv[1:]
    rc = subprocess.call([sys.executable, str(core), *args])
    if rc != 0:
        return rc

    if has_apply(args):
        root = parse_root(args)
        normalize_public_index(root / "index.html")
        write_folder_indexes(root)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
