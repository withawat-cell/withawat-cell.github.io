"""Regenerate the partner and patron logo rows on index.html from content-raw/home-logos.md.

The file has two tables, under "## association" and "## patrons":

    | Name | Link | Logo |
    |---|---|---|
    | Australian Research Council | https://www.arc.gov.au/ | arc.svg |

Name is used for the hover title and the alt text; Logo is a file in assets/img/logos/.
Only the parts between the LOGOS markers in index.html are replaced.
"""
import html
import os
import re

from pubdata import ROOT, read_logo_groups

PAGE = os.path.join(ROOT, "index.html")


def logo_html(row):
    name = html.escape(row["name"], quote=True)
    return (
        f'        <a href="{html.escape(row["link"], quote=True)}" title="{name}">'
        f'<img src="/assets/img/logos/{html.escape(row["logo"], quote=True)}" alt="{name}" loading="lazy"></a>'
    )


with open(PAGE, encoding="utf-8") as f:
    text = f.read()
groups = read_logo_groups()
for name, rows in groups.items():
    pattern = re.compile(rf"        <!-- LOGOS:{name}:START -->.*?<!-- LOGOS:{name}:END -->", re.S)
    new = f"        <!-- LOGOS:{name}:START -->\n" + "\n".join(logo_html(r) for r in rows) + f"\n        <!-- LOGOS:{name}:END -->"
    text, n = pattern.subn(lambda m: new, text, count=1)
    if n != 1:
        raise SystemExit(f"index.html: <!-- LOGOS:{name}:START --> ... <!-- LOGOS:{name}:END --> markers not found")
with open(PAGE, "w", encoding="utf-8", newline="\n") as f:
    f.write(text)
print(f"Wrote index.html logos - {len(groups['association'])} associations, {len(groups['patrons'])} patrons")
