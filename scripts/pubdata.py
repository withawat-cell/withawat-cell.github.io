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

YEAR_BLOCK_RE = re.compile(r"^## (\d{4})\n\n(.*?)(?=\n## |\n---)", re.S | re.M)
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
            row = dict.fromkeys(COLUMNS.values(), "")
            row.update(zip(header, split_row(line)))
            row["abstract"] = row["abstract"].replace("\\|", "|")
            rows.append(row)
        years.append((year, rows))
    return years


def has_recognition(row):
    return bool(row["recognition"])
