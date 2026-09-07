#!/usr/bin/env python3
"""validate_apps.py の陽性対照。

**緑になる検査は、赤にできることを見ていないと意味がない。**
apps.json を一時ディレクトリに複製し、12 通りに壊して、そのすべてで
exit 1 になることと、無傷なら 0 になることを確かめる。

    python scripts/selftest_validate.py
"""
import copy
import json
import pathlib
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import validate_apps  # noqa: E402

ROOT = HERE.parent
BASE = json.loads((ROOT / "data" / "apps.json").read_text(encoding="utf-8"))


def find(doc, app_id):
    for a in doc["apps"]:
        if a["id"] == app_id:
            return a
    raise KeyError(app_id)


def pub(doc):
    return next(a for a in doc["apps"] if a["status"] == "published")


# (名前, 壊し方)。壊したあと必ず exit 1 になること。
BREAKS = [
    ("id が重複", lambda d: d["apps"].append(copy.deepcopy(d["apps"][0]))),
    ("未定義の domain", lambda d: pub(d)["domains"].append("nonexistent-domain")),
    ("未定義の method", lambda d: pub(d)["methods"].append("telepathy")),
    ("未定義の series", lambda d: pub(d).__setitem__("series", "not-a-series")),
    ("未定義の status", lambda d: pub(d).__setitem__("status", "maybe")),
    ("未定義の badge", lambda d: pub(d)["badges"].append("awesome")),
    ("未定義の language", lambda d: pub(d)["languages"].append({"name": "COBOL", "role": "処理"})),
    ("language に role が無い", lambda d: pub(d)["languages"].append({"name": "Python"})),
    ("Domain が空", lambda d: pub(d).__setitem__("domains", [])),
    ("summary が 161 字", lambda d: pub(d).__setitem__("summary", "あ" * 161)),
    ("URL の形式が不正", lambda d: pub(d).__setitem__("appUrl", "http:/broken")),
    ("日付の形式が不正", lambda d: pub(d).__setitem__("updatedAt", "2026/09/07")),
    ("githubUrl が id と食い違う",
     lambda d: pub(d).__setitem__("githubUrl", "https://github.com/twill3c/someone-else")),
    ("featuredOrder が重複", lambda d: [a.__setitem__("featured", True) or
                                        a.__setitem__("featuredOrder", 1)
                                        for a in d["apps"][:2]]),
    ("featured なのに featuredOrder が無い",
     lambda d: pub(d).update({"featured": True, "featuredOrder": None})),
    ("必須項目が無い", lambda d: pub(d).pop("summary")),
    ("published なのに appUrl が無い", lambda d: pub(d).__setitem__("appUrl", "")),
    ("planned なのに appUrl がある",
     lambda d: next(a for a in d["apps"] if a["status"] == "planned")
     .__setitem__("appUrl", "https://example.com")),
]


def run(doc, tmp):
    p = pathlib.Path(tmp) / "apps.json"
    p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    # validate_apps は ROOT からの相対で読むので、一時ファイルを相対に直して渡す
    rel = p.resolve().relative_to(ROOT) if str(p).startswith(str(ROOT)) else p
    return validate_apps.check(False, str(rel), "data/taxonomy.json")


def main():
    tmpdir = ROOT / "scripts" / "_selftest_tmp"
    tmpdir.mkdir(exist_ok=True)
    failures = []
    try:
        # 無傷なら緑
        code = run(copy.deepcopy(BASE), tmpdir)
        if code != 0:
            failures.append("無傷の apps.json が exit 0 にならない")
        else:
            print("OK   無傷 → exit 0")
        for name, break_it in BREAKS:
            doc = copy.deepcopy(BASE)
            break_it(doc)
            code = run(doc, tmpdir)
            if code == 0:
                failures.append(f"{name} を検出できない(exit 0 のまま)")
                print(f"NG   {name} → exit 0(検出できていない)")
            else:
                print(f"OK   {name} → exit 1")
    finally:
        for f in tmpdir.glob("*"):
            f.unlink()
        tmpdir.rmdir()

    print(f"\n陽性対照 {len(BREAKS) + 1} 通り中 {len(BREAKS) + 1 - len(failures)} 通り期待どおり")
    for f in failures:
        print("  ! " + f)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
