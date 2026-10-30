"""Download the small flag icons the stat boxes use and keep them in assets/img/flags/.

    python scripts/fetch_flags.py            fetch any flag that is missing
    python scripts/fetch_flags.py --force    fetch them all again

Which flags are needed comes from content-raw/site-config.json: every country in
"coauthor_countries" and every code in "country_iso". Each country gets a 16x12 file
(code.png) and a 32x24 file for sharp high-density screens (code@2x.png), taken from
flagcdn.com. Run this after adding a country, then run scripts/build_all.py.
Needs network.
"""
import json
import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FLAG_DIR = os.path.join(ROOT, "assets", "img", "flags")
UA = "Mozilla/5.0 (compatible; thz-el-build/1.0; +https://thz-el.org)"


def needed_codes():
    with open(os.path.join(ROOT, "content-raw", "site-config.json"), encoding="utf-8") as f:
        config = json.load(f)
    codes = [c for c, _name in config["coauthor_countries"]] + list(config["country_iso"].values())
    return sorted(set(codes))


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = r.read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise SystemExit(f"{url} did not return a PNG image")
    return data


def main():
    force = "--force" in sys.argv
    os.makedirs(FLAG_DIR, exist_ok=True)
    got = 0
    for code in needed_codes():
        for size, name in (("16x12", f"{code}.png"), ("32x24", f"{code}@2x.png")):
            path = os.path.join(FLAG_DIR, name)
            if os.path.exists(path) and not force:
                continue
            data = fetch(f"https://flagcdn.com/{size}/{code}.png")
            with open(path, "wb") as f:
                f.write(data)
            got += 1
            print(f"  saved assets/img/flags/{name}  {len(data)} bytes")
    print(f"{got} flag file(s) downloaded; {len(needed_codes())} countries covered")


if __name__ == "__main__":
    main()
