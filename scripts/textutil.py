"""Small text helpers shared by the build scripts."""
import re


def md_inline(s):
    """[label](url) -> a link, *text* -> emphasis. (No other escaping: the data files are trusted.)"""
    s = s.strip()
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
    s = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", s)
    return s
