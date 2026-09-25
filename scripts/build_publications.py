import re
import os
import json
import html

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_V = "20260923i"

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

def md_inline(s):
    s = s.strip()
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
    s = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", s)
    return s

TRIM_PREFIXES = ["One of the "]
MAX_PILL_LEN = 46

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
SPECIAL_ISSUE_RE = re.compile(r"\bSpecial Issue\b", re.I)
SPECIAL_COLLECTION_RE = re.compile(r"\bSpecial (Collection|Cluster)\b", re.I)
SPECIAL_KEEP_AS_CHIP = {
    "Special collection of standout research in integrated photonics",
    "Selected by the committee for Special Issue on Asia-Pacific Microwave Conference 2025",
}
ALWAYS_PLAIN = {
    "Supplementary video",
    "online",
}

def cap_first(s):
    for i, ch in enumerate(s):
        if ch.isalpha():
            return s[:i] + ch.upper() + s[i + 1:]
    return s

def split_notes(notes):
    """Split a Notes cell into (pills, remainder_html).
    Each pill is a dict: {short, full (title tooltip or None), href (or None)}.
    Special Issue/Collection/Cluster mentions are always demoted to plain
    text (not chips) -- they're a themed sub-grouping, not a recognition, so
    they read as prose rather than an award-style tag."""
    if not notes or not notes.strip():
        return [], ""
    notes = linkify_known(notes)
    parts = [p.strip() for p in notes.split(";") if p.strip()]
    pills, rest = [], []

    def add_pill(text, href):
        plain = re.sub(r"<[^>]+>", "", text)
        # "Special collection of standout research ..." is a recognition, not
        # a themed special-issue/collection name, so it stays a chip
        demote = plain.strip() in ALWAYS_PLAIN or (
            plain.strip() not in SPECIAL_KEEP_AS_CHIP and (
                SPECIAL_COLLECTION_RE.search(plain) or SPECIAL_ISSUE_RE.search(plain)
            )
        )
        if demote:
            rest.append(f'<a href="{href}">{text}</a>' if href else text)
            return
        shortened = shorten(text)
        short = cap_first(shortened)
        full = text if shortened != text else None
        pills.append({"short": short, "full": full, "href": href})

    for p in parts:
        p_html = md_inline(p)
        links = LINK_RE.findall(p_html)
        plain_len = len(re.sub(r"<[^>]+>", "", p_html))
        anchor_len = sum(len(t) for _, t in links)
        if not links:
            add_pill(p_html, None)
        elif len(links) == 1 and anchor_len >= plain_len * 0.7:
            href, text = links[0]
            add_pill(text, href)
        elif len(links) >= 2:
            # several linked outlets in one clause, e.g.
            # "Covered by X (url), Y (url), Z (url), and other online media"
            for href, text in links:
                add_pill(text, href)
            # the leftover "Covered by ..., and other online scientific news
            # media" filler is dropped entirely -- the outlet chips already
            # say it was covered by press
        else:
            rest.append(p_html)
    return pills, " &middot; ".join(rest)

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
    return '<span class="tag-row" style="margin-top:6px;">' + "".join(spans) + "</span>"

# ---------- Journal articles ----------

def load_journal_images():
    path = os.path.join(ROOT, "content-raw", "journal-article-images.txt")
    imgs = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            idx, url = line.split("|", 1)
            if url != "MISSING":
                imgs[int(idx)] = f"/assets/img/publications/j{idx}.jpg"
    return imgs

TITLE_RE = re.compile(r'"([^"]+)"')

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

TOPIC_LABELS = [
    ("antennas", "Antennas & Beamforming"),
    ("metasurfaces", "Metasurfaces & Polarization Control"),
    ("integration", "Integrated Platforms & Waveguides"),
    ("comms", "Communications & 6G"),
    ("detectors", "Detectors"),
    ("nde", "Non-Destructive Evaluation & Materials"),
    ("reviews", "Reviews & Tutorials"),
]

def build_journal():
    src = os.path.join(ROOT, "content-raw", "publications-journal-articles.md")
    with open(src, encoding="utf-8") as f:
        text = f.read()
    year_blocks = re.findall(r"^## (\d{4})\n\n(.*?)(?=\n## |\n---)", text, re.S | re.M)
    images = load_journal_images()
    used_bibtex_keys = set()

    sections = []
    global_idx = 0
    for year, block in year_blocks:
        rows = [l for l in block.strip().split("\n") if l.startswith("|")][2:]
        entries = []
        for row in rows:
            cells = [c.strip() for c in row.strip().strip("|").split("|")]
            if len(cells) < 4:
                continue
            _, citation, doi, notes = cells[:4]
            topics = cells[4].strip() if len(cells) > 4 else ""
            doi = doi.strip()
            primary_doi = doi.split(" ")[0] if doi.startswith("http") else ""
            citation_html = md_inline(citation)
            m = TITLE_RE.search(citation_html)
            if m and primary_doi:
                title_linked = f'<a href="{html.escape(primary_doi)}">{m.group(1)}</a>'
                citation_html = citation_html[:m.start()] + '"' + title_linked + '"' + citation_html[m.end():]
            pills, rest = split_notes(notes)
            accepted = any(p["short"] == "Accepted" for p in pills)
            if accepted:
                pills = [p for p in pills if p["short"] != "Accepted"]
                citation_html += " (Accepted)"
            plain_citation = citation.replace("*", "")
            if accepted:
                plain_citation += " (Accepted)"
            img = images.get(global_idx)
            thumb = f'<img class="pub-thumb" src="{img}?v={CACHE_V}" alt="" loading="lazy">' if img else '<span class="pub-thumb-empty" aria-hidden="true"></span>'
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
            entries.append(f'''      <li class="pub-entry" data-topics="{topics}">
        {thumb}
        <div class="entry-body">
          <p class="entry-title">{citation_html} {copy_btn}{bibtex_btn}</p>
          {meta_html}
          {pills_html(pills)}
        </div>
      </li>''')
            global_idx += 1
        sections.append(f'    <div class="year-block" data-year="{year}">\n      <h3 class="year-heading">{year}</h3>\n      <ul class="pub-list">\n' + "\n".join(entries) + "\n      </ul>\n    </div>")
    years = [y for y, _ in year_blocks]
    return "\n\n".join(sections), years

# ---------- Conference presentations ----------

def build_conference():
    src = os.path.join(ROOT, "content-raw", "publications-conference-presentations.md")
    with open(src, encoding="utf-8") as f:
        text = f.read()
    year_blocks = re.findall(r"^## (\d{4})\n((?:\d+\..*\n?)+)", text, re.M)
    sections = []
    for year, block in year_blocks:
        lines = [l.strip() for l in block.strip().split("\n") if l.strip()]
        entries = []
        for line in lines:
            m = re.match(r"^\d+\.\s+(.*)$", line)
            if not m:
                continue
            raw = m.group(1)
            # pull trailing "(...)" status annotation off the end, e.g. "(Invited)"
            # or "(Keynote; online)" -- allow one level of nested parens so a
            # linked status like "([Invited](url); online)" still matches
            status_m = re.search(r"\(((?:[^()]|\([^()]*\))*)\)\s*$", raw)
            pills, rest_note = [], ""
            if status_m:
                inner = status_m.group(1)
                raw_wo = raw[:status_m.start()].rstrip()
                sub_pills, sub_rest = split_notes(inner)
                pills = sub_pills
                rest_items = [x.strip() for x in sub_rest.split(" &middot; ")] if sub_rest else []
                online_suffix = ""
                if "online" in rest_items:
                    rest_items.remove("online")
                    online_suffix = " (Online)"
                rest_note = " &middot; ".join(rest_items)
            else:
                raw_wo = raw
                online_suffix = ""
            citation_html = md_inline(raw_wo) + online_suffix
            meta_html = f'<p class="entry-meta">{rest_note}</p>' if rest_note else ""
            inline_pills = pills_html(pills).replace('<span class="tag-row" style="margin-top:6px;">', '<span class="tag-row tag-row-inline">')
            entries.append(f'''      <li class="pub-entry">
        <div class="entry-body">
          <p class="entry-title">{citation_html} {inline_pills}</p>
          {meta_html}
        </div>
      </li>''')
        sections.append(f'    <h3 class="year-heading">{year}</h3>\n    <ul class="pub-list">\n' + "\n".join(entries) + "\n    </ul>")
    return "\n\n".join(sections)

journal_html, journal_years = build_journal()
conference_html = build_conference()

year_filter_options = "\n".join(
    f'          <option value="{y}">{y}</option>' for y in journal_years
)

theses_html = '''      <table class="data">
        <thead>
          <tr><th>Year</th><th>Author</th><th>Thesis title</th></tr>
        </thead>
        <tbody>
          <tr><td>2026</td><td>Sakib Quader</td><td><a href="/assets/theses/quader-2026.pdf">Terahertz Metasurfaces for Wave Manipulation, Detection, and Spectral Analysis</a></td></tr>
          <tr><td>2026</td><td>Linxi Chen</td><td><a href="/assets/theses/linxi-chen-2026.pdf">Enabling Polarisation and Frequency Control in Silicon-based Terahertz Integration</a></td></tr>
          <tr><td>2026</td><td>Bryce Chung</td><td><a href="/assets/theses/bryce-chung-2026.pdf">3D-Printed Quasi-Optical Systems for Terahertz Non-Destructive Testing</a></td></tr>
          <tr><td>2025</td><td>Harrison Lees</td><td><a href="/assets/theses/harrison-lees-2025.pdf">All-dielectric Terahertz Waveguides, Devices, and Techniques</a></td></tr>
          <tr><td>2024</td><td>Stephen Li</td><td><a href="/assets/theses/stephen-li-2024.pdf">Planar Antennas and Lenses for Terahertz Source Integration</a></td></tr>
          <tr><td>2024</td><td>Panisa Dechwechprasit</td><td><a href="/assets/theses/panisa-dechwechprasit-2024.pdf">Tunable Terahertz Components on Substrateless Silicon Platform</a></td></tr>
          <tr><td>2023</td><td>Mohamed Shehata</td><td><a href="/assets/theses/mohamed-shehata-2023.pdf">Pulse Shaping for Terahertz Communications</a></td></tr>
          <tr><td>2022</td><td>Weijie Gao</td><td><a href="/assets/theses/weijie-gao-2022.pdf">Effective-Medium-Clad Dielectric Components Towards Terahertz Integrated Platform</a></td></tr>
          <tr><td>2021</td><td>Xiaolong You</td><td><a href="/assets/theses/xiaolong-you-2021.pdf">Broadband Terahertz Metasurfaces</a></td></tr>
          <tr><td>2018</td><td>Wendy S.-L. Lee</td><td><a href="/assets/theses/wendy-lee-2018.pdf">Terahertz Metasurfaces for Wideband Polarisation Control</a></td></tr>
          <tr><td>2017</td><td>Daniel Headland</td><td><a href="/assets/theses/daniel-headland-2017.pdf">Efficient Terahertz-Range Beam Control Using Flat Optics</a></td></tr>
        </tbody>
      </table>'''

codes_html = '''      <div class="card-grid">
        <div class="card">
          <img src="/assets/img/research/code-comm-chain.jpg?v=20260921g" alt="End-to-end wireless communication chain simulator interface" loading="lazy">
          <h3>End-to-End Wireless Communication Chain Simulator</h3>
          <p>A MATLAB application for modelling, testing, and demonstrating complete wireless communication chains, built to align with the laboratory's transmission hardware. It supports sinusoidal and complex waveform transmission, with built-in digital compensation modules, including IQ-imbalance correction and coarse time-synchronisation, for evaluating system robustness and isolating hardware-induced impairments. Designed as a standalone interface for rapid experimentation, algorithm development, and hardware-in-the-loop testing.</p>
          <p class="small">Developed by <a href="https://www.linkedin.com/in/marlon-kha-208141293/">Marlon Kha</a></p>
          <div class="entry-links"><a href="https://github.com/withawat-cell/comm_chain.git">Repository &rarr;</a></div>
        </div>
        <div class="card">
          <img src="/assets/img/research/code-cst-sim.jpg?v=20260921g" alt="CST simulation of a substrateless terahertz waveguide" loading="lazy">
          <h3>CST Simulation of Substrateless Terahertz Waveguide</h3>
          <p>A Python automation script for CST Studio Suite (Python 3.12, CST Microwave Studio 2025) that builds, configures, and runs full-wave transient simulations for substrateless (effective-medium-clad) dielectric terahertz waveguides, based on the design principles below.</p>
          <p class="small">W. Gao, X. Yu, M. Fujita, T. Nagatsuma, C. Fumeaux, and W. Withayachumnankul, "<a href="https://doi.org/10.1364/OE.382181">Effective-medium-cladded dielectric waveguides for terahertz waves</a>," <em>Optics Express</em>, vol. 27, no. 26, pp. 38721&ndash;38734, 2019.<br>
          W. Gao, W. S.-L. Lee, X. Yu, M. Fujita, T. Nagatsuma, C. Fumeaux, and W. Withayachumnankul, "<a href="https://doi.org/10.1109/TTHZ.2020.3023917">Characteristics of effective-medium-clad dielectric waveguides</a>," <em>IEEE Transactions on Terahertz Science and Technology</em>, vol. 11, no. 1, pp. 28&ndash;41, 2021.</p>
          <div class="entry-links"><a href="https://gist.github.com/withawat-cell/5f3192e66faae0e291e63ef4a68d6c75">Gist &rarr;</a></div>
        </div>
      </div>'''

# ---------- shared page shell ----------

SUBPAGES = [
    ("journal-articles", "Journal Articles"),
    ("conference-presentations", "Conference Presentations"),
    ("phd-theses", "PhD Theses"),
    ("codes", "Codes"),
]

def nav_html(active_slug):
    items = []
    for slug, label in SUBPAGES:
        current = ' aria-current="page"' if slug == active_slug else ""
        items.append(f'            <a href="/publications/{slug}.html"{current}>{label}</a>')
    open_cls = " open" if active_slug else ""
    return f'''        <li class="has-children{open_cls}">
          <button class="nav-parent" aria-expanded="false">Publications</button>
          <div class="submenu">
{chr(10).join(items)}
          </div>
        </li>'''

def page(slug, title, description, eyebrow, h1, lead, body, extra_head="", extra_scripts=""):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<title>{title} — Terahertz Engineering Laboratory</title>
<meta name="description" content="{description}">
<link rel="canonical" href="https://thz-el.org/publications/{slug}.html">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Terahertz Engineering Laboratory">
<meta property="og:title" content="{title} — Terahertz Engineering Laboratory">
<meta property="og:description" content="{description}">
<meta property="og:url" content="https://thz-el.org/publications/{slug}.html">
<meta property="og:image" content="https://thz-el.org/assets/img/group-photo-1.jpg">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/assets/img/brand/favicon.png" type="image/png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/css/style.css?v={CACHE_V}">{extra_head}
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
{nav_html(slug)}
        <li class="has-children">
          <button class="nav-parent" aria-expanded="false">People</button>
          <div class="submenu">
            <a href="/people/researchers.html">Researchers</a>
            <a href="/people/alumni.html">Alumni</a>
            <a href="/people/coursework.html">Coursework Students</a>
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
      <p class="hero-eyebrow">{eyebrow}</p>
      <h1>{h1}</h1>
      <p class="lead">{lead}</p>
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

<script src="/assets/js/main.js?v={CACHE_V}"></script>{extra_scripts}
</body>
</html>
"""

pub_dir = os.path.join(ROOT, "publications")
os.makedirs(pub_dir, exist_ok=True)

topic_filter_buttons = "\n".join(
    f'          <button type="button" class="topic-filter-btn" data-topic="{slug}" aria-pressed="false">{label}</button>'
    for slug, label in TOPIC_LABELS
)

# Journal articles
journal_body = f'''      <div style="display:flex; justify-content:space-between; align-items:flex-end; flex-wrap:wrap; gap:16px;">
        <p class="prose small" style="margin-bottom:0;">Most recent first. Excludes journal publications prior to the lab's establishment and those in the microwave and optics domains outside terahertz.</p>
        <label class="year-filter-label">Year
          <select id="journal-year-filter" class="year-filter">
            <option value="all">All years</option>
{year_filter_options}
          </select>
        </label>
      </div>
      <div class="topic-filter" role="group" aria-label="Filter by topic" style="margin-top:16px;">
{topic_filter_buttons}
      </div>
      <div style="margin-top:24px;">
{journal_html}
      </div>'''
out = page(
    "journal-articles", "Journal Articles",
    "Journal articles from the Terahertz Engineering Laboratory, Adelaide University.",
    "Publications", "Journal articles",
    "Peer-reviewed journal articles from the Terahertz Engineering Laboratory.",
    journal_body,
    extra_scripts=f'\n<script src="/assets/js/publications-filter.js?v={CACHE_V}"></script>',
)
with open(os.path.join(pub_dir, "journal-articles.html"), "w", encoding="utf-8") as f:
    f.write(out)

# Conference presentations
out = page(
    "conference-presentations", "Conference Presentations",
    "Conference presentations from the Terahertz Engineering Laboratory, Adelaide University.",
    "Publications", "Selected conference presentations",
    "Invited talks, keynotes, and presentations at international conferences and workshops.",
    conference_html,
)
with open(os.path.join(pub_dir, "conference-presentations.html"), "w", encoding="utf-8") as f:
    f.write(out)

# PhD theses
out = page(
    "phd-theses", "PhD Theses",
    "PhD theses produced at the Terahertz Engineering Laboratory, Adelaide University.",
    "Publications", "PhD theses",
    "Doctoral theses completed at the Terahertz Engineering Laboratory.",
    theses_html,
)
with open(os.path.join(pub_dir, "phd-theses.html"), "w", encoding="utf-8") as f:
    f.write(out)

# Codes
out = page(
    "codes", "Codes",
    "Research software from the Terahertz Engineering Laboratory, Adelaide University.",
    "Publications", "Codes",
    "Research software developed at the Terahertz Engineering Laboratory.",
    codes_html,
)
with open(os.path.join(pub_dir, "codes.html"), "w", encoding="utf-8") as f:
    f.write(out)

print("Wrote publications/journal-articles.html, conference-presentations.html, phd-theses.html, codes.html")
