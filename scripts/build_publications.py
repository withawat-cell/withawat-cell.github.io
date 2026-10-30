import re
import os
import json
import html

import build_stats
import shell
from pubdata import TOPIC_LABELS, read_tables, read_flat_table, has_recognition
from textutil import md_inline

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

with open(os.path.join(ROOT, "content-raw", "journal-notes-links.json"), encoding="utf-8") as f:
    KNOWN_LINKS = json.load(f)

def linkify_known(notes):
    """Turn 'Label (url)' / 'Label: url' pairs into markdown links.
    Each entry's own adjacent URL (as written in its own notes cell) always
    wins first, since the same outlet name (e.g. "IEEE Spectrum") can point
    to a different URL in different entries. Only labels with no adjacent
    URL of their own fall back to the (text, href) pairs scraped from the
    live page, for the cases where the live site links them as a Google
    Sites "smart chip" with no adjacent URL text at all."""
    # exact known (text, href) pairs first, matched literally -- safest for
    # titles that themselves contain a colon (e.g. compound special-issue
    # names), since the literal text is fixed rather than wildcard-matched
    for item in KNOWN_LINKS:
        text, href = item["text"], item["href"]
        href_re = re.escape(href)
        text_re = re.escape(text)
        notes = re.sub(rf"{text_re}\s*\({href_re}\)", f"[{text}]({href})", notes)
        notes = re.sub(rf"{text_re}\s*:\s*{href_re}", f"[{text}]({href})", notes)
    # outlet names in "Covered by X (url), Y (url)" style clauses: each
    # label is a short run of capitalized words immediately before its own
    # "(url)", so a connector like "Covered by " never gets swept into it
    label_word = r"[A-Z][A-Za-z0-9&.\-']*"
    notes = re.sub(rf"((?:{label_word}\s+)*{label_word})\s*\((https?://[^\s()]+)\)", r"[\1](\2)", notes)
    # phrasal titles in "Label: url" style notes (special issues, etc.)
    notes = re.sub(r'([A-Za-z][A-Za-z0-9 .,&/\'"-]*?):\s*(https?://[^\s;,()]+)', r"[\1](\2)", notes)
    # remaining known labels with no adjacent URL of their own (a Google
    # Sites "smart chip" on the live page) fall back to the scraped href
    for item in KNOWN_LINKS:
        text, href = item["text"], item["href"]
        text_re = re.escape(text)
        if f"[{text}]" not in notes:
            notes = re.sub(rf"(?<!\[){text_re}(?!\])", f"[{text}]({href})", notes, count=1)
    # any bare URL still left unlinked (no label attached in the source
    # text) becomes a plain link using the URL itself as the link text
    notes = re.sub(r"(?<!\]\()(https?://[^\s;,()]+)", r"[\1](\1)", notes)
    return notes

TRIM_PREFIXES = ["One of the "]
MAX_PILL_LEN = 200

def shorten(original):
    p = original
    for pre in TRIM_PREFIXES:
        if p.startswith(pre):
            p = p[len(pre):]
            break
    if len(p) <= MAX_PILL_LEN:
        return p
    return p[:MAX_PILL_LEN].rsplit(" ", 1)[0] + "…"

LINK_RE = re.compile(r'<a href="([^"]+)">([^<]+)</a>')

def cap_first(s):
    for i, ch in enumerate(s):
        if ch.isalpha():
            return s[:i] + ch.upper() + s[i + 1:]
    return s

def split_cell(cell):
    """Split a ';'-separated cell into parts, linking bare URLs on the way."""
    if not cell.strip():
        return []
    return [p.strip() for p in linkify_known(cell).split(";") if p.strip()]

def recognition_pills(cell):
    """Turn a Recognition cell into chips: [{short, full (tooltip or None), href (or None)}].
    Every part of the cell is a chip -- deciding what counts as a recognition
    is done in the markdown, not here. A part naming several linked outlets
    ("Covered by X (url), Y (url), and other media") becomes one chip per
    outlet and the leftover filler words are dropped."""
    pills = []

    def add(text, href):
        shortened = shorten(text)
        pills.append({"short": cap_first(shortened), "full": text if shortened != text else None, "href": href})

    for part in split_cell(cell):
        part_html = md_inline(part)
        links = LINK_RE.findall(part_html)
        if not links:
            add(part_html, None)
        for href, text in links:
            add(text, href)
    return pills

def notes_html(cell):
    """Render a Notes cell (special issues, supplementary material, ...) as
    plain text with links, parts joined by a middle dot."""
    return " &middot; ".join(md_inline(p) for p in split_cell(cell))

def pills_html(pills):
    if not pills:
        return ""
    spans = []
    for pill in pills:
        title_attr = f' title="{html.escape(pill["full"])}"' if pill["full"] else ""
        label = html.escape(pill["short"])
        if pill["href"]:
            inner = f'<a href="{html.escape(pill["href"])}">{label}</a>'
        else:
            inner = label
        spans.append(f'<span class="tag tag-award"{title_attr}>{inner}</span>')
    return '<span class="tag-row tag-row-pills">' + "".join(spans) + "</span>"

# ---------- Journal articles ----------

TITLE_RE = re.compile(r'"([^"]+)"')

INITIALS_RE = re.compile(r"(\b[A-Z]\.(?:-?[A-Z]\.)*) (?=[A-Z\u00C0-\u024F])")

def nbsp_authors(citation_html):
    """Glue each author's initials to their surname so a wrapped line never
    ends on a lone 'W.'. Only the author list (before the quoted title) is
    touched, and only in the displayed HTML, never in the copied text."""
    idx = citation_html.find('"')
    if idx == -1:
        return citation_html
    head, tail = citation_html[:idx], citation_html[idx:]
    return INITIALS_RE.sub(lambda m: m.group(1).replace("-", "\u2011") + "\u00a0", head) + tail

# ---------- BibTeX generation ----------
# Best-effort @article entry parsed from the same raw citation string used
# for the on-page text -- regex-based, so it won't perfectly handle every
# citation's punctuation quirks, but gets close enough that a researcher
# pasting it in only needs to spot-check a field or two, not retype it.

BIBTEX_TAIL_RE = re.compile(
    r"^(?:,\s*vol\.\s*(?P<volume>[\w.]+))?"
    r"(?:,\s*no\.\s*(?P<number>\d+))?"
    r"(?:,\s*art\.\s*no\.\s*(?P<artno>[\w.]+))?"
    r"(?:,\s*pp\.\s*(?P<pages>\d+[–\-]\d+))?"
    r",\s*(?P<year>(?:19|20)\d{2})\.?\s*$"
)
CITATION_RE = re.compile(r'^(?P<authors>.*?),\s*"(?P<title>[^"]+)"\s*\*(?P<journal>[^*]+)\*(?P<tail>.*)$')

# Accented Latin letters -> LaTeX escape codes, so names/titles with
# diacritics (e.g. "Kürner", "Stöhr") render correctly once pasted into a
# BibTeX-consuming tool, instead of raw UTF-8 bytes that break under plain
# BibTeX's ASCII-only .bib parsing.
ACCENT_MAP = {
    "à": r"{\`a}", "á": r"{\'a}", "â": r"{\^a}", "ã": r"{\~a}", "ä": r'{\"a}', "å": r"{\aa}",
    "À": r"{\`A}", "Á": r"{\'A}", "Â": r"{\^A}", "Ã": r"{\~A}", "Ä": r'{\"A}', "Å": r"{\AA}",
    "ç": r"{\c c}", "Ç": r"{\c C}",
    "è": r"{\`e}", "é": r"{\'e}", "ê": r"{\^e}", "ë": r'{\"e}',
    "È": r"{\`E}", "É": r"{\'E}", "Ê": r"{\^E}", "Ë": r'{\"E}',
    "ì": r"{\`i}", "í": r"{\'i}", "î": r"{\^i}", "ï": r'{\"i}',
    "Ì": r"{\`I}", "Í": r"{\'I}", "Î": r"{\^I}", "Ï": r'{\"I}',
    "ñ": r"{\~n}", "Ñ": r"{\~N}",
    "ò": r"{\`o}", "ó": r"{\'o}", "ô": r"{\^o}", "õ": r"{\~o}", "ö": r'{\"o}', "ø": r"{\o}",
    "Ò": r"{\`O}", "Ó": r"{\'O}", "Ô": r"{\^O}", "Õ": r"{\~O}", "Ö": r'{\"O}', "Ø": r"{\O}",
    "ù": r"{\`u}", "ú": r"{\'u}", "û": r"{\^u}", "ü": r'{\"u}',
    "Ù": r"{\`U}", "Ú": r"{\'U}", "Û": r"{\^U}", "Ü": r'{\"U}',
    "ý": r"{\'y}", "ÿ": r'{\"y}', "Ý": r"{\'Y}",
    "ß": r"{\ss}",
}
ACCENT_RE = re.compile("|".join(re.escape(ch) for ch in ACCENT_MAP))

def bibtex_escape(s):
    s = s.replace("&", r"\&").replace("%", r"\%")
    s = s.replace("‐", "-").replace("‑", "-")  # hyphen / non-breaking hyphen
    s = s.replace("–", "--").replace("—", "---")  # en dash / em dash
    return ACCENT_RE.sub(lambda m: ACCENT_MAP[m.group(0)], s)

# Any word carrying a capital letter (acronyms like IEEE, mid-title proper
# nouns like "Bragg", single letters like "Q") is deliberately capitalised
# in the source, not just capitalised-because-first-word text, so it's
# wrapped in braces to survive a BibTeX style's title-case folding.
ACRONYM_RE = re.compile(r"\b[A-Za-z0-9]+\b")

def protect_acronyms(s):
    def wrap(m):
        word = m.group(0)
        return "{" + word + "}" if any(c.isupper() for c in word) else word
    return ACRONYM_RE.sub(wrap, s)

def split_author_name(name):
    """'H. Lees' -> 'Lees, H.' (BibTeX author convention). Splits on the
    last whitespace, so the final token is treated as the surname."""
    parts = name.strip().split()
    if len(parts) <= 1:
        return name.strip()
    return f"{parts[-1]}, {' '.join(parts[:-1])}"

def make_bibtex_key(first_author, year, used_keys):
    tokens = re.sub(r"[^A-Za-z ]", "", first_author).split()
    surname = tokens[-1] if tokens else "ref"
    base = f"{surname}{year}"
    key, suffix = base, ord("a")
    while key in used_keys:
        key = f"{base}{chr(suffix)}"
        suffix += 1
    used_keys.add(key)
    return key

def citation_to_bibtex(citation, used_keys):
    m = CITATION_RE.match(citation.strip())
    if not m:
        return None
    authors_raw = [a.strip() for a in re.split(r",\s*(?:and\s+)?|\s+and\s+", m.group("authors")) if a.strip()]
    if not authors_raw:
        return None
    tail_m = BIBTEX_TAIL_RE.match(m.group("tail").strip())
    if not tail_m:
        return None
    title = m.group("title").strip().rstrip(",").strip()
    journal = m.group("journal").strip()
    year = tail_m.group("year")
    pages = tail_m.group("pages")
    if pages:
        pages = re.sub(r"[–\-]+", "--", pages)

    key = make_bibtex_key(authors_raw[0], year, used_keys)
    fields = [
        ("author", " and ".join(split_author_name(bibtex_escape(a)) for a in authors_raw)),
        ("title", bibtex_escape(protect_acronyms(title))),
        ("journal", bibtex_escape(journal)),
        ("year", year),
    ]
    if tail_m.group("volume"):
        fields.append(("volume", tail_m.group("volume")))
    if tail_m.group("number"):
        fields.append(("number", tail_m.group("number")))
    if tail_m.group("artno"):
        fields.append(("eid", tail_m.group("artno")))
    if pages:
        fields.append(("pages", pages))
    body = ",\n".join(f"  {k} = {{{v}}}" for k, v in fields)
    return f"@article{{{key},\n{body}\n}}"

def build_journal():
    year_blocks = read_tables("publications-journal-articles.md")
    used_bibtex_keys = set()

    sections = []
    global_idx = 0
    total_count = 0
    recognitions_count = 0
    invited_count = 0
    for year, rows in year_blocks:
        entries = []
        for row in rows:
            citation, doi, topics, abstract = row["citation"], row["doi"], row["topics"], row["abstract"]
            primary_doi = doi.split(" ")[0] if doi.startswith("http") else ""
            citation_html = nbsp_authors(md_inline(citation))
            m = TITLE_RE.search(citation_html)
            if m and primary_doi:
                title_linked = f'<a href="{html.escape(primary_doi)}">{m.group(1)}</a>'
                citation_html = citation_html[:m.start()] + '"' + title_linked + '"' + citation_html[m.end():]
            pills = recognition_pills(row["recognition"])
            rest = notes_html(row["notes"])
            status_suffix = f" ({row['status']})" if row["status"] else ""
            citation_html += status_suffix
            total_count += 1
            if has_recognition(row):
                recognitions_count += 1
            if any(p["short"] == "Invited" for p in pills):
                invited_count += 1
            plain_citation = citation.replace("*", "") + status_suffix
            img = f"/assets/img/publications/{row['image']}" if row["image"] else None
            thumb = f'<img class="pub-thumb" src="{img}?v=x" alt="" loading="lazy">' if img else '<span class="pub-thumb-empty" aria-hidden="true"></span>'
            meta_bits = []
            if rest:
                meta_bits.append(rest)
            meta_html = f'<p class="entry-meta">{" &middot; ".join(meta_bits)}</p>' if meta_bits else ""
            copy_btn = f'<button type="button" class="copy-btn copy-btn-sm" aria-label="Copy citation" title="Copy citation" data-copy="{html.escape(plain_citation, quote=True)}"><svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg></button>'
            bibtex = citation_to_bibtex(citation, used_bibtex_keys)
            bibtex_btn = (
                f'<button type="button" class="copy-btn copy-btn-sm bibtex-btn" aria-label="Copy BibTeX" '
                f'title="Copy BibTeX" data-copy="{html.escape(bibtex, quote=True)}">{{}}</button>'
            ) if bibtex else ""
            abs_id = f"abs-{global_idx}"
            abs_btn = (
                f'<button type="button" class="abstract-toggle-btn" aria-expanded="false" '
                f'aria-controls="{abs_id}" aria-label="Show abstract" title="Show abstract">ABS'
                f'<svg viewBox="0 0 24 24" width="8" height="8" fill="none" stroke="currentColor" stroke-width="3" '
                f'stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg></button>'
            ) if abstract else ""
            abstract_html = (
                f'<p class="pub-abstract" id="{abs_id}" hidden>{html.escape(abstract)}</p>'
            ) if abstract else ""
            entries.append(f'''      <li class="pub-entry" data-topics="{topics}">
        {thumb}
        <div class="entry-body">
          <p class="entry-title">{citation_html} <span class="entry-tools">{copy_btn}{bibtex_btn}{abs_btn}</span></p>
          {meta_html}
          {pills_html(pills)}
        </div>
        {abstract_html}
      </li>''')
            global_idx += 1
        sections.append(f'    <div class="year-block" data-year="{year}">\n      <h3 class="year-heading">{year}</h3>\n      <ul class="pub-list">\n' + "\n".join(entries) + "\n      </ul>\n    </div>")
    years = [y for y, _ in year_blocks]
    return "\n\n".join(sections), years, total_count, recognitions_count, invited_count

# ---------- Conference presentations ----------

def build_conference():
    sections = []
    for year, rows in read_tables("publications-conference-presentations.md"):
        entries = []
        for row in rows:
            citation_html = nbsp_authors(md_inline(row["citation"]))
            if row["status"]:
                citation_html += f" ({row['status']})"
            pills = recognition_pills(row["recognition"])
            rest_note = notes_html(row["notes"])
            meta_html = f'<p class="entry-meta">{rest_note}</p>' if rest_note else ""
            inline_pills = pills_html(pills).replace('<span class="tag-row tag-row-pills">', '<span class="tag-row tag-row-inline">')
            entries.append(f'''      <li class="pub-entry">
        <div class="entry-body">
          <p class="entry-title">{citation_html} {inline_pills}</p>
          {meta_html}
        </div>
      </li>''')
        sections.append(f'    <h3 class="year-heading">{year}</h3>\n    <ul class="pub-list pub-list-text">\n' + "\n".join(entries) + "\n    </ul>")
    return "\n\n".join(sections)

journal_html, journal_years, journal_total, journal_recognitions, journal_invited = build_journal()
conference_html = build_conference()

year_filter_options = "\n".join(
    f'          <option value="{y}">{y}</option>' for y in journal_years
)

theses_rows = []
for row in read_flat_table("publications-theses.md"):
    title = html.escape(row["title"], quote=False)
    if row["file"]:
        title = f'<a href="/assets/theses/{html.escape(row["file"], quote=True)}">{title}</a>'
    theses_rows.append(
        f'          <tr><td>{html.escape(row["year"])}</td><td>{html.escape(row["author"], quote=False)}</td><td>{title}</td></tr>'
    )
theses_html = '''      <div class="table-scroll">
      <table class="data theses stack-sm">
        <thead>
          <tr><th>Year</th><th>Author</th><th>Thesis title</th></tr>
        </thead>
        <tbody>
''' + "\n".join(theses_rows) + '''
        </tbody>
      </table>
      </div>'''

with open(os.path.join(ROOT, "content-raw", "codes-cards.html"), encoding="utf-8") as f:
    codes_html = re.sub(r"^<!--.*?-->\n", "", f.read(), count=1, flags=re.S).rstrip("\n")

# ---------- shared page shell ----------

def page(slug, title, description, eyebrow, h1, lead, body, extra_head="", extra_scripts="", extra_hero=""):
    return shell.stamp_html(f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Cache-Control" content="no-cache">
<title>{title} | Terahertz Engineering Laboratory</title>
<meta name="description" content="{description}">
<link rel="canonical" href="https://thz-el.org/publications/{slug}.html">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Terahertz Engineering Laboratory">
<meta property="og:title" content="{title} | Terahertz Engineering Laboratory">
<meta property="og:description" content="{description}">
<meta property="og:url" content="https://thz-el.org/publications/{slug}.html">
<meta property="og:image" content="https://thz-el.org/assets/img/group-photo-1.webp">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/assets/img/brand/favicon.png" type="image/png">
<link rel="preload" as="image" href="/assets/img/brand/header-bg.webp?v=x">
<link rel="stylesheet" href="/assets/css/style.css?v=x">{extra_head}
</head>
<body>

<header class="site-header"></header>

<main>

  <section class="page-hero">
    <div class="wrap-wide">
      <p class="hero-eyebrow">{eyebrow}</p>
      <h1>{h1}</h1>
      <p class="lead">{lead}</p>{extra_hero}
    </div>
  </section>

  <section class="block">
    <div class="wrap-wide">
{body}
    </div>
  </section>

</main>

<footer class="site-footer"></footer>

<script src="/assets/js/main.js?v=x"></script>{extra_scripts}
</body>
</html>
""", f"publications/{slug}.html")

pub_dir = os.path.join(ROOT, "publications")
os.makedirs(pub_dir, exist_ok=True)

topic_filter_buttons = "\n".join(
    f'          <button type="button" class="topic-filter-btn" data-topic="{slug}" aria-pressed="false">{label}</button>'
    for slug, label in TOPIC_LABELS
)

# Journal articles
journal_hero_stats = f'''
      <p class="small">Most recent first. Excludes journal publications prior to the lab's establishment and those in the microwave and optics domains outside terahertz.</p>
      <div class="stats-row">
        <div class="stat">
          <span class="stat-num">{journal_total}</span>
          <span class="stat-label">Journal Articles</span>
          <span class="stat-sub">{journal_recognitions} Recognitions</span>
        </div>
        <div class="stat">
          <span class="stat-num">{journal_invited}</span>
          <span class="stat-label">Invited Papers</span>
        </div>
      </div>'''
journal_body = f'''      <div class="topic-filter" role="group" aria-label="Filter by topic">
{topic_filter_buttons}
        <select id="journal-year-filter" class="year-filter" aria-label="Year">
          <option value="all">All years</option>
{year_filter_options}
        </select>
      </div>
      <div class="pub-lists">
{journal_html}
      </div>'''
out = page(
    "journal-articles", "Journal Articles",
    "Journal articles from the Terahertz Engineering Laboratory, Adelaide University.",
    "Publications", "Journal articles",
    "Peer-reviewed journal articles from the Terahertz Engineering Laboratory.",
    journal_body,
    extra_scripts=f'\n<script src="/assets/js/publications-filter.js?v=x"></script>',
    extra_hero=journal_hero_stats,
)
with open(os.path.join(pub_dir, "journal-articles.html"), "w", encoding="utf-8", newline="\n") as f:
    f.write(out)

# Conference presentations
out = page(
    "conference-presentations", "Conference Presentations",
    "Conference presentations from the Terahertz Engineering Laboratory, Adelaide University.",
    "Publications", "Selected conference presentations",
    "Invited talks, keynotes, and presentations at international conferences and workshops.",
    conference_html,
)
with open(os.path.join(pub_dir, "conference-presentations.html"), "w", encoding="utf-8", newline="\n") as f:
    f.write(out)

# PhD theses
# Commendation/Medal counts come from build_stats.py (computed from the people data).
theses_hero_stats = "\n      <!-- STATS:START -->\n" + build_stats.theses_stats_html + "\n      <!-- STATS:END -->"
out = page(
    "phd-theses", "PhD Theses",
    "PhD theses produced at the Terahertz Engineering Laboratory, Adelaide University.",
    "Publications", "PhD theses",
    "Doctoral theses completed at the Terahertz Engineering Laboratory.",
    theses_html,
    extra_hero=theses_hero_stats,
)
with open(os.path.join(pub_dir, "phd-theses.html"), "w", encoding="utf-8", newline="\n") as f:
    f.write(out)

# Codes
out = page(
    "codes", "Codes",
    "Research software from the Terahertz Engineering Laboratory, Adelaide University.",
    "Publications", "Codes",
    "Research software developed at the Terahertz Engineering Laboratory.",
    codes_html,
)
with open(os.path.join(pub_dir, "codes.html"), "w", encoding="utf-8", newline="\n") as f:
    f.write(out)

print(f"Wrote publications/journal-articles.html ({journal_total} articles, {journal_recognitions} recognitions, {journal_invited} invited), conference-presentations.html, phd-theses.html, codes.html")
