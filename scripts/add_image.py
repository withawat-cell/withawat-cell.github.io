"""Resize a local image and save it as a web-ready WebP inside assets/img/.

    python scripts/add_image.py shot.png publications/lees-2026-new-paper.webp --width 320
    python scripts/add_image.py me.jpg people/jane-doe.webp --width 400 --crop 5:6
    python scripts/add_image.py team.jpg team/team-2027.webp --width 1200

DEST is relative to assets/img/ (or starts with assets/ to say it in full).
Typical widths used on this site: journal thumbnails 320, portraits 300-400
(cropped 5:6), research cards about 640, team and campus photos 900-1200.

Then reference the file by name in the data file (e.g. the Image column of the
journal table, or `- Photo:` in a people file) and run: python scripts/build_all.py
Requires Pillow (pip install -r requirements.txt).
"""
import argparse
import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG_DIR = os.path.join(ROOT, "assets", "img")
WARN_KB = 150


def crop_to_ratio(im, ratio):
    w, h = im.size
    target = ratio[0] / ratio[1]
    if w / h > target:  # too wide: trim the sides
        new_w = round(h * target)
        left = (w - new_w) // 2
        return im.crop((left, 0, left + new_w, h))
    new_h = round(w / target)  # too tall: trim top and bottom
    top = (h - new_h) // 2
    return im.crop((0, top, w, top + new_h))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", help="the image to convert (any format Pillow reads)")
    ap.add_argument("dest", help="where to save it, relative to assets/img/, ending in .webp")
    ap.add_argument("--width", type=int, default=640, help="maximum width in pixels (default 640; never enlarges)")
    ap.add_argument("--crop", help="centre-crop to a ratio first, e.g. 5:6 for portraits")
    ap.add_argument("--quality", type=int, default=82, help="WebP quality 1-100 (default 82)")
    ap.add_argument("--force", action="store_true", help="overwrite an existing file")
    args = ap.parse_args()

    if not args.dest.lower().endswith(".webp"):
        sys.exit("DEST must end in .webp")
    rel = args.dest[len("assets/img/"):] if args.dest.startswith("assets/img/") else args.dest
    out = os.path.normpath(os.path.join(IMG_DIR, rel))
    if not out.startswith(IMG_DIR + os.sep):
        sys.exit("DEST must stay inside assets/img/")
    if os.path.exists(out) and not args.force:
        sys.exit(f"{os.path.relpath(out, ROOT)} already exists (use --force to replace it)")

    im = Image.open(args.source)
    im.load()
    if args.crop:
        a, _, b = args.crop.partition(":")
        im = crop_to_ratio(im, (float(a), float(b)))
    if im.width > args.width:
        im = im.resize((args.width, max(1, round(im.height * args.width / im.width))), Image.LANCZOS)
    im = im.convert("RGBA") if im.mode in ("RGBA", "LA", "P") else im.convert("RGB")

    os.makedirs(os.path.dirname(out), exist_ok=True)
    im.save(out, "WEBP", quality=args.quality, method=6)
    kb = os.path.getsize(out) / 1024
    print(f"Saved {os.path.relpath(out, ROOT)}  {im.width}x{im.height}  {kb:.0f} KB")
    if kb > WARN_KB:
        print(f"  note: over {WARN_KB} KB; consider a smaller --width or lower --quality")


if __name__ == "__main__":
    main()
