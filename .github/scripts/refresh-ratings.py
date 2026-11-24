#!/usr/bin/env python3
"""Refresh the hardcoded Garmin Connect IQ ratings on the roxzone.app store page.

Fetches averageRating / reviewCount for ROXZONE and the Chan Digital fleet from
the public store API and rewrites index.html:
  - the ROXZONE line in the reviews section ("4.7 out of 5 · N reviews")
  - the hero's proof row (hero__stat-rating, hero__stat-reviews)
  - ratingValue / ratingCount / reviewCount in the AggregateRating JSON-LD
  - every fleet-strip caption (each card appears twice: marquee + hidden copy)

Runs daily from .github/workflows/refresh-ratings.yml, which commits the page
when a number changed. By hand, from the repo root:
  python3 .github/scripts/refresh-ratings.py            # edit index.html
  python3 .github/scripts/refresh-ratings.py --dry-run  # print, change nothing
  python3 .github/scripts/refresh-ratings.py PATH       # another index.html

Anything unexpected (store down, a rating outside 1-5, ROXZONE's review count
falling by more than a few, a page element not found) stops it before it
writes, so a bad answer from the store never reaches the page.
"""
import json, os, re, sys, urllib.request

API = "https://apps.garmin.com/api/appsLibraryExternalServices/api/asw/apps/{}"
APPS = {
    "ROXZONE": "95ff2e3b-7417-4bcf-8ced-7e4b70113616",
    "LoopFace": "df1d472a-ffc8-4890-8820-12cee16da2db",
    "Padel Go": "3f718124-ae33-4086-a695-06ed70efd676",
    "Tennis Go": "c4e0d92b-5e7b-4dde-940d-0f54ebd69922",
    "Pickleball Go": "3664a87d-6d4e-4d39-9257-efb877f2db3f",
    "Badminton Go": "58a3a8cc-b48d-431e-8575-3e06cc450cb6",
    "Table Tennis Go": "1d31283c-0efc-4c5a-8550-26a199a5dc8f",
    "Squash Go": "d7b2e447-49fa-4b8d-aeca-29335cc0c5ba",
    "Drink Water!": "f7ca63e4-4f0e-4e89-b28b-599b81f0237b",
    "Pill Time!": "58883c09-b43b-4531-bed3-a2a85208dddb",
    "QRGANISER": "6237b782-54a1-4fb0-9755-517a360eda17",
    "Earn Your Beer": "4d3c35ad-1c2a-49dc-a9d0-5779c168c82f",
}

args = [a for a in sys.argv[1:] if not a.startswith("--")]
dry = "--dry-run" in sys.argv
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
path = args[0] if args else os.path.join(root, "index.html")

ratings = {}
for name, uuid in APPS.items():
    req = urllib.request.Request(API.format(uuid), headers={"User-Agent": "Mozilla/5.0"})
    d = json.load(urllib.request.urlopen(req, timeout=20))
    avg_raw, count = d.get("averageRating"), d.get("reviewCount")
    if not isinstance(count, int) or count < 1 or not isinstance(avg_raw, (int, float)) or not 1 <= avg_raw <= 5:
        sys.exit(f"{name}: unexpected rating {avg_raw!r} ({count!r}); nothing written")
    ratings[name] = (avg_raw, count)
    print(f"{name:16} {ratings[name][0]:.1f} ({ratings[name][1]})")
if dry:
    sys.exit(0)

html = open(path, encoding="utf-8").read()
original = html
avg, n = ratings["ROXZONE"]
# Reviews can be removed, but never many at once: a sharp fall means the store
# answered wrongly, not that the page should say so.
m = re.search(r'<strong>[\d.]+ out of 5</strong> · (\d+) reviews', html)
if not m:
    sys.exit("reviews line not found; nothing written")
if n < int(m.group(1)) - 5:
    sys.exit(f"ROXZONE reviews fell from {m.group(1)} to {n}; nothing written")
html = re.sub(r'"ratingCount": "\d+"', f'"ratingCount": "{n}"', html)
html = re.sub(r'"reviewCount": "\d+"', f'"reviewCount": "{n}"', html)
html = re.sub(r'<strong>[\d.]+ out of 5</strong> · \d+ reviews',
              f'<strong>{avg} out of 5</strong> · {n} reviews', html)
# The hero's proof row (added 2026-11-24): the big rating and the review count
# under it. Optional so the script still runs on an index.html without it.
html, k1 = re.subn(r'(<span class="hero__stat-rating">)[\d.]+(</span>)',
                   lambda m: m.group(1) + str(avg) + m.group(2), html)
html, k2 = re.subn(r'(<span class="hero__stat-reviews">)\d+(</span>)',
                   lambda m: m.group(1) + str(n) + m.group(2), html)
if (k1, k2) != (1, 1):
    sys.exit(f"hero rating found {k1}x, review count {k2}x (expected 1 each); nothing written")
html = re.sub(r'("ratingValue": ")[\d.]+(",\s*"bestRating": "5",\s*"worstRating": "1",\s*"ratingCount")',
              lambda m: m.group(1) + str(avg) + m.group(2), html)
for name, (a, c) in ratings.items():
    if name == "ROXZONE":
        continue
    pat = re.compile(r'(translate="no">' + re.escape(name) +
                     r'</span>\s*<span class="fleet-card__meta">[^<]*<span class="fleet-card__score">'
                     r'<span class="fleet-card__star">★</span> )[\d.]+ \(\d+\)')
    html, k = pat.subn(lambda m: m.group(1) + f"{a:.1f} ({c})", html)
    if k != 2:
        sys.exit(f"{name}: expected 2 fleet captions, found {k}; nothing written")
if html == original:
    print("no change")
    sys.exit(0)
open(path, "w", encoding="utf-8").write(html)
print("updated", path)
