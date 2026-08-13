# app-menu

**▶ 公開: https://app-menu-amber.vercel.app**(GitHub 連携 Vercel、main への push で自動デプロイ)

Vercel で公開中のアプリ 19 本をカテゴリ別に並べた一覧メニューサイト。
単一の `index.html` による完全静的サイト(ビルド不要・依存ゼロ)。

## 構成

- `index.html` — 全アプリのカード一覧(検索フィルタ付き、ダークモード対応)

## アプリを追加するには

`index.html` の該当カテゴリ `<section>` に `.card` を 1 枚追加して push するだけ。
