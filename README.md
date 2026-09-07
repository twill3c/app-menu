# app-menu — Portfolio Edition V2.0

**▶ 公開: https://app-menu-amber.vercel.app**(GitHub 連携 Vercel、main への push で自動デプロイ)

> 公開データを集め、測り、学習させ、ブラウザで触れる形にする。

個人で作って公開しているアプリを、**対象分野・手法・体験・言語・実装・出典**の軸で
横断して探せる技術ポートフォリオ。「何を作ったか」だけでなく「何ができるか」が
見えることを目的にしている(変更仕様書 `docs/SPEC_V2.md`)。

単一の静的サイト。ビルド不要・外部 UI フレームワーク不要・API キー不要。

## 構成

```
index.html                 画面の骨組み(アプリ名もカテゴリ名も書かない)
styles.css                 見た目
app.js                     検索・絞り込み・描画(Vanilla JavaScript)
data/apps.json             アプリ情報の唯一の出どころ
data/taxonomy.json         分類語彙(表示名・順序・アイコン・バッジの条件)
data/search-synonyms.json  静的な同義語辞書
scripts/validate_apps.py   apps.json の検査(CI)
scripts/selftest_validate.py 検査そのものの陽性対照(CI)
scripts/generate_stats.py  内訳を数える
scripts/measure_repos.py   兄弟リポジトリの実測(手元専用)
scripts/migrate_v2.py      V1 → V2 の移行記録(再実行不要)
tools/update_dates.py      最終更新日を実測値に同期(日次 CI)
tools/probe_ui.mjs         実ブラウザ検品(playwright)
tools/probe_expect.py      検品の期待値を apps.json から独立に数え直す
```

## アプリを追加するには

`data/apps.json` の `apps` に 1 レコード足して push するだけ。**HTML は触らない。**

```json
{
  "id": "example-atlas",
  "title": "例のアトラス",
  "shortTitle": "example-atlas",
  "aliases": [],
  "icon": "🗺️",
  "series": "atlas-ai",
  "tracks": ["data-geo"],
  "domains": ["weather-environment"],
  "methods": ["gis", "statistics"],
  "experience": ["map", "chart"],
  "languages": [{ "name": "Python", "role": "ETL・集計" }],
  "runtimes": ["Browser"],
  "architecture": ["static-site", "no-api", "client-only"],
  "dataSources": [{ "category": "jma", "name": "気象庁 平年値" }],
  "libraries": [{ "name": "MapLibre GL JS", "role": "ship" }],
  "summary": "160 字以内。カードの仕事は「開くかどうかを決めさせること」だけ。",
  "badges": ["verified", "open-data", "static-deploy"],
  "appUrl": "https://example-atlas.vercel.app",
  "githubUrl": "https://github.com/twill3c/example-atlas",
  "license": "MIT",
  "featured": false, "featuredOrder": null,
  "firstDeployedAt": "2026-09-07", "updatedAt": "2026-09-07",
  "status": "published"
}
```

新しい分類語が要るときは `data/taxonomy.json` に足す。**HTML にカテゴリ名を
ハードコードしない**(SPEC §34)。まだ公開していないものは `status: "planned"` で
登録できる。既定では出ず、「企画中も見る」を押したときだけ出る。

```bash
python scripts/validate_apps.py --verbose   # 検査(CI と同じもの)
python scripts/generate_stats.py            # 内訳
```

## 絞り込みの決まり

| 軸 | 何で切るか |
|---|---|
| Portfolio Track | どんな能力を示すか(最上位の入口) |
| Domain | 何を対象にしているか |
| Method | どんな分析・推論をしているか |
| Experience | どう見せ、どう触らせるか |
| Language / Runtime | 何で書いたか |
| Architecture | どう配っているか |
| Data Source | データがどこから来たか |
| Series | どのブランドに属するか |

**同じ軸の中は OR、違う軸どうしは AND。** 各チップの数字は「いま押したら何件になるか」で、
0 件のチップは押せない。ただし選択中のものと「指定なし」は必ず残す —— 全部が
無効になると絞り込みから出られなくなるため。

絞り込みの状態は URL の `#` に載るので、そのまま共有できる。

```
#domain=literature-folklore-language&method=nlp&series=atlas-ai&q=青空文庫
```

V1 の `#g=` `#cat=` `#tag=` `#src=` も、移せる範囲で読み替える。

## 検索

- Unicode NFKC 正規化・小文字化・空白の圧縮・記号の寄せ
- 複数語は **AND**(すべての語がどこかの欄に在ること)
- 静的な同義語辞書(`data/search-synonyms.json`)。**AI API は使わない**
- 欄ごとの重み付けスコアで並べる(title 10 … description 2)。
  同義語で当たった分は割り引く —— 割り引かないと「深層学習」で引いたときに
  AI 全般が返り、実際に深層学習を使っているものが埋もれる

## 測って書いていること

カードに出る言語・実装・バッジは、書いたのではなく**兄弟リポジトリを実測した値**。

- `scripts/measure_repos.py` が各リポジトリを走査する。手元専用
  (兄弟は別リポジトリで 9 件が private のため CI からは見えない)
- **同じ内容のファイルが 3 プロジェクト以上に在れば配布物とみなして数えない。**
  `harness/` は 111 プロジェクトすべてでバイト単位に同一で、これを数えると
  Python がほぼ全カードに付く。名前でも内容でも落とす
- **ビルド出力(`.next/` `out/`)を数えない**
- **役割は置き場所で決める。** `scripts/` にしか無い JavaScript を
  「ブラウザ実装」と書いたら嘘になる
- `verified` `cross-validated` `trained-model` などのバッジは、
  `data/taxonomy.json` に判定条件を書いてある。**自己申告の装飾にしない**(SPEC §30)

## 説明文は 160 字以内

カードは横に並ぶ。1 枚だけ極端に長いと高さが崩れ、見比べるという一覧の役目が壊れる。
詳しい話は各アプリの「歩き方」「設計図」に置く。`validate_apps.py` が落とす。

## 検品

```bash
python -m http.server 8099 &
PLAYWRIGHT="file:///c:/_ClaudeCode/hoshihata/node_modules/playwright/index.mjs" \
  node tools/probe_ui.mjs http://127.0.0.1:8099/ shot.png > probe.json
python tools/probe_expect.py probe.json
```

`probe_ui.mjs` は画面から値を読むだけで、期待値を持たない。`probe_expect.py` が
`apps.json` から**独立に数え直して**突き合わせる(二実装照合・159 項目)。
検査が緑でも画面が壊れていることはこのフリートで何度も起きているので、
DOM を実際に触って測る。CI には載せていない(node 環境が無い)。

## 最終更新日は自動同期

```bash
python tools/update_dates.py --check   # 差分の確認だけ
python tools/update_dates.py           # apps.json を実測値に更新
```

`.github/workflows/update-dates.yml` が毎日 JST 12:17 頃に走る。
**取得できなかったことを黙って飲み込まない** —— private な兄弟リポジトリは CI の
`GITHUB_TOKEN` では 404 になるので、終了時に必ず内訳を出す。手元で走らせれば
`gh` の PAT で読める。

## 承知のうえの割り切り

- **画面は JavaScript で描く。** apps.json を唯一の出どころにする以上、HTML には
  アプリが 1 件も書かれていない。JSON-LD は出しているが、JS を実行しない
  クローラからは一覧が見えない。静的な HTML を生成する手は残してある
  (`scripts/generate_stats.py` と同じ場所に置ける)が、V2.0 では入れていない
- **`offline` / `pwa` は名乗らない。** Service Worker を持つアプリが実測で 0 件だったため

MIT License
