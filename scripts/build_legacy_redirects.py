"""Generate static redirect stubs for the old Google Sites URL structure.

thz-el.org used to be mapped to a Google Site (sites.google.com/view/thzel),
whose pages live at extension-less paths like /home, /research,
/publications/journal-articles, /people/researchers, etc. GitHub Pages
already serves a clean path like /research directly from research.html with
no redirect (confirmed for every legacy path except one), so a stub is only
needed where no equivalently-named .html file exists at the new site's
root -- which is just the landing page (home.html has no equivalent; the
new site's landing page is index.html).
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (legacy path under sites.google.com/view/thzel/, target path on the new site)
MAPPING = [
    ("home", "/index.html"),
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
