# -*- coding: utf-8 -*-
"""カードの技術タグ(data-tags)を検査する。

カテゴリは主題、タグは技術という二軸で並べている。タグが増えるほど
「WASM のアプリだけ見る」のような横断が効くが、語彙が野放しに増えると
同義語が分裂して横断そのものが壊れる。そこで語彙をチップ行に固定し、
カード側がその外の語を使っていないかをここで見る。

検査するのは 3 点。
  1. カードの data-tags がすべてチップ行の語彙に収まっているか
  2. チップ行の語がどれも 1 件以上のカードで使われているか(死んだチップ)
  3. data-tags 属性そのものの欠落

usage: python tools/check_tags.py [--verbose]
      違反が 1 件でもあれば exit 1
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"

CARD_RE = re.compile(r'<a class="card"(?P<attrs>[^>]*)>(?P<body>.*?)</a>', re.S)
TAGS_ATTR_RE = re.compile(r'data-tags="([^"]*)"')
NAME_RE = re.compile(r'<div class="name">([^<]*)</div>')
# チップは <button>(キーボードで押せる)。以前は <span> だったので両方を拾う。
CHIP_RE = re.compile(r'<(?:span|button)[^>]*class="chip tagchip[^"]*"[^>]*data-tag="([^"]+)"')


def main(verbose: bool) -> int:
    html = INDEX.read_text(encoding="utf-8")
    vocab = [t for t in CHIP_RE.findall(html) if t != "ALL"]

    rows: list[tuple[str, list[str] | None]] = []
    for m in CARD_RE.finditer(html):
        name = NAME_RE.search(m.group("body"))
        card = name.group(1).split(" —")[0].strip() if name else "(不明)"
        attr = TAGS_ATTR_RE.search(m.group("attrs"))
        if attr is None:
            rows.append((card, None))
            continue
        rows.append((card, [t for t in attr.group(1).split(",") if t]))

    missing = [c for c, t in rows if t is None]
    used = Counter(t for _, tags in rows if tags for t in tags)
    unknown = sorted({t for t in used if t not in vocab})
    dead = [t for t in vocab if used[t] == 0]
    untagged = [c for c, t in rows if t == []]

    print(f"カード {len(rows)} 件 / 語彙 {len(vocab)} 種 / タグなし {len(untagged)} 件")
    if verbose:
        for t in vocab:
            print(f"  {used[t]:4}  {t}")
        if untagged:
            print("  タグなし: " + " / ".join(untagged))
    for c in missing:
        print(f"  [data-tags 属性なし] {c}")
    for t in unknown:
        holders = [c for c, tags in rows if tags and t in tags]
        print(f"  [語彙外のタグ] {t}: {' / '.join(holders)}")
    for t in dead:
        print(f"  [使われていないチップ] {t}")

    if missing or unknown or dead:
        return 1
    print("語彙と一致")
    return 0


if __name__ == "__main__":
    sys.exit(main("--verbose" in sys.argv[1:]))
