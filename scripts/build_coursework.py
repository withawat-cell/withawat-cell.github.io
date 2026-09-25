import re
import os
import html

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "content-raw", "people-coursework.md")
OUT = os.path.join(ROOT, "people", "coursework.html")

with open(SRC, "r", encoding="utf-8") as f:
    text = f.read()

year_blocks = re.findall(r"^## (\d{4})\n\|(.*?)\n\n", text, re.S | re.M)

def md_inline(s):
    s = s.strip()
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
    s = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", s)
    return s

# internal cross-reference notes (left over from this project's own research
# notes) should point at the real page, not at another content-raw filename
CROSS_REFS = {
    "publications-codes.md": ("/publications/codes.html", "Codes"),
    "people-researchers.md": ("/people/researchers.html", "Researchers"),
    "people-alumni.md": ("/people/alumni.html", "Alumni"),
}

def fix_cross_refs(s):
    for filename, (href, label) in CROSS_REFS.items():
        s = s.replace(f"see {filename}", f'see <a href="{href}">{label}</a>')
    return s

AWARD_KEYWORDS = ["Scholarship", "Fellowship", "Award", "Medal", "Prize", "Commendation", "Grant", "Exhibit", "First author"]

CROSS_REF_PAREN_RE = re.compile(r"\s*\((also[^()]*?see [\w-]+\.md)\)")

def format_notes(notes):
    if not notes.strip():
        return ""
    # pull "(also ... see some-file.md)" asides out of whatever clause they're
    # stuck to, so they render as their own plain-text note, not inside a pill
    asides = CROSS_REF_PAREN_RE.findall(notes)
    notes = CROSS_REF_PAREN_RE.sub("", notes)
    clauses = [c.strip() for c in notes.split(";") if c.strip()]
    out = []
    for c in clauses:
        if any(k in c for k in AWARD_KEYWORDS):
            out.append(f'<span class="tag-note">{md_inline(c)}</span>')
        else:
            out.append(md_inline(c))
    for a in asides:
        a = re.sub(r"^also\s+", "", a, flags=re.I)
        a = re.sub(r"^an?\s+", "", a, flags=re.I)
        a = a[:1].upper() + a[1:]
        a = re.sub(r"\s*—\s*", ", ", a)
        out.append(fix_cross_refs(a))
    return '<span class="note-sep">|</span>'.join(out)

sections = []
total = 0
for year, block in year_blocks:
    rows = [l for l in ("|" + block).strip().split("\n") if l.startswith("|")]
    rows = rows[2:]
    trs = []
    for row in rows:
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        if len(cells) < 4:
            continue
        name, yrs, area, notes = cells
        total += 1
        trs.append(f"          <tr><td>{md_inline(name)}</td><td>{html.escape(yrs)}</td><td>{html.escape(area)}</td><td class=\"small\">{format_notes(notes)}</td></tr>")
    sections.append(f'''      <h3 class="year-heading">{year}</h3>
      <table class="data cols-4">
        <colgroup><col class="c1"><col class="c2"><col class="c3"><col class="c4"></colgroup>
        <thead><tr><th>Name</th><th>Year(s)</th><th>Area</th><th>Notes</th></tr></thead>
        <tbody>
{chr(10).join(trs)}
        </tbody>
      </table>''')

body = "\n\n".join(sections)

template = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<title>Coursework Students — Terahertz Engineering Laboratory</title>
<meta name="description" content="Honours, master's, and undergraduate research students at the Terahertz Engineering Laboratory, Adelaide University.">
<link rel="canonical" href="https://thz-el.org/people/coursework.html">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Terahertz Engineering Laboratory">
<meta property="og:title" content="Coursework Students — Terahertz Engineering Laboratory">
<meta property="og:description" content="Honours, master's, and undergraduate research students at the Terahertz Engineering Laboratory, Adelaide University.">
<meta property="og:url" content="https://thz-el.org/people/coursework.html">
<meta property="og:image" content="https://thz-el.org/assets/img/group-photo-1.jpg">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/assets/img/brand/favicon.png" type="image/png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/css/style.css?v=20260923f">
</head>
<body>

<header class="site-header">
  <div class="site-header-inner">
    <a class="brand plain" href="/index.html">
      <img class="brand-mark" src="/assets/img/brand/mark-white.png" alt="THz">
      <span class="brand-name">Terahertz Engineering Laboratory</span>
    </a>
    <nav class="primary-nav" aria-label="Primary">
      <ul>
        <li><a href="/index.html">Home</a></li>
        <li><a href="/research.html">Research</a></li>
        <li class="has-children">
          <button class="nav-parent" aria-expanded="false">Publications</button>
          <div class="submenu">
            <a href="/publications/journal-articles.html">Journal Articles</a>
            <a href="/publications/conference-presentations.html">Conference Presentations</a>
            <a href="/publications/phd-theses.html">PhD Theses</a>
            <a href="/publications/codes.html">Codes</a>
          </div>
        </li>
        <li class="has-children open">
          <button class="nav-parent" aria-expanded="false">People</button>
          <div class="submenu">
            <a href="/people/researchers.html">Researchers</a>
            <a href="/people/alumni.html">Alumni</a>
            <a href="/people/coursework.html" aria-current="page">Coursework Students</a>
            <a href="/people/visitors.html">Visitors</a>
          </div>
        </li>
        <li><a href="/opportunities.html">Opportunities</a></li>
        <li><a href="/contact.html">Contact</a></li>
      </ul>
    </nav>
    <button class="nav-toggle" aria-label="Toggle navigation" aria-expanded="false"><span></span></button>
  </div>
</header>

<main>

  <section class="page-hero">
    <div class="wrap-wide">
      <p class="hero-eyebrow">People</p>
      <h1>Coursework students</h1>
      <p class="lead">Honours, master's, and undergraduate research students who have contributed to the laboratory's projects, grouped by year.</p>
      <p class="small">Photos are not included here &mdash; see the <a href="https://sites.google.com/view/thzel/people/coursework">previous website</a> for those.</p>
      <div class="stats-row" style="grid-template-columns: max-content;">
        <div class="stat">
          <span class="stat-num">{total}</span>
          <span class="stat-label">Coursework Students</span>
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

<footer class="site-footer">
  <div class="wrap-wide" style="display:block;">
    <div style="display:flex; justify-content:space-between; flex-wrap:wrap; gap:16px;">
      <span>&copy; <span data-copyright-year>2026</span> Terahertz Engineering Laboratory, Adelaide University</span>
      <span><a href="/contact.html">Contact</a> &middot; <a href="https://www.linkedin.com/company/thz-el">LinkedIn</a></span>
    </div>
  </div>
</footer>

<script src="/assets/js/main.js?v=20260923f"></script>
</body>
</html>
"""

with open(OUT, "w", encoding="utf-8") as f:
    f.write(template.replace("{body}", body).replace("{total}", str(total)))

print("Wrote", OUT, "-", len(year_blocks), "year sections,", total, "students")
