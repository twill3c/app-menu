#!/usr/bin/env python3
"""probe_ui.mjs が画面から読んだ値を、apps.json から独立に数え直して突き合わせる。

app.js と同じ規則(正規化・同義語・AND/OR・重み)をここで**もう一度**書いている。
写すのではなく書き直すのが目的で、片方だけの思い違いはここで落ちる。

    python tools/probe_expect.py probe.json          # 違いがあれば exit 1
    python tools/probe_expect.py probe.json --list   # 全項目を出す
"""
import json
import pathlib
import re
import sys
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
APPS = json.loads((ROOT / "data" / "apps.json").read_text(encoding="utf-8"))["apps"]
TAX = json.loads((ROOT / "data" / "taxonomy.json").read_text(encoding="utf-8"))
SYNJ = json.loads((ROOT / "data" / "search-synonyms.json").read_text(encoding="utf-8"))

LABEL = {k: {e["id"]: e for e in v} for k, v in TAX.items() if isinstance(v, list)}
WEIGHT = {"title": 10, "aliases": 8, "keywords": 8, "summary": 6, "tracks": 5,
          "domains": 5, "methods": 5, "experience": 4, "languages": 4, "series": 4,
          "architecture": 4, "dataSources": 3, "libraries": 3, "description": 2}
DASH = dict.fromkeys(map(ord, "‐‑‒–—―ー−"), "-")
SPACE = dict.fromkeys(map(ord, "・･「」『』()（）[]【】、,"), " ")


def normalize(s):
    s = unicodedata.normalize("NFKC", str(s or "")).lower()
    s = s.translate(DASH).translate(SPACE)
    return re.sub(r"\s+", " ", s.strip())


SYN = {}
for group in SYNJ["groups"]:
    vs = [normalize(x) for x in group]
    for v in vs:
        SYN.setdefault(v, set()).update(vs)


def field_has(text, needle):
    if re.fullmatch(r"[a-z0-9+#.]{1,3}", needle):
        return re.search(r"(^|[^a-z0-9])" + re.escape(needle) + r"([^a-z0-9]|$)", text) is not None
    return needle in text


def labels_of(key, ids):
    return [f"{LABEL[key][i]['label']} {i}" if i in LABEL[key] else i for i in ids]


def index(a):
    f = {
        "title": [a["title"], a["shortTitle"]],
        "aliases": a["aliases"],
        "keywords": a.get("keywords", []),
        "summary": [a["summary"]],
        "description": [a.get("description", "")],
        "tracks": labels_of("tracks", a["tracks"]),
        "domains": labels_of("domains", a["domains"]),
        "methods": labels_of("methods", a["methods"]),
        "experience": labels_of("experience", a["experience"]),
        "languages": [l["name"] for l in a["languages"]] + [l["role"] for l in a["languages"]],
        "series": labels_of("series", [a["series"]]),
        "architecture": labels_of("architecture", a["architecture"]),
        "dataSources": labels_of("dataSources", [s["category"] for s in a["dataSources"]])
                       + [s["name"] for s in a["dataSources"]],
        "libraries": [l["name"] for l in a["libraries"]],
    }
    a["_f"] = {k: normalize(" ".join(v)) for k, v in f.items()}
    a["_facet"] = {
        "tracks": a["tracks"], "domains": a["domains"], "methods": a["methods"],
        "experience": a["experience"], "languages": [l["name"] for l in a["languages"]],
        "architecture": a["architecture"],
        "dataSources": [s["category"] for s in a["dataSources"]], "series": [a["series"]],
    }


for a in APPS:
    index(a)

FACETS = ["tracks", "domains", "methods", "experience", "languages",
          "architecture", "dataSources", "series"]


def matches(a, tokens):
    for t in tokens:
        vs = SYN.get(t, set()) | {t}
        if not any(field_has(a["_f"][k], v) for k in WEIGHT for v in vs if a["_f"].get(k)):
            return False
    return True


def tokenize(q):
    whole = normalize(q)
    # 空白を含む見出し(deep learning)は割らずに 1 語として扱う
    if whole and whole in SYN:
        return [whole]
    return [t for t in whole.split(" ") if t]


def select(sel=None, q="", planned=False):
    sel = sel or {}
    tokens = tokenize(q)
    out = []
    for a in APPS:
        if not planned and a["status"] != "published":
            continue
        ok = True
        for key, want in sel.items():
            if want and not set(want) & set(a["_facet"][key]):
                ok = False
                break
        if ok and matches(a, tokens):
            out.append(a)
    return out


def main(probe_path, show=False):
    got = json.loads(pathlib.Path(probe_path).read_text(encoding="utf-8"))
    pub = [a for a in APPS if a["status"] == "published"]
    checks = []

    def eq(name, expected, actual):
        checks.append((name, expected, actual, expected == actual))

    # --- コンソールにエラーが出ていないこと
    eq("console errors", [], got["consoleErrors"])

    # --- KPI
    kpi = got["kpi"]
    eq("KPI 公開アプリ", len(pub), kpi.get("公開アプリ"))
    eq("KPI AI / ML", sum(1 for a in pub if "ai-insight" in a["tracks"]), kpi.get("AI / ML"))
    eq("KPI Atlas AI", sum(1 for a in pub if a["series"] == "atlas-ai"), kpi.get("Atlas AI"))
    eq("KPI Browser AI", sum(1 for a in pub if "browser-ai" in a["tracks"]), kpi.get("Browser AI"))
    eq("KPI Open Data", sum(1 for a in pub if "open-data" in a["badges"]), kpi.get("Open Data"))
    eq("KPI 言語", len({l["name"] for a in pub for l in a["languages"]}), kpi.get("言語"))

    # --- Featured(順序も)
    feat = sorted([a for a in APPS if a["featured"]], key=lambda a: a["featuredOrder"])
    eq("Featured 件数", len(feat), got["featuredCount"])
    eq("Featured の順序", [a["title"] for a in feat],
       [re.sub(r"^\W*\s*", "", t) for t in got["featured"]])

    # --- Track の件数
    for t, obs in zip(TAX["tracks"], got["tracks"]):
        eq(f"Track {t['id']} の件数", len(select({"tracks": [t["id"]]})), obs["n"])

    # --- ファセットのチップの件数(全軸・全チップ)
    axis_of = {"分野": "domains", "手法": "methods", "表示・体験": "experience",
               "言語": "languages", "実装": "architecture", "出典": "dataSources",
               "シリーズ": "series"}
    for row in got["facets"]:
        key = axis_of[row["axis"]]
        for c in row["chips"]:
            if c["label"] == "指定なし":
                eq(f"{row['axis']}/指定なし", len(select()), c["n"])
                continue
            ids = [e["id"] for e in TAX[key]
                   if re.sub(r"^\W+\s*", "", c["label"]).strip() ==
                      re.sub(r"^\W+\s*", "", e["label"]).strip()]
            if not ids:
                checks.append((f"{row['axis']}/{c['label']} の語彙", "taxonomy に在る", "無い", False))
                continue
            eq(f"{row['axis']}/{c['label']}", len(select({key: [ids[0]]})), c["n"])

    eq("表示件数(初期)", len(select()), got["initialShown"])
    eq("カード枚数(初期)", len(select()), got["initialCards"])

    # --- 同じ軸は OR、違う軸は AND(SPEC §23)
    lit, his = "literature-folklore-language", "history-archaeology-faith"
    eq("分野 1 つ", len(select({"domains": [lit]})), got["afterDomain"]["shown"])
    eq("分野 1 つ(カード)", len(select({"domains": [lit]})), got["afterDomain"]["cards"])
    eq("同じ軸は OR", len(select({"domains": [lit, his]})), got["afterTwoDomains"]["shown"])
    eq("違う軸は AND", len(select({"domains": [lit, his], "methods": ["gis"]})),
       got["afterDomainAndMethod"]["shown"])
    eq("0 件のチップだけが押せない", True, got["disabledRule"])

    # --- URL 共有と復元
    eq("URL に載る", True, "domain=" in got["afterDomain"]["hash"])
    eq("リロードで復元", len(select({"domains": [lit, his], "methods": ["gis"]})),
       got["afterReload"]["shown"])
    eq("復元後の選択チップ数", 3, len(got["afterReload"]["selected"]))
    eq("クリアで戻る", len(select()), got["afterClear"]["shown"])
    eq("クリアで # も消える", "", got["afterClear"]["hash"])

    # --- 自由入力
    for q, obs in got["searches"].items():
        eq(f"検索「{q}」", len(select(q=q)), obs["shown"])
        eq(f"検索「{q}」のカード枚数", len(select(q=q)), obs["cards"])
    # 同義語は対称でなければならない。片方だけが広い群に入っていると、
    # 狭い語で引いたときに広い群がまるごと返る(実測で 11 件が 53 件になった)。
    eq("同義語は対称(深層学習 = deep learning)",
       got["searches"]["深層学習"]["shown"], got["searches"]["deep learning"]["shown"])
    eq("当たらない語は 0 件", 0, got["searches"]["ないはずのことば"]["shown"])
    eq("0 件のときだけ「該当なし」が出る", True,
       got["searches"]["ないはずのことば"]["noresult"]
       and not got["searches"]["防災"]["noresult"])

    # --- 企画中
    eq("企画中も見る", len(select(planned=True)), got["plannedShown"])
    eq("企画中を足した差", len(APPS) - len(pub), got["plannedShown"] - got["initialShown"])

    # --- カード
    eq("生の HTML タグが出ていない", [], got["rawTagLeak"])
    eq("公開カードには必ずアプリへの導線がある", [], got["cardsWithoutLink"])

    # --- アクセシビリティ
    for k, v in got["a11y"].items():
        eq(f"a11y {k}", True, v)
    eq("畳みの中のチップに焦点が当たる", True, got["keyboard"])
    eq("横スクロールが出ていない", True,
       got["overflow"]["bodyScrollWidth"] <= got["overflow"]["innerWidth"] + 1)
    if "mobileOverflow" in got:
        eq("横スクロールが出ていない(390px)", True,
           got["mobileOverflow"]["bodyScrollWidth"] <= got["mobileOverflow"]["innerWidth"] + 1)

    bad = [c for c in checks if not c[3]]
    for name, exp, act, ok in checks:
        if show or not ok:
            print(("OK   " if ok else "NG   ") + f"{name}: 期待 {exp!r} / 実際 {act!r}")
    print(f"\n{len(checks)} 項目中 {len(checks) - len(bad)} 件一致、{len(bad)} 件不一致")
    return 1 if bad else 0


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    sys.exit(main(args[0], "--list" in sys.argv))
