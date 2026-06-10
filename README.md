<p align="center">
  <img src="./bg.png" alt="KodiWulf Repository Banner" width="100%">
</p>

# # # # # # # # # # # # # #
# KodiWulf Repository #
# # # # # # # # # # # # # #

KodiWulf repository skeleton for Kodi add-ons, modeled after a classic web-served Kodi repository layout.

## Correct GitHub Pages URL

This is a project page, so the public URL is:

```text
https://n-e-o-w-u-l-f.github.io/kodiwulf-repo/
```

Not:

```text
https://kodiwulf-repo.github.io/
```

## Kodi repository URLs

```text
https://n-e-o-w-u-l-f.github.io/kodiwulf-repo/addons.xml
https://n-e-o-w-u-l-f.github.io/kodiwulf-repo/addons.xml.md5
https://n-e-o-w-u-l-f.github.io/kodiwulf-repo/repository.kodiwulf/repository.kodiwulf-0.0.2.zip
```

## Expected add-ons

```text
plugin.video.vavooto/
plugin.video.xwulf/
repository.kodinerds/
repository.michaz/
repository.kodiwulf/
```

Kodi expects package ZIP files in this pattern:

```text
addon.id/addon.id-version.zip
```

Example:

```text
plugin.video.xwulf/plugin.video.xwulf-10.06.2026.zip
repository.michaz/repository.michaz-5.0.zip
```

## Local ZIP import

Put your ZIP files either in the repository root, in `zips/`, or directly inside their add-on folder.

Then run:

```bash
python3 tools/build_repo.py
```

The builder will inspect ZIP files, extract `addon.xml`, place each ZIP into the correct `addon.id/` folder, rebuild `addons.xml` and generate static `index.html` pages for GitHub Pages.

## GitHub Pages

Enable:

```text
Settings → Pages → Deploy from a branch → main → / root
```

The root `index.html` exists so the website is visible in a browser. The `.nojekyll` file disables Jekyll processing for this static repository layout.
