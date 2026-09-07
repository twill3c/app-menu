#!/usr/bin/env python3
"""data/apps.json と data/taxonomy.json の検査(SPEC §35)。

CI(.github/workflows/check.yml)で push と PR のたびに走る。手元でも同じものを
そのまま走らせられる:

    python scripts/validate_apps.py           # 違反があれば exit 1
    python scripts/validate_apps.py --verbose # 警告と統計も出す

V1 の tools/check_desc.py(説明文 160 字)・check_tags.py(語彙外・死んだチップ)・
check_src.py・check_cats.py・check_lib.py がやっていたことは、対象が HTML から
JSON へ移ったのでこの 1 本に畳んである。**緑になる検査は赤にできることを
見ていないと意味がない**ので、陽性対照は scripts/selftest_validate.py に置いた。
"""
import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SUMMARY_MAX = 160          # カードの高さが崩れる。V1 から据え置き
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")
URL = re.compile(r"^https://[^\s\"']+$")
REQUIRED = ["id", "title", "shortTitle", "series", "tracks", "domains", "methods",
            "experience", "languages", "architecture", "dataSources", "libraries",
            "summary", "badges", "appUrl", "githubUrl", "status"]
LIB_ROLES = {"ship", "build", "oracle"}


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def check(verbose=False, apps_path="data/apps.json", tax_path="data/taxonomy.json"):
    errors, warnings = [], []
    tax = load(tax_path)
    data = load(apps_path)
    apps = data["apps"]
    vocab = {k: {e["id"] for e in v} for k, v in tax.items() if isinstance(v, list)}

    def err(app_id, msg):
        errors.append(f"{app_id}: {msg}")

    seen_ids = {}
    featured_orders = {}
    used = {k: set() for k in vocab}

    for a in apps:
        aid = a.get("id", "<id なし>")
        for key in REQUIRED:
            if key not in a:
                err(aid, f"必須項目 {key} が無い")
        if not ID.match(str(aid)):
            err(aid, "id は英小文字・数字・ハイフンだけ")
        if aid in seen_ids:
            err(aid, "id が重複している")
        seen_ids[aid] = True

        # --- taxonomy に無い値を使っていないか
        for field, key in (("tracks", "tracks"), ("domains", "domains"),
                           ("methods", "methods"), ("experience", "experience"),
                           ("architecture", "architecture"), ("badges", "badges")):
            for v in a.get(field, []):
                if v not in vocab[key]:
                    err(aid, f"未定義の {field}: {v}")
                else:
                    used[key].add(v)
        if a.get("series") not in vocab["series"]:
            err(aid, f"未定義の series: {a.get('series')}")
        else:
            used["series"].add(a["series"])
        if a.get("status") not in vocab["status"]:
            err(aid, f"未定義の status: {a.get('status')}")
        else:
            used["status"].add(a["status"])
        for l in a.get("languages", []):
            if l.get("name") not in vocab["languages"]:
                err(aid, f"未定義の language: {l.get('name')}")
            else:
                used["languages"].add(l["name"])
            if not l.get("role"):
                err(aid, f"language {l.get('name')} に role が無い(何に使ったかを書く)")
        for r in a.get("runtimes", []):
            if r not in vocab["runtimes"]:
                err(aid, f"未定義の runtime: {r}")
            else:
                used["runtimes"].add(r)
        for s in a.get("dataSources", []):
            if s.get("category") not in vocab["dataSources"]:
                err(aid, f"未定義の dataSource: {s.get('category')}")
            else:
                used["dataSources"].add(s["category"])
            if not s.get("name"):
                err(aid, "dataSource に name が無い(どの資料かを書く)")
        for l in a.get("libraries", []):
            if l.get("role") not in LIB_ROLES:
                err(aid, f"library {l.get('name')} の role が {LIB_ROLES} のどれでもない")

        # --- 分類の最低条件(SPEC §48)
        if not a.get("domains"):
            err(aid, "Domain が 1 つも無い(全公開アプリは最低 1 つ持つ)")

        # --- 表示に効く決まり
        if len(a.get("summary", "")) > SUMMARY_MAX:
            err(aid, f"summary が {len(a['summary'])} 字(上限 {SUMMARY_MAX})")
        if not a.get("summary"):
            err(aid, "summary が空")

        # --- URL と日付
        for key in ("appUrl", "githubUrl"):
            v = a.get(key, "")
            if v and not URL.match(v):
                err(aid, f"{key} の形式が不正: {v}")
        gh = a.get("githubUrl", "")
        if gh:
            if not gh.startswith("https://github.com/"):
                err(aid, f"githubUrl が github.com ではない: {gh}")
            elif gh.rstrip("/").rsplit("/", 1)[-1] != aid:
                err(aid, f"githubUrl の末尾が id と食い違う: {gh}")
        for key in ("firstDeployedAt", "updatedAt"):
            v = a.get(key, "")
            if v and not DATE.match(v):
                err(aid, f"{key} の日付形式が不正: {v}")
        if a.get("firstDeployedAt") and a.get("updatedAt") \
                and a["updatedAt"] < a["firstDeployedAt"]:
            err(aid, "updatedAt が firstDeployedAt より前")

        # --- status ごとの整合
        if a.get("status") == "published":
            if not a.get("appUrl"):
                err(aid, "published なのに appUrl が無い")
            if not a.get("languages"):
                warnings.append(f"{aid}: published なのに languages が空")
            if not a.get("methods"):
                warnings.append(f"{aid}: methods が空(横断できる手法が無いなら空でよい)")
        else:
            if a.get("appUrl"):
                err(aid, f"status={a['status']} なのに appUrl がある")
            if a.get("featured"):
                err(aid, "公開していないものを Featured にはできない")

        # --- Featured
        if a.get("featured") != (a.get("featuredOrder") is not None):
            err(aid, "featured と featuredOrder が食い違う")
        if a.get("featuredOrder") is not None:
            o = a["featuredOrder"]
            if o in featured_orders:
                err(aid, f"featuredOrder {o} が {featured_orders[o]} と重複")
            featured_orders[o] = aid

    n_featured = len(featured_orders)
    if n_featured and not (4 <= n_featured <= 8):
        warnings.append(f"Featured が {n_featured} 件(SPEC §17.2 は 4〜8 件・推奨 6 件)")

    # --- 誰も使っていない語彙 = 死んだチップ。画面には出さないが、
    #     放っておくと語彙が腐るので必ず見えるところに出す。
    for key in ("tracks", "domains", "methods", "experience", "architecture",
                "badges", "series", "dataSources", "languages", "runtimes"):
        dead = sorted(vocab[key] - used[key])
        if dead:
            warnings.append(f"どのアプリも使っていない {key}: {', '.join(dead)}")

    if verbose:
        pub = [a for a in apps if a.get("status") == "published"]
        print(f"アプリ {len(apps)} 件(公開 {len(pub)} / それ以外 {len(apps) - len(pub)})")
        print(f"Featured {n_featured} 件")
        for key in ("tracks", "domains", "series"):
            print(f"  {key}: 使用 {len(used[key])}/{len(vocab[key])}")

    for w in warnings:
        print("警告: " + w)
    for e in errors:
        print("違反: " + e)
    if errors:
        print(f"\n{len(errors)} 件の違反")
    elif verbose:
        print("\n違反なし")
    return 1 if errors else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--apps", default="data/apps.json")
    ap.add_argument("--taxonomy", default="data/taxonomy.json")
    args = ap.parse_args()
    sys.exit(check(args.verbose, args.apps, args.taxonomy))
