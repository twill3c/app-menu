#!/usr/bin/env python3
"""apps.json を数えて内訳を出す(SPEC §31)。

画面の KPI は app.js が同じ数え方でその場で出す。こちらは手元で全体を
見渡すためのもので、**数字を書き写して二重管理にしない**ための道具でもある
—— README にも index.html にも件数は書かない。

    python scripts/generate_stats.py            # 人が読む形
    python scripts/generate_stats.py --json     # 機械が読む形
"""
import collections
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
APPS = json.loads((ROOT / "data" / "apps.json").read_text(encoding="utf-8"))["apps"]
TAX = json.loads((ROOT / "data" / "taxonomy.json").read_text(encoding="utf-8"))
LABEL = {k: {e["id"]: e["label"] for e in v} for k, v in TAX.items() if isinstance(v, list)}


def counts(apps, field, key=None):
    c = collections.Counter()
    for a in apps:
        v = a[field]
        for x in (v if isinstance(v, list) else [v]):
            c[x[key] if key else x] += 1
    return c


def main(as_json=False):
    pub = [a for a in APPS if a["status"] == "published"]
    stats = {
        "総数": len(APPS),
        "公開": len(pub),
        "企画中ほか": len(APPS) - len(pub),
        "Featured": sum(1 for a in APPS if a["featured"]),
        "tracks": dict(counts(pub, "tracks")),
        "domains": dict(counts(pub, "domains")),
        "methods": dict(counts(pub, "methods")),
        "experience": dict(counts(pub, "experience")),
        "languages": dict(counts(pub, "languages", "name")),
        "architecture": dict(counts(pub, "architecture")),
        "dataSources": dict(counts(pub, "dataSources", "category")),
        "series": dict(counts(pub, "series")),
        "badges": dict(counts(pub, "badges")),
        "GitHub 公開": sum(1 for a in pub if a["githubUrl"]),
    }
    if as_json:
        print(json.dumps(stats, ensure_ascii=False, indent=1))
        return 0
    print(f"アプリ {stats['総数']} 件(公開 {stats['公開']} / 企画中ほか {stats['企画中ほか']})")
    print(f"GitHub のソースを公開しているもの {stats['GitHub 公開']} 件")
    for key in ("tracks", "domains", "series", "languages", "methods",
                "experience", "architecture", "dataSources", "badges"):
        print(f"\n[{key}]")
        for k, v in sorted(stats[key].items(), key=lambda x: -x[1]):
            print(f"  {v:4}  {LABEL.get(key, {}).get(k, k)}")
    return 0


if __name__ == "__main__":
    sys.exit(main("--json" in sys.argv))
