"""Reads the journal and conference tables in content-raw/ into plain dicts.

Both files hold one markdown table per year under a "## YYYY" heading. The
header row names the columns, so their order doesn't matter:

    Citation, DOI / Link, Recognition, Notes, Status, Image, Topics, Abstract

Recognition is the single source of truth for what counts as a recognition:
a row has one if (and only if) its Recognition cell is non-empty. Both
build_publications.py (the gold chips) and build_stats.py (the counters)
read it through here, so they can never disagree.
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

COLUMNS = {
    "citation": "citation",
    "doi / link": "doi",
    "recognition": "recognition",
    "notes": "notes",
    "status": "status",
    "image": "image",
    "topics": "topics",
    "abstract": "abstract",
}

# Journal topic filters: the slugs allowed in the Topics column, and their button labels.
TOPIC_LABELS = [
    ("antennas", "Antennas & Beamforming"),
    ("metasurfaces", "Metasurfaces & Polarization Control"),
    ("integration", "Integrated Platforms & Waveguides"),
    ("comms", "Communications & 6G"),
    ("detectors", "Detectors"),
    ("nde", "Non-Destructive Evaluation & Materials"),
    ("reviews", "Reviews & Tutorials"),
]

YEAR_BLOCK_RE = re.compile(r"^## (\d{4})\n\n(.*?)(?=\n## |\n---|\Z)", re.S | re.M)
UNESCAPED_PIPE_RE = re.compile(r"(?<!\\)\|")


def split_row(line):
    return [c.strip() for c in UNESCAPED_PIPE_RE.split(line.strip()[1:-1])]


def read_tables(filename):
    """Return [(year, [row, ...]), ...] in file order (newest year first).
    Each row is a dict with every column in COLUMNS (empty string if the
    table has no such column or the cell is blank)."""
    with open(os.path.join(ROOT, "content-raw", filename), encoding="utf-8") as f:
        text = f.read()
    years = []
    for year, block in YEAR_BLOCK_RE.findall(text):
        lines = [l for l in block.strip().split("\n") if l.startswith("|")]
        header = []
        for name in split_row(lines[0]):
            if name.lower() not in COLUMNS:
                raise SystemExit(f"{filename}: unknown column {name!r} in the {year} table")
            header.append(COLUMNS[name.lower()])
        rows = []
        for line in lines[2:]:
            cells = split_row(line)
            if len(cells) != len(header):
                raise SystemExit(
                    f"{filename} ({year}): expected {len(header)} cells ({' | '.join(header)}) "
                    f"but found {len(cells)} in: {line[:70]}"
                )
            row = dict.fromkeys(COLUMNS.values(), "")
            row.update(zip(header, cells))
            row["abstract"] = row["abstract"].replace("\\|", "|")
            rows.append(row)
        years.append((year, rows))
    return years


def has_recognition(row):
    return bool(row["recognition"])


def read_flat_table(filename):
    """Read the single (year-less) table in a content-raw/*.md file into a list of
    dicts keyed by lower-cased header ("Year" -> "year")."""
    with open(os.path.join(ROOT, "content-raw", filename), encoding="utf-8") as f:
        lines = [l for l in f.read().splitlines() if l.startswith("|")]
    header = [h.lower() for h in split_row(lines[0])]
    rows = []
    for line in lines[2:]:
        cells = split_row(line)
        if len(cells) != len(header):
            raise SystemExit(f"{filename}: expected {len(header)} cells but found {len(cells)} in: {line[:70]}")
        rows.append(dict(zip(header, cells)))
    return rows


GROUPS = ("association", "patrons")


def read_logo_groups():
    groups, current = {}, None
    with open(os.path.join(ROOT, "content-raw", "home-logos.md"), encoding="utf-8") as f:
        lines = f.read().splitlines()
    in_comment = False
    for n, line in enumerate(lines, 1):
        if in_comment:
            in_comment = "-->" not in line
            continue
        if line.startswith("<!--"):
            in_comment = "-->" not in line
            continue
        if line.startswith("## "):
            current = line[3:].strip().lower()
            if current not in GROUPS:
                raise SystemExit(f"home-logos.md:{n}: heading must be one of {', '.join(GROUPS)}")
            groups[current] = {"header": None, "rows": []}
        elif line.startswith("|"):
            if current is None:
                raise SystemExit(f"home-logos.md:{n}: a table must come under a '## association' or '## patrons' heading")
            cells = split_row(line)
            g = groups[current]
            if g["header"] is None:
                g["header"] = [c.lower() for c in cells]
                if g["header"] != ["name", "link", "logo"]:
                    raise SystemExit(f"home-logos.md:{n}: the table header must be: Name | Link | Logo")
            elif re.fullmatch(r"[-| ]+", line.strip("|")) or set(line) <= set("|- "):
                continue
            else:
                if len(cells) != 3 or not all(cells):
                    raise SystemExit(f"home-logos.md:{n}: expected Name | Link | Logo, got: {line[:70]}")
                g["rows"].append(dict(zip(("name", "link", "logo"), cells)))
    for g in GROUPS:
        if g not in groups or not groups[g]["rows"]:
            raise SystemExit(f"home-logos.md: no logos found under '## {g}'")
    return {g: groups[g]["rows"] for g in GROUPS}
