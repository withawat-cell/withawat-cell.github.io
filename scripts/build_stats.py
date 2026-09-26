"""Recompute the home page's "Lab history" stat strip from the already-built
publications pages and the People pages, and write the numbers into
index.html between the STATS:START/STATS:END markers.

Run this AFTER build_publications.py and build_coursework.py, since it
reads their output.
"""
import os
import re
from bs4 import BeautifulSoup

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def read(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as f:
        return f.read()

# ---------- journal articles ----------

journal_soup = BeautifulSoup(read("publications/journal-articles.html"), "html.parser")
journal_entries = journal_soup.select("li.pub-entry")
journal_total = len(journal_entries)
journal_recognitions = sum(1 for e in journal_entries if e.select_one(".tag-award"))

# ---------- conference presentations ----------

conf_soup = BeautifulSoup(read("publications/conference-presentations.html"), "html.parser")
conf_entries = conf_soup.select("li.pub-entry")
conf_invited = sum(1 for e in conf_entries if e.select_one(".tag-award"))

# ---------- PhD theses ----------

theses_soup = BeautifulSoup(read("publications/phd-theses.html"), "html.parser")
theses_total = len(theses_soup.select("table.data tbody tr"))

# ---------- IEEE student grants ----------
# A tag-note counts if it mentions IEEE together with Fellowship/Scholarship/Grant
# (this naturally excludes things like "IEEE Fellow" -- the senior lifetime
# honorific, not a student grant -- and "IEEE ... Young Professional
# Ambassador"/"Honorary Mention", none of which contain those three words).
IEEE_GRANT_RE = re.compile(r"\bIEEE\b.*?\b(Fellowship|Scholarship|Grant)\b", re.I)

def person_awards(html):
    """Yield (person_name, award_text) for every tag-note inside a .person card."""
    soup = BeautifulSoup(html, "html.parser")
    for person in soup.select("div.person"):
        name_el = person.select_one(".person-name")
        if not name_el:
            continue
        name = name_el.get_text(strip=True)
        for note in person.select(".tag-note"):
            yield name, note.get_text(strip=True)

def coursework_awards(html):
    """Yield (student_name, award_text) for every tag-note inside a coursework row."""
    soup = BeautifulSoup(html, "html.parser")
    for row in soup.select("table.data tbody tr"):
        cells = row.select("td")
        if not cells:
            continue
        name = cells[0].get_text(strip=True)
        for note in row.select(".tag-note"):
            yield name, note.get_text(strip=True)

def normalize_name(name):
    return re.sub(r"^(Dr\.|Prof\.)\s+", "", name, flags=re.I).strip().lower()

# Some people appear on more than one page (e.g. a current postgrad who also
# has a Coursework Students record from their undergrad years), and the same
# real-world award can be worded slightly differently between pages (e.g.
# "AP-S" vs "Antennas and Propagation Society (APS)"). Dedupe by
# (person, year) rather than exact award text, since nobody in practice gets
# two different IEEE student grants in the same calendar year.
ieee_grants = set()
for html_path, extractor in [
    ("people/researchers.html", person_awards),
    ("people/alumni.html", person_awards),
    ("people/coursework.html", coursework_awards),
]:
    for name, award in extractor(read(html_path)):
        if IEEE_GRANT_RE.search(award):
            year_match = re.search(r"\b(19|20)\d{2}\b", award)
            key = (normalize_name(name), year_match.group(0) if year_match else award)
            ieee_grants.add(key)

ieee_grant_count = len(ieee_grants)

# ---------- University Doctoral Research Medal ----------

MEDAL_RE = re.compile(r"\bUniversity Doctoral Research Medal\b", re.I)

medals = set()
for html_path, extractor in [
    ("people/researchers.html", person_awards),
    ("people/alumni.html", person_awards),
    ("people/coursework.html", coursework_awards),
]:
    for name, award in extractor(read(html_path)):
        if MEDAL_RE.search(award):
            year_match = re.search(r"\b(19|20)\d{2}\b", award)
            key = (normalize_name(name), year_match.group(0) if year_match else award)
            medals.add(key)

medal_count = len(medals)

# ---------- Commendation for Doctoral Thesis Excellence ----------
# Dedupe by person alone (not person+year, unlike the awards above): this is
# a one-time thesis honour, and the exact wording varies by who signed off
# ("PVC Commendation..." vs "Dean's Commendation...") so a text-based key
# would risk double-counting someone tagged with both phrasings.

COMMENDATION_RE = re.compile(r"\bCommendation for Doctoral Thesis Excellence\b", re.I)

commendations = set()
for html_path, extractor in [
    ("people/researchers.html", person_awards),
    ("people/alumni.html", person_awards),
    ("people/coursework.html", coursework_awards),
]:
    for name, award in extractor(read(html_path)):
        if COMMENDATION_RE.search(award):
            commendations.add(normalize_name(name))

commendation_count = len(commendations)

# ---------- ARC research grants ----------
# Counted directly from the ARC grant codes (e.g. LE180100003, DP170101922)
# named in the "Lab history" prose paragraph on this same page.

ARC_GRANT_RE = re.compile(r"\b(?:LE|DP|DE|FT|CE)\d{9}\b")

def read_index():
    with open(os.path.join(ROOT, "index.html"), encoding="utf-8") as f:
        return f.read()

lab_history_html = read_index()
lab_history_match = re.search(r"<h2>Lab history</h2>.*?<!-- STATS:START -->", lab_history_html, re.S)
arc_grant_count = len(set(ARC_GRANT_RE.findall(lab_history_match.group(0))))

# ---------- ARC fellows ----------
# "ARC Future Fellow" / "ARC DECRA" mentions anywhere in a person's card --
# unlike the tag-note-only awards above, this also has to catch Withawat's
# own "ARC Future Fellow" line, which isn't a .tag-note (it's a senior/
# permanent designation shown as plain text), so this scans every
# person-meta paragraph rather than just .tag-note spans.

ARC_FELLOW_RE = re.compile(r"\bARC\b.{0,20}?\b(Future Fellow|DECRA)\b", re.I)

def person_full_text(html):
    """Yield (person_name, all person-meta text) for every .person card."""
    soup = BeautifulSoup(html, "html.parser")
    for person in soup.select("div.person"):
        name_el = person.select_one(".person-name")
        if not name_el:
            continue
        name = name_el.get_text(strip=True)
        text = " ".join(p.get_text(" ", strip=True) for p in person.select("p.person-meta"))
        yield name, text

arc_fellows = set()
for html_path in ["people/researchers.html", "people/alumni.html"]:
    for name, text in person_full_text(read(html_path)):
        if ARC_FELLOW_RE.search(text):
            arc_fellows.add(normalize_name(name))

arc_fellow_count = len(arc_fellows)

# ---------- international collaborator countries ----------
# Unlike the stats above, country-of-affiliation for journal co-authors
# isn't data that lives anywhere on the site -- it only exists in DOI/
# publisher metadata, which isn't something worth fetching at build time
# (adds a network dependency that could break the build). So this one is
# a hand-maintained list: update it on the rare occasion a paper is
# published with a collaborator country not already listed here.
# (ISO 3166-1 alpha-2 code, country name) -- flag images from flagcdn.com.
INTL_COLLAB_COUNTRIES = [
    ("jp", "Japan"),
    ("de", "Germany"),
    ("cn", "China"),
    ("es", "Spain"),
    ("us", "United States"),
    ("ch", "Switzerland"),
    ("fr", "France"),
    ("nl", "Netherlands"),
    ("th", "Thailand"),
]

def flags_html(countries):
    return "".join(
        f'<img src="https://flagcdn.com/16x12/{code}.png" srcset="https://flagcdn.com/32x24/{code}.png 2x" '
        f'width="12" height="9" alt="{name}" title="{name}" loading="lazy">'
        for code, name in countries
    )

intl_collab_flags = flags_html(INTL_COLLAB_COUNTRIES)

# ---------- visitor countries ----------
# Unlike the collaborator countries above (which come from off-site DOI/
# publisher metadata this site doesn't have), each visitor's country is
# already on the page -- it's reliably the last comma-separated segment of
# their affiliation line (e.g. "Zhejiang University, China"). So this is
# parsed straight from people/visitors.html rather than hand-maintained;
# only the name -> ISO code mapping (needed for the flag icon) is a small
# static table, extended whenever a visitor from an uncovered country is
# added.
COUNTRY_ISO = {
    "New Zealand": "nz",
    "China": "cn",
    "Japan": "jp",
    "Germany": "de",
    "Australia": "au",
    "Thailand": "th",
    "Taiwan": "tw",
}

def visitor_country_names(html):
    """Yield each distinct country in first-appearance order, one per
    visitor -- taken from the last comma-separated part of the first
    non-"Now:" .person-meta paragraph in each visitor's card."""
    soup = BeautifulSoup(html, "html.parser")
    seen = set()
    for person in soup.select("div.person"):
        metas = [p.get_text(" ", strip=True) for p in person.select("p.person-meta")]
        affil = next((m for m in metas if not m.startswith("Now")), None)
        if not affil:
            continue
        country = affil.rsplit(",", 1)[-1].strip()
        if country not in seen:
            seen.add(country)
            yield country

VISITOR_COUNTRIES = []
for name in visitor_country_names(read("people/visitors.html")):
    code = COUNTRY_ISO.get(name)
    if not code:
        raise SystemExit(f"No ISO code mapped for visitor country {name!r} -- add it to COUNTRY_ISO in build_stats.py")
    VISITOR_COUNTRIES.append((code, name))
visitor_flags = flags_html(VISITOR_COUNTRIES)

# ---------- per-page person categories (Visitors, Researchers) ----------
# Each category is its own "section.block" on the page, labelled by a
# ".section-num" span (e.g. "PhD Candidates") -- counted directly so a new
# section or person added there is picked up automatically.

def page_categories(html):
    soup = BeautifulSoup(html, "html.parser")
    for section in soup.select("section.block"):
        label_el = section.select_one(".section-num")
        if not label_el:
            continue
        yield label_el.get_text(strip=True), len(section.select(".person"))

VISITOR_CATEGORIES = list(page_categories(read("people/visitors.html")))

# ---------- write into index.html ----------

# Journal articles published by lab members before the lab's own 2018
# establishment aren't listed on the Journal Articles page, so the stat
# needs an asterisk pointing to that caveat.
PRE_LAB_JOURNAL_COUNT = 69

stats_html = f"""      <div class="stats-row">
        <a class="stat" href="/publications/journal-articles.html">
          <span class="stat-num">{journal_total}<sup>*</sup></span>
          <span class="stat-label">Journal Articles</span>
          <span class="stat-sub">{journal_recognitions} Recognitions</span>
        </a>
        <a class="stat" href="/publications/conference-presentations.html">
          <span class="stat-num">{conf_invited}</span>
          <span class="stat-label">Invited Conferences</span>
        </a>
        <a class="stat" href="/publications/phd-theses.html">
          <span class="stat-num">{theses_total}</span>
          <span class="stat-label">PhD Theses</span>
        </a>
        <div class="stat">
          <span class="stat-num">{ieee_grant_count}</span>
          <span class="stat-label">IEEE AP/MTT Students/Postdocs Grants</span>
        </div>
        <a class="stat" href="/people/alumni.html">
          <span class="stat-num">{medal_count}</span>
          <span class="stat-label">University Doctoral Research Medals</span>
        </a>
        <div class="stat">
          <span class="stat-num">{arc_grant_count}</span>
          <span class="stat-label">ARC Research Grants</span>
        </div>
        <a class="stat" href="/people/researchers.html">
          <span class="stat-num">{arc_fellow_count}</span>
          <span class="stat-label">ARC Fellows</span>
        </a>
        <a class="stat" href="/publications/journal-articles.html">
          <span class="stat-num">{len(INTL_COLLAB_COUNTRIES)}</span>
          <span class="stat-label">Collaborator Countries</span>
          <span class="stat-flags">{intl_collab_flags}</span>
        </a>
      </div>
      <p class="small" style="margin-top:10px;">*Excludes {PRE_LAB_JOURNAL_COUNT} journal articles published prior to the lab's establishment in 2018.</p>"""

def write_stats_block(rel_path, block_html):
    """Replace the content between STATS:START/STATS:END markers in a
    hand-authored page with freshly computed stats. Every page below is
    static HTML edited directly (not generated from content-raw), so this
    marker-replace is the only thing that ever touches their stat chips."""
    path = os.path.join(ROOT, rel_path)
    with open(path, encoding="utf-8") as f:
        page_html = f.read()
    new_html, n = re.subn(
        r"<!-- STATS:START -->.*?<!-- STATS:END -->",
        "<!-- STATS:START -->\n" + block_html + "\n      <!-- STATS:END -->",
        page_html,
        flags=re.S,
    )
    if n != 1:
        raise SystemExit(f"STATS:START/STATS:END markers not found (or found more than once) in {rel_path}")
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_html)

write_stats_block("index.html", stats_html)

# ---------- write into publications/phd-theses.html ----------

theses_stats_html = f"""      <div class="stats-row">
        <a class="stat" href="/people/alumni.html">
          <span class="stat-num">{commendation_count}</span>
          <span class="stat-label">Commendations for Doctoral<br>Thesis Excellence</span>
        </a>
        <a class="stat" href="/people/alumni.html">
          <span class="stat-num">{medal_count}</span>
          <span class="stat-label">University Doctoral<br>Research Medals</span>
        </a>
      </div>"""
write_stats_block("publications/phd-theses.html", theses_stats_html)

def category_chips_html(categories):
    return "\n".join(
        f'''        <div class="stat">
          <span class="stat-num">{count}</span>
          <span class="stat-label">{label}</span>
        </div>'''
        for label, count in categories
    )

# ---------- write into people/visitors.html ----------

visitors_stats_html = f"""      <div class="stats-row">
{category_chips_html(VISITOR_CATEGORIES)}
        <div class="stat">
          <span class="stat-num">{len(VISITOR_COUNTRIES)}</span>
          <span class="stat-label">Visitor Countries</span>
          <span class="stat-flags">{visitor_flags}</span>
        </div>
      </div>"""
write_stats_block("people/visitors.html", visitors_stats_html)

print(
    f"Wrote stats to index.html: {journal_total} journal articles "
    f"({journal_recognitions} recognitions), {conf_invited} invited conferences, "
    f"{theses_total} PhD theses, {ieee_grant_count} IEEE student grants, "
    f"{medal_count} University Doctoral Research Medals, "
    f"{arc_grant_count} ARC research grants, {arc_fellow_count} ARC fellows, "
    f"{len(INTL_COLLAB_COUNTRIES)} international collaborator countries"
)
print(
    f"Wrote stats to publications/phd-theses.html: {commendation_count} commendations, "
    f"{medal_count} medals"
)
def summarize(categories):
    return ", ".join(f"{count} {label}" for label, count in categories)

print(f"Wrote stats to people/visitors.html: {summarize(VISITOR_CATEGORIES)}, {len(VISITOR_COUNTRIES)} visitor countries")
