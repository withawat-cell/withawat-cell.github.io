"""Run every build script in the required order and stop at the first failure.

Order matters: build_publications.py and build_coursework.py write placeholder
stat blocks, which build_stats.py then fills in from their output, and
build_legacy_redirects.py is independent but kept last for tidiness.

Usage: python scripts/build_all.py
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

STEPS = [
    "build_publications.py",
    "build_coursework.py",
    "build_stats.py",
    "build_legacy_redirects.py",
]

for step in STEPS:
    print(f"==> {step}")
    result = subprocess.run([sys.executable, os.path.join(HERE, step)])
    if result.returncode != 0:
        sys.exit(f"{step} failed (exit code {result.returncode}); stopping.")

print("All build steps completed.")
