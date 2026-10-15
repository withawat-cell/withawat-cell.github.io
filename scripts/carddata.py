"""Reader for the simple "cards" markdown files (research clusters, gallery).

    ## Section heading            (optional; cards before any heading form an unnamed section)

    ### Card title
    - Image: file.webp             (inside assets/img/research/)
    - Alt: Description of the picture
    - Text: One paragraph, all on one line.
    - Tags: first tag; second tag    (optional, separated by ;)

Which fields a file accepts is decided by the script that reads it.
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read_cards(filename, fields, required=()):
    path = os.path.join(ROOT, "content-raw", filename)
    sections, section, card, in_comment = [], None, None, False
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
        if line.startswith("## "):
            section = {"heading": line[3:].strip(), "cards": []}
            sections.append(section)
            card = None
        elif line.startswith("### "):
            if section is None:
                section = {"heading": "", "cards": []}
                sections.append(section)
            card = {"title": line[4:].strip(), "where": where}
            section["cards"].append(card)
        elif line.startswith("- "):
            if card is None:
                raise SystemExit(f"{where}: a '- Field: value' line must come under a '### Title'")
            key, _, value = line[2:].partition(":")
            key = key.strip().lower()
            if key not in fields:
                raise SystemExit(f"{where}: unknown field {key!r} (allowed: {', '.join(f.title() for f in fields)})")
            if key in card:
                raise SystemExit(f"{where}: {key!r} given twice for {card['title']}")
            card[key] = value.strip()
        else:
            raise SystemExit(f"{where}: can't read this line: {line[:60]!r}")
    for sec in sections:
        for c in sec["cards"]:
            for req in required:
                if not c.get(req):
                    raise SystemExit(f"{c['where']}: {c['title']} is missing '{req.title()}'")
    return sections
