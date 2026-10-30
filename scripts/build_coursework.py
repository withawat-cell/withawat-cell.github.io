import re
import os
import html

import shell
from peopledata import coursework_rows, split_items
from textutil import md_inline

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "content-raw", "people-coursework.md")
OUT = os.path.join(ROOT, "people", "coursework.html")

year_blocks = coursework_rows()

def format_notes(awards, notes):
    """Award items become gold chips, Notes items plain text; all separated by bullets."""
    out = [f'<span class="tag-note">{md_inline(c)}</span>' for c in split_items(awards)]
    out += [md_inline(c) for c in split_items(notes)]
    return ' <span class="note-sep">&bull;</span> '.join(out)

DOI_RE = re.compile(r"https://doi\.org/\S+?(?=[\s)\]]|$)")

PHOTO_DIR = os.path.join(ROOT, "assets", "img", "people", "coursework")

def slug(name):
    s = name.lower()
    s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = s.strip()
    s = re.sub(r"\s+", "-", s)
    return s

sections = []
total = 0
ieee_award_count = 0
doi_set = set()
for year, rows in year_blocks:
    trs = []
    photos = []
    for name, yrs, area, awards, notes in rows:
        total += 1
        # "First author" items are journal-paper mentions (styled the same
        # as awards), not actual IEEE awards, so they're excluded here even
        # though the journal's own name happens to contain "IEEE"
        for item in split_items(awards):
            if "IEEE" in item and "First author" not in item:
                ieee_award_count += 1
        doi_set.update(DOI_RE.findall(awards + " " + notes))
        prize = "First Prize" in awards or "1st Prize" in awards
        tr_cls = ' class="prize-row"' if prize else ""
        trs.append(f"          <tr{tr_cls}><td>{md_inline(name)}</td><td>{html.escape(yrs)}</td><td>{html.escape(area)}</td><td class=\"small\">{format_notes(awards, notes)}</td></tr>")
        photo_slug = slug(name)
        if os.path.exists(os.path.join(PHOTO_DIR, f"{photo_slug}.webp")):
            photos.append(f'''          <div class="coursework-photo-wrap">
            <img class="coursework-photo" src="/assets/img/people/coursework/{photo_slug}.webp?v=x" alt="{html.escape(name)}" title="{html.escape(name)}" loading="lazy">
            <span class="coursework-photo-name">{html.escape(name)}</span>
          </div>''')
    photos_html = ""
    if photos:
        photos_html = f'''
      <div class="coursework-photos">
{chr(10).join(photos)}
      </div>'''
    sections.append(f'''      <h3 class="year-heading">{year}</h3>
      <div class="table-scroll">
      <table class="data cols-4 stack-sm">
        <colgroup><col class="c1"><col class="c2"><col class="c3"><col class="c4"></colgroup>
        <thead><tr><th>Name</th><th>Year(s)</th><th>Area</th><th>Notes</th></tr></thead>
        <tbody>
{chr(10).join(trs)}
        </tbody>
      </table>
      </div>{photos_html}''')

body = "\n\n".join(sections)

template = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Cache-Control" content="no-cache">
<title>Coursework Students | Terahertz Engineering Laboratory</title>
<meta name="description" content="Honours, master's, and undergraduate research students at the Terahertz Engineering Laboratory, Adelaide University.">
<link rel="canonical" href="https://thz-el.org/people/coursework.html">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Terahertz Engineering Laboratory">
<meta property="og:title" content="Coursework Students | Terahertz Engineering Laboratory">
<meta property="og:description" content="Honours, master's, and undergraduate research students at the Terahertz Engineering Laboratory, Adelaide University.">
<meta property="og:url" content="https://thz-el.org/people/coursework.html">
<meta property="og:image" content="https://thz-el.org/assets/img/group-photo-1.webp">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/assets/img/brand/favicon.png" type="image/png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<link rel="preload" as="image" href="/assets/img/brand/header-bg.webp?v=x">
<link rel="stylesheet" href="/assets/css/style.css?v=x">
</head>
<body>

<header class="site-header"></header>

<main>

  <section class="page-hero">
    <div class="wrap-wide">
      <p class="hero-eyebrow">People</p>
      <h1>Coursework students</h1>
      <p class="lead">Honours, master's, and undergraduate research students who have contributed to the laboratory's projects, grouped by year.</p>
      <div class="stats-row">
        <div class="stat">
          <span class="stat-num">{total}</span>
          <span class="stat-label">Coursework Students</span>
        </div>
        <div class="stat">
          <span class="stat-num">{ieee_awards}</span>
          <span class="stat-label">IEEE AP/MTT Grants</span>
        </div>
        <div class="stat">
          <span class="stat-num">{first_author_papers}</span>
          <span class="stat-label">First-Author<br>Journal Articles</span>
        </div>
      </div>
    </div>
  </section>

  <section class="block">
    <div class="wrap-wide">
{body}
    </div>
  </section>

</main>

<footer class="site-footer"></footer>

<script src="/assets/js/main.js?v=x"></script>
</body>
</html>
"""

page = (
    template.replace("{body}", body)
    .replace("{total}", str(total))
    .replace("{ieee_awards}", str(ieee_award_count))
    .replace("{first_author_papers}", str(len(doi_set)))
)
with open(OUT, "w", encoding="utf-8", newline="\n") as f:
    f.write(shell.stamp_html(page, "people/coursework.html"))

print("Wrote", OUT, "-", len(year_blocks), "year sections,", total, "students,",
      ieee_award_count, "IEEE awards,", len(doi_set), "first-author journal articles")
