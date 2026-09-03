# -*- coding: utf-8 -*-
"""チップ絞り込みの実ブラウザ検品(probe_chips.mjs)の期待値を作る。

**権威側**。ブラウザ側は index.html の JS が出した数を読み、こちらは同じ
HTML を Python で独立に数え直す。両方が一致して初めて「チップの件数は
他の軸で数え直されている」と言える(二実装照合)。

チップの件数は「その軸だけを仮に v にしたとき、他の軸と自由入力の現在の
選択のもとで何枚残るか」。単独の総数を出していた頃は、押した先が 0 件の
チップに大きな数字が並んでいた —— 実測で三軸の組合せ 17,784 通りのうち
92.2% が 0 件、主題を 1 つ選ぶと技術チップは平均 3.1/11 しか生きていない。

usage: python tools/probe_chips_expect.py <出力する JSON のパス>
"""
from __future__ import annotations

import html as html_mod
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"

CAT_CHIP = re.compile(r'<(?:span|button)[^>]*class="chip"[^>]*data-cat="(cat\d+)"')
TAG_CHIP = re.compile(r'<(?:span|button)[^>]*class="chip tagchip[^"]*"[^>]*data-tag="([^"]+)"')
SRC_CHIP = re.compile(r'<(?:span|button)[^>]*class="chip srcchip[^"]*"[^>]*data-src="([^"]+)"')
SECTION_RE = re.compile(r'<section data-section data-cat="([^"]+)"[^>]*>(.*?)</section>', re.S)
CARD_RE = re.compile(r'<a class="card"(.*?)>(.*?)</a>', re.S)

MISS_QUERY = "ぬるぽ"   # どのカードにも無い文字列(0 件の状態を作るため)
PROBE_CATS = ("cat18", "cat2", "cat12", "cat14")
PROBE_PAIRS = (("cat12", "統計"), ("cat5", "自然言語処理"))
PROBE_TAG = "量子・計算理論"
QUERY = "青空文庫"


def main(out: Path) -> int:
    html = INDEX.read_text(encoding="utf-8")
    cat_order = CAT_CHIP.findall(html)
    tag_order = [t for t in TAG_CHIP.findall(html) if t != "ALL"]
    src_order = [s for s in SRC_CHIP.findall(html) if s != "ALL"]

    cards = []
    for sec in SECTION_RE.finditer(html):
        for m in CARD_RE.finditer(sec.group(2)):
            attrs, body = m.group(1), m.group(2)
            tg = re.search(r'data-tags="([^"]*)"', attrs)
            sr = re.search(r'data-src="([^"]*)"', attrs)
            tags = [x for x in (tg.group(1).split(",") if tg else []) if x]
            srcs = [x for x in (sr.group(1).split(",") if sr else []) if x]
            # JS 側は丸を描いたあとの textContent を見るので、タグ名・出典名も
            # 自由入力の対象に入る。ここでも同じ文字列を作る。
            text = html_mod.unescape(re.sub(r"<[^>]+>", " ", body)) + " " + " ".join(tags + srcs)
            cards.append(dict(cat=sec.group(1), tags=tags, srcs=srcs, text=text.lower()))

    def sel(cat="ALL", tag="ALL", src="ALL", q=""):
        return [c for c in cards
                if (cat == "ALL" or c["cat"] == cat)
                and (tag == "ALL" or tag in c["tags"])
                and (src == "ALL" or src in c["srcs"])
                and (q == "" or q in c["text"])]

    def live_tags(cat="ALL", q=""):
        return [[t, len(sel(cat=cat, tag=t, q=q))] for t in tag_order if sel(cat=cat, tag=t, q=q)]

    def live_srcs(cat="ALL", q=""):
        return [[s, len(sel(cat=cat, src=s, q=q))] for s in src_order if sel(cat=cat, src=s, q=q)]

    data = dict(
        total=len(cards),
        cats=[dict(id=c, n=len(sel(cat=c))) for c in cat_order],
        tags=[dict(v=t, n=len(sel(tag=t))) for t in tag_order],
        srcs=[dict(v=s, n=len(sel(src=s))) for s in src_order],
        probes=[dict(cat=c, n=len(sel(cat=c)), liveTags=live_tags(c), liveSrcs=live_srcs(c))
                for c in PROBE_CATS],
        pairs=[dict(cat=c, tag=t, n=len(sel(cat=c, tag=t)), tagTotal=len(sel(tag=t)))
               for c, t in PROBE_PAIRS],
        probeTag=PROBE_TAG,
        quantumTotal=len(sel(tag=PROBE_TAG)),
        quantumLiveCats=[[c, len(sel(cat=c, tag=PROBE_TAG))] for c in cat_order
                         if sel(cat=c, tag=PROBE_TAG)],
        missQuery=MISS_QUERY,
        cat0=len(sel(cat="cat0")),
        cat0AutoUpdate=len(sel(cat="cat0", tag="自動更新")),
        query=dict(q=QUERY, n=len(sel(q=QUERY)),
                   liveCats=[[c, len(sel(cat=c, q=QUERY))] for c in cat_order
                             if sel(cat=c, q=QUERY)]),
    )

    if sel(q=MISS_QUERY):
        print(f"  [検品用の文字列がカードに実在する] {MISS_QUERY} — 別の語に変える")
        return 1

    out.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"カード {data['total']} 枚 / 主題 {len(cat_order)} / 技術 {len(tag_order)} / "
          f"出典 {len(src_order)} → {out}")
    for p in data["probes"]:
        print(f"  {p['cat']:6} n={p['n']:3} 生きている技術 {len(p['liveTags']):2}/{len(tag_order)}"
              f" / 出典 {len(p['liveSrcs']):2}/{len(src_order)}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__.strip().splitlines()[-1])
        sys.exit(2)
    sys.exit(main(Path(sys.argv[1])))
