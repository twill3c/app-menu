# -*- coding: utf-8 -*-
"""カードの「最終更新」を各リポジトリの最終コミット日(JST)に揃える。

手書きの日付は必ず腐る(cron で毎時更新されるアプリは毎日ズレる)。
GitHub API から実測値を取り、差分があるカードだけ書き換える。

- リポジトリ名は URL のサブドメインから推定し、異なる場合はカードの
  data-repo 属性で上書きする(例: kokorograph → kokoro-graph)
- 「初回デプロイ」は作成日なので触らない
- --check を付けると書き換えずに差分だけ表示する(CI の確認用)

usage: python tools/update_dates.py [--check]
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"
OWNER = "twill3c"
JST = timezone(timedelta(hours=9))

# <a class="card" ... data-repo="..."? ... href="https://<host>.vercel.app" ... 最終更新 YYYY-MM-DD</span>
CARD_RE = re.compile(
    r'<a class="card"(?P<attrs>[^>]*)href="https://(?P<host>[a-z0-9-]+)\.vercel\.app"'
    r'(?P<body>.*?)最終更新 (?P<date>\d{4}-\d{2}-\d{2})</span>',
    re.S)
REPO_ATTR_RE = re.compile(r'data-repo="([\w.-]+)"')


def repo_of(match: re.Match) -> str:
    m = REPO_ATTR_RE.search(match.group("attrs"))
    return m.group(1) if m else match.group("host")


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


def last_commit_jst(repo: str) -> str | None:
    """既定ブランチの最終コミット日(JST)。取得できなければ None。"""
    url = f"https://api.github.com/repos/{OWNER}/{repo}/commits?per_page=1"
    headers = {"User-Agent": "app-menu-update-dates",
               "Accept": "application/vnd.github+json"}
    token = _token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        print(f"  ! {repo}: 取得失敗({type(e).__name__})— 既存の日付を維持")
        return None
    if not data:
        return None
    iso = data[0]["commit"]["committer"]["date"]
    dt = datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return dt.astimezone(JST).strftime("%Y-%m-%d")


def main(check_only: bool) -> int:
    html = INDEX.read_text(encoding="utf-8")
    matches = list(CARD_RE.finditer(html))
    if not matches:
        print("カードが 1 枚も見つからない — index.html の構造を確認すること")
        return 1

    repos = [repo_of(m) for m in matches]
    with ThreadPoolExecutor(max_workers=8) as ex:
        actual = list(ex.map(last_commit_jst, repos))

    changes: list[tuple[str, str, str]] = []
    out, pos = [], 0
    for m, repo, new in zip(matches, repos, actual):
        old = m.group("date")
        if new and new != old:
            changes.append((repo, old, new))
            start = m.start("date")
            out.append(html[pos:start])
            out.append(new)
            pos = m.end("date")
    out.append(html[pos:])

    print(f"カード {len(matches)} 件 / 更新 {len(changes)} 件")
    for repo, old, new in changes:
        print(f"  {repo}: {old} → {new}")
    if not changes:
        print("すべて最新")
        return 0
    if check_only:
        return 1
    INDEX.write_text("".join(out), encoding="utf-8", newline="\n")
    print("index.html を更新")
    return 0


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv[1:]))
