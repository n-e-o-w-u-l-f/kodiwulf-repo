# # # # # # # # # # # # # # # # # #
# KODIWULF UPDATE PROCESS #
# # # # # # # # # # # # # # # # # #

## 1. Add or update an add-on

Place every Kodi add-on in its own folder at the repository root, for example:

```text
plugin.video.example/
repository.kodiwulf/
```

Each add-on folder must contain a valid `addon.xml`.

## 2. Rebuild repository files

Run:

```bash
python3 tools/build_repo.py
```

This updates:

```text
addons.xml
addons.xml.md5
repository.kodiwulf/repository.kodiwulf-<version>.zip
```

## 3. Commit and push

```bash
git add .
git commit -m "chore(repo): rebuild Kodi repository index"
git push
```

## 4. Enable GitHub Pages

In GitHub:

```text
Settings → Pages → Deploy from a branch → main → / root
```

After publishing, the repository XML should be available at:

```text
https://n-e-o-w-u-l-f.github.io/kodiwulf-repo/addons.xml
```
