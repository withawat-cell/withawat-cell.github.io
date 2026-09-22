# Terahertz Engineering Laboratory — website

Static site for the Terahertz Engineering Laboratory (Adelaide University), rebuilt from the previous Google Sites site. Plain HTML/CSS/JS, no build step, no framework — designed to be served as-is by GitHub Pages.

## Structure

```
index.html                  Home
research.html                Research clusters + gallery of experiments
publications/
  journal-articles.html       Has a year filter
  conference-presentations.html
  phd-theses.html
  codes.html
opportunities.html
contact.html
people/
  researchers.html            Academic staff + postgraduate researchers, "Lab through the years" photos
  alumni.html
  coursework.html
  visitors.html
assets/
  css/style.css               Design system (dark, minimal, academic)
  js/main.js                  Nav toggle/dropdown, active-link highlight, footer year, photo lightbox
  js/publications-filter.js   Journal articles year filter
  img/                        All images, already resized/compressed for the web
  theses/                     PhD thesis PDFs (in Git LFS), linked from publications/phd-theses.html
                              and people/alumni.html
scripts/
  fetch_images.py             Downloads + resizes images from a JSON manifest (Pillow)
  build_publications.py       Regenerates publications/*.html from content-raw/publications-*.md
  build_coursework.py         Regenerates people/coursework.html from content-raw/people-coursework.md
  build_stats.py              Recomputes the home page's stat strip (run after the two build
                               scripts above, and after editing people/researchers.html or
                               people/alumni.html) -- writes into index.html between the
                               <!-- STATS:START/END --> markers; requires BeautifulSoup (bs4)
  check_links.py              Crawls every page and checks internal href/src paths resolve
```

There are no server-side includes — the header/nav/footer markup is duplicated at the top/bottom of every page. If you change the nav, update it in every `.html` file (a simple find-and-replace across the project works fine).

PDF theses in `assets/theses/` are stored in [Git LFS](https://git-lfs.github.com/) (some are 40&ndash;80MB). Run `git lfs install` once per machine before cloning, or `git lfs pull` afterwards, otherwise those files check out as small text pointers instead of the actual PDFs.

## Local preview

Any static file server works, e.g.:

```bash
python -m http.server 8090
```

then open `http://localhost:8090/index.html`. Don't open the HTML files directly via `file://` — the site uses root-relative asset paths (`/assets/...`) which only resolve correctly from a server root.

After changing anything, run `python scripts/check_links.py` (with the server above running) to confirm every internal link/asset path still resolves.

## Deploying on GitHub Pages

The repo must be **public** for GitHub Pages to work on a free plan, and deploys via the GitHub Actions workflow at `.github/workflows/deploy-pages.yml`, not the legacy "deploy from branch" method. That workflow runs on every push to `main`: it checks out the repo with `lfs: true` (so the thesis PDFs are checked out as real binaries, not Git LFS pointer text), then publishes via `actions/upload-pages-artifact` + `actions/deploy-pages`.

1. Push this repo to GitHub (already public, already set up this way).
2. In the repo's Settings → Pages → Build and deployment, the source must be set to **GitHub Actions** (not "Deploy from a branch").
3. `.nojekyll` disables Jekyll processing so files are served as-is — the Actions-based deploy doesn't run Jekyll anyway, but it's harmless to keep.
4. **Custom domain (`thz-el.org`)**: not yet configured — the site currently serves from the default `https://<username>.github.io/` address only, with no `CNAME` file in the repo. To cut over: first remove the domain's mapping from the old Google Site (Settings → Custom URLs there), then add the custom domain in this repo's Pages settings (Settings → Pages → Custom domain — this recreates `CNAME` automatically), point DNS at GitHub Pages' IPs (`185.199.108.153`, `.109.153`, `.110.153`, `.111.153`) per [GitHub's custom domain docs](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site), and enable "Enforce HTTPS" once DNS has propagated.
5. **`robots.txt`** currently blocks all crawlers (`Disallow: /`) — this is deliberate while the site is a preview at the default domain, not yet meant to be indexed. Remove or relax it once the site is genuinely live at the real domain.

## Updating content

Everything is hand-authored HTML — open the relevant page and edit directly. For the two data-heavy generated pages (publications, coursework students), it's easier to add a row to the corresponding table in `content-raw/*.md` and re-run the matching `scripts/build_*.py` script, which regenerates the HTML from scratch. `content-raw/` is the source of truth for those two pages but is gitignored (working notes, not part of the shipped site).

The home page's "Lab history" stat strip (journal articles, invited conferences, PhD theses, IEEE student grants) is auto-generated too. After editing publications content, `people/researchers.html`, or `people/alumni.html`, run `python scripts/build_publications.py && python scripts/build_coursework.py && python scripts/build_stats.py` (in that order) to keep it in sync.

Whenever `assets/css/style.css`, `assets/js/main.js`, or `assets/js/publications-filter.js` change, bump the `?v=` cache-busting query string on every page that links to them (and in both build script templates) so browsers don't keep serving a stale cached copy.

## Adding new images

Write a manifest JSON — a list of `{"url": ..., "out": "assets/img/...", "max_w": 700}` objects — then run:

```bash
python scripts/fetch_images.py your_manifest.json
```

This downloads each image and resizes/compresses it so nothing ships at full source resolution. See `scripts/fetch_images.py`'s docstring for the full manifest format.
