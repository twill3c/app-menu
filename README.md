# app-menu

**▶ 公開: https://app-menu-amber.vercel.app**(GitHub 連携 Vercel、main への push で自動デプロイ)

Vercel で公開中のアプリ 19 本をカテゴリ別に並べた一覧メニューサイト。
単一の `index.html` による完全静的サイト(ビルド不要・依存ゼロ)。

## 構成

- `index.html` — 全アプリのカード一覧(検索フィルタ付き、ダークモード対応)

## アプリを追加するには

`index.html` の該当カテゴリ `<section>` に `.card` を 1 枚追加して push するだけ。

## 説明文は 160 字以内

`.desc` の説明文は **表示文字数で 160 字を上限**とする(タグは数えない)。

- カードは横に並ぶ。1 枚だけ極端に長いと高さが崩れ、見比べるという一覧の役目が壊れる
- 絞り込みは `card.textContent` 全体を走査するので、長い説明文は検索のノイズになる
- 詳しい話は各アプリの「歩き方」「設計図」に書く。カードの仕事は**開くかどうかを決めさせること**だけ

```bash
python tools/check_desc.py    # 160 字超のカードを一覧(超過があれば exit 1)
```

## カードの最終更新日は自動同期

`最終更新` は手書きではなく、各リポジトリの最終コミット日(JST)に日次で揃えている。

```bash
python tools/update_dates.py --check   # 差分の確認だけ(CI 用)
python tools/update_dates.py           # index.html を実測値に更新
```

- `.github/workflows/update-dates.yml` が毎日 JST 12:17 頃に実行し、差分があればコミットする
- リポジトリ名は URL のサブドメインから推定する。異なる場合はカードに `data-repo="..."` を付ける
  (例: `kokorograph` → `kokoro-graph`)
- `初回デプロイ` は作成日なので自動更新の対象外(手書きのまま)
- GitHub API の取得に失敗した会社は既存の日付を維持する(劣化継続)
