"""Reads the people lists in content-raw/people-*.md and renders them as cards.

Format (one file per page; see the comment at the top of each file):

    Grid: wide                      (wide = portrait left of the text, compact = small cards)

    ## Section heading              (optional; people before any heading form an unnamed section)
    Intro: A note shown above the heading.      (optional)

    ### Person name
    - Photo: file.webp              (inside assets/img/people/)
    - Profile: https://...          (optional: makes the name a link)
    - Role: Group Leader
    - Info: Any line of text, with [links](https://...)     (repeat for more lines)
    - Awards: IEEE Fellow; Optica Fellow                    (gold chips, separated by ;)
    - Email: name@adelaide.edu.au   (optional)
    - Scholar: https://scholar.google.com/...               (optional)
    - LinkedIn: https://www.linkedin.com/in/...             (optional)

Info and Awards lines appear on the card in the order written. Everything the
award stats count (build_stats.py) is read from the same data.
"""
import html
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")

KEYS = {
    "photo": "photo", "profile": "profile", "role": "role", "info": "info",
    "awards": "awards", "email": "email", "scholar": "scholar", "linkedin": "linkedin",
}

ICON_ATTRS = 'viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"'
ICONS = {
    "email": ("Email", f'<svg {ICON_ATTRS}><rect x="2" y="4" width="20" height="16" rx="2"></rect><path d="m2 7 10 7 10-7"></path></svg>'),
    "scholar": ("Google Scholar", f'<svg {ICON_ATTRS}><path d="M22 10 12 5 2 10l10 5 10-5Z"></path><path d="M6 12v5c0 1.5 3 3 6 3s6-1.5 6-3v-5"></path></svg>'),
    "linkedin": ("LinkedIn", f'<svg {ICON_ATTRS}><path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z"></path><rect x="2" y="9" width="4" height="12"></rect><circle cx="4" cy="4" r="2"></circle></svg>'),
}


def inline_html(text):
    """Escape plain text and turn [label](url) into links."""
    out, pos = [], 0
    for m in LINK_RE.finditer(text):
        out.append(html.escape(text[pos:m.start()], quote=False))
        out.append(f'<a href="{html.escape(m.group(2), quote=True)}">{html.escape(m.group(1), quote=False)}</a>')
        pos = m.end()
    out.append(html.escape(text[pos:], quote=False))
    return "".join(out)


def plain(text):
    """The text a visitor reads: [label](url) -> label."""
    return LINK_RE.sub(r"\1", text)


def read_people(filename):
    path = os.path.join(ROOT, "content-raw", filename)
    page = {"grid": "wide", "sections": []}
    section = person = None
    in_comment = False
    with open(path, encoding="utf-8") as f:
        lines = f.read().split("\n")
    for n, raw in enumerate(lines, 1):
        line = raw.rstrip()
        where = f"{filename}:{n}"
        if in_comment:
            in_comment = "-->" not in line
            continue
        if line.startswith("<!--"):
            in_comment = "-->" not in line
            continue
        if not line.strip() or line.startswith("# "):
            continue
        if line.startswith("Grid:"):
            page["grid"] = line.split(":", 1)[1].strip()
            if page["grid"] not in ("wide", "compact"):
                raise SystemExit(f"{where}: Grid must be 'wide' or 'compact'")
        elif line.startswith("## "):
            section = {"heading": line[3:].strip(), "intro": "", "people": []}
            page["sections"].append(section)
            person = None
        elif line.startswith("Intro:"):
            if section is None or person is not None:
                raise SystemExit(f"{where}: Intro: belongs directly under a '## heading'")
            section["intro"] = line.split(":", 1)[1].strip()
        elif line.startswith("### "):
            if section is None:
                section = {"heading": "", "intro": "", "people": []}
                page["sections"].append(section)
            person = {"name": line[4:].strip(), "lines": [], "where": where}
            section["people"].append(person)
        elif line.startswith("- "):
            if person is None:
                raise SystemExit(f"{where}: a '- Key: value' line must come under a '### Name'")
            key, _, value = line[2:].partition(":")
            key = key.strip().lower()
            if key not in KEYS:
                raise SystemExit(f"{where}: unknown field {key!r} (allowed: {', '.join(k.title() for k in KEYS)})")
            value = value.strip()
            if key in ("info", "awards"):
                person["lines"].append((key, value))
            elif key in person:
                raise SystemExit(f"{where}: {key!r} given twice for {person['name']}")
            else:
                person[key] = value
        else:
            raise SystemExit(f"{where}: can't read this line: {line[:60]!r}")
    for sec in page["sections"]:
        for p in sec["people"]:
            for req in ("photo", "role"):
                if not p.get(req):
                    raise SystemExit(f"{p['where']}: {p['name']} is missing '{req.title()}'")
            p["awards"] = [a.strip() for kind, v in p["lines"] if kind == "awards" for a in v.split(";") if a.strip()]
            p["info"] = [v for kind, v in p["lines"] if kind == "info"]
    return page


def card_html(p):
    name = html.escape(p["name"], quote=False)
    name_html = f'<a href="{html.escape(p["profile"], quote=True)}">{name}</a>' if p.get("profile") else name
    rows = [
        '        <div class="person">',
        f'          <img class="person-photo" src="/assets/img/people/{html.escape(p["photo"], quote=True)}" alt="{html.escape(p["name"], quote=True)}" loading="lazy">',
        f'          <p class="person-name">{name_html}</p>',
        f'          <p class="person-role">{inline_html(p["role"])}</p>',
    ]
    for kind, value in p["lines"]:
        if kind == "info":
            rows.append(f'          <p class="person-meta">{inline_html(value)}</p>')
        else:
            notes = [f'<span class="tag-note">{inline_html(a.strip())}</span>' for a in value.split(";") if a.strip()]
            rows.append('          <p class="person-meta awards-line">' + ' <span class="note-sep">&bull;</span> '.join(notes) + "</p>")
    links = []
    for key in ("email", "scholar", "linkedin"):
        if p.get(key):
            label, svg = ICONS[key]
            href = ("mailto:" + p[key]) if key == "email" else p[key]
            links.append(f'<a href="{html.escape(href, quote=True)}" aria-label="{label}" title="{label}">{svg}</a>')
    if links:
        rows.append('          <div class="person-links">' + "".join(links) + "</div>")
    rows.append("        </div>")
    return "\n".join(rows)


def sections_html(page):
    blocks = []
    for sec in page["sections"]:
        parts = ['  <section class="block">', '    <div class="wrap-wide">']
        if sec["intro"]:
            parts.append(f'      <p class="small section-intro">{inline_html(sec["intro"])}</p>')
        if sec["heading"]:
            parts.append(f'      <h2>{html.escape(sec["heading"], quote=False)}</h2>')
        parts.append(f'      <div class="people-grid people-grid-{page["grid"]}">')
        parts.append("")
        parts.append("\n\n".join(card_html(p) for p in sec["people"]))
        parts.append("")
        parts.append("      </div>")
        parts.append("    </div>")
        parts.append("  </section>")
        blocks.append("\n".join(parts))
    return "\n\n".join(blocks)


# ---------------------------------------------------------------- coursework students
# Shared by build_coursework.py (the table) and build_stats.py (the counters).


def split_items(cell):
    """The ';'-separated items of an Awards or Notes cell."""
    return [c.strip() for c in cell.split(";") if c.strip()]


def coursework_rows():
    """[(year, [(name, years, area, awards, notes), ...]), ...] from people-coursework.md."""
    with open(os.path.join(ROOT, "content-raw", "people-coursework.md"), encoding="utf-8") as f:
        text = f.read()
    years = []
    for year, block in re.findall(r"^## (\d{4})\n\|(.*?)\n\n", text, re.S | re.M):
        rows = [l for l in ("|" + block).strip().split("\n") if l.startswith("|")][2:]
        parsed = []
        for row in rows:
            cells = [c.strip() for c in row.strip().strip("|").split("|")]
            if len(cells) != 5:
                raise SystemExit(
                    f"people-coursework.md ({year}): expected 5 cells (Name | Year(s) | Area | Awards | Notes), "
                    f"got {len(cells)} in: {row[:70]}"
                )
            parsed.append(tuple(cells))
        years.append((year, parsed))
    return years


def plain_md(text):
    """What a visitor reads for a markdown snippet: links -> label, *emphasis* -> text."""
    return re.sub(r"\*([^*]+)\*", r"\1", plain(text)).strip()
