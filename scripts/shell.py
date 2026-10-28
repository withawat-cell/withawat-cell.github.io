"""The site's shared page shell: header/nav, footer and cache-busting.

Edit NAV or FOOTER_* below to change the menu or footer on EVERY page, then
run `python scripts/build_all.py`. Pages only need an (even empty)
`<header class="site-header"></header>` and `<footer class="site-footer"></footer>`;
stamp_html() fills them in and marks the current page in the menu.

stamp_html() also gives every local css/js/image reference (`/assets/...`) a
`?v=<hash of that file>` suffix, so browsers re-download an asset exactly when
its contents change. Nothing ever needs bumping by hand.
"""
import hashlib
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SITE_NAME = "Terahertz Engineering Laboratory"

# (label, href) is a plain link; (label, [(label, href), ...]) is a dropdown.
NAV = [
    ("Home", "/index.html"),
    ("Research", "/research.html"),
    ("Publications", [
        ("Journal Articles", "/publications/journal-articles.html"),
        ("Conference Presentations", "/publications/conference-presentations.html"),
        ("PhD Theses", "/publications/phd-theses.html"),
        ("Codes", "/publications/codes.html"),
    ]),
    ("People", [
        ("Researchers", "/people/researchers.html"),
        ("Alumni", "/people/alumni.html"),
        ("Coursework Students", "/people/coursework.html"),
        ("Visitors", "/people/visitors.html"),
    ]),
    ("Opportunities", "/opportunities.html"),
    ("Contact", "/contact.html"),
]

FOOTER_COPYRIGHT = "Terahertz Engineering Laboratory, Adelaide University"
FOOTER_LINKS = [
    ("Contact", "/contact.html"),
    ("LinkedIn", "https://www.linkedin.com/company/thz-el"),
]


def header_html(current):
    """current: the page's root-relative path, e.g. "/people/alumni.html"."""
    def link(label, href, indent):
        mark = ' aria-current="page"' if href == current else ""
        return f'{indent}<a href="{href}"{mark}>{label}</a>'

    items = []
    for label, target in NAV:
        if isinstance(target, str):
            items.append(f'        <li>{link(label, target, "").strip()}</li>')
        else:
            sub = "\n".join(link(l, h, "            ") for l, h in target)
            items.append(
                '        <li class="has-children">\n'
                f'          <button class="nav-parent" aria-expanded="false">{label}</button>\n'
                '          <div class="submenu">\n'
                f"{sub}\n"
                "          </div>\n"
                "        </li>"
            )
    nav = "\n".join(items)
    return f'''<header class="site-header">
  <div class="site-header-inner">
    <a class="brand plain" href="/index.html">
      <img class="brand-mark" src="/assets/img/brand/mark-white.webp" alt="THz">
      <span class="brand-name">{SITE_NAME}</span>
    </a>
    <nav class="primary-nav" aria-label="Primary">
      <ul>
{nav}
      </ul>
    </nav>
    <button class="nav-toggle" aria-label="Toggle navigation" aria-expanded="false"><span></span></button>
  </div>
</header>'''


def footer_html():
    links = " &middot; ".join(f'<a href="{h}">{l}</a>' for l, h in FOOTER_LINKS)
    return f'''<footer class="site-footer">
  <div class="wrap-wide" style="display:block;">
    <div style="display:flex; justify-content:space-between; flex-wrap:wrap; gap:16px;">
      <span>&copy; <span data-copyright-year>2026</span> {FOOTER_COPYRIGHT}</span>
      <span>{links}</span>
    </div>
  </div>
</footer>'''


# matches any earlier form of the analytics tag so a rebuild always leaves exactly one
BEACON_RE = re.compile(
    r"""[ \t]*<script(?:[^>]*src=["']https://static\.cloudflareinsights\.com/beacon\.min\.js["'][^>]*>|>[^<]*static\.cloudflareinsights\.com[^<]*)</script>\n?"""
)


def analytics_token():
    """The Cloudflare Web Analytics token from content-raw/site-config.json ("" = off)."""
    with open(os.path.join(ROOT, "content-raw", "site-config.json"), encoding="utf-8") as f:
        return json.load(f).get("cloudflare_analytics_token", "").strip()


HEADER_RE = re.compile(r'<header class="site-header">.*?</header>', re.S)
FOOTER_RE = re.compile(r'<footer class="site-footer">.*?</footer>', re.S)

# any local css/js/image URL in a quoted attribute, with or without an old ?v=
ASSET_RE = re.compile(
    r'(["\'])(/assets/[^"\'?#\s]+\.(?:css|js|webp|png|jpe?g|gif|svg|ico))(?:\?v=[0-9A-Za-z]*)?\1'
)
_hashes = {}


def asset_version(path):
    if path not in _hashes:
        full = os.path.join(ROOT, path.lstrip("/").replace("/", os.sep))
        if os.path.exists(full):
            with open(full, "rb") as f:
                _hashes[path] = hashlib.sha1(f.read()).hexdigest()[:8]
        else:
            _hashes[path] = None  # missing file: leave the URL alone (validate.py reports it)
    return _hashes[path]


def stamp_html(html, relpath):
    """Fill the shared header/footer and refresh asset versions in one page.
    relpath is the page's path relative to the site root, e.g. "people/alumni.html"."""
    current = "/" + relpath.replace(os.sep, "/")
    if HEADER_RE.search(html):
        html = HEADER_RE.sub(lambda m: header_html(current), html, count=1)
    if FOOTER_RE.search(html):
        html = FOOTER_RE.sub(lambda m: footer_html(), html, count=1)

    def version(m):
        v = asset_version(m.group(2))
        url = m.group(2) + (f"?v={v}" if v else "")
        return f"{m.group(1)}{url}{m.group(1)}"

    html = ASSET_RE.sub(version, html)

    # Cloudflare Web Analytics (cookie-free), when a token is set. It is added only AFTER the
    # page has finished loading, so a slow or blocked analytics host can never keep the
    # browser's "loading" indicator spinning.
    html = BEACON_RE.sub("", html)
    token = analytics_token()
    if token and "</body>" in html:
        config = json.dumps({"token": token})
        beacon = (
            "<script>window.addEventListener('load',function(){var s=document.createElement('script');"
            "s.src='https://static.cloudflareinsights.com/beacon.min.js';s.defer=true;"
            f"s.setAttribute('data-cf-beacon','{config}');document.body.appendChild(s);}});</script>\n"
        )
        html = html.replace("</body>", beacon + "</body>", 1)
    return html


def page_files():
    """Every hand-authored or generated .html page (not the redirect stub)."""
    out = []
    for dirpath, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in (".git", "assets", "home", "content-raw", "scripts")]
        for name in files:
            if name.endswith(".html"):
                out.append(os.path.join(dirpath, name))
    return sorted(out)


CSS_URL_RE = re.compile(
    r"""(url\(["']?)(/assets/[^"')?#\s]+\.(?:webp|png|jpe?g|gif|svg))(?:\?v=[0-9A-Za-z]*)?(["']?\))"""
)


def stamp_css():
    """Version the images the stylesheet itself refers to (url(...)), so they use the same
    ?v=<hash> as the pages' preload tags and are downloaded once, not twice."""
    path = os.path.join(ROOT, "assets", "css", "style.css")
    with open(path, encoding="utf-8") as f:
        old = f.read()

    def version(m):
        v = asset_version(m.group(2))
        return m.group(1) + m.group(2) + (f"?v={v}" if v else "") + m.group(3)

    new = CSS_URL_RE.sub(version, old)
    if new != old:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new)
    _hashes.pop("/assets/css/style.css", None)  # the stylesheet's own version must reflect this edit


def stamp_site():
    stamp_css()
    changed = 0
    for path in page_files():
        with open(path, encoding="utf-8") as f:
            old = f.read()
        new = stamp_html(old, os.path.relpath(path, ROOT))
        if new != old:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new)
            changed += 1
    return changed
