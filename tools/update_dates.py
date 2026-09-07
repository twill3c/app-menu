# -*- coding: utf-8 -*-
"""data/apps.json の updatedAt を各リポジトリの最終コミット日(JST)に揃える。

手書きの日付は必ず腐る(cron で毎時更新されるアプリは毎日ズレる)。
GitHub API から実測値を取り、差があるレコードだけ書き換える。

V1 では index.html のカードを正規表現で書き換えていた。V2 では apps.json が
唯一の出どころなのでそちらを直す(SPEC §31)。

**取得できなかったことを黙って飲み込まない。** V1 のこの道具は
「取得失敗 — 既存の日付を維持」と印字して success で終わっていたので、
private な兄弟リポジトリの日付が 10 日間凍っていても誰も気づかなかった。
いまは終了時に必ず内訳を出し、404 以外の失敗があれば --strict で赤にする。

usage:
    python tools/update_dates.py            # 実測値に更新
    python tools/update_dates.py --check    # 書き換えず差分だけ(差があれば exit 1)
    python tools/update_dates.py --strict   # 404 以外の取得失敗があれば exit 1
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APPS = ROOT / "data" / "apps.json"
OWNER = "twill3c"
JST = timezone(timedelta(hours=9))


def _token() -> str:
    """CI では GITHUB_TOKEN、手元では gh の認証を使う(未認証は 60 回/時で足りない)。"""
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        return token
    try:
        import subprocess
        out = subprocess.run(["gh", "auth", "token"], capture_output=True,
                             text=True, timeout=20)
        return out.stdout.strip()
    except Exception:
        return ""


TOKEN = _token()


def last_commit_jst(repo: str):
    """(日付, 失敗の種類)。取得できたら (YYYY-MM-DD, None)。"""
    url = f"https://api.github.com/repos/{OWNER}/{repo}/commits?per_page=1"
    headers = {"User-Agent": "app-menu-update-dates",
               "Accept": "application/vnd.github+json"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        # 404 は「private で見えない」か「存在しない」。CI の GITHUB_TOKEN は
        # このリポジトリにしか効かないので、兄弟が private なら必ずこうなる。
        return None, ("404" if e.code == 404 else f"HTTP {e.code}")
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        return None, type(e).__name__
    if not data:
        return None, "空の応答"
    iso = data[0]["commit"]["committer"]["date"]
    dt = datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return dt.astimezone(JST).strftime("%Y-%m-%d"), None


def main(check_only: bool, strict: bool) -> int:
    doc = json.loads(APPS.read_text(encoding="utf-8"))
    targets = [a for a in doc["apps"] if a.get("status") == "published"]
    if not targets:
        print("公開アプリが 1 件も無い — data/apps.json を確認すること")
        return 1

    with ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(lambda a: last_commit_jst(a["id"]), targets))

    changes, failures = [], []
    for app, (new, why) in zip(targets, results):
        if why:
            failures.append((app["id"], why))
            continue
        if new != app.get("updatedAt"):
            changes.append((app["id"], app.get("updatedAt"), new))
            app["updatedAt"] = new

    print(f"公開アプリ {len(targets)} 件 / 更新 {len(changes)} 件 / 取得できず {len(failures)} 件")
    for repo, old, new in changes:
        print(f"  {repo}: {old} → {new}")
    if failures:
        kinds = {}
        for _, why in failures:
            kinds[why] = kinds.get(why, 0) + 1
        print("  取得できなかった内訳: "
              + ", ".join(f"{k} × {v}" for k, v in sorted(kinds.items())))
        print("  (既存の日付を維持。private な兄弟リポジトリは CI の GITHUB_TOKEN では"
              " 404 になる —— 手元で走らせれば gh の PAT で読める)")
    hard = [f for f in failures if f[1] != "404"]
    if hard:
        for repo, why in hard:
            print(f"  ! {repo}: {why}")

    if changes and check_only:
        return 1
    if changes:
        APPS.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n",
                        encoding="utf-8", newline="\n")
        print("data/apps.json を更新")
    elif not failures:
        print("すべて最新")
    return 1 if (strict and hard) else 0


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv[1:], "--strict" in sys.argv[1:]))
