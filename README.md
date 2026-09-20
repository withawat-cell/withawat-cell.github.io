# Terahertz Engineering Laboratory — website

Static site for the Terahertz Engineering Laboratory (Adelaide University), rebuilt from the previous Google Sites site. Plain HTML/CSS/JS, no build step, no framework — designed to be served as-is by GitHub Pages.

## Structure

```
index.html                  Home
research.html                Research clusters + gallery of experiments
publications.html            Journal articles, conference presentations, PhD theses, codes
                              (filter tabs; journal articles also have a year filter)
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
  js/publications-filter.js   Publications page type/year filtering
  img/                        All images, already resized/compressed for the web
  theses/                     PhD thesis PDFs, linked from publications.html and people/alumni.html
scripts/
  fetch_images.py             Downloads + resizes images from a JSON manifest (Pillow)
  build_publications.py       Regenerates publications.html from content-raw/publications-*.md
  build_coursework.py         Regenerates people/coursework.html from content-raw/people-coursework.md
  check_links.py              Crawls every page and checks internal href/src paths resolve
```

There are no server-side includes — the header/nav/footer markup is duplicated at the top/bottom of every page. If you change the nav, update it in every `.html` file (a simple find-and-replace across the project works fine).

## Local preview

Any static file server works, e.g.:

```bash
python -m http.server 8090
```

then open `http://localhost:8090/index.html`. Don't open the HTML files directly via `file://` — the site uses root-relative asset paths (`/assets/...`) which only resolve correctly from a server root.

After changing anything, run `python scripts/check_links.py` (with the server above running) to confirm every internal link/asset path still resolves.

## Deploying on GitHub Pages

1. Push this repo to GitHub.
2. In the repo's Settings → Pages, set the source to the `main` branch, root folder.
3. The `CNAME` file already points at `thz-el.org` — set your DNS (A/ALIAS or CNAME record) to GitHub Pages per [GitHub's custom domain docs](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site), and enable "Enforce HTTPS" once DNS has propagated.
4. `.nojekyll` disables Jekyll processing so files are served as-is.

## Updating content

Everything is hand-authored HTML — open the relevant page and edit directly. For the two data-heavy generated pages (publications, coursework students), it's easier to add a row to the corresponding table in `content-raw/*.md` and re-run the matching `scripts/build_*.py` script, which regenerates the HTML from scratch. `content-raw/` is the source of truth for those two pages but is gitignored (working notes, not part of the shipped site).

Whenever `assets/css/style.css`, `assets/js/main.js`, or `assets/js/publications-filter.js` change, bump the `?v=` cache-busting query string on every page that links to them (and in both build script templates) so browsers don't keep serving a stale cached copy.

## Adding new images

Write a manifest JSON — a list of `{"url": ..., "out": "assets/img/...", "max_w": 700}` objects — then run:

```bash
python scripts/fetch_images.py your_manifest.json
```

This downloads each image and resizes/compresses it so nothing ships at full source resolution. See `scripts/fetch_images.py`'s docstring for the full manifest format.
