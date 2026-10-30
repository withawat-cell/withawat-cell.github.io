"""Copy only the files that belong on the live website into a folder (default: _site).

The repository keeps everything (scripts, content-raw data, README, workflows) as
your backup, but visitors only need the pages and their assets. The GitHub deploy
publishes this folder instead of the whole repo, so addresses like
thz-el.org/content-raw/... or thz-el.org/scripts/... no longer exist.

Usage: python scripts/stage_site.py [folder]
"""
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# directories that are part of the site, copied whole
SITE_DIRS = ["assets", "people", "publications", "home"]
# single files at the top level that are part of the site
SITE_FILE_SUFFIXES = (".html",)
SITE_FILES = ["CNAME", "robots.txt", "sitemap.xml", ".nojekyll"]


def stage(dest):
    dest = os.path.abspath(dest)
    root = os.path.abspath(ROOT)
    if dest == root or root.startswith(dest + os.sep):
        raise SystemExit("Refusing to stage into the project folder or a folder above it (it is emptied first)")
    if os.path.exists(dest):
        shutil.rmtree(dest)
    os.makedirs(dest)
    copied = 0
    for name in sorted(os.listdir(ROOT)):
        src = os.path.join(ROOT, name)
        if os.path.isdir(src) and name in SITE_DIRS:
            shutil.copytree(src, os.path.join(dest, name), ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            copied += sum(len(files) for _, _, files in os.walk(os.path.join(dest, name)))
        elif os.path.isfile(src) and (name.endswith(SITE_FILE_SUFFIXES) or name in SITE_FILES):
            shutil.copy2(src, os.path.join(dest, name))
            copied += 1
    return dest, copied


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "_site")
    out, n = stage(target)
    print(f"Staged {n} site files into {out}")
