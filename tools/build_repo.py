#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
# # # # # # # # # # # # # # #
# KodiWulf Repository Builder #
# # # # # # # # # # # # # # #

Erzeugt Kodi-kompatible Add-on-ZIP-Dateien, addons.xml,
addons.xml.md5 und eine ZIP-orientierte index.html.

Wichtig:
- Kodi-ZIP muss den Add-on-Ordner als obersten ZIP-Ordner enthalten.
- index.html verlinkt keine Plugin-Ordner, damit Kodi bei "Install from ZIP"
  keine Add-on-Ordner doppelt anzeigt.
"""

from __future__ import annotations

import hashlib
import html
import re
import shutil
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


REPO_ROOT = Path(__file__).resolve().parents[1]

SKIP_DIRS = {
    ".git",
    ".github",
    ".idea",
    ".vscode",
    "__pycache__",
    "tools",
    "build",
    "dist",
    "test",
    "tests",
}


def log(message: str) -> None:
    """Gibt eine Builder-Meldung aus."""
    print(message, flush=True)


def read_text(path: Path) -> str:
    """Liest eine Textdatei UTF-8-kompatibel ein."""
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    """Schreibt eine Textdatei mit UTF-8 und Unix-Zeilenenden."""
    path.write_text(content, encoding="utf-8", newline="\n")


def parse_addon_metadata(addon_xml: Path) -> tuple[str, str, str]:
    """Liest id, version und name aus einer addon.xml."""
    root = ET.fromstring(read_text(addon_xml))
    addon_id = root.attrib.get("id", "").strip()
    version = root.attrib.get("version", "").strip()
    name = root.attrib.get("name", addon_id).strip()

    if not addon_id:
        raise ValueError(f"addon.xml ohne id: {addon_xml}")
    if not version:
        raise ValueError(f"addon.xml ohne version: {addon_xml}")

    return addon_id, version, name


def strip_xml_declaration(xml_text: str) -> str:
    """Entfernt eine optionale XML-Deklaration am Anfang."""
    return re.sub(r"^\s*<\?xml[^>]*\?>\s*", "", xml_text, count=1).strip()


def discover_addons() -> list[dict[str, str | Path]]:
    """Findet alle Add-on-Ordner mit addon.xml im Repository-Root."""
    addons: list[dict[str, str | Path]] = []

    for directory in sorted(REPO_ROOT.iterdir()):
        if not directory.is_dir():
            continue
        if directory.name in SKIP_DIRS:
            continue
        if directory.name.startswith("."):
            continue

        addon_xml = directory / "addon.xml"
        if not addon_xml.is_file():
            continue

        addon_id, version, name = parse_addon_metadata(addon_xml)

        if addon_id != directory.name:
            log(f"[WARN] Ordnername und addon id unterscheiden sich: {directory.name} != {addon_id}")

        addons.append(
            {
                "id": addon_id,
                "version": version,
                "name": name,
                "dir": directory,
                "addon_xml": addon_xml,
            }
        )

    return addons


def should_include_file(path: Path) -> bool:
    """Entscheidet, ob eine Datei in die Add-on-ZIP aufgenommen wird."""
    name = path.name

    if name.endswith(".zip"):
        return False
    if name.endswith(".pyc"):
        return False
    if name in {".DS_Store", "Thumbs.db"}:
        return False

    parts = set(path.parts)
    if "__pycache__" in parts:
        return False

    return True


def build_zip(addon: dict[str, str | Path]) -> Path:
    """Baut eine Kodi-kompatible ZIP für ein Add-on."""
    addon_id = str(addon["id"])
    version = str(addon["version"])
    addon_dir = Path(addon["dir"])

    zip_name = f"{addon_id}-{version}.zip"
    zip_path = addon_dir / zip_name

    if zip_path.exists():
        zip_path.unlink()

    log(f"[ZIP] {zip_path.relative_to(REPO_ROOT)}")

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file_path in sorted(addon_dir.rglob("*")):
            if not file_path.is_file():
                continue
            if not should_include_file(file_path):
                continue

            relative_inside_addon = file_path.relative_to(addon_dir)
            archive_name = Path(addon_dir.name) / relative_inside_addon
            zf.write(file_path, archive_name.as_posix())

    return zip_path


def build_addons_xml(addons: list[dict[str, str | Path]]) -> Path:
    """Erzeugt die zentrale Kodi addons.xml."""
    blocks: list[str] = []

    for addon in addons:
        addon_xml = Path(addon["addon_xml"])
        xml_text = strip_xml_declaration(read_text(addon_xml))
        blocks.append(xml_text)

    content = "<addons>\n"
    content += "\n\n".join(blocks)
    content += "\n</addons>\n"

    addons_xml = REPO_ROOT / "addons.xml"
    write_text(addons_xml, content)

    log("[OK] addons.xml erzeugt")
    return addons_xml


def build_md5(addons_xml: Path) -> Path:
    """Erzeugt die MD5-Prüfsumme für addons.xml."""
    digest = hashlib.md5(addons_xml.read_bytes()).hexdigest()
    md5_path = REPO_ROOT / "addons.xml.md5"
    write_text(md5_path, digest)
    log(f"[OK] addons.xml.md5 erzeugt: {digest}")
    return md5_path


def build_index(addons: list[dict[str, str | Path]], zip_paths: list[Path]) -> Path:
    """Erzeugt eine einfache ZIP-Liste ohne klickbare Add-on-Ordner."""
    rows: list[str] = []

    for addon, zip_path in zip(addons, zip_paths):
        addon_id = str(addon["id"])
        version = str(addon["version"])
        rel_zip = zip_path.relative_to(REPO_ROOT).as_posix()

        rows.append(
            "      <tr>"
            f"<td>{html.escape(addon_id)}</td>"
            f"<td>{html.escape(version)}</td>"
            f'<td><a href="{html.escape(rel_zip)}">{html.escape(zip_path.name)}</a></td>'
            "</tr>"
        )

    index = f"""<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <title>KodiWulf Repository</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>
  <h1>KodiWulf Repository</h1>

  <p>
    Für Kodi: <strong>Install from ZIP</strong> soll die Repository-ZIP installieren.
    Danach verwendet Kodi <code>addons.xml</code> und <code>addons.xml.md5</code>.
  </p>

  <h2>Repository Dateien</h2>
  <ul>
    <li><a href="addons.xml">addons.xml</a></li>
    <li><a href="addons.xml.md5">addons.xml.md5</a></li>
  </ul>

  <h2>ZIP Downloads</h2>
  <table border="1" cellpadding="6" cellspacing="0">
    <thead>
      <tr>
        <th>Add-on</th>
        <th>Version</th>
        <th>ZIP</th>
      </tr>
    </thead>
    <tbody>
{chr(10).join(rows)}
    </tbody>
  </table>
</body>
</html>
"""

    index_path = REPO_ROOT / "index.html"
    write_text(index_path, index)
    log("[OK] index.html erzeugt, ohne Plugin-Ordnerlinks")
    try:
        from kodiwulf_addons_xml import write_addons_xml_from_zips
        _, _, addon_count = write_addons_xml_from_zips(REPO_ROOT)
        log(f"[OK] addons.xml aus ZIPs erzeugt: {addon_count} Add-ons")
    except Exception as exc:
        log(f"[WARN] addons.xml konnte nicht aus ZIPs erzeugt werden: {exc}")
    try:
        from kodiwulf_dark_index import write_dark_index
        write_dark_index(REPO_ROOT)
        log("[OK] dunkle KodiWulf index.html erzeugt")
    except Exception as exc:
        log(f"[WARN] dunkle KodiWulf index.html konnte nicht erzeugt werden: {exc}")
    return index_path


def main() -> int:
    """Startet den KodiWulf Repository Build."""
    log("============================================================")
    log("KodiWulf Repository Build")
    log("============================================================")
    log(f"[INFO] Root: {REPO_ROOT}")

    try:
        addons = discover_addons()

        if not addons:
            log("[FEHLER] Keine Add-on-Ordner mit addon.xml gefunden.")
            return 2

        log("")
        log("[INFO] Gefundene Add-ons:")
        for addon in addons:
            log(f"  - {addon['id']} {addon['version']}")

        log("")
        zip_paths = [build_zip(addon) for addon in addons]

        log("")
        addons_xml = build_addons_xml(addons)
        build_md5(addons_xml)
        build_index(addons, zip_paths)

        log("")
        log("============================================================")
        log("Build fertig")
        log("============================================================")
        log("[OK] Erzeugt:")
        for zip_path in zip_paths:
            log(f"  - {zip_path.relative_to(REPO_ROOT)}")
        log("  - addons.xml")
        log("  - addons.xml.md5")
        log("  - index.html")
        return 0

    except Exception as exc:
        log("")
        log("============================================================")
        log("Build fehlgeschlagen")
        log("============================================================")
        log(f"[FEHLER] {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
