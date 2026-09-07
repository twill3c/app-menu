#!/usr/bin/env python3
"""V1 の index.html から V2 の data/apps.json を組み立てる一度きりの移行スクリプト。

以後 apps.json が唯一の出どころ(SPEC §31)で、このスクリプトを再実行する必要はない。
残してあるのは「V2 の各欄がどこから来たか」を後から辿れるようにするため。

各欄の出どころ:
  title / summary / url / 日付 / license  … V1 のカード(scripts/_cards_raw.json)
  languages / architecture / badges       … 兄弟リポジトリの実測(scripts/_measured.json)
  githubUrl                               … gh repo list の visibility(scripts/_repos.json)
  tracks / domains / methods / experience … 下の FACETS 表(人手・カード本文と実測から判断)

実測の注意:
  - harness/ は 111 プロジェクトすべてでバイト単位に同一のスキャフォールドなので
    言語の集計から除いている。含めると Python が 100 枚のカードに付く(嘘になる)。
  - .claude/ と public/ も同じ理由で除く。ただし .wasm と重みファイルの検出だけは
    public/ を含めて別に走らせている(Go/Rust の成果物は public/ に置かれるため)。
"""
import html
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent

# ---------------------------------------------------------------- 略号
# tracks
A, G, H, S, B, P = ("ai-insight", "data-geo", "computational-humanities",
                    "simulation", "browser-ai", "practical-tools")
# domains
SOC, DIS, AGR, WEA, HIS, LIT, ART, SCI, AI, BIZ, GAME = (
    "society-transport", "disaster-infra", "agri-forest-fishery",
    "weather-environment", "history-archaeology-faith",
    "literature-folklore-language", "art-music", "science-medical",
    "ai-computing", "business-governance", "game-education")

# FACETS[id] = (series, [tracks], [domains], [methods], [experience])
FACETS = {
 "midashi-sanmenkyo": ("standalone", [P, H], [SOC], ["nlp", "statistics"], ["dashboard", "comparison", "chart"]),
 "koho-lens":         ("lens", [P], [BIZ], ["rule-based"], ["dashboard"]),
 "kiban-lens":        ("lens", [P], [AI], ["rule-based"], ["dashboard"]),
 "kasumigaseki-lens": ("lens", [P], [BIZ, SOC], ["rule-based"], ["dashboard"]),
 "hyakunin-lens":     ("lens", [P], [AI], ["rule-based"], ["dashboard", "search"]),
 "hyakugaku-lens":    ("lens", [P], [AI, SOC], ["rule-based"], ["dashboard", "search"]),
 "hodo-hangenki":     ("standalone", [P, G], [SOC], ["statistics", "time-series"], ["chart", "dashboard"]),

 "yomikiri-ban":   ("games", [S], [GAME], ["search"], ["game", "interactive"]),
 "karakuri-hako":  ("games", [], [GAME], [], ["game", "interactive"]),
 "nanpure-forge":  ("forge", [S], [GAME], ["search"], ["generator", "game"]),
 "jirai-sweep":    ("games", [S], [GAME], ["search", "rule-based"], ["game"]),
 "meikyu-rogue":   ("games", [S], [GAME], ["search", "simulation"], ["game"]),
 "soko-forge":     ("forge", [S], [GAME], ["search", "optimization"], ["game", "generator"]),

 "kawara-kuzushi":  ("games", [S], [GAME], ["simulation"], ["game", "animation"]),
 "yagura-defense":  ("games", [S], [GAME], ["simulation"], ["game"]),
 "kaguya-lander":   ("games", [S], [GAME, SCI], ["simulation", "numerical"], ["game"]),
 "go-particle-lab": ("lab", [S], [GAME, SCI], ["simulation", "numerical"], ["game", "simulator", "interactive"]),
 "yokemichi":       ("games", [S], [GAME], ["search"], ["game"]),

 "command-type": ("games", [], [GAME], [], ["game"]),
 "bungo-type":   ("games", [], [GAME, LIT], [], ["game"]),
 "onkan-dojo":   ("dojo", [S], [ART, GAME], ["numerical", "simulation"], ["game", "interactive"]),

 "tsugi-no-hito-ji": ("standalone", [A, B], [AI, LIT], ["nlp", "machine-learning", "statistics"], ["interactive", "chart", "game"]),
 "token-hakari":     ("standalone", [A], [AI, LIT], ["nlp"], ["comparison", "interactive"]),
 "imi-chizu":        ("standalone", [A], [AI, LIT], ["nlp", "embedding", "statistics"], ["interactive", "comparison", "chart"]),
 "oto-utsushi":      ("lab", [B, A], [AI, LIT], ["speech-recognition", "deep-learning", "nlp"], ["interactive", "comparison"]),
 "sahai-dojo":       ("dojo", [P, A], [AI], ["rule-based", "search"], ["interactive", "simulator"]),
 "tenkyo-lab":       ("lab", [B, A], [AI, BIZ], ["nlp", "embedding", "statistics"], ["dashboard", "chart", "search"]),
 "kizami-ji":        ("standalone", [A], [AI, LIT], ["nlp", "search"], ["interactive", "chart"]),
 "kizami-kurabe":    ("standalone", [A], [AI, LIT], ["nlp"], ["comparison", "interactive"]),

 "shinka-lander": ("simulator", [S, A], [AI, GAME], ["optimization", "machine-learning", "simulation"], ["simulator", "animation", "chart"]),
 "toba-bandit":   ("standalone", [A, S], [AI], ["reinforcement-learning", "statistics", "simulation"], ["chart", "simulator"]),
 "murewake-lab":  ("lab", [A], [AI], ["clustering", "machine-learning"], ["animation", "interactive", "chart"]),
 "kobai-walk":    ("standalone", [A, S], [AI], ["optimization", "numerical", "machine-learning"], ["chart", "animation"]),
 "kyokai-lab":    ("lab", [A], [AI], ["deep-learning", "machine-learning"], ["interactive", "chart", "animation"]),
 "kyoka-grid":    ("standalone", [A, S], [AI], ["reinforcement-learning", "simulation"], ["heatmap", "animation", "interactive"]),

 "asterism-lens":   ("lens", [A, B], [SCI], ["deep-learning", "image-recognition"], ["interactive", "chart"]),
 "kansetsu-koyomi": ("standalone", [G], [WEA], ["statistics", "time-series", "statistical-test"], ["chart", "timeline", "dashboard"]),
 "korona-zuroku":   ("standalone", [G], [SCI, SOC], ["statistics", "time-series", "gis"], ["chart", "map", "dashboard"]),
 "manazashi-lab":   ("lab", [B, A], [AI], ["image-recognition", "deep-learning"], ["interactive", "chart", "comparison"]),
 "jocho-iro":       ("standalone", [H], [LIT], ["nlp", "statistics"], ["chart", "comparison", "dashboard"]),
 "kokoro-graph":    ("standalone", [H], [LIT], ["nlp", "statistics"], ["chart", "dashboard"]),
 "satei-kobo":      ("standalone", [A], [BIZ, AI], ["regression", "statistics", "machine-learning"], ["chart", "interactive", "comparison"]),
 "wakachi-ki":      ("standalone", [A], [AI, GAME], ["machine-learning", "statistics"], ["chart", "interactive"]),
 "tegaki-yomi":     ("standalone", [B, A], [AI], ["deep-learning", "image-recognition"], ["interactive"]),
 "kuzushi-yomi":    ("standalone", [B, A], [AI, HIS], ["deep-learning", "image-recognition"], ["interactive", "chart"]),
 "senzai-niwa":     ("standalone", [B, A], [AI], ["deep-learning"], ["interactive", "animation"]),
 "sumi-tsukuroi":   ("standalone", [B, A], [AI], ["deep-learning", "image-recognition"], ["interactive", "comparison"]),
 "gihitsu-kobo":    ("standalone", [B, A], [AI, HIS], ["deep-learning"], ["animation", "interactive", "timeline"]),
 "yonmoku-narabe":  ("dojo", [B, A, S], [AI, GAME], ["reinforcement-learning", "deep-learning", "search"], ["game", "chart"]),

 "toukei-atlas":       ("atlas-ai", [G], [SOC], ["gis", "statistics", "spatial-statistics"], ["map", "chart"]),
 "tsukiji-atlas":      ("atlas-ai", [G, H], [HIS, SOC], ["gis"], ["map", "timeline", "layers"]),
 "bunka-cluster-map":  ("standalone", [G], [SOC, ART], ["gis", "spatial-statistics", "statistics"], ["map", "heatmap", "layers"]),
 "sakaba-density-map": ("standalone", [G], [SOC], ["gis", "spatial-statistics", "statistics"], ["map", "heatmap"]),
 "yamato-gaze":        ("standalone", [G, H], [LIT, HIS], ["nlp", "gis", "statistics"], ["map", "comparison"]),

 "saitojo-zu":      ("standalone", [H], [LIT], ["graph-analysis", "statistics", "nlp"], ["network", "chart"]),
 "kyoen-zu":        ("standalone", [H], [LIT], ["graph-analysis", "nlp", "statistics"], ["network", "chart"]),
 "furigana-keiryo": ("standalone", [H], [LIT], ["nlp", "statistics", "statistical-test"], ["chart", "comparison"]),
 "fukuo-keiryo":    ("standalone", [H], [LIT, HIS], ["nlp", "statistics", "statistical-test"], ["chart"]),
 "onomato-atlas":   ("atlas-ai", [H], [LIT], ["nlp", "statistics", "embedding", "statistical-test"], ["chart", "comparison", "search"]),
 "ango-atlas":      ("atlas-ai", [H, B], [LIT], ["nlp", "embedding", "statistics"], ["search", "chart", "timeline"]),
 "neko-atlas":      ("atlas-ai", [H], [LIT], ["nlp", "statistics"], ["chart", "dashboard"]),
 "jikenbo-atlas":   ("atlas-ai", [H, G], [LIT], ["nlp", "gis", "graph-analysis"], ["map", "network", "timeline", "search"]),
 "kiko-atlas":      ("atlas-ai", [H, G], [LIT, HIS], ["nlp", "gis"], ["map", "timeline"]),
 "honyaku-atlas":   ("atlas-ai", [H], [LIT], ["rule-based"], ["dashboard", "comparison", "search"]),
 "honyaku-query":   ("standalone", [H, P], [LIT], ["nlp", "rule-based"], ["generator", "search"]),
 "aozora-sakuin":   ("standalone", [H], [LIT], ["nlp", "search"], ["search"]),
 "hanshichi-atlas": ("atlas-ai", [H, G], [LIT, HIS], ["nlp", "gis"], ["map", "timeline", "search"]),

 "makura-atlas":    ("atlas-ai", [H], [LIT], ["nlp", "statistics"], ["chart", "timeline"]),
 "hojoki-atlas":    ("atlas-ai", [H], [LIT], ["nlp", "statistics"], ["chart", "timeline"]),
 "tsurezure-atlas": ("atlas-ai", [H], [LIT], ["nlp", "statistics"], ["chart", "comparison"]),
 "saijiki-lens":    ("lens", [H], [LIT, WEA], ["nlp", "statistics"], ["chart", "timeline"]),
 "iro-koyomi":      ("standalone", [H], [LIT, ART], ["nlp", "statistics"], ["chart", "comparison"]),

 "kuriya-cho":  ("standalone", [H], [LIT, HIS], ["nlp", "statistics"], ["comparison", "search"]),
 "beagle-atlas": ("atlas-ai", [H, G], [LIT, SCI], ["nlp", "statistics", "gis", "statistical-test"], ["map", "timeline", "chart", "search"]),
 "mondo-atlas": ("atlas-ai", [H], [LIT, HIS], ["nlp", "statistics", "statistical-test"], ["chart", "search", "comparison"]),
 "omotegae-za": ("standalone", [H, S], [LIT, ART], ["graph-analysis", "optimization", "search"], ["network", "chart", "comparison"]),
 "uta-gaeshi":  ("standalone", [H], [LIT], ["nlp", "statistics"], ["search", "comparison"]),
 "ikari-uta":   ("standalone", [H], [LIT], ["nlp", "statistics"], ["search", "comparison"]),

 "disaster-drill":      ("simulator", [S, P], [DIS, GAME], ["simulation", "search", "rule-based"], ["simulator", "interactive", "game"]),
 "tarp-shelter-lab":    ("lab", [S, P], [DIS, GAME], ["simulation", "numerical"], ["simulator", "interactive", "game"]),
 "diamond-fuji-finder": ("planner", [S, G], [WEA, SCI], ["numerical", "simulation"], ["chart", "search"]),
 "yama-tenki-finder":   ("planner", [G, P], [WEA], ["rule-based", "time-series"], ["dashboard", "comparison"]),
 "pack-weight-sim":     ("simulator", [P], [BIZ], ["rule-based"], ["simulator", "dashboard"]),
 "bunka-hashigo":       ("planner", [P, G], [ART, SOC], ["optimization", "search", "gis"], ["map", "generator", "simulator"]),
 "hashigo-planner":     ("planner", [P, G], [SOC], ["optimization", "search", "gis"], ["map", "generator"]),
 "senbero-sim":         ("simulator", [P], [SOC, BIZ], ["rule-based"], ["simulator", "dashboard"]),
 "grutto-sim":          ("simulator", [P], [ART, BIZ], ["optimization", "search"], ["simulator", "comparison"]),

 "go-realtime-processing-simulator": ("simulator", [S], [AI], ["simulation", "numerical"], ["simulator", "chart", "interactive"]),
 "go-parallel-web-crawler":          ("standalone", [S, P], [AI], ["simulation", "search"], ["simulator", "dashboard", "chart"]),
 "mugen-tape":      ("standalone", [S], [AI, SCI], ["simulation", "search"], ["simulator", "interactive", "animation"]),
 "shinpuku-gekijo": ("standalone", [S], [SCI, AI], ["simulation", "numerical"], ["animation", "chart", "interactive"]),
 "kasane-kairo":    ("standalone", [S], [SCI, AI], ["simulation", "numerical"], ["interactive", "chart", "three-d"]),
 "transit-lens":    ("lens", [A, B], [SCI], ["deep-learning", "time-series"], ["interactive", "chart"]),
 "solar-system":    ("simulator", [S], [SCI], ["simulation", "numerical"], ["three-d", "animation", "interactive"]),
 "orbit-census":    ("standalone", [S, G], [SCI], ["simulation", "numerical", "gis"], ["three-d", "map", "animation"]),

 "zensen-goyomi": ("standalone", [G], [WEA, AGR], ["time-series", "statistics", "gis", "spatial-statistics"], ["map", "animation", "timeline", "chart"]),
 "na-no-eda":     ("standalone", [G], [SCI, WEA], ["statistics", "statistical-test", "graph-analysis"], ["network", "chart"]),

 "senoto-mori":   ("standalone", [P], [BIZ], ["rule-based"], ["dashboard", "interactive"]),
 "hoshihata":     ("standalone", [P, G], [BIZ, WEA], ["gis", "numerical", "rule-based"], ["map", "dashboard", "chart"]),
 "sugi-nami":     ("standalone", [P], [BIZ], ["rule-based"], ["dashboard"]),
 "kototoi-do":    ("standalone", [B, H], [LIT, AI], ["embedding", "nlp"], ["search"]),
 "mashaku":       ("standalone", [P, B], [BIZ, AI], ["embedding", "statistics", "rule-based"], ["dashboard", "comparison", "generator"]),
 "chikuma-seiki": ("standalone", [P, A], [BIZ], ["machine-learning", "optimization", "statistics"], ["dashboard", "chart", "simulator"]),

 "hanshoku-atlas": ("atlas-ai", [A, H], [ART, HIS], ["clustering", "image-recognition", "statistics"], ["chart", "comparison", "timeline"]),
 "kozu-lab":       ("lab", [A, H], [ART], ["statistics", "statistical-test", "image-recognition"], ["interactive", "chart", "comparison"]),

 "kitei-forge":   ("forge", [P], [BIZ], ["rule-based"], ["generator", "dashboard"]),
 "mamori-forge":  ("forge", [P], [BIZ], ["rule-based"], ["generator", "dashboard"]),
 "hacchu-forge":  ("forge", [P], [BIZ], ["rule-based"], ["generator", "dashboard"]),
 "hogo-forge":    ("forge", [P], [BIZ], ["rule-based"], ["generator", "dashboard"]),
 "soncho-forge":  ("forge", [P], [BIZ], ["rule-based"], ["generator", "dashboard"]),
 "zaitaku-forge": ("forge", [P], [BIZ], ["rule-based"], ["generator", "dashboard"]),
}

# V1 の data-src(何を測ったものか)から V2 の Data Source(category + 具体名)へ。
# 具体名まで書けるものは書く —— 「政府・自治体データ」だけでは何を見たか分からない。
SRC_MAP = {
    "青空文庫": ("aozora", "青空文庫"),
    "Project Gutenberg": ("gutenberg", "Project Gutenberg"),
    "Perseus": ("perseus", "Perseus Digital Library"),
    "Wikimedia": ("wikimedia", "Wikimedia / Wikidata"),
    "美術館オープンアクセス": ("museum-open-access", "メトロポリタン美術館 Open Access"),
    "報道・公式発表": ("press-release", "報道機関・企業・官公庁の公式発表"),
    "政府・自治体データ": ("gov-statistics", "政府・自治体の公開データ"),
    "気象・天文データ": ("jma", "気象庁"),
    "公開データセット": ("research-dataset", "公開研究データセット"),
    "地理院タイル": ("gsi", "国土地理院 タイル"),
}
# 上の既定を、アプリごとの実測で上書きする(同じ「政府・自治体データ」でも
# 統計表と法令とでは別物なので、カテゴリごと差し替える)。
SRC_OVERRIDE = {
 "midashi-sanmenkyo": [("press-release", "NHK・朝日新聞・毎日新聞のニュース見出し")],
 "hodo-hangenki":     [("press-release", "NHK ニュース RSS")],
 "koho-lens":         [("press-release", "IT サービス企業 11 社のプレスリリース")],
 "kiban-lens":        [("press-release", "AI 基盤モデル企業 23 社の公式ブログ")],
 "kasumigaseki-lens": [("press-release", "中央省庁等 15 機関の報道発表")],
 "hyakunin-lens":     [("press-release", "AI 研究者 100 名の公開フィード")],
 "hyakugaku-lens":    [("press-release", "学者 100 名の公開フィード"), ("research-dataset", "OpenAlex")],
 "tenkyo-lab":        [("laws-guidelines", "e-Gov 法令データ")],
 "kitei-forge":       [("laws-guidelines", "政府指針・ガイドライン 14 件")],
 "mamori-forge":      [("laws-guidelines", "IPA・経済産業省の指針と関係法令 10 件")],
 "hacchu-forge":      [("laws-guidelines", "フリーランス法・公正取引委員会規則")],
 "hogo-forge":        [("laws-guidelines", "個人情報保護法・施行令")],
 "soncho-forge":      [("laws-guidelines", "労働施策総合推進法ほか四本柱の指針・告示")],
 "zaitaku-forge":     [("laws-guidelines", "厚生労働省 テレワークガイドライン・労働基準法")],
 "toukei-atlas":      [("gov-statistics", "国勢調査ほか政府統計")],
 "tsukiji-atlas":     [("municipal-open-data", "東京都オープンデータ"), ("wikimedia", "Wikidata"), ("gsi", "国土地理院 タイル")],
 "bunka-cluster-map": [("municipal-open-data", "東京都の文化施設データ"), ("gsi", "国土地理院 タイル")],
 "sakaba-density-map": [("municipal-open-data", "食品営業許可データ(東京都)"), ("gsi", "国土地理院 タイル")],
 "na-no-eda":         [("gov-dataset", "環境省レッドリスト"), ("research-dataset", "系統樹データ")],
 "asterism-lens":     [("astronomy-catalog", "恒星カタログ")],
 "solar-system":      [("astronomy-catalog", "天文暦(軌道要素)")],
 "orbit-census":      [("astronomy-catalog", "CelesTrak 軌道要素(TLE)")],
 "diamond-fuji-finder": [("astronomy-catalog", "天文計算(太陽位置)")],
 "transit-lens":      [("astronomy-catalog", "NASA Kepler 光度曲線"), ("research-dataset", "NASA Exoplanet Archive")],
 "kansetsu-koyomi":   [("jma", "気象庁 初冠雪観測(1873–2026 寒候年)")],
 "zensen-goyomi":     [("jma", "気象庁 生物季節観測(1953 年以降)")],
 "yama-tenki-finder": [("jma", "気象庁 天気予報")],
 "senoto-mori":       [("jma", "気象庁 平年値")],
 "hoshihata":         [("jma", "気象庁 日別平年値"), ("gsi", "国土地理院 標高タイル")],
 "korona-zuroku":     [("research-dataset", "COVID-19 公開データ")],
 "satei-kobo":        [("research-dataset", "Ames Housing(JSE 一次配布)")],
 "wakachi-ki":        [("research-dataset", "titanic3(Vanderbilt 大学)")],
 "tegaki-yomi":       [("research-dataset", "MNIST")],
 "kuzushi-yomi":      [("research-dataset", "KMNIST(ROIS-DS 人文学オープンデータ共同利用センター)")],
 "senzai-niwa":       [("research-dataset", "MNIST / KMNIST")],
 "sumi-tsukuroi":     [("research-dataset", "KMNIST")],
 "gihitsu-kobo":      [("research-dataset", "KMNIST")],
 "manazashi-lab":     [("wikimedia", "Wikimedia Commons")],
 "tarp-shelter-lab":  [("wikimedia", "Wikimedia Commons"), ("other-open-data", "米陸軍サバイバル・マニュアル FM 3-05.70")],
 "bungo-type":        [("aozora", "青空文庫"), ("other-open-data", "小倉百人一首")],
 "hanshoku-atlas":    [("museum-open-access", "メトロポリタン美術館 Open Access(CC0)")],
 "kozu-lab":          [("museum-open-access", "メトロポリタン美術館 Open Access(CC0)")],
 "bunka-hashigo":     [("gsi", "国土地理院 タイル"), ("municipal-open-data", "文化施設の公開情報")],
 "hashigo-planner":   [("gsi", "国土地理院 タイル")],
 "mashaku":           [("press-release", "AI 導入に関する公開資料")],
 "yamato-gaze":       [("aozora", "青空文庫"), ("gsi", "国土地理院 タイル")],
}

# 言語の役割。実測で「その言語がこのリポジトリに実在する」ことは分かるが、
# 何のために使ったかは書かないと分からない(SPEC §11)。
LANG_ROLE_DEFAULT = {
    "Python": "データ処理・検証",
    "TypeScript": "フロントエンド",
    "JavaScript": "ブラウザ実装",
    "Go": "計算エンジン",
    "Rust": "計算コア",
    "R": "統計解析・作図",
    "Ruby": "テキスト処理",
    "HTML": "画面",
    "CSS": "表現",
}
LANG_ROLE = {
 ("midashi-sanmenkyo", "R"): "見出しの癖の統計量算出と作図",
 ("hodo-hangenki", "R"): "生存時間解析(survival)と作図",
 ("fukuo-keiryo", "R"): "敬体率の区間推定と作図",
 ("toukei-atlas", "R"): "sf + ggplot2 による主題図の生成",
 ("yomikiri-ban", "Rust"): "終盤完全読み切りの探索エンジン(WASM)",
 ("nanpure-forge", "Rust"): "一意解を保証する生成器とソルバー(WASM)",
 ("aozora-sakuin", "Rust"): "FM-index 全文索引の構築と検索(WASM)",
 ("hanshoku-atlas", "Rust"): "k-means による版色復元(WASM)",
 ("kozu-lab", "Rust"): "構図スコアの走査(WASM)",
 ("go-particle-lab", "Go"): "粒子物理エンジン(WASM)",
 ("go-realtime-processing-simulator", "Go"): "goroutine / channel の並行処理エンジン(WASM)",
 ("go-parallel-web-crawler", "Go"): "goroutine / Worker Pool による並行クローラ",
 ("furigana-keiryo", "Ruby"): "青空文庫のルビ解析",
 ("karakuri-hako", "CSS"): "JavaScript を使わない仕掛けの実装",
 ("karakuri-hako", "HTML"): "状態を持つ仕掛けの構造",
}
# モデル学習に使った Python は役割を書き分ける
ML_TRAIN = {"asterism-lens", "transit-lens", "senzai-niwa", "sumi-tsukuroi", "gihitsu-kobo",
            "kuzushi-yomi", "tegaki-yomi", "yonmoku-narabe", "ango-atlas", "imi-chizu",
            "tsugi-no-hito-ji", "token-hakari"}

# 自前で学習した重みを配っているもの(実測で weights が立ったもののうち、
# 学習したのが自分であるものだけ。既製の埋め込みを配るだけのものは含めない)。
TRAINED_MODEL = {"tsugi-no-hito-ji", "imi-chizu", "kizami-ji", "asterism-lens",
                 "kuzushi-yomi", "senzai-niwa", "sumi-tsukuroi", "gihitsu-kobo",
                 "yonmoku-narabe", "transit-lens", "tegaki-yomi", "token-hakari"}

# cross-validated は二つの実測経路のどちらかで立てる。散文で「二実装」と
# 書いてあるだけでは足りない —— 検査が実際にそれを守っていることを見る。
#   (1) テスト/ゲートのファイル本体に「二実装・独立実装・二経路…」が出てくる
#   (2) V1 の data-lib に「照合:」役の依存がある(オラクル専用の別実装)
# README や SPEC の散文だけを見ると 50 本当たるが、そのうち 10 本は
# 検査を持っていなかった。

# Featured Works(SPEC §17)。アクセス数順ではなく、技術的な幅が一目で分かる 6 本。
# ブラウザ内推論 / 計量人文学 / 科学 AI / 公開データと地図(R) / WASM 探索 / 実務。
FEATURED = {
 "manazashi-lab": 1,   # Browser AI —— 推論を端末で完結させ、モデルを解剖する
 "mondo-atlas": 2,     # Computational Humanities —— Perseus 全 36 篇
 "transit-lens": 3,    # Scientific AI —— NASA Kepler の 1D CNN
 "toukei-atlas": 4,    # Public Data & Geo —— R(sf + ggplot2)の主題図
 "yomikiri-ban": 5,    # Simulation —— Rust + WASM の完全読み切り
 "kitei-forge": 6,     # Practical —— 典拠つき規程ジェネレータ
}

# SPEC §44 の「今後企画するアプリ群」。status=planned で登録しておき、
# 既定では出さない(「企画中も見る」を押したときだけ出る)。
# 書けるのは §44 が決めていること —— Series と Domain と Track だけ。
# 手法や体験は作ってから測って書く(まだ測っていないものを書かない)。
PLANNED = [
 ("station-flow-atlas-ai", "Japan Station Flow Atlas AI", [G], [SOC], "全国の鉄道駅の乗降客数推移を地図と時系列で可視化する。"),
 ("food-self-sufficiency-atlas-ai", "Food Self-Sufficiency Atlas AI", [G], [AGR], "作物別自給率を都道府県・時系列で可視化する。"),
 ("forestry-atlas-ai", "Forestry Atlas AI", [G], [AGR], "森林資源・林業の統計を地図で読む。"),
 ("disaster-base-atlas-ai", "Disaster Base Atlas AI", [G], [DIS], "防災拠点の配置と到達圏を地図で読む。"),
 ("river-fishery-rights-atlas-ai", "River Fishery Rights Atlas AI", [G], [AGR], "内水面漁業権の区域を地図で読む。"),
 ("ja-atlas-ai", "JA Atlas AI", [G], [AGR], "農業協同組合の分布と再編を地図で読む。"),
 ("fishing-port-atlas-ai", "Fishing Port Atlas AI", [G], [AGR], "漁港の規模と水揚げを地図で読む。"),
 ("weather-atmosphere-atlas-ai", "Japan Weather & Atmosphere Atlas AI", [G], [WEA], "気象と大気の観測を地図と時系列で読む。"),
 ("long-trail-atlas-ai", "Japan Long Trail Atlas AI", [G], [WEA, SOC], "ロングトレイルの経路と標高・気象を地図で読む。"),
 ("torahiko-geoscience-atlas-ai", "Torahiko GeoScience Atlas AI", [H, G], [LIT, WEA], "寺田寅彦の随筆に現れる地球科学の記述を地図と主題で読む。"),
 ("yanagita-folklore-atlas-ai", "Yanagita Folklore Atlas AI", [H, G], [LIT], "柳田國男の民俗資料に現れる土地と伝承を地図で読む。"),
 ("mystery-weird-atlas-ai", "Mystery & Weird Literature Atlas AI", [H, G], [LIT], "探偵小説・怪奇小説の舞台と主題を地図で読む。"),
 ("matatabi-atlas-ai", "Matatabi Atlas AI", [H, G], [LIT], "股旅物の道行きを地図で読む。"),
 ("aozora-flora-atlas-ai", "Aozora Flora Atlas AI", [H, G], [LIT, WEA], "青空文庫に現れる植物の名を季節と土地に結ぶ。"),
 ("world-folktale-atlas-ai", "World Folktale Atlas AI", [H, G], [LIT], "世界の民話の型と分布を地図で読む。"),
 ("kofun-atlas-ai", "Kofun Atlas AI", [G, H], [HIS], "古墳の分布と規模を地図で読む。"),
 ("jinja-origin-atlas-ai", "Jinja Origin Atlas AI", [G, H], [HIS], "神社の由緒と祭神の分布を地図で読む。"),
 ("archaeostone-atlas-ai", "ArchaeoStone Atlas AI", [G, H], [HIS], "石造遺物の分布と年代を地図で読む。"),
]

# 名前が示す以上の別名(検索で当てたい語)
EXTRA_ALIASES = {
 "kokorograph": ["kokoro-graph"],
 "app-menu": ["アプリメニュー"],
}


def read_json(name):
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def strip_tags(s):
    """V1 のカード本文は HTML だった(<b> で目玉を強調していた)。V2 のカードは
    textContent で描くので、タグを残すと画面に <b> がそのまま出る。実体参照も
    ここで戻す(tarp-shelter-lab の "TARP &amp; SHELTER LAB")。"""
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def main():
    cards = read_json("_cards_raw.json")
    measured = read_json("_measured.json")
    repos = {r["name"]: r for r in read_json("_repos.json")}
    tax = json.loads((ROOT / "data" / "taxonomy.json").read_text(encoding="utf-8"))
    known = {k: {e["id"] for e in v} for k, v in tax.items() if isinstance(v, list)}

    apps = []
    problems = []
    for c in cards:
        # リポジトリ名は data-repo があればそれ、無ければ URL のサブドメイン。
        # transit-lens だけは素の名前を他者が取っていて Vercel 側が別名なので直す。
        sub = c["repo"] or re.sub(r"^https?://", "", c["href"]).split(".")[0]
        app_id = {"transit-lens-one": "transit-lens"}.get(sub, sub)
        mv = measured[app_id]
        name = strip_tags(c["name"])
        slug, _, jp = name.partition("—")
        slug = slug.strip()
        jp = jp.strip()
        title = jp or slug
        aliases = sorted({slug, jp, app_id} - {title, ""})
        aliases += EXTRA_ALIASES.get(app_id, [])

        if app_id not in FACETS:
            problems.append(f"FACETS に {app_id} がない")
            continue
        series, tracks, domains, methods, experience = FACETS[app_id]

        # ---- languages(実測 + 役割)
        langs = mv["langs"]
        total = sum(langs.values()) or 1
        # しきい値は行数の絶対値だけで決める。「全体に占める割合」も条件にすると、
        # データを 1 枚の巨大な HTML に埋めている作品(kansetsu-koyomi は 58,142 行)
        # で分母が膨らみ、2,467 行の TypeScript が 3.9% になって落ちる。
        rare = {"Go", "Rust", "R", "Ruby", "SQL"}
        picked = [k for k, n in langs.items() if n >= (100 if k in rare else 300)]
        # HTML / CSS は「それが主役のとき」だけ載せる。全部に付けると意味が消える。
        # karakuri-hako は JavaScript を 1 行も出荷しない造りで、仕掛けは CSS が持つ。
        if app_id == "karakuri-hako":
            picked = ["HTML", "CSS"]
        else:
            picked = [k for k in picked if k not in ("HTML", "CSS")]
        order = {"Python": 0, "TypeScript": 1, "JavaScript": 2, "Go": 3, "Rust": 4,
                 "R": 5, "Ruby": 6, "HTML": 7, "CSS": 8}
        picked.sort(key=lambda k: order.get(k, 9))
        # 役割は「どこに置かれているか」で決める。scripts/ と tests/ にしか無い
        # JavaScript を「ブラウザ実装」と書くと嘘になる —— mondo-atlas の JS 453 行は
        # 全部 build_stamp と etl の点検で、ブラウザには 1 行も出て行かない。
        tool_dirs = {"scripts", "tools", "tests", "test", "etl", "bin", "notebooks",
                     "eval", "analysis", ".github"}
        bydir = mv.get("bydir", {})
        languages = []
        for k in picked:
            places = bydir.get(k, {})
            tot_k = sum(places.values()) or 1
            tool_share = sum(n for d, n in places.items() if d in tool_dirs) / tot_k
            role = LANG_ROLE.get((app_id, k))
            if role is None and k == "Python":
                role = "モデル学習・データ処理" if app_id in ML_TRAIN else LANG_ROLE_DEFAULT[k]
            if role is None and k in ("JavaScript", "TypeScript") and tool_share >= 0.6:
                role = "検査・生成スクリプト"
            if role is None:
                role = LANG_ROLE_DEFAULT.get(k, "")
            languages.append({"name": k, "role": role, "loc": langs[k]})

        # ---- data sources
        srcs = []
        if app_id in SRC_OVERRIDE:
            srcs = [{"category": cat, "name": nm} for cat, nm in SRC_OVERRIDE[app_id]]
        else:
            for s in [x for x in c["src"].split(",") if x]:
                cat, nm = SRC_MAP[s]
                srcs.append({"category": cat, "name": nm})

        # ---- libraries(V1 の data-lib「役割:名前」をそのまま)
        rolemap = {"出荷": "ship", "生成": "build", "照合": "oracle"}
        libs = []
        for entry in [x for x in c["lib"].split(",") if x]:
            r, _, nm = entry.partition(":")
            libs.append({"name": nm, "role": rolemap.get(r, r)})

        # ---- architecture(実測)
        flags = set(mv["flags"])
        tags = set(x for x in c["tags"].split(",") if x)
        arch = ["static-site"] if "server-api" not in flags else ["serverless"]
        if "server-api" not in flags:
            arch += ["no-api"]
        if "wasm" in flags:
            arch.append("webassembly")
        if "web-worker" in flags:
            arch.append("web-worker")
        if "ci" in flags:
            arch.append("github-actions")
        if "自動更新" in tags or "cron" in flags:
            arch.append("auto-update")
        if "ブラウザ内推論" in tags:
            arch.append("browser-inference")
        if "server-api" not in flags and not mv.get("secret_envs"):
            arch.append("client-only")
        if "ブラウザ内推論" in tags or app_id in ("mashaku", "kototoi-do", "sahai-dojo"):
            arch.append("local-processing")
        if "ci-test" in flags:
            arch.append("reproducible-build")
        if not mv.get("deps"):
            arch.append("zero-dependency")
        arch = sorted(set(arch), key=lambda x: [e["id"] for e in tax["architecture"]].index(x))

        # ---- badges(条件は taxonomy.json に書いた通り)
        badges = []
        if mv.get("testfiles"):
            badges.append("verified")
        if "server-api" not in flags:
            badges.append("static-deploy")
        if not mv.get("secret_envs"):
            badges += ["client-only", "no-api-key"]
        if "ブラウザ内推論" in tags:
            badges.append("browser-inference")
        if srcs:
            badges.append("open-data")
        if any(s["category"] in ("aozora", "gutenberg", "perseus", "museum-open-access")
               for s in srcs):
            badges.append("public-domain")
        if app_id in TRAINED_MODEL:
            badges.append("trained-model")
        if "ci-test" in flags:
            badges.append("reproducible")
        if mv.get("xval_test_hits") or any(l["role"] == "oracle" for l in libs):
            badges.append("cross-validated")
        badges = sorted(set(badges), key=lambda x: [e["id"] for e in tax["badges"]].index(x))

        # ---- meta(日付・ライセンス・スマホ)
        first = last = ""
        lic = ""
        mobile = False
        for s in c["meta"]:
            s = strip_tags(s)
            if s.startswith("初回デプロイ"):
                first = s.split()[-1]
            elif s.startswith("最終更新"):
                last = s.split()[-1]
            elif "スマホ" in s:
                mobile = True
            elif s.strip():
                lic = s.strip()

        gh = repos.get(app_id)
        github_url = gh["url"] if gh and gh["visibility"] == "PUBLIC" else ""

        app = {
            "id": app_id,
            "title": title,
            "shortTitle": slug,
            "aliases": aliases,
            "icon": c["icon"],
            "series": series,
            "tracks": tracks,
            "domains": domains,
            "methods": methods,
            "experience": experience,
            "languages": languages,
            "runtimes": sorted(
                (["WebAssembly"] if "wasm" in flags else [])
                + (["GitHub Actions"] if "ci" in flags else [])
                + ["Browser"]),
            "architecture": arch,
            "dataSources": srcs,
            "libraries": libs,
            "summary": strip_tags(c["desc"]),
            "description": "",
            "keywords": [],
            "badges": badges,
            "appUrl": c["href"],
            "githubUrl": github_url,
            "license": lic,
            "mobile": mobile,
            "featured": app_id in FEATURED,
            "featuredOrder": FEATURED.get(app_id),
            "firstDeployedAt": first,
            "updatedAt": last,
            "status": "published",
        }
        for key, field in (("tracks", "tracks"), ("domains", "domains"),
                           ("methods", "methods"), ("experience", "experience"),
                           ("architecture", "architecture"), ("badges", "badges")):
            for v in app[field]:
                if v not in known[key]:
                    problems.append(f"{app_id}: 未定義の {field} = {v}")
        for s in srcs:
            if s["category"] not in known["dataSources"]:
                problems.append(f"{app_id}: 未定義の dataSource = {s['category']}")
        apps.append(app)

    for pid, ptitle, ptracks, pdomains, psummary in PLANNED:
        apps.append({
            "id": pid, "title": ptitle, "shortTitle": ptitle, "aliases": [],
            "icon": "🗺️", "series": "atlas-ai", "tracks": ptracks,
            "domains": pdomains, "methods": [], "experience": ["map"],
            "languages": [], "runtimes": [], "architecture": [],
            "dataSources": [], "libraries": [], "summary": psummary,
            "description": "", "keywords": [], "badges": [],
            "appUrl": "", "githubUrl": "", "license": "", "mobile": False,
            "featured": False, "featuredOrder": None,
            "firstDeployedAt": "", "updatedAt": "", "status": "planned",
        })

    out = {"$comment": "アプリ情報の唯一の出どころ(SPEC §31)。追加は 1 レコードの追記で完結する。",
           "apps": apps}
    (ROOT / "data" / "apps.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"apps.json: {len(apps)} records")
    if problems:
        print("PROBLEMS:")
        for p in problems:
            print("  " + p)
        sys.exit(1)


if __name__ == "__main__":
    main()
