#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KodiWulf repository builder.

Builds Kodi repository index files and versioned ZIP packages from add-on folders.
"""
from __future__ import annotations

import hashlib
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {'.git', '.github', 'tools', '.build', 'build', 'dist', '__pycache__'}


def read_text(path: Path) -> str:
    """Liest eine Textdatei stabil als UTF-8 ein."""
    return path.read_text(encoding='utf-8').strip()


def addon_id_and_version(addon_xml: Path) -> tuple[str, str]:
    """Liest Add-on-ID und Version aus einer addon.xml."""
    root = ET.fromstring(addon_xml.read_text(encoding='utf-8'))
    addon_id = root.attrib.get('id')
    version = root.attrib.get('version')
    if not addon_id or not version:
        raise ValueError(f'Missing id/version in {addon_xml}')
    return addon_id, version


def addon_directories() -> list[Path]:
    """Findet alle Add-on-Verzeichnisse auf Root-Ebene."""
    dirs: list[Path] = []
    for child in sorted(ROOT.iterdir()):
        if not child.is_dir() or child.name in EXCLUDED_DIRS:
            continue
        if (child / 'addon.xml').is_file():
            dirs.append(child)
    return dirs


def write_addons_xml(addons: list[Path]) -> Path:
    """Schreibt die zentrale addons.xml aus allen gefundenen addon.xml-Dateien."""
    blocks = []
    for addon_dir in addons:
        content = read_text(addon_dir / 'addon.xml')
        content = re.sub(r'^<\?xml[^>]+>\s*', '', content, flags=re.MULTILINE)
        blocks.append(content)

    output = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<addons>\n'
    output += '\n'.join(blocks)
    output += '\n</addons>\n'

    addons_xml = ROOT / 'addons.xml'
    addons_xml.write_text(output, encoding='utf-8', newline='\n')
    return addons_xml


def write_md5(path: Path) -> Path:
    """Schreibt die MD5-Checksumme der addons.xml im Kodi-kompatiblen Format."""
    digest = hashlib.md5(path.read_bytes()).hexdigest()
    md5_path = ROOT / 'addons.xml.md5'
    md5_path.write_text(digest, encoding='utf-8', newline='\n')
    return md5_path


def create_addon_zip(addon_dir: Path) -> Path:
    """Erzeugt eine versionierte ZIP-Datei für ein Add-on."""
    addon_id, version = addon_id_and_version(addon_dir / 'addon.xml')
    zip_path = addon_dir / f'{addon_id}-{version}.zip'
    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(addon_dir.rglob('*')):
            if path == zip_path or path.name.endswith('.zip'):
                continue
            if path.is_file():
                zf.write(path, path.relative_to(ROOT).as_posix())
    return zip_path


def main() -> int:
    """Baut Repository-Index und Add-on-ZIP-Dateien."""
    addons = addon_directories()
    if not addons:
        print('[ERROR] No add-on directories with addon.xml found.', file=sys.stderr)
        return 1

    for addon_dir in addons:
        zip_path = create_addon_zip(addon_dir)
        print(f'[OK] Built {zip_path.relative_to(ROOT)}')

    addons_xml = write_addons_xml(addons)
    md5_path = write_md5(addons_xml)
    print(f'[OK] Wrote {addons_xml.relative_to(ROOT)}')
    print(f'[OK] Wrote {md5_path.relative_to(ROOT)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
