# Terahertz Engineering Laboratory website

Static site for the Terahertz Engineering Laboratory (Adelaide University), rebuilt from the previous Google Sites site. Plain HTML/CSS/JS with no framework, served as-is by GitHub Pages. Page text (home, research, opportunities, contact, the intro paragraphs) is hand-written HTML. The lists (publications, theses, codes, people, coursework students) live in `content-raw/` and small Python scripts turn them into HTML. The generated pages are committed, so the deployed site needs no build step.

## Editing the site

| To change | Edit | Notes |
|---|---|---|
| A journal article | `content-raw/publications-journal-articles.md` | One table row per paper, in the right year's table. The **Recognition** column makes the gold chips and is what the stats count. `Notes` is plain text (special issues, supplementary material), `Status` is added in brackets after the citation (e.g. `Accepted`), `Image` is a thumbnail filename inside `assets/img/publications/` (blank for none). |
| A conference presentation | `content-raw/publications-conference-presentations.md` | Columns: Citation, Recognition (Invited, Keynote, ...), Status (e.g. `Online`). |
| A PhD thesis | `content-raw/publications-theses.md` | Put the PDF in `assets/theses/` and name it in the File column. |
| A code card | `content-raw/codes-cards.html` | Plain HTML: copy a whole `<div class="card">` block. |
| A researcher, alumnus or visitor | `content-raw/people-researchers.md`, `people-alumni.md`, `people-visitors.md` | One `### Name` block with `- Photo:`, `- Role:`, `- Info:`, `- Awards:` and link lines. The field list is at the top of each file. |
| A coursework student | `content-raw/people-coursework.md` | One row in the right year's table. **Awards** become gold chips (and are counted by the home-page award stats), **Notes** are plain text; separate several items with `;`. |
| A research cluster card | `content-raw/research-clusters.md` | `## Heading` is a cluster, `### Title` a card (Image, Alt, Text, Tags). |
| A photo in "Gallery of experiments" | `content-raw/research-gallery.md` | `### Caption` with Image and Alt. |
| A partner or patron logo on the home page | `content-raw/home-logos.md` | One table row (Name, Link, Logo file in `assets/img/logos/`) under `association` or `patrons`. |
| The menu or footer | `scripts/shell.py` (`NAV`, `FOOTER_*`) | Applied to every page by the build. |
| Numbers that can't be worked out from the data | `content-raw/site-config.json` | Coauthor countries (flags), the pre-2018 journal count, and the country-to-flag map for visitors. |
| Page text on Home, Research, Opportunities, Contact, or the intro of any page; the Contact address cards; the team photos | the `.html` file itself | Leave the generated regions alone: between the `PEOPLE`, `CLUSTERS`, `GALLERY`, `LOGOS` and `STATS` `:START`/`:END` markers, and everything in `publications/` and `people/coursework.html`. |

After any edit, run:

```bash
python scripts/build_all.py            # rebuild everything and check it
python scripts/build_all.py --serve    # ...and then preview at http://localhost:8090/
```

`build_all.py` runs, in this order, and stops at the first failure: `build_publications.py`, `build_coursework.py`, `build_people.py`, `build_research.py`, `build_home.py`, `build_stats.py`, `build_legacy_redirects.py`, `stamp_pages.py`, `validate.py`. Order matters because the generators reset the stat placeholders that `build_stats.py` fills in, so if you ever run a generator on its own, finish with `build_all.py`.

`validate.py` catches mistakes before you push: a table row with the wrong number of cells, an unknown column or topic, a thumbnail, person photo or thesis PDF that doesn't exist, a duplicate DOI, or a link to a page that doesn't exist. It doesn't fetch external URLs: with the preview server running, `python scripts/check_links.py` does that.

Cache-busting is automatic: `stamp_pages.py` adds `?v=<hash of the file>` to every local CSS, JS and image reference, so browsers re-download an asset exactly when it changes. There is nothing to bump by hand.

The home page's "Lab history" stat strip and the stat boxes on the PhD theses and Visitors pages are generated from the same data (publication Recognition columns, people awards, coursework awards, theses, visitors), so they update on every build.

## Structure

```
index.html                  Home
research.html                Research clusters + gallery of experiments (cards generated)
opportunities.html
contact.html
publications/                Generated from content-raw (do not edit by hand)
  journal-articles.html       Topic + year filters (state kept in the URL), collapsible abstracts
  conference-presentations.html
  phd-theses.html
  codes.html
people/
  researchers.html            Hand-written intro + team photos; the cards are generated
  alumni.html                 (same)
  visitors.html               (same)
  coursework.html             Generated from content-raw/people-coursework.md
assets/
  css/style.css               Design system (dark, minimal, academic)
  js/main.js                  Nav toggle/dropdown, footer year, photo lightbox, copy buttons, abstract toggles
  js/publications-filter.js   Journal articles topic/year filter (mirrored into ?topic=...&year=...)
  img/                        All images, already resized/compressed for the web
  theses/                     PhD thesis PDFs (in Git LFS), linked from phd-theses and alumni
content-raw/                 The data the build reads (see the table above)
  publications-journal-articles.md, publications-conference-presentations.md,
  publications-theses.md, codes-cards.html, people-researchers.md, people-alumni.md,
  people-visitors.md, people-coursework.md, research-clusters.md, research-gallery.md,
  home-logos.md, journal-notes-links.json, site-config.json
scripts/
  build_all.py                Runs every step below in order (use this)
  build_publications.py       Journal, conference, theses and codes pages
  build_coursework.py         people/coursework.html
  build_people.py             The cards on Researchers, Alumni and Visitors
  build_research.py           The cluster cards and gallery on research.html
  build_home.py               The partner and patron logo rows on index.html
  build_stats.py              The stat strips (home, theses, visitors)
  build_legacy_redirects.py   /home/index.html, a redirect stub for the one old Google Sites path
  stamp_pages.py              Shared header/footer + asset versions, on every page
  validate.py                 Data and site checks (see above)
  shell.py                    The menu, footer and cache-busting (edit NAV here)
  pubdata.py, peopledata.py, carddata.py   Readers for the markdown tables, people lists and card lists
  check_links.py              Crawls every page and checks internal and external links
  fetch_images.py             Downloads + resizes images from a JSON manifest (Pillow)
```

PDF theses in `assets/theses/` are stored in [Git LFS](https://git-lfs.github.com/) (some are 40-80MB). Run `git lfs install` once per machine before cloning, or `git lfs pull` afterwards, otherwise those files check out as small text pointers instead of the actual PDFs.

The build needs Python 3 only (no packages) apart from `fetch_images.py` (Pillow) and `check_links.py`.

## Local preview

`python scripts/build_all.py --serve` builds and serves the site. Any static file server also works, e.g. `python -m http.server 8090`, then open `http://localhost:8090/index.html`. Don't open the HTML files directly via `file://`: the site uses root-relative asset paths (`/assets/...`) which only resolve correctly from a server root.

## Deploying on GitHub Pages

The repo must be **public** for GitHub Pages to work on a free plan, and deploys via the GitHub Actions workflow at `.github/workflows/deploy-pages.yml`, not the legacy "deploy from branch" method. That workflow runs on every push to `main`: it checks out the repo with `lfs: true` (so the thesis PDFs are checked out as real binaries, not Git LFS pointer text), then publishes via `actions/upload-pages-artifact` + `actions/deploy-pages`.

1. Push this repo to GitHub (already public, already set up this way).
2. In the repo's Settings → Pages → Build and deployment, the source must be set to **GitHub Actions** (not "Deploy from a branch").
3. `.nojekyll` disables Jekyll processing so files are served as-is. The Actions-based deploy doesn't run Jekyll anyway, but it's harmless to keep.
4. **Custom domain (`thz-el.org`)**: the repo contains a `CNAME` file for `thz-el.org`, and `sitemap.xml` and the page canonical URLs use that domain. DNS should point at GitHub Pages' IPs (`185.199.108.153`, `.109.153`, `.110.153`, `.111.153`) per [GitHub's custom domain docs](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site), with "Enforce HTTPS" enabled in Settings → Pages.
5. **`robots.txt`** allows all crawlers and points to `sitemap.xml`.

## Adding new images

Write a manifest JSON, a list of `{"url": ..., "out": "assets/img/...", "max_w": 700}` objects, then run:

```bash
python scripts/fetch_images.py your_manifest.json
```

This downloads each image and resizes/compresses it so nothing ships at full source resolution. See `scripts/fetch_images.py`'s docstring for the full manifest format. Reference the file by path in the page or data file; the build adds the cache-busting version.
