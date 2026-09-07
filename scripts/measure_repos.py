#!/usr/bin/env python3
"""兄弟リポジトリを実測して scripts/_measured.json を作る。

apps.json の languages / architecture / badges は、書いたのではなく測ったもの。
このスクリプトは「何をもって測ったと言うか」の定義そのもので、手元専用
(CI では走らない —— 兄弟は別リポジトリで 9 件が private)。

測るときに踏んだ罠(同じ穴を掘らないために残す):

  1. **スキャフォールドを数えない。** harness/ は 111 プロジェクトすべてで
     バイト単位に同一。数えると Python が 100 枚のカードに付く。個別に
     ディレクトリ名を除外すると次のスキャフォールドを取りこぼすので、
     **同じ内容のファイルが 3 プロジェクト以上に在れば配布物**とみなして落とす。
     これで harness/ も scripts/verify.mjs も *.config.mjs も一度に消える。
  2. **ビルド出力を数えない。** .next/ と out/ には minify 済みの束が入る。
  3. **テストはファイル名だけでは分からない。** Rust は #[cfg(test)] が
     src/*.rs の中にある。名前で探すと yomikiri-ban / nanpure-forge が
     「テスト無し」に見える。
  4. **.wasm と重みは public/ に置かれる。** 言語の集計からは public/ を
     外すが、成果物の検出では見る。
"""
import collections
import hashlib
import json
import os
import pathlib
import re
import sys

ROOT = pathlib.Path(r"C:\_ClaudeCode")
HERE = pathlib.Path(__file__).resolve().parent

SKIP_DIRS = {"node_modules", ".git", ".next", "target", "dist", "build", ".venv",
             "venv", "__pycache__", ".vercel", "out", ".cache", "vendor",
             ".pytest_cache", ".mypy_cache", ".loop", ".claude",
             # harness/ は名前でも落とす。内容ハッシュだけに頼ると、その
             # プロジェクトで 1 行直したスキャフォールドが「固有のコード」に
             # 化けて戻ってくる(mondo-atlas で JavaScript 1,034 行がそうなった)。
             "harness"}
LANG_SKIP_DIRS = {"public"}          # 言語の集計だけで外す(成果物は見る)
EXT = {".py": "Python", ".ts": "TypeScript", ".tsx": "TypeScript", ".js": "JavaScript",
       ".mjs": "JavaScript", ".cjs": "JavaScript", ".jsx": "JavaScript", ".go": "Go",
       ".rs": "Rust", ".R": "R", ".r": "R", ".Rmd": "R", ".sql": "SQL",
       ".html": "HTML", ".css": "CSS", ".rb": "Ruby"}
ML = re.compile(r"\b(torch|tensorflow|keras|chainer|sklearn|scikit-learn|transformers|onnxruntime|jax)\b", re.I)
BROWSER_AI = re.compile(r"(onnxruntime-web|@xenova/transformers|@huggingface/transformers|@tensorflow/tfjs|webgpu)", re.I)
WORKER = re.compile(r"new\s+Worker\s*\(")
SECRET = re.compile(r"KEY|TOKEN|SECRET|PASSWORD|CRED")
TEST_PATH = re.compile(r"(^|/)(tests?|__tests__)/|\.(test|spec)\.[tj]sx?$|(^|/)test_[^/]+\.py$"
                       r"|_test\.go$|(^|/)tools/check_[^/]*\.py$|(^|/)scripts/(check|verify|gate)")
TEST_INLINE = re.compile(r"#\[cfg\(test\)\]|^func Test[A-Z]|^\s*def test_", re.M)
XVAL = re.compile(r"二実装|二重実装|独立実装|二経路|独立に実装|二つの独立|別実装|クロス実装|二重採点|相互検証")
WEIGHT_EXT = {".onnx", ".pt", ".pth", ".h5", ".npz", ".keras", ".safetensors", ".bin"}


def walk(d, skip_extra=frozenset()):
    for dirpath, dirnames, filenames in os.walk(d):
        dirnames[:] = [x for x in dirnames
                       if x not in SKIP_DIRS and x not in skip_extra
                       and not x.endswith(".worktrees")]
        for f in filenames:
            yield os.path.join(dirpath, f), os.path.relpath(os.path.join(dirpath, f), d).replace("\\", "/")


def main(dirs):
    # --- パス 1: 言語ファイルの内容ハッシュを採り、何プロジェクトに現れるか数える
    seen = collections.defaultdict(set)
    per_repo = {}
    for name in dirs:
        d = ROOT / name
        if not d.is_dir():
            per_repo[name] = None
            continue
        files = []
        for full, rel in walk(d, LANG_SKIP_DIRS):
            if EXT.get(pathlib.Path(full).suffix) is None:
                continue
            try:
                raw = open(full, "rb").read()
            except OSError:
                continue
            h = hashlib.sha1(raw).hexdigest()
            seen[h].add(name)
            files.append((full, rel, h, raw))
        per_repo[name] = files

    shared = {h for h, s in seen.items() if len(s) >= 3}
    print(f"共有ファイル(3 プロジェクト以上に同一内容): {len(shared)} 種", file=sys.stderr)

    out = {}
    for name in dirs:
        files = per_repo[name]
        rec = {"dir": name, "exists": files is not None, "langs": {}, "flags": [],
               "deps": [], "pyimports": [], "envs": [], "license": None,
               "testfiles": 0, "xval_test_hits": 0, "xval_test_where": [],
               "shared_skipped": 0}
        if files is None:
            out[name] = rec
            continue
        d = ROOT / name
        counts = collections.Counter()
        # 言語ごとに「どこに置かれているか」も数える。役割(SPEC §11)を
        # 書き分けるのに要る —— scripts/ にしか無い JavaScript を
        # 「ブラウザ実装」と書いたら嘘になる。
        bydir = collections.defaultdict(collections.Counter)
        pyimp, envs = set(), set()
        flags = set()
        for full, rel, h, raw in files:
            lang = EXT[pathlib.Path(full).suffix]
            if h in shared:
                rec["shared_skipped"] += 1
                continue
            text = raw.decode("utf-8", "ignore")
            n_lines = text.count("\n") + 1
            counts[lang] += n_lines
            bydir[lang][rel.split("/")[0] if "/" in rel else "."] += n_lines
            if lang == "Python":
                pyimp |= {m.group(1).lower() for m in ML.finditer(text)}
            if WORKER.search(text):
                flags.add("web-worker")
            for m in re.finditer(r"(?:process\.env|os\.environ(?:\.get)?[\[\(])\s*['\"]?([A-Z_][A-Z0-9_]*)", text):
                e = m.group(1)
                if e not in {"NODE_ENV", "VERCEL_URL", "CI", "PATH", "TMPDIR", "VERCEL_ENV"} \
                        and not e.startswith("NEXT_PUBLIC"):
                    envs.add(e)
            is_test = bool(TEST_PATH.search(rel)) or bool(TEST_INLINE.search(text))
            if is_test:
                rec["testfiles"] += 1
                n = len(XVAL.findall(text))
                if n:
                    rec["xval_test_hits"] += n
                    if len(rec["xval_test_where"]) < 3:
                        rec["xval_test_where"].append(rel)
        rec["langs"] = dict(counts.most_common())
        rec["bydir"] = {k: dict(v.most_common(6)) for k, v in bydir.items()}
        rec["pyimports"] = sorted(pyimp)
        rec["envs"] = sorted(envs)
        rec["secret_envs"] = sorted(e for e in envs if SECRET.search(e))

        # --- 成果物と設定(public/ も見る)
        names = []
        for full, rel in walk(d):
            names.append(rel)
            e = pathlib.Path(full).suffix.lower()
            if e == ".wasm":
                flags.add("wasm")
            if e in WEIGHT_EXT:
                try:
                    if os.path.getsize(full) > 20000:
                        flags.add("weights")
                except OSError:
                    pass
        joined = "\n".join(names)
        if (d / "Cargo.toml").exists() or "/Cargo.toml" in joined:
            flags |= {"cargo", "wasm"}
        if (d / "go.mod").exists() or "/go.mod" in joined:
            flags.add("go")
        if re.search(r"(^|/)(app|pages|src/app|src/pages)/api/|^api/.*\.(ts|js|py|go)$", joined, re.M):
            flags.add("server-api")
        wf = d / ".github" / "workflows"
        if wf.is_dir():
            ws = list(wf.glob("*.yml")) + list(wf.glob("*.yaml"))
            if ws:
                flags.add("ci")
            for w in ws:
                t = w.read_text(encoding="utf-8", errors="ignore")
                if re.search(r"^\s*schedule:", t, re.M):
                    flags.add("cron")
                if re.search(r"pytest|check_|npm test|vitest|cargo test|go test|Rscript", t):
                    flags.add("ci-test")
        pj = d / "package.json"
        if pj.exists():
            try:
                j = json.loads(pj.read_text(encoding="utf-8"))
                rec["deps"] = sorted(set(list((j.get("dependencies") or {}).keys())
                                         + list((j.get("devDependencies") or {}).keys())))
                if BROWSER_AI.search(" ".join(rec["deps"])):
                    flags.add("browser-ai-dep")
            except (OSError, ValueError):
                pass
        lic = d / "LICENSE"
        if lic.exists():
            head = lic.read_text(encoding="utf-8", errors="ignore")[:400]
            rec["license"] = "MIT" if "MIT" in head[:200] else (
                "CC BY 4.0" if "Creative Commons" in head else "other")
        if rec["testfiles"]:
            flags.add("tests")
        rec["flags"] = sorted(flags)
        out[name] = rec

    (HERE / "_measured.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    c = collections.Counter()
    for v in out.values():
        for f in v["flags"]:
            c[f] += 1
    print(f"{len(out)} repos measured: {dict(c)}")
    missing = [k for k, v in out.items() if not v["exists"]]
    if missing:
        print("見つからないディレクトリ:", missing)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        names = sys.argv[1:]
    else:
        # apps.json があればそこから、無ければ V1 の抽出結果から
        appsf = HERE.parent / "data" / "apps.json"
        if appsf.exists():
            names = [a["id"] for a in json.loads(appsf.read_text(encoding="utf-8"))["apps"]]
        else:
            raw = json.loads((HERE / "_cards_raw.json").read_text(encoding="utf-8"))
            names = [c["repo"] or re.sub(r"^https?://", "", c["href"]).split(".")[0] for c in raw]
    main(names)
