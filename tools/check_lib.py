# -*- coding: utf-8 -*-
"""カードの実装ライブラリ(data-lib)を検査する。

技術タグ(check_tags.py)は横断の軸で、こちらは実装の名前。「PyTorch で
書いたものはどれ」に答えられるようにするために足した。**説明文(.desc)には
入れない** —— 該当カードは 160 字の上限を 151〜153 字まで使い切っていて、
「PyTorch」の 7 文字が入らない。data-lib は .meta に丸として描かれるので
上限を 1 文字も食わず、card.textContent を走る自由入力でも当たる。

値は「役割:名前」をカンマ区切りで並べる。役割は 3 つ。
  出荷 = ブラウザに出て行く
  生成 = 手元で回して出荷物(重み・JSON)を作る
  照合 = オラクル専用。出荷実装はこれを参照しない

役割を書かせるのは、名前だけ貼ると嘘になるから。manazashi-lab の
requirements.txt は自ら「オラクル(権威)側の依存。出荷物ではない」と書いて
いるし、kuzushi-yomi の Chainer はブラウザには一切出て行かない。

検査するのは 4 点。
  1. 役割が 3 つの語彙に収まっているか
  2. 名前が語彙(VOCAB)に収まっているか(括弧の中身は自由)
  3. 語彙に誰も使っていない名前が無いか(死んだ語彙)
  4. 同じカードに同じ 役割:名前 が二度出ていないか

**語彙をこのファイルが持っているのは、実装の丸にはチップ行が無いから。**
タグと出典は「チップ行が語彙」だが、実装は絞り込みの軸にしていない
(PyTorch 2 枚・Chainer 1 枚・LangChain 1 枚 —— チップにすると死んだチップに
なる)。増えて 5 枚を超えたら技術タグへの昇格を考える。

--measure を付けると、兄弟リポジトリを実際に走査して data-lib と突き合わせる。
**CI では走らない**(兄弟は別リポジトリで 9 件が private・そもそも app-menu の
CI からは見えない)。手元で走らせる検査。

**走査で当たっても本文の言及は貼らないこと。**satei-kobo の "sklearn" は
「sklearn とは照合しない(SPEC §5)」という宣言、ango-atlas の "sklearn" は
「numpy だけで実装する(scipy/sklearn 非依存)」という宣言だった。だから
--measure は import 文と依存表だけを見る。

usage: python tools/check_lib.py [--verbose] [--measure]
      違反が 1 件でもあれば exit 1
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"
FLEET = ROOT.parent          # c:\_ClaudeCode

ROLES = ("出荷", "生成", "照合")

# 名前の語彙。括弧の前までを見る(R(sf/dplyr) の中身は自由)。
VOCAB = {
    # 出荷側
    "Transformers.js", "ONNX Runtime Web", "three.js", "satellite.js",
    "MapLibre GL JS", "CodeMirror", "docx",
    # 生成側
    "PyTorch", "Chainer", "TensorFlow", "Keras", "NumPy", "Transformers",
    "fugashi", "R",
    # 照合側
    "MeCab", "LangChain", "JAX", "ONNX Runtime",
}

# --measure が探す印。値は (探すファイル, 正規表現)。
# import 文と依存表だけを見る —— 本文の言及を拾わないため。
SIGNS = {
    "PyTorch": [("*.py", r"^\s*(?:import|from)\s+torch\b"), ("requirements*.txt", r"^torch\b")],
    "Chainer": [("*.py", r"^\s*(?:import|from)\s+chainer\b"), ("requirements*.txt", r"^chainer\b")],
    "TensorFlow": [("*.py", r"^\s*(?:import|from)\s+tensorflow\b|\btf\.keras\b"),
                   ("requirements*.txt", r"^tensorflow\b")],
    "Keras": [("*.py", r"^\s*(?:import|from)\s+keras\b"), ("requirements*.txt", r"^keras\b")],
    "JAX": [("requirements*.txt", r"^jax\b"), ("*.py", r"^\s*(?:import|from)\s+jax\b")],
    "NumPy": [("*.py", r"^\s*import numpy\b")],
    "Transformers": [("*.py", r"^\s*(?:import|from)\s+transformers\b"),
                     ("requirements*.txt", r"^transformers\b")],
    "ONNX Runtime": [("*.py", r"^\s*import onnxruntime\b"), ("requirements*.txt", r"^onnxruntime\b")],
    "fugashi": [("*.py", r"\bfugashi\.(?:Generic)?Tagger\(")],
    "MeCab": [("*.py", r"\bfugashi\.(?:Generic)?Tagger\(")],   # fugashi = MeCab の Python 束縛
    "LangChain": [("*.py", r"^\s*(?:import|from)\s+langchain\w*")],
    # library() は行頭に無いことがある(fukuo-keiryo は
    # suppressPackageStartupMessages(library(ggplot2)) と包んでいる)。
    "R": [("*.R", r"\blibrary\([A-Za-z0-9._]+\)")],
    "Transformers.js": [("package.json", r'"@(?:huggingface|xenova)/transformers"\s*:')],
    "ONNX Runtime Web": [("package.json", r'"onnxruntime-web"\s*:')],
    "three.js": [("package.json", r'"three"\s*:')],
    "satellite.js": [("package.json", r'"satellite\.js"\s*:')],
    "MapLibre GL JS": [("package.json", r'"maplibre-gl"\s*:')],
    "CodeMirror": [("package.json", r'"codemirror"\s*:')],
    "docx": [("package.json", r'"docx"\s*:')],
}

SKIP_DIRS = {"node_modules", ".git", ".next", "out", ".venv", "venv", "target",
             "coverage", "__pycache__", ".pytest_cache", ".vercel"}

CARD_RE = re.compile(r'<a class="card"(?P<attrs>[^>]*)>(?P<body>.*?)</a>', re.S)
LIB_ATTR_RE = re.compile(r'data-lib="([^"]*)"')
REPO_RE = re.compile(r'data-repo="([^"]+)"')
HOST_RE = re.compile(r'href="https://([^."]+)\.vercel\.app')
NAME_RE = re.compile(r'<div class="name">([^<]*)</div>')


def bare(name: str) -> str:
    """R(sf/dplyr) → R。括弧の中身は語彙の対象にしない。"""
    return name.split("(", 1)[0].strip()


def slug_of(attrs: str) -> str:
    m = REPO_RE.search(attrs) or HOST_RE.search(attrs)
    return m.group(1) if m else ""


def measure(slug: str, names: set[str]) -> list[str]:
    """兄弟リポジトリを走査し、印が見つからなかった名前を返す。"""
    root = FLEET / slug
    if not root.is_dir():
        return [f"(ローカルに {slug} が無いので確かめられない)"]
    texts: dict[str, list[str]] = {}
    for path in root.rglob("*"):
        if not path.is_file() or SKIP_DIRS & set(path.parts):
            continue
        if path.suffix not in (".py", ".R", ".r", ".json", ".txt"):
            continue
        try:
            if path.stat().st_size > 2_000_000:
                continue
            texts.setdefault(path.name, []).append(
                path.read_text(encoding="utf-8", errors="ignore"))
        except OSError:
            continue

    def bodies(pattern: str) -> list[str]:
        if "*" not in pattern:
            return texts.get(pattern, [])
        out = []
        for name, blobs in texts.items():
            if re.fullmatch(pattern.replace(".", r"\.").replace("*", ".*"), name):
                out += blobs
        return out

    unproven = []
    for name in sorted(names):
        signs = SIGNS.get(name, [])
        found = any(re.search(rx, body, re.M)
                    for glob, rx in signs for body in bodies(glob))
        if not found:
            unproven.append(name)
    return unproven


def main(verbose: bool, do_measure: bool) -> int:
    html = INDEX.read_text(encoding="utf-8")
    rows: list[tuple[str, str, list[tuple[str, str]]]] = []
    bad_role, bad_name, dup_entry = [], [], []

    for m in CARD_RE.finditer(html):
        attrs = m.group("attrs")
        name_m = NAME_RE.search(m.group("body"))
        card = name_m.group(1).split(" —")[0].strip() if name_m else "(不明)"
        attr = LIB_ATTR_RE.search(attrs)
        if attr is None:
            continue                      # data-lib は任意。無いのが 64 枚ある
        entries = []
        for raw in [x for x in attr.group(1).split(",") if x]:
            if ":" not in raw:
                bad_role.append((card, raw))
                continue
            role, lib = raw.split(":", 1)
            entries.append((role, lib))
            if role not in ROLES:
                bad_role.append((card, raw))
            if bare(lib) not in VOCAB:
                bad_name.append((card, lib))
        for entry, n in Counter(entries).items():
            if n > 1:
                dup_entry.append((card, f"{entry[0]}:{entry[1]}"))
        rows.append((card, slug_of(attrs), entries))

    used = Counter(bare(lib) for _, _, es in rows for _, lib in es)
    dead = sorted(v for v in VOCAB if used[v] == 0)

    total_cards = len(CARD_RE.findall(html))
    print(f"カード {total_cards} 枚 / 実装の丸がある {len(rows)} 枚 / "
          f"語彙 {len(VOCAB)} 種 / 実際に使われている {len(used)} 種")
    if verbose:
        for card, _, es in rows:
            print("  " + card + ": " + " / ".join(f"{r}:{l}" for r, l in es))
        print("  --- 名前ごとの枚数 ---")
        for name, n in used.most_common():
            print(f"  {n:4}  {name}")

    for card, raw in bad_role:
        print(f"  [役割が語彙外] {card}: {raw}(役割は {' / '.join(ROLES)})")
    for card, lib in bad_name:
        print(f"  [名前が語彙外] {card}: {lib}")
    for card, raw in dup_entry:
        print(f"  [同じ役割と名前が二度] {card}: {raw}")
    for name in dead:
        print(f"  [誰も使っていない語彙] {name}")

    unproven_all = []
    if do_measure:
        print("  --- 兄弟リポジトリの実測との突き合わせ ---")
        for card, slug, es in rows:
            names = {bare(lib) for _, lib in es}
            unproven = measure(slug, names)
            if unproven:
                unproven_all.append((card, unproven))
                print(f"  [印が見つからない] {card}({slug}): {' / '.join(unproven)}")
        if not unproven_all:
            print(f"  {len(rows)} 枚すべて、書いてある名前の印がリポジトリで見つかった")

    if bad_role or bad_name or dup_entry or dead or unproven_all:
        return 1
    print("実装ライブラリの語彙と一致")
    return 0


if __name__ == "__main__":
    args = sys.argv[1:]
    sys.exit(main("--verbose" in args, "--measure" in args))
