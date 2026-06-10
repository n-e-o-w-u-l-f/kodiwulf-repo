#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
KodiWulf repository builder.

Zweck:
- importiert lokale Kodi-Add-on-ZIP-Dateien aus zips/, Root oder Add-on-Ordnern,
- legt sie in der Kodi-kompatiblen Struktur addon.id/addon.id-version.zip ab,
- extrahiert addon.xml und wichtige Assets für Web-/Indexansicht,
- baut addons.xml und addons.xml.md5,
- erzeugt statische index.html-Dateien für GitHub Pages.
'''
from __future__ import annotations

import hashlib
import html
import re
import shutil
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_BASE_URL = 'https://n-e-o-w-u-l-f.github.io/kodiwulf-repo'
EXCLUDED_DIRS = {'.git', '.github', 'tools', '.build', 'build', 'dist', '__pycache__', 'zips', '_incoming', 'incoming-zips'}
EXPECTED_ADDONS = ['repository.kodiwulf', 'plugin.video.vavooto', 'plugin.video.xwulf', 'repository.kodinerds', 'repository.michaz']
ZIP_SCAN_DIRS = [ROOT, ROOT / 'zips', ROOT / '_incoming', ROOT / 'incoming-zips']
GENERATED_WEB_FILES = {'index.html'}
GENERATED_MARKERS = {'.kodiwulf-imported'}


def log(level: str, message: str) -> None:
    '''Gibt eine einheitliche Statusmeldung aus.'''
    print(f'[{level}] {message}')


def read_text(path: Path) -> str:
    '''Liest eine Textdatei stabil als UTF-8 ein.'''
    return path.read_text(encoding='utf-8').strip()


def strip_xml_declaration(xml_text: str) -> str:
    '''Entfernt eine XML-Deklaration für die Einbettung in addons.xml.'''
    return re.sub(r'^\s*<\?xml[^>]+>\s*', '', xml_text.strip(), flags=re.MULTILINE)


def parse_addon_xml(xml_text: str, source: str) -> tuple[str, str]:
    '''Liest Add-on-ID und Version aus einem addon.xml-Inhalt.'''
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise ValueError(f'Invalid addon.xml in {source}: {exc}') from exc
    addon_id = root.attrib.get('id', '').strip()
    version = root.attrib.get('version', '').strip()
    if not addon_id or not version:
        raise ValueError(f'Missing id/version in {source}')
    return addon_id, version


def addon_id_and_version(addon_xml: Path) -> tuple[str, str]:
    '''Liest Add-on-ID und Version aus einer addon.xml-Datei.'''
    return parse_addon_xml(addon_xml.read_text(encoding='utf-8'), str(addon_xml))


def find_zip_addon_xml(zf: zipfile.ZipFile) -> tuple[str, str]:
    '''Sucht die addon.xml innerhalb einer ZIP-Datei und gibt Pfad und Inhalt zurück.'''
    candidates = []
    for name in zf.namelist():
        clean = name.strip('/')
        if clean.endswith('/addon.xml') or clean == 'addon.xml':
            candidates.append(clean)
    if not candidates:
        raise ValueError('No addon.xml found inside ZIP')
    candidates.sort(key=lambda item: (item.count('/'), item))
    addon_xml_name = candidates[0]
    xml_text = zf.read(addon_xml_name).decode('utf-8')
    return addon_xml_name, xml_text


def zip_root_prefix(addon_xml_name: str) -> str:
    '''Ermittelt den Root-Ordner innerhalb einer ZIP-Datei.'''
    parts = addon_xml_name.split('/')
    return parts[0] + '/' if len(parts) > 1 else ''


def safe_extract_member(zf: zipfile.ZipFile, member: str, target: Path) -> None:
    '''Extrahiert genau ein ZIP-Mitglied ohne Path-Traversal-Risiko.'''
    target = target.resolve()
    root = ROOT.resolve()
    if not str(target).startswith(str(root)):
        raise ValueError(f'Unsafe extraction target: {target}')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(zf.read(member))


def copy_asset_candidates(zf: zipfile.ZipFile, addon_xml_name: str, addon_dir: Path) -> None:
    '''Kopiert typische Kodi-Assets aus einer ZIP-Datei in den Add-on-Ordner.'''
    xml_text = zf.read(addon_xml_name).decode('utf-8')
    prefix = zip_root_prefix(addon_xml_name)
    wanted = {'icon.png', 'fanart.jpg', 'fanart.png', 'changelog.txt', 'resources/icon.png', 'resources/fanart.jpg', 'resources/fanart.png', 'resources/media/banner.png', 'resources/media/banner.jpg'}
    try:
        root = ET.fromstring(xml_text)
        for asset in root.findall('.//assets/*'):
            if asset.text and asset.text.strip():
                wanted.add(asset.text.strip().lstrip('/'))
    except ET.ParseError:
        pass
    names = set(zf.namelist())
    for rel in sorted(wanted):
        member = prefix + rel
        if member in names:
            safe_extract_member(zf, member, addon_dir / rel)


def import_zip_package(zip_path: Path) -> tuple[str, str] | None:
    '''Importiert eine lokale Add-on-ZIP-Datei in die passende Repository-Struktur.'''
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            addon_xml_name, xml_text = find_zip_addon_xml(zf)
            addon_id, version = parse_addon_xml(xml_text, str(zip_path))
            addon_dir = ROOT / addon_id
            addon_dir.mkdir(parents=True, exist_ok=True)
            target_zip = addon_dir / f'{addon_id}-{version}.zip'
            if zip_path.resolve() != target_zip.resolve():
                shutil.copy2(zip_path, target_zip)
            (addon_dir / 'addon.xml').write_text(xml_text.strip() + '\n', encoding='utf-8', newline='\n')
            marker_source = zip_path.relative_to(ROOT) if zip_path.is_relative_to(ROOT) else zip_path
            (addon_dir / '.kodiwulf-imported').write_text(f'Imported from {marker_source}\n', encoding='utf-8', newline='\n')
            copy_asset_candidates(zf, addon_xml_name, addon_dir)
            log('OK', f'Imported {zip_path.relative_to(ROOT) if zip_path.is_relative_to(ROOT) else zip_path} -> {target_zip.relative_to(ROOT)}')
            return addon_id, version
    except Exception as exc:
        log('WARN', f'Skipped ZIP {zip_path}: {exc}')
        return None


def scan_zip_packages() -> list[Path]:
    '''Findet lokale ZIP-Dateien, die importiert werden können.'''
    found: list[Path] = []
    for scan_dir in ZIP_SCAN_DIRS:
        if scan_dir.is_dir():
            found.extend(path for path in scan_dir.glob('*.zip') if path.is_file())
    for child in ROOT.iterdir():
        if child.is_dir() and child.name not in EXCLUDED_DIRS:
            found.extend(path for path in child.glob('*.zip') if path.is_file())
    return sorted(set(found))


def addon_directories() -> list[Path]:
    '''Findet alle Add-on-Verzeichnisse auf Root-Ebene.'''
    dirs: list[Path] = []
    for child in sorted(ROOT.iterdir()):
        if not child.is_dir() or child.name in EXCLUDED_DIRS:
            continue
        if (child / 'addon.xml').is_file():
            dirs.append(child)
    return dirs


def should_build_zip_from_source(addon_dir: Path) -> bool:
    '''Entscheidet, ob aus einem Add-on-Ordner eine ZIP-Datei gebaut werden soll.'''
    return (addon_dir / 'addon.xml').is_file() and not (addon_dir / '.kodiwulf-imported').exists()


def create_addon_zip(addon_dir: Path) -> Path:
    '''Erzeugt eine versionierte ZIP-Datei für ein Quell-Add-on.'''
    addon_id, version = addon_id_and_version(addon_dir / 'addon.xml')
    zip_path = addon_dir / f'{addon_id}-{version}.zip'
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(addon_dir.rglob('*')):
            if path == zip_path or path.name.endswith('.zip'):
                continue
            if path.name in GENERATED_WEB_FILES or path.name in GENERATED_MARKERS:
                continue
            if path.name.endswith('.bak') or '.bak.' in path.name or '__pycache__' in path.parts:
                continue
            if path.is_file():
                zf.write(path, path.relative_to(ROOT).as_posix())
    return zip_path


def write_addons_xml(addons: list[Path]) -> Path:
    '''Schreibt die zentrale addons.xml aus allen gefundenen addon.xml-Dateien.'''
    blocks = [strip_xml_declaration(read_text(addon_dir / 'addon.xml')) for addon_dir in addons]
    output = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<addons>\n' + '\n\n'.join(blocks) + '\n</addons>\n'
    addons_xml = ROOT / 'addons.xml'
    addons_xml.write_text(output, encoding='utf-8', newline='\n')
    return addons_xml


def write_md5(path: Path) -> Path:
    '''Schreibt die MD5-Checksumme der addons.xml im Kodi-kompatiblen Format.'''
    digest = hashlib.md5(path.read_bytes()).hexdigest()
    md5_path = ROOT / 'addons.xml.md5'
    md5_path.write_text(digest, encoding='utf-8', newline='\n')
    return md5_path


def relative_url(path: Path) -> str:
    '''Erzeugt eine relative URL für eine Datei innerhalb des Repositories.'''
    return path.relative_to(ROOT).as_posix()


def write_addon_index(addon_dir: Path) -> Path:
    '''Erzeugt eine statische index.html für einen Add-on-Ordner.'''
    addon_id = addon_dir.name
    files = [path for path in sorted(addon_dir.iterdir()) if path.is_file() and not path.name.startswith('.')]
    rows = []
    for path in files:
        rows.append(f'<tr><td><a href="{html.escape(path.name)}">{html.escape(path.name)}</a></td><td>{path.stat().st_size}</td></tr>')
    if not rows:
        rows.append('<tr><td colspan="2">Noch keine Dateien vorhanden.</td></tr>')
    content = f'''<!doctype html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Index of /{html.escape(addon_id)}/</title><style>body{{background:#0b0b0f;color:#e8e8ee;font-family:system-ui,sans-serif;margin:2rem}}a{{color:#8be9fd;text-decoration:none}}a:hover{{text-decoration:underline}}table{{border-collapse:collapse;min-width:min(760px,100%)}}th,td{{border-bottom:1px solid #30303a;padding:.55rem .75rem;text-align:left}}.muted{{color:#a4a4b3}}</style></head>
<body><h1>Index of /{html.escape(addon_id)}/</h1><p><a href="../">Parent Directory</a></p><table><thead><tr><th>Name</th><th>Size bytes</th></tr></thead><tbody>{''.join(rows)}</tbody></table><p class="muted">Generated by tools/build_repo.py.</p></body></html>
'''
    index_path = addon_dir / 'index.html'
    index_path.write_text(content, encoding='utf-8', newline='\n')
    return index_path


def write_root_index(addons: list[Path]) -> Path:
    '''Erzeugt eine statische Startseite für GitHub Pages.'''
    generated_at = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    rows = []
    for addon_dir in addons:
        addon_id, version = addon_id_and_version(addon_dir / 'addon.xml')
        zip_files = sorted(addon_dir.glob(f'{addon_id}-*.zip'))
        zip_links = ', '.join(f'<a href="{html.escape(relative_url(path))}">{html.escape(path.name)}</a>' for path in zip_files) or '<span class="missing">ZIP fehlt</span>'
        rows.append(f'<tr><td><a href="{html.escape(addon_id)}/">{html.escape(addon_id)}</a></td><td>{html.escape(version)}</td><td>{zip_links}</td></tr>')
    for expected in EXPECTED_ADDONS:
        if not any(path.name == expected for path in addons):
            rows.append(f'<tr><td>{html.escape(expected)}</td><td><span class="missing">noch nicht importiert</span></td><td><span class="missing">ZIP fehlt</span></td></tr>')
    content = f'''<!doctype html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>KodiWulf Repository</title><style>body{{background:#09090d;color:#ededf4;font-family:system-ui,sans-serif;margin:2rem;line-height:1.5}}a{{color:#8be9fd;text-decoration:none}}a:hover{{text-decoration:underline}}code{{background:#181820;padding:.15rem .35rem;border-radius:.25rem}}table{{border-collapse:collapse;width:min(1100px,100%);margin-top:1rem}}th,td{{border-bottom:1px solid #30303a;padding:.6rem .8rem;text-align:left;vertical-align:top}}.box{{border:1px solid #30303a;border-radius:.75rem;padding:1rem;background:#111118;max-width:1100px}}.missing{{color:#ffb86c}}.muted{{color:#a4a4b3}}</style></head>
<body><h1>KodiWulf Repository</h1><div class="box"><p>Kodi Repository Root für KodiWulf Add-ons.</p><p>Kodi Repository XML: <a href="addons.xml">addons.xml</a></p><p>Kodi Checksumme: <a href="addons.xml.md5">addons.xml.md5</a></p><p>Repository Add-on: <a href="repository.kodiwulf/">repository.kodiwulf/</a></p></div>
<h2>Add-ons</h2><table><thead><tr><th>Add-on</th><th>Version</th><th>ZIP</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
<h2>Kodi URLs</h2><pre><code>{html.escape(PUBLIC_BASE_URL)}/addons.xml\n{html.escape(PUBLIC_BASE_URL)}/addons.xml.md5\n{html.escape(PUBLIC_BASE_URL)}/repository.kodiwulf/</code></pre><p class="muted">Generated: {generated_at}</p></body></html>
'''
    index_path = ROOT / 'index.html'
    index_path.write_text(content, encoding='utf-8', newline='\n')
    return index_path


def validate_expected_addons(addons: list[Path]) -> None:
    '''Warnt, wenn erwartete Add-ons noch nicht im Repository gefunden wurden.'''
    present = {path.name for path in addons}
    for addon_id in EXPECTED_ADDONS:
        if addon_id not in present:
            log('WARN', f'Expected add-on missing until ZIP/source is added: {addon_id}')


def main() -> int:
    '''Baut Repository-Index, Web-Index und Add-on-ZIP-Dateien.'''
    log('INFO', f'Repository root: {ROOT}')
    for zip_path in scan_zip_packages():
        import_zip_package(zip_path)
    addons = addon_directories()
    if not addons:
        log('ERROR', 'No add-on directories with addon.xml found.')
        return 1
    for addon_dir in addons:
        if should_build_zip_from_source(addon_dir):
            zip_path = create_addon_zip(addon_dir)
            log('OK', f'Built {zip_path.relative_to(ROOT)}')
        else:
            log('INFO', f'Using imported ZIP package for {addon_dir.name}')
    addons = addon_directories()
    validate_expected_addons(addons)
    for addon_dir in addons:
        index_path = write_addon_index(addon_dir)
        log('OK', f'Wrote {index_path.relative_to(ROOT)}')
    root_index = write_root_index(addons)
    addons_xml = write_addons_xml(addons)
    md5_path = write_md5(addons_xml)
    log('OK', f'Wrote {root_index.relative_to(ROOT)}')
    log('OK', f'Wrote {addons_xml.relative_to(ROOT)}')
    log('OK', f'Wrote {md5_path.relative_to(ROOT)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
