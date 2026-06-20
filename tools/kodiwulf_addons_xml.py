#!/usr/bin/env python3
"""
KodiWulf addons.xml builder.

Erzeugt addons.xml und addons.xml.md5 idempotent aus:
  - ZIPs/VIDEO/*.zip
  - ZIPs/PROGRAMM/*.zip
  - ZIPs/REPOSITORY/*.zip
  - repository.kodiwulf/repository.kodiwulf-*.zip

Wichtig:
Die generierte repository.kodiwulf-ZIP muss zusätzlich aufgenommen werden,
weil sie nicht in ZIPs/ liegt, aber für Kodi-Repository-Updates in addons.xml
stehen soll.
"""

from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile, BadZipFile
import hashlib
import re
import xml.etree.ElementTree as ET


def read_text_from_zip(zip_path: Path, member: str) -> str:
    """Liest eine Textdatei aus einer ZIP-Datei."""
    with ZipFile(zip_path) as zf:
        return zf.read(member).decode("utf-8", errors="replace")


def find_addon_xml_name(zip_path: Path) -> str | None:
    """Findet die addon.xml innerhalb einer Kodi-Addon-ZIP."""
    try:
        with ZipFile(zip_path) as zf:
            names = zf.namelist()
    except BadZipFile:
        return None

    candidates = [
        name for name in names
        if name == "addon.xml" or name.endswith("/addon.xml")
    ]
    return candidates[0] if candidates else None


def addon_identity(zip_path: Path) -> tuple[str, str] | None:
    """Liest Add-on-ID und Version aus einer ZIP-Datei."""
    addon_xml_name = find_addon_xml_name(zip_path)
    if not addon_xml_name:
        return None

    raw = read_text_from_zip(zip_path, addon_xml_name)
    root = ET.fromstring(raw)
    addon_id = (root.attrib.get("id") or "").strip()
    version = (root.attrib.get("version") or "").strip()

    if not addon_id or not version:
        return None

    return addon_id, version


def normalized_addon_xml(zip_path: Path) -> bytes:
    """Extrahiert und normalisiert die addon.xml eines Add-ons."""
    addon_xml_name = find_addon_xml_name(zip_path)
    if not addon_xml_name:
        raise ValueError(f"Keine addon.xml gefunden: {zip_path}")

    raw = read_text_from_zip(zip_path, addon_xml_name)
    root = ET.fromstring(raw)

    # ElementTree normalisiert kleine Whitespace-/Serialisierungsunterschiede.
    xml_text = ET.tostring(root, encoding="unicode", short_empty_elements=False)
    xml_text = xml_text.strip()

    return (xml_text + "\n").encode("utf-8")


def source_zip_paths(root: Path) -> list[Path]:
    """Ermittelt alle ZIPs, die in addons.xml aufgenommen werden sollen."""
    paths: list[Path] = []

    input_dirs = [
        root / "ZIPs" / "PROGRAMM",
        root / "ZIPs" / "REPOSITORY",
        root / "ZIPs" / "VIDEO",
    ]

    for input_dir in input_dirs:
        if input_dir.is_dir():
            paths.extend(sorted(input_dir.glob("*.zip")))

    # Die eigene generierte Repository-ZIP liegt absichtlich außerhalb von ZIPs/.
    # Sie muss trotzdem in addons.xml stehen.
    canonical_repo_dir = root / "repository.kodiwulf"
    if canonical_repo_dir.is_dir():
        paths.extend(sorted(canonical_repo_dir.glob("repository.kodiwulf-*.zip")))

    # Fallback für Install-from-ZIP-Kopie, falls canonical fehlt.
    public_repo_dir = root / "Repository"
    if not any(p.name.startswith("repository.kodiwulf-") for p in paths):
        if public_repo_dir.is_dir():
            paths.extend(sorted(public_repo_dir.glob("repository.kodiwulf-*.zip")))

    # Dedupe nach Add-on-ID + Version. Canonical gewinnt vor Public-Kopie.
    by_identity: dict[tuple[str, str], Path] = {}
    for path in paths:
        identity = addon_identity(path)
        if identity is None:
            continue
        by_identity.setdefault(identity, path)

    return [
        by_identity[key]
        for key in sorted(by_identity, key=lambda item: (item[0].lower(), item[1]))
    ]


def write_if_changed(path: Path, data: bytes) -> bool:
    """Schreibt Bytes nur, wenn sich der Inhalt geändert hat."""
    if path.exists() and path.read_bytes() == data:
        return False
    path.write_bytes(data)
    return True


def write_text_if_changed(path: Path, text: str) -> bool:
    """Schreibt Text nur, wenn sich der Inhalt geändert hat."""
    data = text.encode("utf-8")
    return write_if_changed(path, data)


def build_addons_xml(root: Path) -> tuple[bytes, int]:
    """Baut die komplette addons.xml aus allen relevanten ZIPs."""
    zip_paths = source_zip_paths(root)

    addon_blocks: list[bytes] = []
    for zip_path in zip_paths:
        addon_blocks.append(normalized_addon_xml(zip_path))

    content = b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<addons>\n'
    for block in addon_blocks:
        for line in block.decode("utf-8", errors="replace").splitlines():
            content += f"  {line}\n".encode("utf-8")
    content += b"</addons>\n"

    # Stabile Whitespace-Normalisierung.
    content = re.sub(rb"[ \t]+\n", b"\n", content)
    content = content.replace(b"\r\n", b"\n").replace(b"\r", b"\n")

    return content, len(addon_blocks)


def write_addons_xml_from_zips(root: Path | str) -> tuple[Path, Path, int]:
    """Schreibt addons.xml und addons.xml.md5 idempotent."""
    root = Path(root)
    addons_xml_path = root / "addons.xml"
    addons_md5_path = root / "addons.xml.md5"

    addons_xml, addon_count = build_addons_xml(root)
    digest = hashlib.md5(addons_xml).hexdigest()

    changed_xml = write_if_changed(addons_xml_path, addons_xml)
    changed_md5 = write_text_if_changed(addons_md5_path, digest)

    if changed_xml:
        print(f"[OK] geschrieben: {addons_xml_path}")
    else:
        print(f"[OK] unverändert: {addons_xml_path}")

    if changed_md5:
        print(f"[OK] geschrieben: {addons_md5_path}")
    else:
        print(f"[OK] unverändert: {addons_md5_path}")

    return addons_xml_path, addons_md5_path, addon_count


if __name__ == "__main__":
    write_addons_xml_from_zips(Path.cwd())
