"""Recompute the home page's "Lab history" stat strip (plus the stat boxes on the
PhD theses and Visitors pages) and write the numbers into the pages between
their STATS:START/STATS:END markers.

Every number comes from the data files in content-raw/ (publications tables,
people lists, coursework table, theses table) and site-config.json, plus the
ARC grant codes written in the home page's own "Lab history" paragraph.
Nothing is read back from the generated pages, so the order only matters in
that the other build scripts reset the stat placeholders first
(scripts/build_all.py runs everything in the right order).
"""
import json
import os
import re

from peopledata import coursework_rows, plain, plain_md, read_people, split_items
from pubdata import has_recognition, read_flat_table, read_tables

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

with open(os.path.join(ROOT, "content-raw", "site-config.json"), encoding="utf-8") as f:
    CONFIG = json.load(f)

# ---------- journal articles and conference presentations ----------
# A row counts as a recognition if its Recognition cell is non-empty.

journal_rows = [r for _, rows in read_tables("publications-journal-articles.md") for r in rows]
journal_total = len(journal_rows)
journal_recognitions = sum(1 for r in journal_rows if has_recognition(r))

conf_rows = [r for _, rows in read_tables("publications-conference-presentations.md") for r in rows]
conf_recognitions = sum(1 for r in conf_rows if has_recognition(r))

# ---------- PhD theses ----------

theses_total = len(read_flat_table("publications-theses.md"))

# ---------- people and awards ----------

def people_in(filename):
    for section in read_people(filename)["sections"]:
        yield from section["people"]

def all_awards():
    """Yield (person_name, award_text) for every gold award chip on the Researchers
    and Alumni pages and in the coursework table."""
    for filename in ("people-researchers.md", "people-alumni.md"):
        for person in people_in(filename):
            for award in person["awards"]:
                yield person["name"], plain_md(award)
    for _, rows in coursework_rows():
        for name, _yrs, _area, awards, _notes in rows:
            for item in split_items(awards):
                yield plain_md(name), plain_md(item)

AWARDS = list(all_awards())

def normalize_name(name):
    return re.sub(r"^(Dr\.|Prof\.)\s+", "", name, flags=re.I).strip().lower()

# ---------- IEEE student grants ----------
# An award counts if it mentions IEEE together with Fellowship/Scholarship/Grant
# (this naturally excludes things like "IEEE Fellow" -- the senior lifetime
# honorific, not a student grant -- and "IEEE ... Young Professional
# Ambassador"/"Honorary Mention", none of which contain those three words).
IEEE_GRANT_RE = re.compile(r"\bIEEE\b.*?\b(Fellowship|Scholarship|Grant)\b", re.I)

# Some people appear on more than one page (e.g. a current postgrad who also
# has a Coursework Students record from their undergrad years), and the same
# real-world award can be worded slightly differently between pages (e.g.
# "AP-S" vs "Antennas and Propagation Society (APS)"). Dedupe by
# (person, year) rather than exact award text, since nobody in practice gets
# two different IEEE student grants in the same calendar year.
def award_key(name, award):
    year_match = re.search(r"\b(19|20)\d{2}\b", award)
    return (normalize_name(name), year_match.group(0) if year_match else award)

ieee_grant_count = len({award_key(n, a) for n, a in AWARDS if IEEE_GRANT_RE.search(a)})

# ---------- University Doctoral Research Medal ----------

MEDAL_RE = re.compile(r"\bUniversity Doctoral Research Medal\b", re.I)

medal_count = len({award_key(n, a) for n, a in AWARDS if MEDAL_RE.search(a)})

# ---------- Commendation for Doctoral Thesis Excellence ----------
# Dedupe by person alone (not person+year, unlike the awards above): this is
# a one-time thesis honour, and the exact wording varies by who signed off
# ("PVC Commendation..." vs "Dean's Commendation...") so a text-based key
# would risk double-counting someone tagged with both phrasings.

COMMENDATION_RE = re.compile(r"\bCommendation for Doctoral Thesis Excellence\b", re.I)

commendation_count = len({normalize_name(n) for n, a in AWARDS if COMMENDATION_RE.search(a)})

# ---------- ARC research grants ----------
# Counted directly from the ARC grant codes (e.g. LE180100003, DP170101922)
# named in the "Lab history" prose paragraph on this same page.

ARC_GRANT_RE = re.compile(r"\b(?:LE|DP|DE|FT|CE)\d{9}\b")

with open(os.path.join(ROOT, "index.html"), encoding="utf-8") as f:
    lab_history_html = f.read()
lab_history_match = re.search(r"<h2>Lab history</h2>.*?<!-- STATS:START -->", lab_history_html, re.S)
arc_grant_count = len(set(ARC_GRANT_RE.findall(lab_history_match.group(0))))

# ---------- ARC fellows ----------
# "ARC Future Fellow" / "ARC DECRA" mentioned anywhere on a person's card (their
# Info and Awards lines), so Withawat's own "ARC Future Fellow" is caught too.

ARC_FELLOW_RE = re.compile(r"\bARC\b.{0,20}?\b(Future Fellow|DECRA)\b", re.I)

def card_lines(person):
    """The text of each meta line on a person's card, in order (Awards lines joined by bullets)."""
    out = []
    for kind, value in person["lines"]:
        if kind == "info":
            out.append(plain(value))
        else:
            out.append(" \u2022 ".join(plain(a.strip()) for a in value.split(";") if a.strip()))
    return out

arc_fellows = set()
for filename in ("people-researchers.md", "people-alumni.md"):
    for person in people_in(filename):
        if ARC_FELLOW_RE.search(" ".join(card_lines(person))):
            arc_fellows.add(normalize_name(person["name"]))

arc_fellow_count = len(arc_fellows)

# ---------- international collaborator countries ----------
# Unlike the stats above, country-of-affiliation for journal co-authors
# isn't data that lives anywhere on the site -- it only exists in DOI/
# publisher metadata, which isn't something worth fetching at build time
# (adds a network dependency that could break the build). So this one is
# a hand-maintained list: update it on the rare occasion a paper is
# published with a collaborator country not already listed here.
# (ISO 3166-1 alpha-2 code, country name) -- flag images from flagcdn.com.
INTL_COLLAB_COUNTRIES = [tuple(c) for c in CONFIG["coauthor_countries"]]

def flags_html(countries):
    return "".join(
        f'<img src="https://flagcdn.com/16x12/{code}.png" srcset="https://flagcdn.com/32x24/{code}.png 2x" '
        f'width="16" height="12" alt="{name}" title="{name}" loading="lazy">'
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
COUNTRY_ISO = CONFIG["country_iso"]

def visitor_country_names():
    """Yield each distinct country in first-appearance order, one per visitor --
    the last comma-separated part of the first affiliation line (an Info line
    not starting with "Now") on each visitor's card."""
    seen = set()
    for person in people_in("people-visitors.md"):
        affil = next((plain(v) for v in person["info"] if not plain(v).startswith("Now")), None)
        if not affil:
            continue
        country = affil.rsplit(",", 1)[-1].strip()
        if country not in seen:
            seen.add(country)
            yield country

VISITOR_COUNTRIES = []
for name in visitor_country_names():
    code = COUNTRY_ISO.get(name)
    if not code:
        raise SystemExit(f"No ISO code mapped for visitor country {name!r} -- add it to country_iso in content-raw/site-config.json")
    VISITOR_COUNTRIES.append((code, name))
visitor_flags = flags_html(VISITOR_COUNTRIES)

# ---------- write into index.html ----------

# Journal articles published by lab members before the lab's own 2018
# establishment aren't listed on the Journal Articles page, so the stat
# needs an asterisk pointing to that caveat.
PRE_LAB_JOURNAL_COUNT = CONFIG["pre_lab_journal_count"]

stats_html = f"""      <div class="stats-row">
        <a class="stat" href="/publications/journal-articles.html">
          <span class="stat-num">{journal_total}<sup>*</sup></span>
          <span class="stat-label">Journal Articles</span>
          <span class="stat-sub">{journal_recognitions} Recognitions</span>
        </a>
        <a class="stat" href="/publications/conference-presentations.html">
          <span class="stat-num">{conf_recognitions}</span>
          <span class="stat-label">Conference Recognitions</span>
        </a>
        <a class="stat" href="/publications/phd-theses.html">
          <span class="stat-num">{theses_total}</span>
          <span class="stat-label">PhD Theses</span>
        </a>
        <div class="stat">
          <span class="stat-num">{ieee_grant_count}</span>
          <span class="stat-label">IEEE AP/MTT Students/<wbr>Postdocs Grants</span>
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
          <span class="stat-label">Coauthor Countries</span>
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
          <span class="stat-label">Commendations for Doctoral Thesis Excellence</span>
        </a>
        <a class="stat" href="/people/alumni.html">
          <span class="stat-num">{medal_count}</span>
          <span class="stat-label">University Doctoral Research Medals</span>
        </a>
      </div>"""
write_stats_block("publications/phd-theses.html", theses_stats_html)

# ---------- write into people/visitors.html ----------

visitors_stats_html = f"""      <div class="stats-row">
        <div class="stat">
          <span class="stat-num">{len(VISITOR_COUNTRIES)}</span>
          <span class="stat-label">Visitor Countries</span>
          <span class="stat-flags">{visitor_flags}</span>
        </div>
      </div>"""
write_stats_block("people/visitors.html", visitors_stats_html)

print(
    f"Wrote stats to index.html: {journal_total} journal articles "
    f"({journal_recognitions} recognitions), {conf_recognitions} conference recognitions, "
    f"{theses_total} PhD theses, {ieee_grant_count} IEEE student grants, "
    f"{medal_count} University Doctoral Research Medals, "
    f"{arc_grant_count} ARC research grants, {arc_fellow_count} ARC fellows, "
    f"{len(INTL_COLLAB_COUNTRIES)} international collaborator countries"
)
print(
    f"Wrote stats to publications/phd-theses.html: {commendation_count} commendations, "
    f"{medal_count} medals"
)
print(f"Wrote stats to people/visitors.html: {len(VISITOR_COUNTRIES)} visitor countries")
