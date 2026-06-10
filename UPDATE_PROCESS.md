# # # # # # # # # # # # # # # # # #
# KODIWULF UPDATE PROCESS #
# # # # # # # # # # # # # # # # # #

## 1. Richtigen lokalen Repository-Pfad verwenden

```text
/home/deck/Projekte/n-e-o-w-u-l-f/kodiwulf-repo/
```

## 2. Add-on-ZIP-Dateien lokal ablegen

```text
kodiwulf-repo/
kodiwulf-repo/zips/
kodiwulf-repo/plugin.video.xwulf/
kodiwulf-repo/plugin.video.vavooto/
kodiwulf-repo/repository.kodinerds/
kodiwulf-repo/repository.michaz/
```

## 3. Repository lokal bauen

```bash
python3 tools/build_repo.py
```

## 4. Sicher committen und pushen

Für interaktive Terminals keine Rohblöcke mit `exit 1` oder `set -e` verwenden. Nutze eine Kind-Shell und Statusvariablen.

## 5. GitHub Pages aktivieren

```text
Settings → Pages → Deploy from a branch → main → / root
```

Projekt-URL:

```text
https://n-e-o-w-u-l-f.github.io/kodiwulf-repo/
```
