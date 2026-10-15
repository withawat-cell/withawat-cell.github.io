"""Stamp the shared header/footer and fresh asset versions into every page.

Run last (build_all.py does): see shell.py for what is stamped and how to
edit the menu and footer.
"""
import shell

n = shell.stamp_site()
print(f"Stamped shared header/footer and asset versions ({n} pages updated)")
