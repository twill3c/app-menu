# app-menu Portfolio Edition V2.0 変更仕様書

- 文書種別: 変更仕様書
- 対象システム: `app-menu`
- 対象URL: https://app-menu-amber.vercel.app/
- バージョン: V2.0
- 作成日: 2026-09-07
- 方針: 現行の軽量・静的・無料運用を維持しつつ、「アプリ一覧」から「AI・公開データ・可視化ポートフォリオ」へ再設計する

---

## 1. 目的

本変更の目的は、`app-menu` を単なる公開アプリの一覧ページから、制作者の技術的能力・研究領域・設計思想・実装技術を横断的に提示できるポートフォリオへ発展させることである。

今後、以下のようなアプリ群が継続的に追加されることを前提とする。

- AI / 深層学習アプリ
- 公開データ分析アプリ
- GIS / 地図可視化アプリ
- Atlas AI 系アプリ
- 青空文庫等を用いた計量文学・文化分析アプリ
- 農林水産・防災・気象・交通・歴史・考古等の公開データ分析
- Go / Rust / R / Python / TypeScript 等の複数言語を用いた技術デモ
- WebAssembly / ブラウザ内推論 / 静的配信等のフロントエンド実験
- シミュレーション、教育、実務支援アプリ

V2.0では、作品数が200～300本規模に拡大しても分類・検索体系が破綻しないことを目標とする。

---

## 2. 基本コンセプト

### 2.1 サイトの位置づけ

従来:

> 公開しているアプリをカテゴリ別に探すメニュー

V2.0:

> 公開データを集め、測り、学習し、ブラウザで触れる形にする技術ポートフォリオ

単なる「何を作ったか」だけではなく、以下を閲覧者が理解できる構成とする。

1. 何を題材にしているか
2. どのような分析・AI手法を使っているか
3. どのような可視化・体験を提供しているか
4. どの言語・ランタイム・ライブラリで実装しているか
5. どの公開データを利用しているか
6. なぜその技術を選択したか
7. どのシリーズ・研究テーマに属するか

---

## 3. 変更方針

### 3.1 維持するもの

以下の現行思想は維持する。

- Vercelによる無料公開
- GitHubによるソース管理
- 静的サイト中心
- 原則として外部有料APIへ依存しない
- 軽量なフロントエンド
- URLで検索・絞り込み状態を共有可能
- フィルター件数の動的再計算
- 該当件数0の選択肢の無効化
- 出典・利用ライブラリ・ライセンスの明示
- 再現性・検証可能性を重視

### 3.2 変更するもの

以下をV2.0で変更する。

- トップレベルカテゴリ
- 「棚」の意味
- 技術タグの構造
- 検索方式
- 複数条件フィルター
- アプリカード
- Featured Works
- Series分類
- Language分類
- Engineering Badge
- データ定義方式
- `apps.json` を中心としたデータ駆動構成

---

# 4. 情報アーキテクチャ

## 4.1 旧分類の課題

従来の分類では、例えば以下の概念が同一階層に存在する。

- 遊ぶ
- AI・機械学習
- データ・地図
- 文学・古典・美術
- しくみ・実務

これらは、

- 体験形式
- 分析技術
- 表示形式
- 対象分野
- 利用目的

が混在している。

複合型アプリが増えた場合、例えば

> 文学 × GIS × NLP × 深層学習 × 青空文庫

を一つのカテゴリへ配置することが困難になる。

V2.0では分類を複数の独立したFacetへ分離する。

---

# 5. Facet構成

V2.0では、以下の7軸を正式な検索・分類軸とする。

1. Portfolio Track
2. Domain
3. Method
4. Experience / Visualization
5. Language / Runtime
6. Architecture / Engineering
7. Data Source

さらに独立属性として、

8. Series

を持たせる。

---

# 6. Portfolio Track

## 6.1 目的

Portfolio Trackは、「制作者がどのような能力を持っているか」を示す最上位の見せ方である。

厳密な分類ではなく、ポートフォリオ閲覧者の入口として利用する。

1アプリが複数Trackに所属してよい。

## 6.2 初期Track

### `ai-insight`

表示名:

> AIを理解・可視化する

対象例:

- 深層学習
- 機械学習
- XAI
- モデル解析
- 特徴量可視化
- 学習過程可視化

---

### `data-geo`

表示名:

> 公開データを地図で読む

対象例:

- GIS
- 地理空間分析
- 公開統計
- 地域差分析
- 時系列地図
- Atlas AI

---

### `computational-humanities`

表示名:

> 文学・文化を計量する

対象例:

- 青空文庫
- Project Gutenberg
- 民俗学
- 歴史資料
- NLP
- Embedding
- 地名抽出
- 文学地理

---

### `simulation`

表示名:

> シミュレーションで理解する

対象例:

- 物理
- 探索
- 最適化
- 強化学習
- エージェント
- Go/WASM
- 数値計算

---

### `browser-ai`

表示名:

> ブラウザだけでAIを動かす

対象例:

- ONNX Runtime Web
- Transformers.js
- WebGPU
- WebAssembly
- TensorFlow.js
- ブラウザ内推論

---

### `practical-tools`

表示名:

> 実務に落とし込む

対象例:

- 業務支援
- ジェネレータ
- プランナー
- 可視化ツール
- データ変換
- ガバナンス支援

---

# 7. Domain

## 7.1 原則

Domainは「何を対象としているか」だけを表す。

技術、UI形式、プログラミング言語は含めない。

## 7.2 初期Domain

| ID | 表示名 |
|---|---|
| `society-transport` | 社会・都市・交通 |
| `disaster-infra` | 防災・インフラ |
| `agri-forest-fishery` | 農林水産 |
| `weather-environment` | 気象・自然環境 |
| `history-archaeology-faith` | 歴史・考古・信仰 |
| `literature-folklore-language` | 文学・民俗・言語 |
| `art-music` | 芸術・音楽 |
| `science-medical` | 科学・医療 |
| `ai-computing` | AI・コンピューティング |
| `business-governance` | 実務・ガバナンス |
| `game-education` | ゲーム・教育 |

1アプリに複数Domainを付与可能とする。

---

# 8. Method

## 8.1 目的

分析・推論・処理方法を独立して検索できるようにする。

## 8.2 初期Method

- 深層学習
- 機械学習
- 自然言語処理
- Embedding
- 画像認識
- 音声認識
- 時系列分析
- 統計解析
- 統計検定
- 回帰
- クラスタリング
- 異常検知
- 空間統計
- GIS
- グラフ分析
- 強化学習
- 最適化
- 探索
- シミュレーション
- 数値計算
- ルールベース分析

---

# 9. Experience / Visualization

## 9.1 目的

利用者が「どのように情報を見る・操作するか」を表す。

## 9.2 初期値

- 地図 / Atlas
- ダッシュボード
- チャート
- タイムライン
- ネットワーク
- 3D
- ヒートマップ
- シミュレータ
- 検索
- 比較
- ジェネレータ
- ゲーム
- インタラクティブ教材
- レイヤー管理
- アニメーション

---

# 10. Language / Runtime

## 10.1 方針

プログラミング言語は、DomainやMethodとは別の独立Facetとする。

R、Go、Rustを用いているという情報はポートフォリオ上有効であるため、正式に保持する。

ただし、

> AI / 地図 / 文学 / Rust

のように対象分野と同じカテゴリ階層には置かない。

## 10.2 初期Language

- Python
- TypeScript
- JavaScript
- Go
- Rust
- R
- SQL
- DAX
- HTML
- CSS

## 10.3 Runtime

Languageと同じUIグループ内で、必要に応じてRuntimeも表示可能とする。

- WebAssembly
- WebGPU
- Node.js
- Browser
- Python Runtime
- GitHub Actions

## 10.4 ポートフォリオ上の意味

| 技術 | 主な意味 |
|---|---|
| Python | AI、深層学習、ETL、データ分析 |
| TypeScript | Web UI、型安全なフロントエンド |
| JavaScript | 軽量ブラウザ実装 |
| Go | 並行処理、ネットワーク処理、高速バックエンド、WASM |
| Rust | メモリ安全、高速処理、WASM、システム寄り処理 |
| R | 統計解析、検定、回帰、可視化 |
| SQL | データ抽出・集計 |
| DAX | BI・分析モデル |

---

# 11. 技術利用理由

言語・ライブラリ名だけではなく、可能な場合は「何のために使ったか」を記録する。

例:

```json
{
  "name": "Go",
  "role": "並列クローラーの実装",
  "reason": "大量URLをgoroutineで並行処理するため"
}
```

```json
{
  "name": "Rust",
  "role": "ブラウザ内数値計算",
  "reason": "WASM経由で高速かつ安全な処理を実現するため"
}
```

```json
{
  "name": "R",
  "role": "統計検定",
  "reason": "回帰分析と統計検定の再現可能な検証環境として利用"
}
```

カード上では必要に応じて以下のように表示する。

> Go — 並列クローラー処理

> Rust — WASMによるブラウザ内高速計算

> R — 統計検定・回帰分析

---

# 12. Architecture / Engineering

## 12.1 初期タグ

- ブラウザ内推論
- Client-only
- 静的サイト
- WebAssembly
- WebGPU
- Web Worker
- GitHub Actions
- 自動更新
- オフライン対応
- PWA
- API不要
- サーバーレス
- 依存ゼロ
- ローカル処理
- 再現可能ビルド

---

# 13. Data Source

## 13.1 方針

公開データや資料の出典を独立Facetとして管理する。

## 13.2 初期カテゴリ

- 青空文庫
- Project Gutenberg
- Perseus
- Internet Archive
- Wikimedia Commons
- 政府統計
- 国土数値情報
- 自治体オープンデータ
- 気象庁
- 国土地理院
- 農林水産省
- 林野庁
- 水産庁
- 国立国会図書館
- 公開研究データセット
- Kaggle
- GitHub公開データ
- その他Public Domain / Open Data

具体的な機関名・データセット名は、別途配列として保持する。

---

# 14. Series

## 14.1 目的

共通した設計思想・UI・研究アプローチを持つアプリ群をブランドとしてまとめる。

## 14.2 初期Series

- Atlas AI
- Lens
- Lab
- Forge
- Dojo
- Simulator
- Planner
- Games
- Standalone

---

# 15. Atlas AI Collection

Atlas AIをV2.0の中心的シリーズとして正式に扱う。

## 15.1 コンセプト

> 公開データ・文献・位置情報を統合し、GIS・統計・機械学習・深層学習によって「場所から読む」シリーズ

## 15.2 想定サブグループ

### Public Data & Geo Intelligence

- Japan Station Flow Atlas AI
- Food Self-Sufficiency Atlas AI
- Forestry Atlas AI
- Disaster Base Atlas AI
- River Fishery Rights Atlas AI
- JA Atlas AI
- Fishing Port Atlas AI
- Japan Weather & Atmosphere Atlas AI
- Japan Long Trail Atlas AI

### Computational Humanities

- Torahiko GeoScience Atlas AI
- Yanagita Folklore Atlas AI
- Mystery & Weird Literature Atlas AI
- Matatabi Atlas AI
- Aozora Flora Atlas AI
- World Folktale Atlas AI

### History & Culture

- Kofun Atlas AI
- Jinja Origin Atlas AI
- ArchaeoStone Atlas AI

Atlas AIはDomainではなくSeriesである。

---

# 16. トップページ再設計

## 16.1 Hero

トップには次を表示する。

```text
AI / Public Data / Visualization Portfolio

公開データを集め、測り、学習し、
ブラウザで触れる形にする。
```

サイト名として個人名またはGitHubハンドルの併記を許容する。

---

## 16.2 KPI

Hero直下にポートフォリオの規模を示す。

例:

```text
公開アプリ 128
AI / ML 47
Atlas AI 23
Browser AI 19
Open Data 61
```

件数は`apps.json`から自動計算する。

---

# 17. Featured Works

## 17.1 目的

作品数が増えても、初訪問者が代表的な能力を短時間で把握できるようにする。

## 17.2 表示数

4～8件。

推奨6件。

## 17.3 選定基準

アクセス数順には限定しない。

以下の技術的な幅を示せる作品を優先する。

- Browser AI
- Atlas AI
- Computational Humanities
- Simulation
- Scientific AI
- Practical AI

`featured: true` と `featuredOrder` で管理する。

---

# 18. Explore the Portfolio

Featured Worksの後にTrackによる入口を表示する。

```text
🤖 AIを理解・可視化する
🗺️ 公開データを地図で読む
📚 文学・文化を計量する
🧪 シミュレーションで理解する
🌐 ブラウザだけでAIを動かす
🛠️ 実務に落とし込む
```

クリックすると該当Trackが選択された状態で一覧へスクロールする。

---

# 19. 検索機能

## 19.1 基本検索

検索欄は以下を対象とする。

- アプリ名
- 別名
- 概要
- キーワード
- Domain
- Track
- Method
- Experience
- Language
- Architecture
- Data Source
- Series
- ライブラリ
- 利用データセット名

---

## 19.2 正規化

検索前に以下を実行する。

1. Unicode NFKC正規化
2. 英字小文字化
3. 前後空白除去
4. 連続空白圧縮
5. 記号の一部正規化

---

## 19.3 複数語検索

検索文字列:

```text
青空文庫 地図 pytorch
```

は3トークンとして扱う。

初期仕様ではAND検索とする。

すべての語が何らかの検索対象フィールドに存在するアプリを候補とする。

---

# 20. 同義語検索

AI APIを検索のためだけに利用しない。

静的同義語辞書を持たせる。

例:

```json
{
  "ai": ["ai", "人工知能", "機械学習", "深層学習"],
  "dl": ["dl", "deep learning", "深層学習", "ニューラルネット"],
  "nlp": ["nlp", "自然言語処理"],
  "map": ["map", "地図", "atlas", "gis", "地理空間"],
  "aozora": ["青空文庫", "aozora"],
  "wasm": ["wasm", "webassembly"],
  "防災": ["防災", "災害", "避難", "地震", "洪水"]
}
```

辞書は`search-synonyms.json`または`app.js`内で管理する。

---

# 21. 検索結果ランキング

単純な部分一致だけでなく、検索中はスコアリングを行う。

推奨重み:

| フィールド | 重み |
|---|---:|
| title | 10 |
| aliases | 8 |
| keywords | 8 |
| summary | 6 |
| tracks | 5 |
| domains | 5 |
| methods | 5 |
| experience | 4 |
| languages | 4 |
| series | 4 |
| dataSources | 3 |
| libraries | 3 |
| description | 2 |

複数語の場合は各語のスコアを合算する。

同点の場合は以下の優先順位とする。

1. Featured
2. 最終更新日
3. タイトル昇順

---

# 22. フィルター

## 22.1 UI

検索欄直下には「詳細条件」を設置する。

展開時:

```text
領域
[文学] [農林水産] [防災] [気象] [歴史] ...

手法
[深層学習] [NLP] [画像認識] [GIS] [統計] ...

表示・体験
[地図] [ネットワーク] [時系列] [シミュレータ] ...

言語
[Python] [TypeScript] [Go] [Rust] [R] ...

実装
[ブラウザ内推論] [WASM] [WebGPU] [自動更新] ...

出典
[青空文庫] [政府統計] [気象庁] [Gutenberg] ...

シリーズ
[Atlas AI] [Lens] [Lab] [Forge] ...
```

---

# 23. フィルター論理

## 23.1 同一Facet

複数選択を許可する。

初期仕様:

> OR

例:

```text
Language = Go OR Rust
```

## 23.2 異なるFacet

> AND

例:

```text
Domain = 農林水産
AND
Method = 深層学習
AND
Experience = 地図
AND
Language = Python
```

---

# 24. 動的件数

各チップに現在条件下での件数を表示する。

例:

```text
[深層学習 28]
[GIS 17]
[Go 5]
[Rust 4]
[R 6]
```

現在の条件を追加した結果0件になる選択肢は無効化する。

既存機能がある場合は維持・拡張する。

---

# 25. URL状態共有

検索・Facet選択状態をURLで共有可能とする。

推奨例:

```text
#q=青空文庫&domain=literature-folklore-language&method=nlp&series=atlas-ai
```

URLSearchParams相当の形式を利用する。

旧URLとの互換性を可能な範囲で維持する。

---

# 26. 検索中の表示

通常時はDomainまたはTrack単位でセクション表示してよい。

自由検索文字列が入力されている場合は、棚構造を解除し、

```text
検索結果 18件
```

としてランキング順に単一リスト表示する。

---

# 27. アプリカード変更

## 27.1 旧カード

従来カードで優先されていた情報:

- 名称
- 説明
- URL
- 初回デプロイ
- 最終更新
- ライセンス
- タグ

## 27.2 新カード

ポートフォリオ向けに優先順位を変更する。

推奨構成:

```text
[ATLAS AI] [農林水産]

🌾 Food Self-Sufficiency Atlas AI

作物別自給率を都道府県・時系列で可視化し、
関連指標から将来傾向をモデル化。

深層学習 · 時系列 · GIS
Python · PyTorch · MapLibre
政府公開データ

✓ 検証済み   🌐 Open Data

[アプリを見る] [GitHub] [詳細]
```

---

# 28. カードで優先する情報

1. タイトル
2. 1～2行の概要
3. Series
4. Domain
5. Method
6. Language
7. 主要ライブラリ
8. Data Source
9. Engineering Badge
10. アプリリンク
11. GitHubリンク

URL文字列そのものは通常表示しない。

---

# 29. Engineering Badge

## 29.1 目的

単に「動くアプリ」ではなく、検証・再現性・アーキテクチャ上の特徴を示す。

## 29.2 初期Badge

- `verified` — 検証済み
- `client-only` — ブラウザ内完結
- `open-data` — Open Data
- `trained-model` — 学習済みモデル
- `cross-validated` — 相互検証・二重照合
- `static-deploy` — 静的デプロイ
- `offline` — オフライン対応
- `reproducible` — 再現可能
- `public-domain` — Public Domain
- `no-api-key` — APIキー不要

---

# 30. Badgeの条件

Badgeは自己申告的装飾にしない。

可能な限り判定条件を定義する。

例:

### verified

以下のいずれかが存在する。

- テストコード
- 比較検証
- オラクル実装
- 統計検定
- 他実装との照合

### client-only

入力データが外部サーバーへ送信されず、推論・処理がブラウザ内で完結する。

### open-data

主要データソースが再利用可能な公開データである。

---

# 31. データ駆動化

## 31.1 方針

V2.0では、アプリ情報をHTMLへ直接記述する方式から、`apps.json` を単一情報源とする方式へ移行する。

推奨構成:

```text
/
├─ index.html
├─ styles.css
├─ app.js
├─ data/
│  ├─ apps.json
│  ├─ taxonomy.json
│  └─ search-synonyms.json
├─ scripts/
│  ├─ validate_apps.py
│  └─ generate_stats.py
└─ README.md
```

Next.js、React、データベースは必須としない。

依存ゼロまたは最小依存を原則とする。

---

# 32. apps.json スキーマ

## 32.1 例

```json
{
  "id": "station-flow-atlas-ai",
  "title": "Japan Station Flow Atlas AI",
  "shortTitle": "Station Flow Atlas",
  "aliases": [
    "駅乗降者数可視化"
  ],
  "series": "atlas-ai",
  "tracks": [
    "data-geo",
    "ai-insight"
  ],
  "domains": [
    "society-transport"
  ],
  "methods": [
    "deep-learning",
    "time-series",
    "gis"
  ],
  "experience": [
    "map",
    "chart",
    "prediction"
  ],
  "languages": [
    {
      "name": "Python",
      "role": "ETL・モデル学習"
    },
    {
      "name": "TypeScript",
      "role": "フロントエンド"
    }
  ],
  "architecture": [
    "static-site",
    "github-actions"
  ],
  "dataSources": [
    {
      "category": "government-open-data",
      "name": "公開鉄道統計",
      "license": "source-dependent"
    }
  ],
  "libraries": [
    {
      "name": "PyTorch",
      "role": "モデル学習",
      "delivery": "build"
    },
    {
      "name": "MapLibre GL JS",
      "role": "地図表示",
      "delivery": "runtime"
    }
  ],
  "summary": "全国の鉄道駅の乗降者数推移を地図と時系列で可視化し、将来傾向を分析する。",
  "description": "",
  "keywords": [
    "駅",
    "鉄道",
    "乗降者数",
    "railway",
    "station"
  ],
  "badges": [
    "open-data",
    "static-deploy"
  ],
  "appUrl": "",
  "githubUrl": "",
  "license": "MIT",
  "featured": false,
  "featuredOrder": null,
  "firstDeployedAt": null,
  "updatedAt": null,
  "status": "planned"
}
```

---

# 33. status

今後の企画アプリも登録可能とするため、公開済み以外の状態を持てるようにする。

許容値:

- `planned`
- `prototype`
- `beta`
- `published`
- `archived`

通常のトップ一覧は原則 `published` を表示する。

「企画中を見る」を有効化した場合のみplanned等を表示してもよい。

---

# 34. taxonomy.json

カテゴリ名称・順序・説明をデータ化する。

例:

```json
{
  "domains": [
    {
      "id": "agri-forest-fishery",
      "label": "農林水産",
      "icon": "🌾",
      "order": 30
    }
  ],
  "methods": [
    {
      "id": "deep-learning",
      "label": "深層学習",
      "order": 10
    }
  ]
}
```

HTMLへカテゴリ名をハードコードしない。

---

# 35. apps.json検証

Pythonスクリプト `scripts/validate_apps.py` を設置する。

検証内容:

- `id` 重複
- 必須項目
- 未定義taxonomy
- URL形式
- 日付形式
- series値
- status値
- badge値
- language名
- 空配列
- featuredOrder重複
- GitHub URLの不整合

GitHub Actionsでpush時に実行可能とする。

---

# 36. 検索インデックス

初期段階では外部検索ライブラリを導入しない。

JavaScriptで各レコードから検索用文字列を生成する。

例:

```js
const searchText = normalize([
  app.title,
  app.shortTitle,
  ...(app.aliases ?? []),
  app.summary,
  ...(app.keywords ?? []),
  ...resolveLabels(app.tracks),
  ...resolveLabels(app.domains),
  ...resolveLabels(app.methods),
  ...app.languages.map(x => x.name),
  ...app.libraries.map(x => x.name),
  ...app.dataSources.map(x => x.name)
].join(" "));
```

アプリ数が1,000件を超える場合のみFuse.js等の導入を再検討する。

---

# 37. 人気の入口

検索欄付近に代表的なショートカットを配置する。

例:

- Atlas AI
- Browser AI
- 青空文庫
- 公開データ
- 深層学習
- WASM
- Go
- Rust
- R

利用頻度やアプリ増加に応じて変更可能とする。

---

# 38. 詳細ページ

V2.0初期では必須ではない。

カードから外部アプリとGitHubへ直接遷移できればよい。

将来V2.1以降で、`?app=id` またはモーダルにより以下を表示可能とする。

- 技術構成
- 利用データ
- モデル
- 精度
- 技術選定理由
- アーキテクチャ図
- スクリーンショット
- 開発履歴

---

# 39. レスポンシブ対応

## Desktop

- 左右に十分な余白
- Featured Works: 3列
- All Projects: 3～4列
- 詳細Facetを複数列

## Tablet

- Featured Works: 2列
- All Projects: 2列

## Mobile

- 1列
- FacetはAccordion
- 選択済み条件を検索欄直下にChip表示
- 「条件をクリア」を固定表示可能

---

# 40. アクセシビリティ

最低限以下を満たす。

- button要素を利用
- キーボード操作可能
- `aria-expanded`
- `aria-pressed`
- 十分なコントラスト
- focus-visible
- アイコンだけで意味を伝えない
- 絵文字には必要に応じてaria-hidden

---

# 41. パフォーマンス

目標:

- 外部UIフレームワーク不要
- 初回JS 100KB未満を目標
- JSONはgzip前提
- 画像lazy loading
- フォント依存を最小化
- Core Web Vitalsを阻害しない

200～300アプリ程度はクライアント側フィルターで処理する。

---

# 42. SEO

以下を設定する。

```html
<title>AI / Public Data / Visualization Portfolio</title>
```

meta descriptionには、

- AI
- Deep Learning
- Public Data
- GIS
- Visualization
- WebAssembly
- Open Data

等を自然に含める。

各アプリは可能であればJSON-LD `SoftwareApplication` として出力する。

---

# 43. GitHubとの関係

カードには可能な限り、

- Live App
- GitHub

の両方を表示する。

ポートフォリオの評価では実装確認可能性が重要であるため、GitHubリンクをURL文字列そのものより優先する。

---

# 44. 今日企画したアプリ群の登録方針

以下は原則としてSeries=`atlas-ai`とする。

| アプリ | 主Domain |
|---|---|
| Japan Station Flow Atlas AI | 社会・都市・交通 |
| Food Self-Sufficiency Atlas AI | 農林水産 |
| Forestry Atlas AI | 農林水産 |
| Disaster Base Atlas AI | 防災・インフラ |
| River Fishery Rights Atlas AI | 農林水産 |
| JA Atlas AI | 農林水産 |
| Fishing Port Atlas AI | 農林水産 |
| Japan Weather & Atmosphere Atlas AI | 気象・自然環境 |
| Japan Long Trail Atlas AI | 気象・自然環境 / 社会・都市・交通 |
| ArchaeoStone Atlas AI | 歴史・考古・信仰 |
| Kofun Atlas AI | 歴史・考古・信仰 |
| Jinja Origin Atlas AI | 歴史・考古・信仰 |
| Torahiko GeoScience Atlas AI | 文学・民俗・言語 / 気象・自然環境 |
| Yanagita Folklore Atlas AI | 文学・民俗・言語 |
| Mystery & Weird Literature Atlas AI | 文学・民俗・言語 |
| Matatabi Atlas AI | 文学・民俗・言語 |
| Aozora Flora Atlas AI | 文学・民俗・言語 / 気象・自然環境 |
| World Folktale Atlas AI | 文学・民俗・言語 |

---

# 45. R / Go / Rust作品の見せ方

## Go

主に以下を訴求できる。

- goroutine
- channel
- 並行処理
- ネットワーク処理
- WebAssembly
- 軽量バックエンド

カード例:

```text
Go · WebAssembly
並列シミュレーション
```

## Rust

主に以下を訴求できる。

- メモリ安全
- 高速数値計算
- WebAssembly
- 所有権モデル
- システムプログラミング

カード例:

```text
Rust · WASM
ブラウザ内高速計算
```

## R

主に以下を訴求できる。

- 統計分析
- 回帰
- 検定
- 可視化
- データサイエンス

カード例:

```text
R
統計検定・回帰分析
```

---

# 46. 実装優先順位

## Phase 1 — データモデル

1. `apps.json`
2. `taxonomy.json`
3. 既存アプリ移行
4. JSON validation

最優先。

---

## Phase 2 — Facet Search

1. Domain
2. Method
3. Experience
4. Language
5. Architecture
6. Data Source
7. Series

複数選択対応。

---

## Phase 3 — Portfolio UI

1. Hero
2. KPI
3. Featured Works
4. Portfolio Tracks
5. 新カード

---

## Phase 4 — Search Upgrade

1. NFKC正規化
2. 複数語AND
3. 同義語
4. スコアリング
5. 検索結果ランキング

---

## Phase 5 — Engineering Presentation

1. Badge
2. 技術利用理由
3. GitHub導線
4. 検証情報

---

# 47. 非目標

V2.0では以下を必須としない。

- Next.js移行
- React移行
- データベース
- CMS
- ユーザーアカウント
- コメント
- いいね
- サーバーサイド検索
- LLM検索
- ベクトルDB
- 有料API
- 有料Vercel機能

---

# 48. 受入条件

## 分類

- 全公開アプリが少なくとも1つのDomainを持つ
- MethodとDomainが混在しない
- SeriesとDomainが混在しない
- Languageが独立Facetとして存在する
- Go / Rust / Rでフィルター可能

## 検索

- タイトル検索可能
- 技術名検索可能
- データソース検索可能
- 日本語・英語混在検索可能
- 複数語検索可能
- 検索結果が関連度順に並ぶ

## フィルター

- 同一Facetで複数選択可能
- 同一FacetはOR
- 異なるFacetはAND
- 各選択肢に件数表示
- 0件選択肢を無効化
- 条件を一括解除可能

## URL

- 検索状態を再読込後も復元可能
- URL共有可能

## UI

- Featured Worksを表示
- Track入口を表示
- Seriesをカードに表示可能
- Languageをカードに表示可能
- Engineering Badgeを表示可能

## データ管理

- アプリ情報が`apps.json`から生成される
- taxonomy未定義値をCIで検出可能
- ID重複をCIで検出可能

---

# 49. 成功指標

定量的には以下を参考値とする。

- 任意アプリへ3操作以内に到達
- 技術名から該当アプリを2操作以内で表示
- Domain × Method × Languageの検索が可能
- 200アプリでも検索応答が体感即時
- トップ画面で代表的な6能力領域を把握可能
- アプリ追加時にHTML編集不要

---

# 50. 将来拡張

V2.1以降の候補:

- 技術詳細モーダル
- アプリ比較
- Timeline表示
- GitHub更新情報自動取得
- スクリーンショット
- アーキテクチャ図
- 「この技術を使った作品」逆引き
- 「このデータソースを使った作品」逆引き
- 技術スタックネットワーク
- Portfolio Map
- 年別開発履歴
- Languages Dashboard
- AI / GIS / Humanitiesの比率可視化

---

# 51. 最終UI概念

```text
┌───────────────────────────────────────────────┐
│ AI / Public Data / Visualization Portfolio   │
│                                               │
│ 公開データを集め、測り、学習し、             │
│ ブラウザで触れる形にする。                    │
│                                               │
│ Apps 128  AI 47  Atlas 23  Browser AI 19     │
└───────────────────────────────────────────────┘

Featured Works

[Atlas AI] [Browser AI] [Simulation]
[Humanities] [Scientific AI] [Practical]

Explore the Portfolio

🤖 AI
🗺 Public Data & Geo
📚 Computational Humanities
🧪 Simulation
🌐 Browser AI
🛠 Practical Tools

───────────────────────────────────────────────

🔍 アプリ・技術・データを検索
   青空文庫 地図 / PyTorch / 防災 深層学習

[Atlas AI] [WASM] [Go] [Rust] [R]

詳細条件 ▼

Domain
Method
Experience
Language
Architecture
Data Source
Series

───────────────────────────────────────────────

All Projects / Search Results

[App Card]
[App Card]
[App Card]
```

---

# 52. 設計原則

本変更では以下を最重要原則とする。

### 1. 「何を作ったか」だけではなく「何ができるか」を見せる

個別アプリを分類するだけでなく、AI、GIS、NLP、統計、WASM、Go、Rust、Rなどを横断的に発見できること。

### 2. 対象・手法・言語・見せ方を混同しない

Domain / Method / Experience / Language / Architectureを明確に分離する。

### 3. シリーズをブランドとして育てる

特にAtlas AIを、公開データ・地理空間・AIを組み合わせた代表シリーズとして位置づける。

### 4. 技術名だけでなく採用理由を示す

「Rustを使用」より、

> RustをWASMへコンパイルし、ブラウザ内で高速数値計算

の方がポートフォリオとして価値が高い。

### 5. 静的・軽量・無料という長所を維持する

ポートフォリオ化のために重量級フレームワークや有料サービスを導入しない。

### 6. データ駆動で継続的に拡張できる構造にする

アプリ追加作業は原則`apps.json`への1レコード追加で完結させる。

---

# 53. 完成時のサイトの性格

V2.0完成後の`app-menu`は、以下の3つの役割を同時に持つ。

1. **Application Directory**  
   公開アプリを探して利用する場所

2. **Technical Portfolio**  
   AI、GIS、NLP、統計、Go、Rust、R、WASM等の実装能力を示す場所

3. **Research / Experiment Catalogue**  
   公開データ、文学、歴史、自然科学、社会データ等を用いた研究・実験成果を蓄積する場所

したがって、V2.0では単なるカテゴリ整理ではなく、

> **作品を検索するサイトから、技術・研究能力を探索できるサイトへの転換**

を本変更の本質とする。

---

# 54. バージョン定義

## V1.x

- アプリ一覧
- 単純分類
- 基本フィルター

## V2.0

- Portfolio Track
- 多軸Facet
- Series
- Language / Runtime
- Engineering Badge
- Featured Works
- 高機能検索
- `apps.json`中心のデータ駆動構成

## V2.1以降

- 個別詳細
- 技術グラフ
- 開発Timeline
- 自動GitHub連携
- Portfolio Dashboard

---

# 55. 実装判断

V2.0の初期実装は、

- HTML
- CSS
- Vanilla JavaScript
- JSON
- Pythonによる検証スクリプト
- GitHub Actions
- Vercel

を標準構成とする。

React / Next.js等への移行は行わない。

理由:

- 現行の軽量性を維持できる
- 数百件規模ならブラウザ検索で十分高速
- Vercel無料枠と相性がよい
- GitHub上でデータ差分を確認しやすい
- 依存更新コストを抑制できる
- ポートフォリオそのものの長期保守性が高い

以上を **app-menu Portfolio Edition V2.0** の変更仕様とする。
