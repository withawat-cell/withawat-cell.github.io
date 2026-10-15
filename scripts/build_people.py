"""Regenerate the people cards on Researchers, Alumni and Visitors from
content-raw/people-researchers.md, people-alumni.md and people-visitors.md.

Only the part of each page between <!-- PEOPLE:START --> and <!-- PEOPLE:END -->
is replaced; the intro, team photos and so on stay hand-written in the .html.
"""
import os
import re

import peopledata

ROOT = peopledata.ROOT

PAGES = [
    ("people/researchers.html", "people-researchers.md"),
    ("people/alumni.html", "people-alumni.md"),
    ("people/visitors.html", "people-visitors.md"),
]

REGION_RE = re.compile(r"  <!-- PEOPLE:START -->.*?<!-- PEOPLE:END -->", re.S)

for html_path, md_name in PAGES:
    page = peopledata.read_people(md_name)
    path = os.path.join(ROOT, html_path.replace("/", os.sep))
    with open(path, encoding="utf-8") as f:
        text = f.read()
    new_region = "  <!-- PEOPLE:START -->\n" + peopledata.sections_html(page) + "\n  <!-- PEOPLE:END -->"
    new_text, n = REGION_RE.subn(lambda m: new_region, text, count=1)
    if n != 1:
        raise SystemExit(f"{html_path}: <!-- PEOPLE:START --> ... <!-- PEOPLE:END --> markers not found")
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_text)
    count = sum(len(s["people"]) for s in page["sections"])
    print(f"Wrote {html_path} - {len(page['sections'])} sections, {count} people")
