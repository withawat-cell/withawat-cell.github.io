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
  <div class="wrap-wide">
    <div class="footer-row">
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
    r'(["\'])(/assets/[^"\'?#\s]+\.(?:css|js|webp|png|jpe?g|gif|svg|ico|woff2))(?:\?v=[0-9A-Za-z]*)?\1'
)

# Fonts are self-hosted (see scripts/fetch_fonts.py). Every page preloads the two files all text
# uses, so text appears without waiting for the stylesheet to discover them. Any leftover Google
# Fonts links are removed, and the preload lines are rewritten on every build.
PRELOAD_FONTS = ["/assets/fonts/inter-latin.woff2", "/assets/fonts/ibm-plex-mono-400-latin.woff2"]
GOOGLE_FONT_LINK_RE = re.compile(r'[ \t]*<link[^>]*(?:fonts\.googleapis\.com|fonts\.gstatic\.com)[^>]*>\n?')
FONT_PRELOAD_RE = re.compile(r'[ \t]*<link rel="preload" href="/assets/fonts/[^>]*>\n?')
STYLESHEET_LINK_RE = re.compile(r'<link rel="stylesheet" href="/assets/css/style\.css[^"]*">')
_hashes = {}


def asset_version(path):
    if path not in _hashes:
        full = os.path.join(ROOT, path.lstrip("/").replace("/", os.sep))
        if os.path.exists(full):
            with open(full, "rb") as f:
                data = f.read()
            if full.lower().endswith((".css", ".js", ".svg")):
                data = data.replace(b"\r\n", b"\n")  # same hash on Windows (CRLF) and Linux (LF)
            _hashes[path] = hashlib.sha1(data).hexdigest()[:8]
        else:
            _hashes[path] = None  # missing file: leave the URL alone (validate.py reports it)
    return _hashes[path]


def image_size(path):
    """(width, height) of a local webp/png/jpeg from its file header, or None. Reading the header
    keeps the build free of image libraries."""
    full = os.path.join(ROOT, path.lstrip("/").replace("/", os.sep))
    try:
        with open(full, "rb") as f:
            head = f.read(64 * 1024)
    except OSError:
        return None
    le = lambda b: int.from_bytes(b, "little")
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        kind = head[12:16]
        if kind == b"VP8X":
            return le(head[24:27]) + 1, le(head[27:30]) + 1
        if kind == b"VP8L":
            b = head[21:25]
            return 1 + (b[0] | (b[1] & 0x3F) << 8), 1 + ((b[1] >> 6) | b[2] << 2 | (b[3] & 0xF) << 10)
        if kind == b"VP8 ":
            return le(head[26:28]) & 0x3FFF, le(head[28:30]) & 0x3FFF
    if head[:8] == b"\x89PNG\r\n\x1a\n":
        return int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")
    if head[:2] == b"\xff\xd8":
        i = 2
        while i + 9 < len(head):
            if head[i] != 0xFF:
                i += 1
                continue
            marker = head[i + 1]
            if marker in (0xC0, 0xC1, 0xC2):
                return int.from_bytes(head[i + 7:i + 9], "big"), int.from_bytes(head[i + 5:i + 7], "big")
            i += 2 + int.from_bytes(head[i + 2:i + 4], "big")
    return None


IMG_TAG_RE = re.compile(r"<img\b[^>]*>")
IMG_SRC_RE = re.compile(r'\ssrc="(/assets/[^"?#]+)')
IMG_SIZE_ATTR_RE = re.compile(r'\s(?:width|height)="[^"]*"')


def size_images(html):
    """Give every local <img> the width/height of its file, so the browser reserves its space
    before it loads and the page doesn't jump. Rewritten on every build, so never stale."""
    def one(m):
        tag = m.group(0)
        src = IMG_SRC_RE.search(tag)
        size = image_size(src.group(1)) if src else None
        if not size:
            return tag
        tag = IMG_SIZE_ATTR_RE.sub("", tag)
        return tag[:-1].rstrip() + f' width="{size[0]}" height="{size[1]}">'
    return IMG_TAG_RE.sub(one, html)


SKIP_LINK_RE = re.compile(r'[ \t]*<a class="skip-link"[^>]*>[^<]*</a>\n?')
MAIN_RE = re.compile(r"<main(?:\s[^>]*)?>")


def add_skip_link(html):
    """A 'Skip to content' link as the first focusable thing on the page, jumping past the menu
    for keyboard and screen-reader users. <main> is its target."""
    html = SKIP_LINK_RE.sub("", html)
    if MAIN_RE.search(html) and "<body>" in html:
        html = MAIN_RE.sub('<main id="main" tabindex="-1">', html, count=1)
        html = html.replace("<body>", '<body>\n<a class="skip-link" href="#main">Skip to content</a>', 1)
    return html


SHARE_IMAGE_ALT = "Members of the Terahertz Engineering Laboratory"
SHARE_IMAGE_RE = re.compile(
    r'(<meta property="og:image" content="https://thz-el\.org(/assets/[^"?#]+)">\n)'
    r'(?:[ \t]*<meta property="og:image:(?:width|height|alt)"[^>]*>\n)*'
)


def add_share_image_details(html):
    """Say how big the social-share image is and what it shows, so link previews lay out
    correctly and are described for screen readers."""
    def one(m):
        size = image_size(m.group(2))
        if not size:
            return m.group(1)
        return (m.group(1)
                + f'<meta property="og:image:width" content="{size[0]}">\n'
                + f'<meta property="og:image:height" content="{size[1]}">\n'
                + f'<meta property="og:image:alt" content="{SHARE_IMAGE_ALT}">\n')
    return SHARE_IMAGE_RE.sub(one, html)


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

    html = GOOGLE_FONT_LINK_RE.sub("", html)
    html = FONT_PRELOAD_RE.sub("", html)
    preload = "".join(f'<link rel="preload" href="{p}" as="font" type="font/woff2" crossorigin>\n' for p in PRELOAD_FONTS)
    html = STYLESHEET_LINK_RE.sub(lambda m: preload + m.group(0), html, count=1)
    html = ASSET_RE.sub(version, html)
    html = size_images(html)
    html = add_skip_link(html)
    html = add_share_image_details(html)

    # Cloudflare Web Analytics (cookie-free), when a token is set. It is added only AFTER the
    # page has finished loading, so a slow or blocked analytics host can never keep the
    # browser's "loading" indicator spinning.
    html = BEACON_RE.sub("", html)
    token = analytics_token()
    if token and "</body>" in html:
        config = json.dumps({"token": token})
        # Only on the live site: local previews and test runs must not send fake visits to the dashboard.
        beacon = (
            "<script>if(/(^|\\.)thz-el\\.org$/.test(location.hostname)){"
            "window.addEventListener('load',function(){var s=document.createElement('script');"
            "s.src='https://static.cloudflareinsights.com/beacon.min.js';s.defer=true;"
            f"s.setAttribute('data-cf-beacon','{config}');document.body.appendChild(s);}});}}</script>\n"
        )
        html = html.replace("</body>", beacon + "</body>", 1)
    return html


def page_files():
    """Every hand-authored or generated .html page (not the redirect stub)."""
    out = []
    for dirpath, dirs, files in os.walk(ROOT):
        # only the real site folders: not assets, the redirect stub, data/scripts, or hidden/staging
        # folders (.git, .venv, .github, _site, ...)
        dirs[:] = [d for d in dirs
                   if d not in ("assets", "home", "content-raw", "scripts", "tests", "node_modules")
                   and not d.startswith((".", "_"))]
        for name in files:
            if name.endswith(".html"):
                out.append(os.path.join(dirpath, name))
    return sorted(out)


CSS_URL_RE = re.compile(
    r"""(url\(["']?)(/assets/[^"')?#\s]+\.(?:webp|png|jpe?g|gif|svg|woff2))(?:\?v=[0-9A-Za-z]*)?(["']?\))"""
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
        with open(path, "w", encoding="utf-8", newline="\n") as f:
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
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(new)
            changed += 1
    return changed
