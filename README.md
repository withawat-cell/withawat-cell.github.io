# Terahertz Engineering Laboratory website

Static site for the Terahertz Engineering Laboratory (Adelaide University), rebuilt from the previous Google Sites site. Plain HTML/CSS/JS with no framework, served by GitHub Pages. Page text (home, research, opportunities, contact, the intro paragraphs) is hand-written HTML. The lists (publications, theses, codes, people, coursework students, research cards, logos) live in `content-raw/` and small Python scripts turn them into HTML. The generated pages are committed, and every push rebuilds and re-checks them before anything is published.

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
| The menu or footer | `scripts/shell.py` (`NAV`, `FOOTER_*`) | Applied to every page by the build. The sitemap follows the menu. |
| Numbers that can't be worked out from the data | `content-raw/site-config.json` | Coauthor countries (flags), the pre-2018 journal count, the country-to-flag map for visitors, and the Cloudflare analytics token (empty = analytics off). |
| Page text on Home, Research, Opportunities, Contact, or the intro of any page; the Contact address cards; the team photos | the `.html` file itself | Leave the generated regions alone: between the `PEOPLE`, `CLUSTERS`, `GALLERY`, `LOGOS` and `STATS` `:START`/`:END` markers, and everything in `publications/` and `people/coursework.html`. |
| A new image | `python scripts/add_image.py source.png publications/name.webp --width 320` | Resizes, converts to WebP and saves it under `assets/img/`. Add `--crop 5:6` for portraits. Then name the file in the data. |

After any edit, run:

```bash
python scripts/build_all.py            # rebuild everything and check it
python scripts/build_all.py --serve    # ...and then preview at http://localhost:8090/
```

`build_all.py` runs these steps in order and stops at the first failure: `build_publications.py`, `build_coursework.py`, `build_people.py`, `build_research.py`, `build_home.py`, `build_stats.py`, `build_legacy_redirects.py`, `build_sitemap.py`, `stamp_pages.py`, `validate.py`. Each generator produces complete pages on its own (including the stat boxes), so the order is not fragile; it just keeps the stamping and checking last.

Every build also gives each local image its `width` and `height` (read from the file, so they follow when you replace it), adds the "Skip to content" link and the share-image size tags, and the validator keeps headings in order and every image described. None of this needs editing by hand.

Cache-busting is automatic: `stamp_pages.py` adds `?v=<hash of the file>` to every local CSS, JS and image reference, including the images the stylesheet itself uses, so browsers re-download an asset exactly when it changes. There is nothing to bump by hand.

The home page's "Lab history" stat strip and the stat boxes on the PhD theses and Visitors pages are generated from the same data (publication Recognition columns, people awards, coursework awards, theses, visitors), so they update on every build.

## Checks and safety nets

| Check | What it catches | Where it runs |
|---|---|---|
| `scripts/validate.py` | a table row with the wrong number of cells, an unknown column or topic, a thumbnail, person photo, logo or thesis PDF that doesn't exist (**with exact upper/lower case**, since the live site is case-sensitive), a duplicate DOI, a link to a missing page, a heading level that jumps (h1 to h3), an image with no `alt`, a missing skip link, images over 150 KB (warning) | every `build_all.py` |
| `scripts/selftest.py` | the build itself: it builds a scratch copy, applies deliberate mistakes and normal edits, and checks they are rejected or flow through to the pages and stats (`--quick` for a short run) | CI on every push (about 2 minutes) |
| CI "out of date" check | committed pages that differ from a fresh build, for example a data edit that wasn't rebuilt | CI on every push |
| `scripts/check_links.py` | broken internal links, checked through the running preview server | by hand |
| `scripts/check_external.py` | dead external links (404/410 or an address that no longer exists). DOIs are checked through doi.org's own lookup. Sites that block automated checks, such as LinkedIn, are listed as "unverified", never as dead | every Monday in CI, which opens an issue if anything is dead; also by hand |

## Structure

```
index.html                  Home
research.html                Research clusters + gallery of experiments (cards generated)
opportunities.html
contact.html
publications/                Generated from content-raw (do not edit by hand)
  journal-articles.html       Search box, topic + year filters (state kept in the URL), collapsible abstracts
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
  js/publications-filter.js   Journal articles search box + topic/year filter (mirrored into ?q=...&topic=...&year=...)
  fonts/                      Inter and IBM Plex Mono (woff2, self-hosted; see fonts/README.txt for the licence)
  img/                        All images, already resized/compressed for the web (img/flags/ = the small flag icons)
  theses/                     PhD thesis PDFs (in Git LFS), linked from phd-theses and alumni
content-raw/                 The data the build reads (see the table above)
  publications-journal-articles.md, publications-conference-presentations.md,
  publications-theses.md, codes-cards.html, people-researchers.md, people-alumni.md,
  people-visitors.md, people-coursework.md, research-clusters.md, research-gallery.md,
  home-logos.md, journal-notes-links.json, site-config.json
scripts/
  build_all.py                Runs every build step in order, then validates (use this)
  build_publications.py       Journal, conference, theses and codes pages
  build_coursework.py         people/coursework.html
  build_people.py             The cards on Researchers, Alumni and Visitors
  build_research.py           The cluster cards and gallery on research.html
  build_home.py               The partner and patron logo rows on index.html
  build_stats.py              The stat strips (home, theses, visitors); also imported by build_publications
  build_legacy_redirects.py   /home/index.html, a redirect stub for the one old Google Sites path
  build_sitemap.py            sitemap.xml, from the pages, in menu order
  stamp_pages.py              Shared header/footer, analytics tag and asset versions, on every page
  validate.py                 Data and site checks (see above)
  selftest.py                 The build's own test suite
  stage_site.py               Copies only the publishable files to a folder (used by the deploy)
  shell.py                    The menu, footer, analytics tag and cache-busting (edit NAV here)
  pubdata.py, peopledata.py, carddata.py, textutil.py   Readers and helpers shared by the build scripts
  check_links.py              Internal link check (needs the preview server running)
  check_external.py           External link check
  add_image.py                Resize and convert a local image to WebP (Pillow)
  fetch_images.py             Downloads + resizes images from a JSON manifest (Pillow)
  fetch_fonts.py              Downloads the fonts into assets/fonts/ and writes their @font-face rules into style.css
  fetch_flags.py              Downloads the flag icons for the countries in site-config.json into assets/img/flags/
.github/workflows/
  deploy-pages.yml            On every push: rebuild, check, self-test, then publish only the site files
  check-links.yml             Weekly external link check
```

The whole repository, including the scripts and the `content-raw` data, is your backup on GitHub. Only the site files are published; the build files are not served from thz-el.org.

PDF theses in `assets/theses/` are stored in [Git LFS](https://git-lfs.github.com/) (some are 40-80MB). Run `git lfs install` once per machine before cloning, or `git lfs pull` afterwards, otherwise those files check out as small text pointers instead of the actual PDFs. LFS keeps every version of a file that was ever committed, which is why `.git/lfs` on your computer can be much larger than the current PDFs; `git lfs prune` frees the old local copies (they remain on GitHub).

The build needs Python 3 only (no packages). `requirements.txt` lists Pillow for the optional image tools.

**Speed:** the site loads nothing from other servers. Fonts and flags are self-hosted, images are small WebP files loaded lazily, the stylesheet and script are tiny single files, the two fonts every page needs are preloaded, and every image carries its size so the page does not jump while it loads. When you add a country (to `coauthor_countries` or `country_iso` in `site-config.json`), run `python scripts/fetch_flags.py` once to download its flag icons; `validate.py` reminds you if they are missing. The Cloudflare analytics script is the only outside resource, loads after the page, and runs only on thz-el.org (never on a local preview).

## Local preview

`python scripts/build_all.py --serve` builds and serves the site. Any static file server also works, e.g. `python -m http.server 8090`, then open `http://localhost:8090/index.html`. Don't open the HTML files directly via `file://`: the site uses root-relative asset paths (`/assets/...`) which only resolve correctly from a server root.

## Deploying on GitHub Pages

The repo must be **public** for GitHub Pages to work on a free plan, and deploys via the GitHub Actions workflow at `.github/workflows/deploy-pages.yml`, not the legacy "deploy from branch" method. On every push to `main` the workflow checks out the repo with `lfs: true` (so the thesis PDFs are real files, not pointer text), rebuilds the site with `build_all.py`, fails if that changes any committed file, runs `selftest.py`, stages just the site files with `stage_site.py`, and publishes that folder via `actions/upload-pages-artifact` + `actions/deploy-pages`. If a check fails, nothing is deployed and the live site stays as it was. The workflow's error message says what to fix; the usual cause is a data edit that wasn't rebuilt, so run `python scripts/build_all.py` and commit the result.

1. Push this repo to GitHub (already public, already set up this way).
2. In the repo's Settings → Pages → Build and deployment, the source must be set to **GitHub Actions** (not "Deploy from a branch").
3. `.nojekyll` disables Jekyll processing so files are served as-is. The Actions-based deploy doesn't run Jekyll anyway, but it's harmless to keep.
4. **Custom domain (`thz-el.org`)**: the repo contains a `CNAME` file for `thz-el.org`, and `sitemap.xml` and the page canonical URLs use that domain. DNS should point at GitHub Pages' IPs (`185.199.108.153`, `.109.153`, `.110.153`, `.111.153`) per [GitHub's custom domain docs](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site), with "Enforce HTTPS" enabled in Settings → Pages.
5. **`robots.txt`** allows all crawlers and points to `sitemap.xml`.
6. **Visitor counts**: put the Cloudflare Web Analytics token in `content-raw/site-config.json` (`cloudflare_analytics_token`). The build adds the cookie-free script after the page has loaded, so a blocked or slow analytics host can't keep the browser's loading indicator spinning.

## Adding new images

For a file you already have, use `python scripts/add_image.py` (see the table above). To download a batch of images from URLs, write a manifest JSON, a list of `{"url": ..., "out": "assets/img/...", "max_w": 700}` objects, then run:

```bash
python scripts/fetch_images.py your_manifest.json
```

Either way the images are resized and compressed so nothing ships at full source resolution. See `scripts/fetch_images.py`'s docstring for the full manifest format. Reference the file by name in the page or data file; the build adds the cache-busting version.
