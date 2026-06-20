![KodiWulf Repository Banner](bg.png)

# # # # # # # # # # # # #
# KodiWulf Repository
# # # # # # # # # # # # #

KodiWulf is a static Kodi 21 Omega repository served through GitHub Pages.

## Public URL

    https://n-e-o-w-u-l-f.github.io/kodiwulf-repo/

## Install from ZIP

Use this ZIP in Kodi:

    https://n-e-o-w-u-l-f.github.io/kodiwulf-repo/Repository/repository.kodiwulf-0.1.0.zip

After installation, Kodi reads:

    https://n-e-o-w-u-l-f.github.io/kodiwulf-repo/addons.xml
    https://n-e-o-w-u-l-f.github.io/kodiwulf-repo/addons.xml.md5

## Current repository state

    repository.kodiwulf 0.1.0
    Kodi target: Kodi 21 Omega
    Add-ons in addons.xml: 18

## Public folders

    Program/       Browser-friendly program add-on ZIPs
    Repository/    Browser-friendly repository ZIPs
    Videos/        Browser-friendly video add-on ZIPs
    <addon.id>/    Canonical Kodi repository folders
    addons.xml     Kodi repository metadata
    addons.xml.md5 Kodi repository checksum
    index.html     GitHub Pages landing page

## Local source ZIP layout

Source ZIPs are local build inputs and are ignored by Git:

    ZIPs/VIDEO/
    ZIPs/PROGRAMM/
    ZIPs/REPOSITORY/

## Rebuild

    python3 tools/kodiwulf_build_repo.py --base-url "https://n-e-o-w-u-l-f.github.io/kodiwulf-repo/" --apply

The active generator also runs:

    tools/kodiwulf_addons_xml.py
    tools/kodiwulf_dark_index.py

Only install Kodi add-ons and repositories you trust.
