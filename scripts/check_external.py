"""Check every external link on the built pages and report the ones that are dead.

    python scripts/check_external.py                  print a summary
    python scripts/check_external.py --report r.md    also write a Markdown report
    python scripts/check_external.py --limit 20       only check the first 20 (testing)

A link is DEAD when the server answers 404 or 410, or the address no longer
exists (DNS failure, connection refused). Exit code 1 only if something is dead.

Sites that refuse automated requests (403, 429, 999, bot walls) or time out are
listed as UNVERIFIED, never as dead and never retried aggressively: this checker
does not try to get around blocks. Open those by hand if you want to be sure.
"""
import argparse
import concurrent.futures
import json
import os
import re
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import shell

ROOT = shell.ROOT
UA = "Mozilla/5.0 (compatible; thz-el-linkcheck/1.0; +https://thz-el.org)"
# addresses that are resources the pages load, not links a reader follows
SKIP_HOSTS = ("static.cloudflareinsights.com", "fonts.googleapis.com", "fonts.gstatic.com", "flagcdn.com", "www.w3.org")
LINK_RE = re.compile(r'(?:href|src)="(https?://[^"]+)"')


def collect():
    """{url: [pages that contain it]}"""
    found = {}
    for path in shell.page_files():
        page = "/" + os.path.relpath(path, ROOT).replace(os.sep, "/")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        for url in LINK_RE.findall(text):
            url = url.replace("&amp;", "&")
            host = url.split("/")[2].lower()
            if host.endswith(SKIP_HOSTS) or host in SKIP_HOSTS:
                continue
            found.setdefault(url, set()).add(page)
    return {u: sorted(p) for u, p in found.items()}


def probe_doi(url, timeout):
    """Ask doi.org's own public lookup whether the DOI is registered. Publishers' pages
    often refuse automated visitors, but this answers for every DOI the same way."""
    doi = url.split("#")[0].split("?")[0].split("/", 3)[3]
    api = "https://doi.org/api/handles/" + urllib.parse.quote(doi, safe="/()-._~:;=@!$&'*+,%")
    req = urllib.request.Request(api, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = json.loads(r.read().decode("utf-8", "replace"))
        return ("OK", "DOI registered") if body.get("responseCode") == 1 else ("UNVERIFIED", f"DOI lookup code {body.get('responseCode')}")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return "DEAD", "DOI is not registered"
        return "UNVERIFIED", f"DOI lookup HTTP {e.code}"
    except Exception as e:  # noqa: BLE001
        return "UNVERIFIED", f"DOI lookup: {type(e).__name__}"


def probe(url, timeout):
    """-> (verdict, detail) where verdict is OK, DEAD or UNVERIFIED."""
    if url.split("/")[2].lower() in ("doi.org", "dx.doi.org") and url.count("/") >= 3:
        return probe_doi(url, timeout)

    def request(method):
        req = urllib.request.Request(url, method=method, headers={"User-Agent": UA, "Accept": "*/*"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status

    last = None
    for method in ("HEAD", "GET"):
        try:
            status = request(method)
            return "OK", str(status)
        except urllib.error.HTTPError as e:
            last = e.code
            if e.code in (404, 410):
                return "DEAD", f"HTTP {e.code}"
            if e.code in (405, 501, 403, 400) and method == "HEAD":
                continue  # some servers refuse HEAD; ask once more with GET
            return "UNVERIFIED", f"HTTP {e.code}"
        except urllib.error.URLError as e:
            reason = e.reason
            if isinstance(reason, socket.gaierror) or "getaddrinfo" in str(reason) or "Name or service" in str(reason):
                return "DEAD", "address no longer exists (DNS)"
            if isinstance(reason, ConnectionRefusedError):
                return "DEAD", "connection refused"
            return "UNVERIFIED", f"{type(reason).__name__}: {str(reason)[:60]}"
        except (socket.timeout, TimeoutError):
            return "UNVERIFIED", "timed out"
        except Exception as e:  # noqa: BLE001 - never let one odd link stop the run
            return "UNVERIFIED", f"{type(e).__name__}: {str(e)[:60]}"
    return "UNVERIFIED", f"HTTP {last}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--report", help="write a Markdown report to this file")
    ap.add_argument("--limit", type=int, help="only check this many links (for testing)")
    ap.add_argument("--timeout", type=int, default=20)
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()

    links = collect()
    urls = sorted(links)[: args.limit] if args.limit else sorted(links)
    print(f"Checking {len(urls)} external links from {len(shell.page_files())} pages ...")

    results = {}
    started = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(probe, u, args.timeout): u for u in urls}
        for fut in concurrent.futures.as_completed(futures):
            results[futures[fut]] = fut.result()

    dead = {u: r for u, r in results.items() if r[0] == "DEAD"}
    unverified = {u: r for u, r in results.items() if r[0] == "UNVERIFIED"}
    ok = len(results) - len(dead) - len(unverified)
    print(f"{ok} OK, {len(dead)} dead, {len(unverified)} unverified ({time.time() - started:.0f}s)")

    lines = [f"# External link check", "",
             f"{len(results)} links checked: **{ok} OK**, **{len(dead)} dead**, {len(unverified)} unverified.", ""]
    if dead:
        lines += ["## Dead links (fix or remove)", ""]
        for u, (_v, detail) in sorted(dead.items()):
            lines.append(f"- {u}  -  {detail}  \n  found on: {', '.join(links[u])}")
            print(f"  DEAD  {u}  ({detail})  on {', '.join(links[u])}")
        lines.append("")
    if unverified:
        lines += ["## Unverified (the site blocked the check or was slow; open by hand if unsure)", ""]
        for u, (_v, detail) in sorted(unverified.items()):
            lines.append(f"- {u}  -  {detail}")
        lines.append("")
    if args.report:
        with open(args.report, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lines) + "\n")
    sys.exit(1 if dead else 0)


if __name__ == "__main__":
    main()
