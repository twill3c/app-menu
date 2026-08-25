# -*- coding: utf-8 -*-
"""カードの説明文(.desc)が 160 字以内かを検査する。

カードは横に並ぶので、1 枚だけ極端に長いと高さが崩れ「見比べる」という
一覧の役目が壊れる。絞り込みは card.textContent 全体を走査するため、
長い説明文は検索のノイズにもなる。詳しい話は各アプリの「歩き方」「設計図」に置く。

数えるのは **表示文字数**(タグを除き、実体参照は展開したうえでの文字数)。
全角・半角の区別はしない。

usage: python tools/check_desc.py [--verbose]
      超過が 1 件でもあれば exit 1(CI の確認用)
"""
from __future__ import annotations

import html as html_mod
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"
LIMIT = 160

CARD_RE = re.compile(r'<a class="card"(?P<attrs>[^>]*)>(?P<body>.*?)</a>', re.S)
REPO_RE = re.compile(r'data-repo="([^"]+)"')
NAME_RE = re.compile(r'<div class="name">([^<]*)</div>')
DESC_RE = re.compile(r'<div class="desc">(.*?)</div>', re.S)
TAG_RE = re.compile(r"<[^>]+>")


def visible_length(desc_html: str) -> int:
    """タグを除き、実体参照を展開した表示文字数を返す。"""
    text = TAG_RE.sub("", desc_html)
    text = html_mod.unescape(text)
    return len(re.sub(r"\s+", " ", text).strip())


def card_id(attrs: str, body: str) -> str:
    """カードの識別名。data-repo があればそれ、無ければ name の左半分。"""
    repo = REPO_RE.search(attrs)
    if repo:
        return repo.group(1)
    name = NAME_RE.search(body)
    return name.group(1).split(" —")[0].strip() if name else "(不明)"


def main(verbose: bool) -> int:
    html = INDEX.read_text(encoding="utf-8")
    rows = []
    for m in CARD_RE.finditer(html):
        desc = DESC_RE.search(m.group("body"))
        if desc is None:
            rows.append((card_id(m.group("attrs"), m.group("body")), -1))
            continue
        rows.append((card_id(m.group("attrs"), m.group("body")), visible_length(desc.group(1))))

    missing = [r for r, n in rows if n < 0]
    over = [(r, n) for r, n in rows if n > LIMIT]
    longest = max((n for _, n in rows if n >= 0), default=0)

    print(f"カード {len(rows)} 件 / 上限 {LIMIT} 字 / 最長 {longest} 字")
    if verbose:
        for repo, n in sorted(rows, key=lambda x: -x[1]):
            print(f"  {n:4}  {repo}")
    for repo in missing:
        print(f"  [説明文なし] {repo}")
    for repo, n in over:
        print(f"  [超過 {n - LIMIT:+}] {repo}: {n} 字")

    if over or missing:
        return 1
    print("すべて上限内")
    return 0


if __name__ == "__main__":
    sys.exit(main("--verbose" in sys.argv[1:]))
