#!/usr/bin/env python3
"""
sentence_audit.py: pull every visible sentence off a running site and list the two kinds of
sentence the anti-slop skill's stage 3 audit reads by hand.

    python3 sentence_audit.py http://localhost:3000 / /about /services ...
    python3 sentence_audit.py http://localhost:3000 --repo ~/my-site   # routes from review-pages.json

Writes to stdout:
  PRONOUN  sentences that open on It / This / That / These / Those / They, each with the sentence
           before it, so you can see whether the subject was named.
  COMMA    every sentence with a comma, so dramatic commas can be read in one pass.

It does not judge. A script cannot tell a list comma from a dramatic pause, or a clear "it" from a
stranded one; that is the hand read. Built 2026-11-02 from the clinic audit (28 fixes). Header, footer, scripts and SVG are
stripped; text shared across pages is listed once, on the first page it appears.
"""
import html
import json
import re
import sys
import urllib.request
from pathlib import Path

PRONOUN = re.compile(r"(It|It's|This|That|These|Those|They|Its)\b")


def sentences(base, route):
    raw = urllib.request.urlopen(base.rstrip("/") + route).read().decode()
    raw = re.sub(r"<(script|style|svg|noscript|header|footer)[^>]*>.*?</\1>", "", raw, flags=re.S)
    out = []
    for _, block in re.findall(r"<(h[1-4]|p|li|dd|figcaption|summary|button|label)[^>]*>(.*?)</\1>", raw, re.S):
        text = re.sub(r"\s+", " ", html.unescape(re.sub("<[^>]+>", " ", block))).strip()
        if len(text) < 3:
            continue
        out.extend(re.split(r"(?<=[.?!])\s+(?=[A-Z\"])", text))
    return out


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    base, rest = args[0], args[1:]
    if rest[:1] == ["--repo"]:
        pages = json.loads((Path(rest[1]).expanduser() / "review-pages.json").read_text())
        pages = pages.get("pages", pages) if isinstance(pages, dict) else pages
        routes = [p["path"] if isinstance(p, dict) else p for p in pages]
    else:
        routes = rest or ["/"]
    seen, pron, comma = set(), [], []
    for route in routes:
        try:
            sents = sentences(base, route)
        except Exception as e:  # a dead route should not hide the rest
            print(f"ERROR {route}: {e}", file=sys.stderr)
            continue
        for i, s in enumerate(sents):
            if s in seen:
                continue
            seen.add(s)
            if PRONOUN.match(s):
                pron.append((route, sents[i - 1] if i else "(start of block)", s))
            if "," in s:
                comma.append((route, s))
    print(f"PRONOUN ({len(pron)})")
    for route, prev, s in pron:
        print(f"{route}\n  before: {prev[:160]}\n  >> {s[:220]}")
    print(f"\nCOMMA ({len(comma)})")
    for route, s in comma:
        print(f"{route}\t{s[:240]}")


if __name__ == "__main__":
    main()
