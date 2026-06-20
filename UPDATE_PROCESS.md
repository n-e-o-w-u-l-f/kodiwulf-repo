# # # # # # # # # # # # # # #
# KodiWulf Update Process
# # # # # # # # # # # # # # #

## 1. Place source ZIPs locally

Source ZIPs are local build inputs and should not be committed.

    ZIPs/VIDEO/
    ZIPs/PROGRAMM/
    ZIPs/REPOSITORY/

## 2. Rebuild

    python3 tools/kodiwulf_build_repo.py --base-url "https://n-e-o-w-u-l-f.github.io/kodiwulf-repo/" --apply

## 3. Validate

Run:

    python3 -m py_compile tools/kodiwulf_build_repo.py tools/kodiwulf_addons_xml.py tools/kodiwulf_dark_index.py

Expected repository metadata:

    Add-ons: 18
    repository.kodiwulf 0.1.0: present
    addons.xml.md5: matches addons.xml

## 4. Commit and push

    git add -A -- .
    git commit -m "fix(repo): update KodiWulf docs"
    git push origin main

## 5. Online checks

    curl -L -I "https://n-e-o-w-u-l-f.github.io/kodiwulf-repo/"
    curl -L -I "https://n-e-o-w-u-l-f.github.io/kodiwulf-repo/addons.xml"
    curl -L -I "https://n-e-o-w-u-l-f.github.io/kodiwulf-repo/addons.xml.md5"
    curl -L -I "https://n-e-o-w-u-l-f.github.io/kodiwulf-repo/Repository/repository.kodiwulf-0.1.0.zip"
