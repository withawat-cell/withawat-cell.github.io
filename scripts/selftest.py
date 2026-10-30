"""Self-test for the build: does it still build, reject mistakes and keep stats right?

    python scripts/selftest.py            full run (a few minutes)
    python scripts/selftest.py --quick    builds, reproducibility, shell, staging only
    python scripts/selftest.py --keep     keep the scratch copy for inspection

It never touches your working files: it copies the project (text files normalised to
LF, thesis PDFs replaced by empty placeholders) into a temporary folder, commits that
copy to a scratch git repository, and runs everything there. Between scenarios the
scratch repo is reset, so each scenario starts from the same clean, built site.

Needs git and Python 3 only. Exit code 1 if any check fails.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEXT_EXT = {".html", ".md", ".py", ".css", ".js", ".json", ".xml", ".txt", ".yml", ".yaml", ".svg", ".gitignore", ".gitattributes", ".nojekyll"}
results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok)))
    print(("PASS  " if ok else "FAIL  ") + name + (f"\n        {detail[-400:]}" if detail and not ok else ""), flush=True)


class Sandbox:
    def __init__(self):
        self.root = tempfile.mkdtemp(prefix="thz-selftest-")
        files = subprocess.run(["git", "ls-files", "-co", "--exclude-standard"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.splitlines()
        for rel in files:
            src = os.path.join(ROOT, rel)
            if not os.path.isfile(src):
                continue
            dst = os.path.join(self.root, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            ext = os.path.splitext(rel)[1].lower()
            if ext == ".pdf":
                open(dst, "wb").close()  # the build only needs the file to exist
            elif ext in TEXT_EXT or os.path.basename(rel) in (".gitignore", ".gitattributes"):
                with open(src, "rb") as f:
                    data = f.read().replace(b"\r\n", b"\n")
                with open(dst, "wb") as f:
                    f.write(data)
            else:
                shutil.copy2(src, dst)
        self.git("init", "-q")
        self.git("config", "user.email", "selftest@example.org")
        self.git("config", "user.name", "selftest")
        self.git("config", "core.autocrlf", "false")
        self.git("add", "-A")
        self.git("commit", "-qm", "base")

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.root, capture_output=True, text=True)

    def run(self, *cmd):
        env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
        r = subprocess.run([sys.executable, *cmd], cwd=self.root, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
        return r.returncode, r.stdout + r.stderr

    def build(self):
        return self.run(os.path.join("scripts", "build_all.py"))

    def reset(self):
        self.git("checkout", "--", ".")
        self.git("clean", "-fdq")

    def changed(self):
        return [l for l in self.git("status", "--porcelain").stdout.splitlines() if l.strip()]

    def read(self, rel):
        with open(os.path.join(self.root, rel), encoding="utf-8") as f:
            return f.read()

    def write(self, rel, text):
        p = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)

    def edit(self, rel, old, new, count=1):
        s = self.read(rel)
        assert old in s, f"{rel}: expected text not found: {old[:60]!r}"
        self.write(rel, s.replace(old, new, count))


# ---------------------------------------------------------------- markdown table helpers
def split_cells(line):
    return [c.strip() for c in re.split(r"(?<!\\)\|", line.strip()[1:-1])]


def join_cells(cells):
    return "| " + " | ".join(cells) + " |"


def md_tables(text):
    """[{'header': [...], 'rows': [(line_index, cells)]}] for every table in a markdown text."""
    lines = text.split("\n")
    out, i = [], 0
    while i < len(lines) - 1:
        if lines[i].startswith("|") and re.fullmatch(r"\|[-| ]+\|", lines[i + 1].strip() or "x"):
            tbl = {"header": split_cells(lines[i]), "sep": i + 1, "rows": []}
            j = i + 2
            while j < len(lines) and lines[j].startswith("|"):
                tbl["rows"].append((j, split_cells(lines[j])))
                j += 1
            out.append(tbl)
            i = j
        else:
            i += 1
    return out


def stat(html, label_start):
    m = re.search(r'<span class="stat-num">(\d+)(?:<sup>\*</sup>)?</span>\s*<span class="stat-label">' + re.escape(label_start), html)
    return int(m.group(1)) if m else None


def insert_row(sb, rel, cells_by_name):
    """Insert a new row right under the header of the first table of a markdown file."""
    text = sb.read(rel)
    t = md_tables(text)[0]
    cells = [cells_by_name.get(h, "") for h in t["header"]]
    lines = text.split("\n")
    lines.insert(t["sep"] + 1, join_cells(cells))
    sb.write(rel, "\n".join(lines))


def set_cell(sb, rel, header_name, value, row=0, table=0):
    text = sb.read(rel)
    t = md_tables(text)[table]
    idx = t["header"].index(header_name)
    li, cells = t["rows"][row]
    cells[idx] = value
    lines = text.split("\n")
    lines[li] = join_cells(cells)
    sb.write(rel, "\n".join(lines))


JOURNAL = "content-raw/publications-journal-articles.md"
CONF = "content-raw/publications-conference-presentations.md"
THESES = "content-raw/publications-theses.md"
COURSE = "content-raw/people-coursework.md"


def run_all(quick, keep):
    sb = Sandbox()
    print(f"Scratch copy: {sb.root}\n", flush=True)
    try:
        scenarios(sb, quick)
    finally:
        if keep:
            print(f"\nKept scratch copy at {sb.root}")
        else:
            shutil.rmtree(sb.root, ignore_errors=True)
    bad = [n for n, ok in results if not ok]
    print(f"\n{len(results) - len(bad)}/{len(results)} checks passed")
    return 1 if bad else 0


def scenarios(sb, quick):
    # ---------------------------------------------------------- builds
    code, out = sb.build()
    check("a clean build passes", code == 0, out)
    check("committed pages equal a fresh build (nothing is stale)", not sb.changed(), "\n".join(sb.changed()))
    sb.git("add", "-A"); sb.git("commit", "-qm", "built", "--allow-empty")
    code, out = sb.build()
    check("a second build changes nothing", code == 0 and not sb.changed(), "\n".join(sb.changed()))
    code, out = sb.run("scripts/build_publications.py")
    check("running one generator alone leaves the pages whole (stats included)", code == 0 and not sb.changed(), "\n".join(sb.changed()))
    sb.reset()

    # ---------------------------------------------------------- shared shell
    pages = site_pages(sb)
    headers, footers, current_ok = set(), set(), True
    for p in pages:
        h = sb.read(p)
        hdr = re.search(r'<header class="site-header">.*?</header>', h, re.S).group(0)
        ftr = re.search(r'<footer class="site-footer">.*?</footer>', h, re.S).group(0)
        marks = re.findall(r'aria-current="page"', hdr)
        current_ok &= len(marks) == 1
        headers.add(hdr.replace(' aria-current="page"', ""))
        footers.add(ftr)
    check(f"all {len(pages)} pages share one header and one footer, each marking its own page once", len(headers) == 1 and len(footers) == 1 and current_ok)
    check("no page keeps an inline style", all("style=\"" not in sb.read(p) for p in pages))

    # ---------------------------------------------------------- staging (what gets published)
    code, out = sb.run("scripts/stage_site.py", os.path.join(sb.root, "_site"))
    staged = os.path.join(sb.root, "_site")
    leaked = [x for x in ("scripts", "content-raw", "README.md", ".github", ".git") if os.path.exists(os.path.join(staged, x))]
    broken = []
    for dp, _d, fs in os.walk(staged):
        for f in fs:
            if f.endswith(".html"):
                t = open(os.path.join(dp, f), encoding="utf-8").read()
                for u in set(re.findall(r'(?:href|src)="(/[^"#?]*)', t)):
                    if u.startswith("//") or u == "/":
                        continue
                    p = os.path.join(staged, u.lstrip("/").replace("/", os.sep))
                    if not (os.path.isfile(p) or os.path.isfile(os.path.join(p, "index.html")) or os.path.isfile(p + ".html")):
                        broken.append(u)
    check("the published copy has the pages and assets but none of the build files, and no broken link",
          code == 0 and not leaked and not broken and os.path.isfile(os.path.join(staged, "index.html")), f"leaked={leaked} broken={broken[:5]}")
    shutil.rmtree(staged, ignore_errors=True)
    sb.reset()

    # ---------------------------------------------------------- analytics tag
    cfg = "content-raw/site-config.json"
    tag = "cloudflareinsights"
    sb.edit(cfg, re.search(r'"cloudflare_analytics_token":\s*"[^"]*"', sb.read(cfg)).group(0), '"cloudflare_analytics_token": "abc123"')
    sb.build(); code, _ = sb.build()
    counts = [sb.read(p).count(tag) for p in pages]
    check("analytics: a token adds the after-load tag exactly once per page, also after rebuilding", all(c == 1 for c in counts) and "abc123" in sb.read("index.html") and "addEventListener('load'" in sb.read("index.html"), str(counts))
    check("analytics: the redirect stub never gets it", tag not in sb.read("home/index.html"))
    sb.edit(cfg, '"cloudflare_analytics_token": "abc123"', '"cloudflare_analytics_token": ""')
    sb.build()
    check("analytics: an empty token removes it everywhere", all(tag not in sb.read(p) for p in pages))
    sb.reset()

    # ---------------------------------------------------------- sitemap
    sb.write("zz-test-page.html", sb.read("contact.html").replace("<title>Contact", "<title>Zz Test"))
    code, out = sb.build()
    sm = sb.read("sitemap.xml")
    check("sitemap: lists every page, including a brand-new one", code == 0 and "https://thz-el.org/zz-test-page.html" in sm and "https://thz-el.org/</loc>" in sm and all(
        ("https://thz-el.org/" + ("" if p == "index.html" else p) + "</loc>") in sm for p in pages), sm[-300:])
    sb.reset()

    # ---------------------------------------------------------- asset versions
    v1 = re.search(r"style\.css\?v=([0-9a-f]+)", sb.read("contact.html")).group(1)
    with open(os.path.join(sb.root, "assets", "css", "style.css"), "a", encoding="utf-8", newline="\n") as f:
        f.write("\n/* selftest */\n")
    sb.build()
    v2 = re.search(r"style\.css\?v=([0-9a-f]+)", sb.read("contact.html")).group(1)
    v2b = re.search(r"style\.css\?v=([0-9a-f]+)", sb.read("publications/journal-articles.html")).group(1)
    hdr_css = set(re.findall(r"header-bg\.webp\?v=([0-9a-f]+)", sb.read("assets/css/style.css")))
    hdr_page = set(re.findall(r"header-bg\.webp\?v=([0-9a-f]+)", sb.read("index.html")))
    check("cache-busting: editing the stylesheet changes its ?v= on hand-written and generated pages", v1 != v2 and v2 == v2b, f"{v1} {v2} {v2b}")
    check("cache-busting: the header image has one address in the CSS and in the pages", len(hdr_css) == 1 and hdr_css == hdr_page, f"{hdr_css} {hdr_page}")
    sb.reset()

    # ---------------------------------------------------------- external link checker (no network)
    code, out = sb.run("-c", "import sys; sys.path.insert(0,'scripts'); import check_external as c; l=c.collect(); print(len(l)); print(any('static.cloudflareinsights' in u or 'flagcdn' in u for u in l))")
    lines = out.strip().splitlines()
    check("external link checker: finds the site's links and skips resource hosts", code == 0 and int(lines[0]) > 50 and lines[1] == "False", out)
    sb.reset()

    if quick:
        return

    # ---------------------------------------------------------- mistakes must be rejected
    def must_fail(name, action, expect):
        sb.reset()
        action()
        code, out = sb.build()
        check(f"rejects: {name}", code != 0 and expect.lower() in out.lower(), out[-300:].replace("\n", " | "))
        sb.reset()

    must_fail("a missing journal thumbnail file", lambda: set_cell(sb, JOURNAL, "Image", "no-such-image.webp"), "does not exist")
    must_fail("an unknown topic", lambda: set_cell(sb, JOURNAL, "Topics", "bogus"), "unknown topic")
    must_fail("a journal row with a missing cell", lambda: _drop_last_cell(sb, JOURNAL), "expected 8 cells")
    must_fail("an unknown column name", lambda: sb.edit(JOURNAL, "| Recognition |", "| Recogniton |"), "unknown column")
    must_fail("a duplicate DOI", lambda: _dup_doi(sb), "appears twice")
    must_fail("a missing person photo", lambda: sb.edit("content-raw/people-alumni.md", "- Photo: ", "- Photo: nope-"), "does not exist")
    must_fail("an unknown person field", lambda: sb.edit("content-raw/people-alumni.md", "- Role:", "- Roel:"), "unknown field")
    must_fail("a bad email address", lambda: sb.write("content-raw/people-researchers.md", re.sub(r"- Email: \S+", "- Email: not-an-address", sb.read("content-raw/people-researchers.md"), count=1)), "should be an address")
    must_fail("a Grid typo", lambda: sb.edit("content-raw/people-visitors.md", "Grid: wide", "Grid: tiny"), "grid must be")
    must_fail("a missing thesis PDF", lambda: set_cell(sb, THESES, "File", "no-such-thesis.pdf"), "does not exist")
    must_fail("a broken internal link on a page", lambda: sb.edit("contact.html", "<h1>Contact</h1>", '<h1>Contact</h1><a href="/nope.html">x</a>'), "doesn't exist")
    must_fail("a coursework row with the wrong number of cells", lambda: _drop_last_cell(sb, COURSE), "expected 5 cells")
    must_fail("a coursework note linking to a missing page", lambda: set_cell(sb, COURSE, "Notes", "See [x](/nowhere.html)"), "doesn't exist")
    must_fail("a missing research card image", lambda: sb.write("content-raw/research-clusters.md", re.sub(r"- Image: \S+", "- Image: no-such.webp", sb.read("content-raw/research-clusters.md"), count=1)), "does not exist")
    must_fail("a missing home logo file", lambda: set_cell(sb, "content-raw/home-logos.md", "Logo", "no-such.svg"), "does not exist")
    must_fail("a file name with the wrong upper/lower case (fine on Windows, broken on the live Linux site)", lambda: _upper_logo(sb), "does not exist")
    must_fail("an unknown research field", lambda: sb.write("content-raw/research-clusters.md", sb.read("content-raw/research-clusters.md").replace("- Alt:", "- Alt text:", 1)), "unknown field")

    # ---------------------------------------------------------- edits you would make by hand
    sb.reset()
    code, out = sb.build()
    base = sb.read("index.html")
    n_j, n_jr, n_c, n_t = stat(base, "Journal Articles"), int(re.search(r"(\d+) Recognitions", base).group(1)), stat(base, "Conference Recognitions"), stat(base, "PhD Theses")
    n_fellows, n_ieee, n_medal = stat(base, "ARC Fellows"), stat(base, "IEEE AP"), stat(base, "University Doctoral Research Medals")
    year = re.search(r"^## (\d{4})$", sb.read(JOURNAL), re.M).group(1)
    insert_row(sb, JOURNAL, {"Citation": f'T. Test and W. Withayachumnankul, "A brand new paper," *Test Journal*, {year}.', "DOI / Link": "https://doi.org/10.0000/selftest.1",
                             "Recognition": "Invited", "Notes": "Special Issue on Testing", "Topics": "antennas", "Abstract": "An abstract."})
    conf_year = re.search(r"^## (\d{4})$", sb.read(CONF), re.M).group(1)
    insert_row(sb, CONF, {"Citation": f'T. Test, "A new talk," *Test Conference*, Adelaide, {conf_year}.', "Recognition": "Keynote", "Status": "Online"})
    insert_row(sb, THESES, {"Year": "2027", "Author": "Test Author", "Title": "A Test Thesis", "File": ""})
    code, out = sb.build()
    idx, jr = sb.read("index.html"), sb.read("publications/journal-articles.html")
    check("hand-added journal, conference and thesis rows build and validate", code == 0, out)
    check("stats follow: journal +1, its recognitions +1, conference +1, theses +1",
          (stat(idx, "Journal Articles"), int(re.search(r"(\d+) Recognitions", idx).group(1)), stat(idx, "Conference Recognitions"), stat(idx, "PhD Theses")) == (n_j + 1, n_jr + 1, n_c + 1, n_t + 1))
    check("the new rows show up: Special Issue as a plain note, (Online) after the conference citation, no thumbnail needed",
          "A brand new paper" in jr and "Special Issue on Testing" in jr and "A new talk" in sb.read("publications/conference-presentations.html") and "(Online)" in sb.read("publications/conference-presentations.html") and "A Test Thesis" in sb.read("publications/phd-theses.html"))
    sb.reset()

    photo = re.search(r"- Photo: (\S+)", sb.read("content-raw/people-researchers.md")).group(1)
    sb.edit("content-raw/people-researchers.md", "\n### ", f"\n### Test Researcher\n- Photo: {photo}\n- Role: PhD student\n- Awards: 2026 IEEE AP-S Fellowship; ARC DECRA Fellow\n\n### ")
    code, out = sb.build(); idx = sb.read("index.html")
    check("a new researcher with an ARC DECRA and an IEEE fellowship raises both home-page stats by 1", code == 0 and stat(idx, "ARC Fellows") == n_fellows + 1 and stat(idx, "IEEE AP") == n_ieee + 1 and "Test Researcher" in sb.read("people/researchers.html"), out[-200:])
    sb.reset()

    aphoto = re.search(r"- Photo: (\S+)", sb.read("content-raw/people-alumni.md")).group(1)
    sb.edit("content-raw/people-alumni.md", "\n### ", f"\n### Test Alumnus\n- Photo: {aphoto}\n- Role: PhD 2020-2024\n- Awards: 2026 University Doctoral Research Medal\n\n### ")
    code, out = sb.build()
    check("a new alumnus with a doctoral medal raises the medal stat by 1", code == 0 and stat(sb.read("index.html"), "University Doctoral Research Medals") == n_medal + 1, out[-200:])
    sb.reset()

    insert_row(sb, COURSE, {"Name": "Zz Test Student", "Year(s)": "2026", "Area": "Testing", "Awards": "2026 IEEE AP-S Fellowship", "Notes": "Also a visitor, see [Visitors](/people/visitors.html)"})
    code, out = sb.build()
    cw = sb.read("people/coursework.html")
    check("a coursework award becomes a gold chip and raises the IEEE stat; the note stays plain text after a bullet",
          code == 0 and '<span class="tag-note">2026 IEEE AP-S Fellowship</span> <span class="note-sep">&bull;</span> Also a visitor, see <a href="/people/visitors.html">Visitors</a>' in cw and stat(sb.read("index.html"), "IEEE AP") == n_ieee + 1, out[-200:])
    sb.reset()

    sb.edit("content-raw/home-logos.md", "| Australian Research Council", "| Test Funder | https://example.org/ | csiro.svg |\n| Australian Research Council")
    gallery_md = sb.read("content-raw/research-gallery.md")
    gallery_image = re.search(r"- Image: (\S+)", gallery_md).group(1)
    sb.write("content-raw/research-gallery.md", gallery_md.replace("\n### ", f"\n### A new gallery photo\n- Image: {gallery_image}\n- Alt: A test photo\n\n### ", 1))
    code, out = sb.build()
    check("a new logo and a new gallery photo appear on the home and research pages", code == 0 and 'title="Test Funder"' in sb.read("index.html") and "A new gallery photo" in sb.read("research.html"), out[-200:])
    sb.reset()


def _upper_logo(sb):
    rel = "content-raw/home-logos.md"
    t = md_tables(sb.read(rel))[0]
    set_cell(sb, rel, "Logo", t["rows"][0][1][t["header"].index("Logo")].upper())


def site_pages(sb):
    """The site's own .html pages (not assets, the redirect stub, data, scripts or hidden/staging folders)."""
    out = []
    for dp, ds, fs in os.walk(sb.root):
        ds[:] = [d for d in ds if d not in ("assets", "home", "content-raw", "scripts", "tests", "node_modules") and not d.startswith((".", "_"))]
        for f in fs:
            if f.endswith(".html"):
                out.append(os.path.relpath(os.path.join(dp, f), sb.root).replace(os.sep, "/"))
    return sorted(out)


def _drop_last_cell(sb, rel):
    text = sb.read(rel)
    t = md_tables(text)[0]
    li, cells = t["rows"][0]
    lines = text.split("\n")
    lines[li] = join_cells(cells[:-1])
    sb.write(rel, "\n".join(lines))


def _dup_doi(sb):
    text = sb.read(JOURNAL)
    t = md_tables(text)[0]
    i = t["header"].index("DOI / Link")
    with_doi = [n for n, (_li, cells) in enumerate(t["rows"]) if cells[i].startswith("http")]  # a row may have no DOI yet
    set_cell(sb, JOURNAL, "DOI / Link", t["rows"][with_doi[0]][1][i], row=with_doi[1])


if __name__ == "__main__":
    sys.exit(run_all("--quick" in sys.argv, "--keep" in sys.argv))
