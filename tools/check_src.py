# -*- coding: utf-8 -*-
"""カードの出典タグ(data-src)を検査する。

軸は 3 本ある。カテゴリ=主題、タグ=技術、そして出典=データがどこから来たか。
出典は「何を測ったものか」で切る(気象庁の平年値は気象・天文データ、
国勢調査や e-Gov 法令は政府・自治体データ)。誰が出したかでは切らない。

技術タグ(check_tags.py)と同じ理由で語彙を固定する。「青空文庫」と
「Aozora」が並び立った時点で、出典で横断するという目的そのものが壊れる。

検査するのは 3 点。
  1. カードの data-src がすべてチップ行の語彙に収まっているか
  2. チップ行の語がどれも 1 件以上のカードで使われているか(死んだチップ)
  3. data-src 属性そのものの欠落

出典を持たないカード(自前生成・編者作成・合成データ)は空で正しい。
無理に埋めない。

usage: python tools/check_src.py [--verbose]
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
SRC_ATTR_RE = re.compile(r'data-src="([^"]*)"')
NAME_RE = re.compile(r'<div class="name">([^<]*)</div>')
# チップは <button>(キーボードで押せる)。以前は <span> だったので両方を拾う。
CHIP_RE = re.compile(r'<(?:span|button)[^>]*class="chip srcchip[^"]*"[^>]*data-src="([^"]+)"')


# 「自作・合成」チップの値。出典を持たないカードを引くための入口で、
# 出典の語彙ではない(カードの data-src には現れない)。
SENTINEL = "__none__"


def main(verbose: bool) -> int:
    html = INDEX.read_text(encoding="utf-8")
    all_chips = CHIP_RE.findall(html)
    vocab = [s for s in all_chips if s not in ("ALL", SENTINEL)]
    has_sentinel = SENTINEL in all_chips

    rows: list[tuple[str, list[str] | None]] = []
    for m in CARD_RE.finditer(html):
        name = NAME_RE.search(m.group("body"))
        card = name.group(1).split(" —")[0].strip() if name else "(不明)"
        attr = SRC_ATTR_RE.search(m.group("attrs"))
        if attr is None:
            rows.append((card, None))
            continue
        rows.append((card, [s for s in attr.group(1).split(",") if s]))

    missing = [c for c, s in rows if s is None]
    used = Counter(s for _, srcs in rows if srcs for s in srcs)
    unknown = sorted({s for s in used if s not in vocab})
    dead = [s for s in vocab if used[s] == 0]
    nosrc = [c for c, s in rows if s == []]

    print(f"カード {len(rows)} 件 / 語彙 {len(vocab)} 種 / 出典なし {len(nosrc)} 件")
    if verbose:
        for s in vocab:
            print(f"  {used[s]:4}  {s}")
        if nosrc:
            print("  出典なし: " + " / ".join(nosrc))
    for c in missing:
        print(f"  [data-src 属性なし] {c}")
    for s in unknown:
        holders = [c for c, srcs in rows if srcs and s in srcs]
        print(f"  [語彙外の出典] {s}: {' / '.join(holders)}")
    for s in dead:
        print(f"  [使われていないチップ] {s}")
    # 「自作・合成」は出典なしのカードが 1 件以上あるときだけ意味を持つ。
    # 全部のカードに出典が付いた日には、このチップも外す。
    stale_sentinel = has_sentinel and not nosrc
    if stale_sentinel:
        print("  [自作・合成チップが空振り] 出典なしのカードが 1 件も無い")
    if nosrc and not has_sentinel:
        print(f"  (出典なし {len(nosrc)} 件を引く入口が無い —— 自作・合成チップは任意)")

    if missing or unknown or dead or stale_sentinel:
        return 1
    print("語彙と一致")
    return 0


if __name__ == "__main__":
    sys.exit(main("--verbose" in sys.argv[1:]))
