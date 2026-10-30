"""Regenerate the research cluster cards and the experiment gallery on research.html
from content-raw/research-clusters.md and research-gallery.md.

Only the parts between the CLUSTERS and GALLERY markers are replaced.
"""
import html
import os
import re

from carddata import ROOT, read_cards

PAGE = os.path.join(ROOT, "research.html")


def esc(s):
    return html.escape(s, quote=False)


def cluster_card(c):
    rows = [
        '          <div class="card">',
        f'            <img src="/assets/img/research/{html.escape(c["image"], quote=True)}" alt="{html.escape(c["alt"], quote=True)}" loading="lazy">',
        f'            <h3>{esc(c["title"])}</h3>',
        f'            <p>{esc(c["text"])}</p>',
    ]
    tags = [t.strip() for t in c.get("tags", "").split(";") if t.strip()]
    if tags:
        rows.append('            <div class="tag-row">')
        rows.append("              " + "".join(f'<span class="tag">{esc(t)}</span>' for t in tags))
        rows.append("            </div>")
    rows.append("          </div>")
    return "\n".join(rows)


def clusters_html(sections):
    blocks = []
    for sec in sections:
        blocks.append(
            '      <div class="cluster-group">\n'
            f'        <h2>{esc(sec["heading"])}</h2>\n'
            '        <div class="card-grid card-grid-compact">\n'
            + "\n".join(cluster_card(c) for c in sec["cards"])
            + "\n        </div>\n      </div>"
        )
    return "\n\n".join(blocks)


def gallery_card(c):
    img = html.escape(c["image"], quote=True)
    return (
        '        <div class="card">\n'
        f'          <a class="lightbox-link" href="/assets/img/research/{img}">\n'
        f'            <img src="/assets/img/research/{img}" alt="{html.escape(c["alt"], quote=True)}" loading="lazy">\n'
        "          </a>\n"
        f'          <p class="small">{esc(c["title"])}</p>\n'
        "        </div>"
    )


def replace_region(text, name, new_inner, indent):
    pattern = re.compile(rf"{indent}<!-- {name}:START -->.*?<!-- {name}:END -->", re.S)
    new = f"{indent}<!-- {name}:START -->\n{new_inner}\n{indent}<!-- {name}:END -->"
    out, n = pattern.subn(lambda m: new, text, count=1)
    if n != 1:
        raise SystemExit(f"research.html: <!-- {name}:START --> ... <!-- {name}:END --> markers not found")
    return out


clusters = read_cards("research-clusters.md", ("image", "alt", "text", "tags"), ("image", "alt", "text"))
gallery = read_cards("research-gallery.md", ("image", "alt"), ("image", "alt"))

with open(PAGE, encoding="utf-8") as f:
    text = f.read()
text = replace_region(text, "CLUSTERS", clusters_html(clusters), "      ")
text = replace_region(text, "GALLERY", "\n".join(gallery_card(c) for sec in gallery for c in sec["cards"]), "        ")
with open(PAGE, "w", encoding="utf-8", newline="\n") as f:
    f.write(text)

n_cards = sum(len(s["cards"]) for s in clusters)
n_gallery = sum(len(s["cards"]) for s in gallery)
print(f"Wrote research.html - {len(clusters)} clusters, {n_cards} cards, {n_gallery} gallery photos")
