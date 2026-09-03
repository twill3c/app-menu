# -*- coding: utf-8 -*-
"""カテゴリ軸(data-cat)の構造を検査する。

軸は 3 本ある。カテゴリ=主題、タグ=技術、出典=データがどこから来たか。
check_tags.py と check_src.py が後ろ 2 本を見ているのに対し、
**カテゴリ軸だけ誰も見ていなかった。**

2026-09-01、同じ「美術・表象」がチップもセクションも 🎨 と 🖼️ の二つに
分かれた状態で 1 日以上通っていた(hanshoku-atlas が 🎨 で作り、
kozu-lab が 🖼️ で作ったため)。絞り込むと両方のセクションが出て、
件数チップも二つ並ぶ。検査 3 本はどれもこれを見なかった ——
**語彙とセクションの対応は見るが、同じ cat が二度定義されることは見ない。**

検査するのは 5 点。
  1. チップの data-cat に重複が無いか
  2. セクションの data-cat に重複が無いか
  3. チップの集合とセクションの集合が一致しているか
     (チップだけあって棚が無い / 棚だけあってチップが無い)
  4. 見出し(h2)の文言がチップの文言と一致しているか
     絵文字違いの同名カテゴリはここで捕まる
  5. 空のセクションが無いか

番号を詰め直さない運用なので欠番(cat1)は正常。連番は要求しない。

usage: python tools/check_cats.py [--verbose]
      違反が 1 件でもあれば exit 1
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"

# チップは <button>(キーボードで押せる)。以前は <span> だったので両方を拾う。
CHIP_RE = re.compile(
    r'<(?:span|button)[^>]*class="chip"[^>]*data-cat="(cat\d+)"[^>]*>(.*?)<span class="n">')
SECTION_RE = re.compile(
    r'<section data-section data-cat="(cat\d+)"[^>]*>\s*<h2>(.*?)</h2>(.*?)</section>',
    re.S)
CARD_RE = re.compile(r'<a class="card"')


def main(verbose: bool) -> int:
    html = INDEX.read_text(encoding="utf-8")
    chips = CHIP_RE.findall(html)
    sections = SECTION_RE.findall(html)

    chip_ids = [c for c, _ in chips]
    sec_ids = [c for c, _, _ in sections]
    chip_label = {c: t.strip() for c, t in chips}
    sec_label = {c: t.strip() for c, t, _ in sections}
    sec_cards = {c: len(CARD_RE.findall(body)) for c, _, body in sections}

    dup_chip = sorted(c for c, n in Counter(chip_ids).items() if n > 1)
    dup_sec = sorted(c for c, n in Counter(sec_ids).items() if n > 1)
    only_chip = sorted(set(chip_ids) - set(sec_ids))
    only_sec = sorted(set(sec_ids) - set(chip_ids))
    mismatch = sorted(c for c in set(chip_ids) & set(sec_ids)
                      if chip_label[c] != sec_label[c])
    empty = sorted(c for c in sec_ids if sec_cards.get(c, 0) == 0)

    # 絵文字を外した名前で突き合わせる。cat15 は 🎨 と 🖼️ で分かれていたので、
    # 文字列そのものの一致だけを見ると「美術・表象」が二つある状態を見逃す。
    def bare(label: str) -> str:
        parts = label.split(None, 1)
        return (parts[1] if len(parts) == 2 else label).strip()

    dup_label = sorted(t for t, n in Counter(bare(s) for s in sec_label.values())
                       .items() if n > 1)

    total = sum(sec_cards.values())
    print(f"カテゴリ {len(set(chip_ids))} 種 / セクション {len(sec_ids)} 件 / "
          f"カード {total} 枚")
    if verbose:
        for c in sec_ids:
            print(f"  {sec_cards[c]:4}  {c:6} {sec_label[c]}")

    for c in dup_chip:
        print(f"  [チップの重複] {c} — {chip_label.get(c)}")
    for c in dup_sec:
        print(f"  [セクションの重複] {c} — {sec_label.get(c)}")
    for c in only_chip:
        print(f"  [チップだけあって棚が無い] {c} — {chip_label[c]}")
    for c in only_sec:
        print(f"  [棚だけあってチップが無い] {c} — {sec_label[c]}")
    for c in mismatch:
        print(f"  [チップと見出しの文言が違う] {c} — "
              f"チップ「{chip_label[c]}」/ 見出し「{sec_label[c]}」")
    for t in dup_label:
        ids = [f"{c}({sec_label[c]})" for c in sec_ids if bare(sec_label[c]) == t]
        print(f"  [同じ名前の棚が複数] {t} — {' / '.join(ids)}")
    for c in empty:
        print(f"  [空のセクション] {c} — {sec_label[c]}")

    if (dup_chip or dup_sec or only_chip or only_sec or mismatch
            or dup_label or empty):
        return 1
    print("カテゴリ軸の構造に矛盾なし")
    return 0


if __name__ == "__main__":
    sys.exit(main("--verbose" in sys.argv[1:]))
