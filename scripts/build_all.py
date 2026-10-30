"""Rebuild the whole site from the data in content-raw/ and check it.

    python scripts/build_all.py            build + validate
    python scripts/build_all.py --serve    ... then preview at http://localhost:8090/
    python scripts/build_all.py --serve 8123

Order matters: the generators first reset the stat placeholders, build_stats.py
then fills them in, stamp_pages.py gives every page the shared header/footer and
fresh asset versions, and validate.py checks the result. A failing step stops
the run.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

STEPS = [
    "build_publications.py",
    "build_coursework.py",
    "build_people.py",
    "build_research.py",
    "build_home.py",
    "build_stats.py",
    "build_legacy_redirects.py",
    "build_sitemap.py",
    "stamp_pages.py",
    "validate.py",
]

for step in STEPS:
    print(f"==> {step}")
    result = subprocess.run([sys.executable, os.path.join(HERE, step)])
    if result.returncode != 0:
        sys.exit(f"{step} failed (exit code {result.returncode}); stopping.")

print("All build steps completed.")

if "--serve" in sys.argv:
    rest = sys.argv[sys.argv.index("--serve") + 1:]
    port = rest[0] if rest and rest[0].isdigit() else "8090"
    print(f"Preview: http://localhost:{port}/index.html  (Ctrl+C to stop)")
    try:
        subprocess.run([sys.executable, "-m", "http.server", port, "--directory", ROOT])
    except KeyboardInterrupt:
        pass
