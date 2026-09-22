"""Generate static redirect stubs for the old Google Sites URL structure.

thz-el.org used to be mapped to a Google Site (sites.google.com/view/thzel),
whose pages live at extension-less paths like /home, /research,
/publications/journal-articles, /people/researchers, etc. Search engines and
old bookmarks/links may still point at those paths, so each one gets a small
static page here that immediately redirects to its equivalent on the new
site, at the same path but as a directory (so it doesn't collide with the
real static/generated file of the same name plus ".html").
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (legacy path under sites.google.com/view/thzel/, target path on the new site)
MAPPING = [
    ("home", "/index.html"),
    ("research", "/research.html"),
    ("opportunities", "/opportunities.html"),
    ("contact", "/contact.html"),
    ("publications/journal-articles", "/publications/journal-articles.html"),
    ("publications/conference-presentations", "/publications/conference-presentations.html"),
    ("publications/phd-theses", "/publications/phd-theses.html"),
    ("publications/codes", "/publications/codes.html"),
    ("people/researchers", "/people/researchers.html"),
    ("people/alumni", "/people/alumni.html"),
    ("people/coursework", "/people/coursework.html"),
    ("people/visitors", "/people/visitors.html"),
]

TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="0; url={target}">
<link rel="canonical" href="https://thz-el.org{target}">
<title>Terahertz Engineering Laboratory</title>
</head>
<body>
<p>This page has moved to <a href="{target}">{target}</a>.</p>
</body>
</html>
"""

for legacy_path, target in MAPPING:
    out_dir = os.path.join(ROOT, legacy_path)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(TEMPLATE.format(target=target))

print(f"Wrote {len(MAPPING)} legacy redirect stubs")
