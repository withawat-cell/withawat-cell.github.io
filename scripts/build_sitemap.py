"""Write sitemap.xml from the site's pages, in menu order.

Every page the build knows about is listed, so a new page can't be forgotten.
No <lastmod> dates: they would depend on git history and make the build differ
between machines, and Google crawls the site regardless.
"""
import os

import shell

ROOT = shell.ROOT
SITE = "https://thz-el.org"


def menu_hrefs():
    out = []
    for _label, target in shell.NAV:
        if isinstance(target, str):
            out.append(target)
        else:
            out.extend(href for _l, href in target)
    return out


def url_for(href):
    return SITE + "/" if href == "/index.html" else SITE + href


pages = {"/" + os.path.relpath(p, ROOT).replace(os.sep, "/") for p in shell.page_files()}
ordered = [h for h in menu_hrefs() if h in pages]
ordered += sorted(pages - set(ordered))  # pages that are not in the menu go last

lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
lines += [f"  <url><loc>{url_for(h)}</loc></url>" for h in ordered]
lines.append("</urlset>")

with open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8", newline="\n") as f:
    f.write("\n".join(lines) + "\n")
print(f"Wrote sitemap.xml - {len(ordered)} pages")
