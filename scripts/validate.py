"""Check the data files and the built site for mistakes. Run by build_all.py last.

Errors (exit code 1) are things that would break or mislead the site: a thumbnail
or PDF that doesn't exist, a link to a missing page, a badly shaped table row.
Warnings are worth a look but don't fail the build.

External URLs are not fetched here; run scripts/check_links.py for those.
"""
import os
import re
import sys

import carddata
import peopledata
import pubdata
import shell

ROOT = pubdata.ROOT
errors, warnings = [], []


def err(msg):
    errors.append(msg)


def warn(msg):
    warnings.append(msg)


_listing = {}


def exact_exists(rel_parts, want_file=False):
    """Does this path exist with EXACTLY this upper/lower case? Windows ignores case but the
    live site (Linux) does not, so a reference like Photo.webp to photo.webp must be an error."""
    path = ROOT
    for part in rel_parts:
        if path not in _listing:
            _listing[path] = set(os.listdir(path)) if os.path.isdir(path) else set()
        if part not in _listing[path]:
            return False
        path = os.path.join(path, part)
    return os.path.isfile(path) if want_file else os.path.exists(path)


def exists(rel):
    return exact_exists([p for p in rel.strip("/").split("/") if p])


def site_has(url_path):
    """True if a root-relative URL path resolves the way GitHub Pages serves it."""
    parts = [p for p in url_path.strip("/").split("/") if p]
    if not parts:
        return True
    return (
        exact_exists(parts, want_file=True)
        or exact_exists(parts + ["index.html"], want_file=True)
        or exact_exists(parts[:-1] + [parts[-1] + ".html"], want_file=True)
    )



# ---------------------------------------------------------------- publications
journal_dois = set()
for year, rows in pubdata.read_tables("publications-journal-articles.md"):
    for r in rows:
        label = f"journal {year}: {r['citation'][:50]}..."
        if not r["citation"]:
            err(f"journal {year}: a row has no citation")
        m = re.search(r"\b((?:19|20)\d{2})\.?(?:\s*\([^)]*\))?\s*$", r["citation"])
        if not m or m.group(1) != year:
            warn(f"{label} the citation's year doesn't match its '## {year}' section")
        if not r["doi"]:
            warn(f"{label} has no DOI / Link yet, so the title isn't a link")
        elif not r["doi"].startswith("http"):
            err(f"{label} DOI / Link must start with http")
        elif r["doi"] in journal_dois:
            err(f"{label} DOI / Link {r['doi']} appears twice")
        journal_dois.add(r["doi"])
        if r["image"] and not exists("assets/img/publications/" + r["image"]):
            err(f"{label} Image file assets/img/publications/{r['image']} does not exist")
        for topic in [t.strip() for t in r["topics"].split(",") if t.strip()]:
            if topic not in dict(pubdata.TOPIC_LABELS):
                err(f"{label} unknown topic {topic!r} (allowed: {', '.join(dict(pubdata.TOPIC_LABELS))})")
        if not r["topics"]:
            warn(f"{label} has no Topics, so it only shows under 'All'")

for year, rows in pubdata.read_tables("publications-conference-presentations.md"):
    for r in rows:
        if not r["citation"]:
            err(f"conference {year}: a row has no citation")
        m = re.search(r"\b((?:19|20)\d{2})\.?\s*$", r["citation"])
        if not m or m.group(1) != year:
            warn(f"conference {year}: the citation's year doesn't match its section: ...{r['citation'][-40:]}")

for row in pubdata.read_flat_table("publications-theses.md"):
    if not re.fullmatch(r"(19|20)\d{2}", row["year"]):
        err(f"theses: bad year {row['year']!r} for {row['author']}")
    if row["file"] and not exists("assets/theses/" + row["file"]):
        err(f"theses: file assets/theses/{row['file']} does not exist ({row['author']})")

# ---------------------------------------------------------------- people
for md in ("people-researchers.md", "people-alumni.md", "people-visitors.md"):
    page = peopledata.read_people(md)
    for section in page["sections"]:
        for p in section["people"]:
            where = f"{md}: {p['name']}"
            if not exists("assets/img/people/" + p["photo"]):
                err(f"{where}: photo assets/img/people/{p['photo']} does not exist")
            for key in ("profile", "scholar", "linkedin"):
                if p.get(key) and not p[key].startswith("http"):
                    err(f"{where}: {key.title()} must be a full https:// address")
            if p.get("email") and "@" not in p["email"]:
                err(f"{where}: Email should be an address like name@adelaide.edu.au")
            for kind, value in p["lines"]:
                for label, url in peopledata.LINK_RE.findall(value):
                    if url.startswith("/") and not url.startswith("//"):
                        if not site_has(url.split("#")[0].split("?")[0]):
                            err(f"{where}: link {label!r} points to {url}, which doesn't exist")
                    elif not url.startswith("http"):
                        err(f"{where}: link {label!r} has a strange address {url!r}")

for year, rows in peopledata.coursework_rows():
    for name, yrs, area, awards, notes in rows:
        if not name:
            err(f"coursework {year}: a row has no name")
        for cell in (awards, notes):
            for label, url in peopledata.LINK_RE.findall(cell):
                if url.startswith("/") and not url.startswith("//"):
                    if not site_has(url.split("#")[0].split("?")[0]):
                        err(f"coursework {year}: {name}: link {label!r} points to {url}, which doesn't exist")
                elif not url.startswith("http"):
                    err(f"coursework {year}: {name}: link {label!r} has a strange address {url!r}")

# ---------------------------------------------------------------- research page and home logos
for filename, fields, required in (
    ("research-clusters.md", ("image", "alt", "text", "tags"), ("image", "alt", "text")),
    ("research-gallery.md", ("image", "alt"), ("image", "alt")),
):
    for section in carddata.read_cards(filename, fields, required):
        for c in section["cards"]:
            if not exists("assets/img/research/" + c["image"]):
                err(f"{filename}: {c['title']}: image assets/img/research/{c['image']} does not exist")

for group, rows in pubdata.read_logo_groups().items():
    for r in rows:
        if not exists("assets/img/logos/" + r["logo"]):
            err(f"home-logos.md: {r['name']}: logo assets/img/logos/{r['logo']} does not exist")
        if not r["link"].startswith("http"):
            err(f"home-logos.md: {r['name']}: Link must start with http")

# ---------------------------------------------------------------- image sizes
IMAGE_WARN_KB = 150
for dirpath, _dirs, files in os.walk(os.path.join(ROOT, "assets", "img")):
    for name in files:
        if name.lower().endswith((".webp", ".png", ".jpg", ".jpeg", ".gif")):
            full = os.path.join(dirpath, name)
            kb = os.path.getsize(full) / 1024
            if kb > IMAGE_WARN_KB:
                warn(f"{os.path.relpath(full, ROOT).replace(os.sep, '/')} is {kb:.0f} KB; "
                     f"consider shrinking it (scripts/add_image.py --width ... --quality ...)")

# ---------------------------------------------------------------- site config
import json
with open(os.path.join(ROOT, "content-raw", "site-config.json"), encoding="utf-8") as f:
    config = json.load(f)
for code, name in config["coauthor_countries"]:
    if not re.fullmatch(r"[a-z]{2}", code):
        err(f"site-config.json: bad country code {code!r} for {name}")

# ---------------------------------------------------------------- built pages
LINK_ATTR_RE = re.compile(r'(?:href|src)="(/[^"#?]*)')


page_paths = shell.page_files()
for path in page_paths:
    rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
    with open(path, encoding="utf-8") as f:
        text = f.read()
    if text.count('<header class="site-header">') != 1 or text.count('<footer class="site-footer">') != 1:
        err(f"{rel}: expected exactly one site header and footer (run build_all.py)")
    if "PEOPLE:START" in text and text.count("PEOPLE:START") != 1:
        err(f"{rel}: more than one PEOPLE:START marker")
    for target in sorted(set(LINK_ATTR_RE.findall(text))):
        if target.startswith("//"):
            continue
        if not site_has(target):
            err(f"{rel}: links to {target}, which doesn't exist")
    if re.search(r"\?v=x\b", text):
        err(f"{rel}: has a placeholder ?v=x (run stamp_pages.py)")

for rel, markers in {
    "index.html": ["STATS:START", "STATS:END", "LOGOS:association:START", "LOGOS:association:END", "LOGOS:patrons:START", "LOGOS:patrons:END"],
    "publications/phd-theses.html": ["STATS:START", "STATS:END"],
    "people/visitors.html": ["STATS:START", "STATS:END", "PEOPLE:START", "PEOPLE:END"],
    "people/researchers.html": ["PEOPLE:START", "PEOPLE:END"],
    "research.html": ["CLUSTERS:START", "CLUSTERS:END", "GALLERY:START", "GALLERY:END"],
    "people/alumni.html": ["PEOPLE:START", "PEOPLE:END"],
}.items():
    with open(os.path.join(ROOT, rel.replace("/", os.sep)), encoding="utf-8") as f:
        text = f.read()
    for m in markers:
        if text.count(m) != 1:
            err(f"{rel}: marker {m} should appear exactly once")

# sitemap lists every page
with open(os.path.join(ROOT, "sitemap.xml"), encoding="utf-8") as f:
    sitemap = f.read()
for path in page_paths:
    rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
    url = "https://thz-el.org/" + ("" if rel == "index.html" else rel)
    if f"<loc>{url}</loc>" not in sitemap:
        warn(f"sitemap.xml does not list {url}")

# ---------------------------------------------------------------- report
for w in warnings:
    print("warning:", w)
for e in errors:
    print("ERROR:  ", e)
print(f"Validation: {len(errors)} error(s), {len(warnings)} warning(s), {len(page_paths)} pages checked")
sys.exit(1 if errors else 0)
