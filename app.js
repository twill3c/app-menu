/* app-menu Portfolio Edition V2.0
 *
 * 画面に出るものはすべて data/*.json から描く(SPEC §31)。HTML にはカテゴリ名も
 * アプリ名も書かない —— アプリの追加は apps.json への 1 レコード追記で完結する。
 *
 * 絞り込みの決まり(SPEC §23):同じ Facet の中は OR、違う Facet どうしは AND。
 * チップの件数は「いま押したら何件になるか」で、0 件は押せない。ただし選択中の
 * ものと各軸の「指定なし」は必ず残す —— 全部死ぬと絞り込みから出られなくなる。
 */
'use strict';

// ---------------------------------------------------------------- 正規化
// SPEC §19.2。NFKC → 小文字 → 前後空白 → 連続空白 → 記号の一部。
// 全角/半角と大文字/小文字の違いで空振りしないためのもの。
function normalize(s) {
  return String(s == null ? '' : s)
    .normalize('NFKC')
    .toLowerCase()
    .replace(/[‐‑‒–—―ー−]/g, '-')   // 各種ダッシュと長音記号を素の - に寄せる
    .replace(/[・･]/g, ' ')
    .replace(/[「」『』()（）\[\]【】、,]/g, ' ')
    .trim()
    .replace(/\s+/g, ' ');
}

// 短い ASCII 語(r / go / ts など)は語の境界で当てる。部分一致にすると
// 「r」がほぼ全件に当たって軸として使えなくなる。
function fieldHas(text, needle) {
  if (/^[a-z0-9+#.]{1,3}$/.test(needle)) {
    return new RegExp('(^|[^a-z0-9])' + needle.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '([^a-z0-9]|$)').test(text);
  }
  return text.indexOf(needle) !== -1;
}

// ---------------------------------------------------------------- 状態
const FACETS = ['tracks', 'domains', 'methods', 'experience', 'languages',
                'architecture', 'dataSources', 'series'];
// URL のキー(短くする)と Facet の対応(SPEC §25)
const URLKEY = {
  tracks: 'track', domains: 'domain', methods: 'method', experience: 'exp',
  languages: 'lang', architecture: 'arch', dataSources: 'src', series: 'series',
};
const FACET_UI = [
  { key: 'domains', label: '分野', tax: 'domains' },
  { key: 'methods', label: '手法', tax: 'methods' },
  { key: 'experience', label: '表示・体験', tax: 'experience' },
  { key: 'languages', label: '言語', tax: 'languages' },
  { key: 'architecture', label: '実装', tax: 'architecture' },
  { key: 'dataSources', label: '出典', tax: 'dataSources' },
  { key: 'series', label: 'シリーズ', tax: 'series' },
];

const state = {
  q: '',
  showPlanned: false,
  sel: { tracks: [], domains: [], methods: [], experience: [], languages: [],
         architecture: [], dataSources: [], series: [] },
};

let TAX = null, APPS = [], SYN = new Map(), LABEL = {}, ORDER = {};
// 実際に 1 件以上のアプリが使っている値(死んだチップを出さないため)
const USED = {};

// ---------------------------------------------------------------- 読み込み
async function load() {
  const [tax, apps, syn] = await Promise.all([
    fetch('data/taxonomy.json').then(r => r.json()),
    fetch('data/apps.json').then(r => r.json()),
    fetch('data/search-synonyms.json').then(r => r.json()),
  ]);
  TAX = tax;
  APPS = apps.apps;

  // 表示名と並び順は taxonomy.json が唯一の出どころ(SPEC §34)
  for (const key of Object.keys(TAX)) {
    if (!Array.isArray(TAX[key])) continue;
    LABEL[key] = {}; ORDER[key] = {};
    TAX[key].forEach((e, i) => { LABEL[key][e.id] = e; ORDER[key][e.id] = e.order != null ? e.order : i; });
  }
  for (const group of syn.groups) {
    const vs = group.map(normalize);
    for (const v of vs) {
      if (!SYN.has(v)) SYN.set(v, new Set());
      vs.forEach(x => SYN.get(v).add(x));
    }
  }
  APPS.forEach(buildIndex);
  for (const key of FACETS) {
    USED[key] = new Set();
    for (const a of APPS) for (const v of a._facet[key]) USED[key].add(v);
  }
}

// 検索対象のフィールドと重み(SPEC §21)
const WEIGHT = { title: 10, aliases: 8, keywords: 8, summary: 6, tracks: 5,
                 domains: 5, methods: 5, experience: 4, languages: 4, series: 4,
                 architecture: 4, dataSources: 3, libraries: 3, description: 2 };
// 同義語で当たった分は、その語そのもので当たった分より軽くする。
// 「深層学習」は辞書の上では「ai」とも繋がっているので、割り引かないと
// 本当に深層学習を使っている作品が AI 全般に埋もれる。
const SYN_DISCOUNT = 0.6;

function labelsOf(taxKey, ids) {
  return ids.map(id => {
    const e = LABEL[taxKey] && LABEL[taxKey][id];
    return e ? e.label + ' ' + id : id;
  });
}

// 1 レコードぶんの索引。ラベルと id の両方を入れるので「深層学習」でも
// 「deep-learning」でも当たる。
function buildIndex(a) {
  a._langs = a.languages.map(l => l.name);
  a._srcs = a.dataSources.map(s => s.category);
  const f = {
    title: [a.title, a.shortTitle],
    aliases: a.aliases,
    keywords: a.keywords || [],
    summary: [a.summary],
    description: [a.description || ''],
    tracks: labelsOf('tracks', a.tracks),
    domains: labelsOf('domains', a.domains),
    methods: labelsOf('methods', a.methods),
    experience: labelsOf('experience', a.experience),
    languages: a._langs.concat(a.languages.map(l => l.role)),
    series: labelsOf('series', [a.series]),
    architecture: labelsOf('architecture', a.architecture),
    dataSources: labelsOf('dataSources', a._srcs).concat(a.dataSources.map(s => s.name)),
    libraries: a.libraries.map(l => l.name),
  };
  a._fields = {};
  for (const k of Object.keys(f)) a._fields[k] = normalize(f[k].join(' '));
  a._facet = {
    tracks: a.tracks, domains: a.domains, methods: a.methods,
    experience: a.experience, languages: a._langs, architecture: a.architecture,
    dataSources: a._srcs, series: [a.series],
  };
}

// ---------------------------------------------------------------- 検索
// 「deep learning」のように空白を含む同義語は、先に語へ割ると永久に当たらない。
// 入力全体が辞書の見出しなら、それを 1 語として扱う。
function tokenize(q) {
  const whole = normalize(q);
  if (whole && SYN.has(whole)) return [whole];
  return whole.split(' ').filter(Boolean);
}
function variantsOf(token) {
  const s = SYN.get(token);
  return s ? Array.from(s).filter(v => v !== token) : [];
}
// すべての語がどこかのフィールドに在ることを求める(AND・SPEC §19.3)。
// スコアは語ごとに当たったフィールドの最大重みを取り、語で合算する(§21)。
function scoreOf(app, tokens) {
  let total = 0;
  for (const t of tokens) {
    const vs = variantsOf(t);
    let exact = 0, syn = 0;
    for (const k of Object.keys(WEIGHT)) {
      const text = app._fields[k];
      if (!text) continue;
      if (fieldHas(text, t)) { if (WEIGHT[k] > exact) exact = WEIGHT[k]; }
      else {
        for (const v of vs) {
          if (fieldHas(text, v)) { if (WEIGHT[k] > syn) syn = WEIGHT[k]; break; }
        }
      }
    }
    const best = exact > 0 ? exact : syn * SYN_DISCOUNT;
    if (best === 0) return -1;   // 一語でも当たらなければ候補から外す
    total += best;
  }
  return total;
}

// ---------------------------------------------------------------- 絞り込み
function passFacets(app, sel, skip) {
  for (const key of FACETS) {
    if (key === skip) continue;
    const want = sel[key];
    if (!want || want.length === 0) continue;
    const have = app._facet[key];
    if (!want.some(v => have.indexOf(v) !== -1)) return false;   // 同じ軸は OR
  }
  return true;                                                    // 違う軸は AND
}

function baseList() {
  return APPS.filter(a => state.showPlanned || a.status === 'published');
}

function query(sel, skip, tokens) {
  const out = [];
  for (const a of baseList()) {
    if (!passFacets(a, sel, skip)) continue;
    if (tokens.length) {
      const s = scoreOf(a, tokens);
      if (s < 0) continue;
      a._score = s;
    } else {
      a._score = 0;
    }
    out.push(a);
  }
  return out;
}

// 同点の並び:Featured → 最終更新日 → タイトル(SPEC §21)
function rank(list) {
  return list.slice().sort((x, y) =>
    (y._score - x._score) ||
    ((x.featuredOrder || 99) - (y.featuredOrder || 99)) ||
    String(y.updatedAt || '').localeCompare(String(x.updatedAt || '')) ||
    x.title.localeCompare(y.title, 'ja'));
}

// ---------------------------------------------------------------- 描画部品
function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text != null) e.textContent = text;
  return e;
}

function chip(label, count, pressed, disabled, onClick, title) {
  const b = el('button', 'chip');
  b.type = 'button';
  b.append(document.createTextNode(label));
  if (count != null) b.append(el('span', 'n', String(count)));
  b.setAttribute('aria-pressed', pressed ? 'true' : 'false');
  b.disabled = !!disabled;
  if (title) b.title = title;
  b.addEventListener('click', onClick);
  return b;
}

function specRow(parent, key, value) {
  if (!value) return;
  const d = el('div');
  d.append(el('span', 'k', key), el('span', 'v', value));
  parent.append(d);
}

const ROLE_ICON = { ship: '🚚', build: '🏭', oracle: '⚖️' };

function badgeRank(id) {
  // 珍しいバッジほど情報が多いので先に出す。件数は毎回数え直す。
  return BADGE_COUNT[id] || 0;
}
let BADGE_COUNT = {};

function renderCard(a, big) {
  const c = el('article', 'card' + (a.status !== 'published' ? ' is-planned' : ''));

  const tops = el('div', 'tops');
  const ser = LABEL.series[a.series];
  if (ser) tops.append(el('span', 'tag series', ser.label));
  for (const d of a.domains.slice(0, 2)) {
    const e = LABEL.domains[d];
    if (e) tops.append(el('span', 'tag domain', (e.icon ? e.icon + ' ' : '') + e.label));
  }
  if (a.status !== 'published') {
    const st = LABEL.status[a.status];
    tops.append(el('span', 'tag status', st ? st.label : a.status));
  }
  c.append(tops);

  const h = el('h3');
  if (a.icon) h.append(el('span', 'ic', a.icon));
  if (a.appUrl) {
    const link = el('a', null, a.title);
    link.href = a.appUrl; link.target = '_blank'; link.rel = 'noopener';
    h.append(link);
  } else {
    h.append(document.createTextNode(a.title));
  }
  c.append(h);
  if (a.shortTitle && a.shortTitle !== a.title) c.append(el('div', 'repo', a.shortTitle));
  c.append(el('div', 'desc', a.summary));

  const specs = el('div', 'specs');
  const way = a.methods.map(m => (LABEL.methods[m] || {}).label || m)
    .concat(a.experience.map(x => (LABEL.experience[x] || {}).label || x));
  specRow(specs, '手法', way.join(' · '));
  if (a.languages.length) {
    const names = a.languages.map(l => l.name).join(' · ');
    // 役割は「何のために使ったか」。名前だけ貼ると嘘になる(SPEC §11)ので、
    // その作品でいちばん物を言う言語の役割を 1 行だけ添える。
    const rare = a.languages.find(l => ['Go', 'Rust', 'R', 'Ruby'].indexOf(l.name) !== -1)
              || a.languages[0];
    const v = el('span', 'v');
    v.append(document.createTextNode(names));
    if (rare && rare.role) v.append(el('span', 'role', ' — ' + rare.name + ' は' + rare.role));
    const d = el('div'); d.append(el('span', 'k', '言語'), v); specs.append(d);
  }
  if (a.libraries.length) {
    specRow(specs, 'ライブラリ',
      a.libraries.map(l => (ROLE_ICON[l.role] || '') + ' ' + l.name).join(' · '));
  }
  if (a.dataSources.length) specRow(specs, '出典', a.dataSources.map(s => s.name).join(' · '));
  c.append(specs);

  if (a.badges.length) {
    const bs = el('div', 'badges');
    const sorted = a.badges.slice().sort((x, y) => badgeRank(x) - badgeRank(y));
    // 珍しい順に 4 つ(Featured は 6 つ)まで。全部出すと 8 個並んで
    // 「検証済み・静的デプロイ・API キー不要」のような全件に付くものが場所を取る。
    const shown = sorted.slice(0, big ? 6 : 4);
    for (const id of shown) {
      const e = LABEL.badges[id];
      if (!e) continue;
      const b = el('span', 'badge', (e.icon ? e.icon + ' ' : '') + e.label);
      b.title = e.condition || '';
      bs.append(b);
    }
    if (sorted.length > shown.length) {
      const rest = sorted.slice(shown.length)
        .map(id => (LABEL.badges[id] || {}).label || id);
      const more = el('span', 'badge more', '+' + rest.length);
      more.title = rest.join(' / ');
      bs.append(more);
    }
    c.append(bs);
  }

  const act = el('div', 'actions');
  if (a.appUrl) {
    const b = el('a', 'btn primary', 'アプリを見る');
    b.href = a.appUrl; b.target = '_blank'; b.rel = 'noopener';
    act.append(b);
  }
  if (a.githubUrl) {
    const g = el('a', 'btn', 'GitHub');
    g.href = a.githubUrl; g.target = '_blank'; g.rel = 'noopener';
    act.append(g);
  }
  if (act.childNodes.length) c.append(act);

  const meta = el('div', 'meta');
  if (a.firstDeployedAt) meta.append(el('span', null, '初回 ' + a.firstDeployedAt));
  if (a.updatedAt) meta.append(el('span', null, '更新 ' + a.updatedAt));
  if (a.license) meta.append(el('span', null, a.license));
  if (a.mobile) meta.append(el('span', null, '📱 スマホ対応'));
  if (meta.childNodes.length) c.append(meta);
  return c;
}

// ---------------------------------------------------------------- 画面
function renderKpi(published) {
  const kpi = document.getElementById('kpi');
  kpi.textContent = '';
  const has = (a, key, v) => a._facet[key].indexOf(v) !== -1;
  const rows = [
    ['公開アプリ', published.length],
    ['AI / ML', published.filter(a => has(a, 'tracks', 'ai-insight')).length],
    ['Atlas AI', published.filter(a => a.series === 'atlas-ai').length],
    ['Browser AI', published.filter(a => has(a, 'tracks', 'browser-ai')).length],
    ['Open Data', published.filter(a => a.badges.indexOf('open-data') !== -1).length],
    ['言語', new Set(published.flatMap(a => a._langs)).size],
  ];
  for (const [k, v] of rows) {
    const d = el('div');
    d.append(el('b', null, String(v)), el('span', null, k));
    kpi.append(d);
  }
  document.getElementById('kpi-total').textContent = published.length;
}

function renderTracks() {
  const wrap = document.getElementById('tracks');
  wrap.textContent = '';
  const tokens = tokenize(state.q);
  for (const t of TAX.tracks) {
    const n = query(withFacet('tracks', [t.id]), null, tokens).length;
    const on = state.sel.tracks.indexOf(t.id) !== -1;
    const b = el('button', 'track');
    b.type = 'button';
    b.setAttribute('aria-pressed', on ? 'true' : 'false');
    b.disabled = n === 0 && !on;
    const title = el('div', 't');
    title.append(el('span', 'ic', t.icon || ''), document.createTextNode(t.label),
                 el('span', 'n', '  ' + n));
    b.append(title, el('div', 'd', t.note || ''));
    b.addEventListener('click', () => { toggle('tracks', t.id); });
    wrap.append(b);
  }
}

function withFacet(key, values) {
  const s = {};
  for (const k of FACETS) s[k] = k === key ? values : state.sel[k];
  return s;
}

// よく使う入口(SPEC §37)。値は Facet の指定そのものなので、押すと
// 検索窓ではなく絞り込みが動く。
const QUICK = [
  ['series', 'atlas-ai'], ['tracks', 'browser-ai'], ['dataSources', 'aozora'],
  ['methods', 'deep-learning'], ['methods', 'gis'], ['architecture', 'webassembly'],
  ['languages', 'Go'], ['languages', 'Rust'], ['languages', 'R'],
];

function renderQuick() {
  const wrap = document.getElementById('quick');
  wrap.textContent = '';
  wrap.append(el('span', 'lead', 'よく使う入口'));
  const tokens = tokenize(state.q);
  for (const [key, id] of QUICK) {
    const taxKey = key === 'languages' ? 'languages' : key;
    const e = (LABEL[taxKey] || {})[id];
    const on = state.sel[key].indexOf(id) !== -1;
    const n = query(withFacet(key, on ? state.sel[key] : [id]), null, tokens).length;
    wrap.append(chip(e ? e.label : id, n, on, n === 0 && !on,
      () => toggle(key, id)));
  }
}

function renderFacets() {
  const wrap = document.getElementById('facets');
  wrap.textContent = '';
  const tokens = tokenize(state.q);
  const box = el('div', 'axis');
  for (const f of FACET_UI) {
    const row = el('div', 'row');
    row.append(el('span', 'lead', f.label));
    const sel = state.sel[f.key];
    // 「指定なし」= この軸を外したときの件数。いまの表示枚数ではない。
    row.append(chip('指定なし', query(withFacet(f.key, []), null, tokens).length,
      sel.length === 0, false, () => { state.sel[f.key] = []; apply(true); },
      'この軸の絞り込みを外す'));
    for (const e of TAX[f.tax]) {
      // どのアプリも使っていない語はチップにしない。ここに出すと、押しても
      // 何も起きない「死んだチップ」が並ぶ(語彙は taxonomy に残しておき、
      // 未使用であることは validate_apps.py が警告で見せる)。
      if (!USED[f.key].has(e.id)) continue;
      const on = sel.indexOf(e.id) !== -1;
      // 同じ軸の中は OR なので、押した先の件数は「その値だけを選んだとき」で数える。
      const n = query(withFacet(f.key, [e.id]), null, tokens).length;
      row.append(chip((e.icon ? e.icon + ' ' : '') + e.label, n, on, n === 0 && !on,
        () => toggle(f.key, e.id), e.note || ''));
    }
    box.append(row);
  }
  wrap.append(box);
}

function renderSelected() {
  const wrap = document.getElementById('selected');
  wrap.textContent = '';
  let any = state.q !== '';
  for (const key of FACETS) {
    for (const id of state.sel[key]) {
      any = true;
      const taxKey = key;
      const e = (LABEL[taxKey] || {})[id];
      wrap.append(chip('× ' + (e ? e.label : id), null, true, false,
        () => toggle(key, id), '外す'));
    }
  }
  document.getElementById('clear').classList.toggle('hidden', !any);
  const inner = [];
  for (const f of FACET_UI) {
    if (state.sel[f.key].length) {
      inner.push(f.label + ' ' + state.sel[f.key]
        .map(id => ((LABEL[f.key] || {})[id] || {}).label || id).join('/'));
    }
  }
  document.getElementById('more-note').textContent = inner.length ? '· ' + inner.join(' · ') : '';
}

function renderResults(list, tokens) {
  const wrap = document.getElementById('results');
  wrap.textContent = '';
  document.getElementById('noresult').classList.toggle('hidden', list.length > 0);

  // 自由入力があるときは棚の構造を解いて、関連度順の 1 本のリストにする(SPEC §26)。
  // 分野で絞っているときも同じにする —— セクションの見出しは「主分野」で立てるので、
  // 「文学」で絞ると 35 件表示なのに見出しは 28 件、という食い違いが見える。
  // (残り 7 件は文学を二番目の分野として持つもので、別の見出しの下に出ていた)
  if (tokens.length || state.sel.domains.length) {
    const h = el('h2', null, tokens.length ? '検索結果' : '絞り込み結果');
    h.append(el('span', 'count', list.length + ' 件' + (tokens.length ? ' · 関連度順' : '')));
    wrap.append(h);
    const g = el('div', 'grid');
    for (const a of rank(list)) g.append(renderCard(a));
    wrap.append(g);
    return;
  }
  // 通常時は分野(Domain)ごとに並べる。1 アプリが複数の分野を持つので、
  // 見出しに使うのは先頭の分野(主分野)だけ —— 二度出すと合計が合わなくなる。
  const byDomain = new Map();
  for (const a of list) {
    const d = a.domains[0] || 'other';
    if (!byDomain.has(d)) byDomain.set(d, []);
    byDomain.get(d).push(a);
  }
  const domains = Array.from(byDomain.keys()).sort(
    (x, y) => (ORDER.domains[x] || 999) - (ORDER.domains[y] || 999));
  for (const d of domains) {
    const e = LABEL.domains[d];
    const h = el('h2', null, (e ? (e.icon ? e.icon + ' ' : '') + e.label : d));
    h.append(el('span', 'count', byDomain.get(d).length + ' 件'));
    wrap.append(h);
    const g = el('div', 'grid');
    for (const a of rank(byDomain.get(d))) g.append(renderCard(a));
    wrap.append(g);
  }
}

function renderFeatured() {
  const wrap = document.getElementById('featured');
  wrap.textContent = '';
  const list = APPS.filter(a => a.featured)
    .sort((x, y) => (x.featuredOrder || 99) - (y.featuredOrder || 99));
  for (const a of list) wrap.append(renderCard(a, true));
  document.getElementById('featured-section').classList.toggle('hidden', list.length === 0);
}

// ---------------------------------------------------------------- 反映
function apply(push) {
  const tokens = tokenize(state.q);
  const list = query(state.sel, null, tokens);
  const published = baseList();
  BADGE_COUNT = {};
  for (const a of published) for (const b of a.badges) BADGE_COUNT[b] = (BADGE_COUNT[b] || 0) + 1;

  renderKpi(APPS.filter(a => a.status === 'published'));
  renderTracks();
  renderQuick();
  renderFacets();
  renderSelected();
  renderResults(list, tokens);

  const filtering = tokens.length > 0 || FACETS.some(k => state.sel[k].length > 0);
  document.getElementById('shown').textContent =
    filtering ? list.length + ' 件を表示中(全 ' + published.length + ' 件中)'
              : published.length + ' 件';
  writeHash(push);
}

function toggle(key, id) {
  const cur = state.sel[key];
  const i = cur.indexOf(id);
  if (i === -1) cur.push(id); else cur.splice(i, 1);
  apply(true);
}

// ---------------------------------------------------------------- URL
// 絞り込みの状態を # に載せる(SPEC §25)。チップは pushState、
// 自由入力は replaceState(打鍵ごとに履歴を積まない)。
function writeHash(push) {
  const p = new URLSearchParams();
  for (const key of FACETS) if (state.sel[key].length) p.set(URLKEY[key], state.sel[key].join(','));
  if (state.q.trim()) p.set('q', state.q.trim());
  if (state.showPlanned) p.set('planned', '1');
  const s = p.toString();
  const url = location.pathname + location.search + (s ? '#' + s : '');
  if (url === location.href.replace(location.origin, '')) return;
  if (push) history.pushState(null, '', url); else history.replaceState(null, '', url);
}

// V1 の # との互換(SPEC §25)。棚(cat)は分野へ、技術(tag)は手法・言語・実装へ
// 寄せる。1 対 1 で移らないものは黙って捨てる —— 古いリンクを空振りにしないため。
const V1_CAT = {
  cat0: 'society-transport', cat2: 'game-education', cat13: 'game-education',
  cat9: 'game-education', cat14: 'art-music', cat10: 'ai-computing',
  cat3: 'ai-computing', cat12: 'ai-computing', cat4: 'society-transport',
  cat5: 'literature-folklore-language', cat11: 'literature-folklore-language',
  cat16: 'literature-folklore-language', cat6: 'business-governance',
  cat7: 'science-medical', cat8: 'business-governance', cat15: 'art-music',
  cat17: 'weather-environment', cat18: 'business-governance',
};
const V1_TAG = {
  '機械学習': ['methods', 'machine-learning'], '統計': ['methods', 'statistics'],
  '自然言語処理': ['methods', 'nlp'], '地図': ['methods', 'gis'],
  '探索': ['methods', 'search'], '物理': ['methods', 'simulation'],
  '量子・計算理論': ['methods', 'simulation'],
  'ブラウザ内推論': ['architecture', 'browser-inference'],
  'Rust/WASM': ['languages', 'Rust'], 'R': ['languages', 'R'],
  '自動更新': ['architecture', 'auto-update'],
};
const V1_SRC = {
  '青空文庫': 'aozora', 'Project Gutenberg': 'gutenberg', 'Perseus': 'perseus',
  'Wikimedia': 'wikimedia', '報道・公式発表': 'press-release',
  '政府・自治体データ': 'gov-statistics', '気象・天文データ': 'jma',
  '公開データセット': 'research-dataset', '地理院タイル': 'gsi',
  '美術館オープンアクセス': 'museum-open-access',
};

function readHash() {
  const p = new URLSearchParams(location.hash.slice(1));
  const valid = (key, id) => {
    if (key === 'languages') return TAX.languages.some(e => e.id === id);
    return (TAX[key] || []).some(e => e.id === id);
  };
  for (const key of FACETS) {
    const raw = p.get(URLKEY[key]);
    // 語彙に無い値は黙って捨てる(打ち間違いや古いリンクで全滅させない)
    state.sel[key] = raw ? raw.split(',').filter(v => valid(key, v)) : [];
  }
  state.q = p.get('q') || '';
  state.showPlanned = p.get('planned') === '1';

  if (p.get('cat') && V1_CAT[p.get('cat')]) state.sel.domains.push(V1_CAT[p.get('cat')]);
  if (p.get('tag') && V1_TAG[p.get('tag')]) {
    const [k, v] = V1_TAG[p.get('tag')];
    if (state.sel[k].indexOf(v) === -1) state.sel[k].push(v);
  }
  if (p.get('src') && V1_SRC[p.get('src')]) state.sel.dataSources.push(V1_SRC[p.get('src')]);

  document.getElementById('q').value = state.q;
  document.getElementById('toggle-planned').setAttribute('aria-pressed', state.showPlanned ? 'true' : 'false');
  if (FACET_UI.some(f => state.sel[f.key].length)) document.getElementById('more').open = true;
}

// ---------------------------------------------------------------- SEO
// 各アプリを SoftwareApplication として出す(SPEC §42)。
function renderJsonLd() {
  const items = APPS.filter(a => a.status === 'published' && a.appUrl).map((a, i) => ({
    '@type': 'ListItem', position: i + 1,
    item: {
      '@type': 'SoftwareApplication', name: a.title, url: a.appUrl,
      applicationCategory: 'WebApplication', operatingSystem: 'Web browser',
      description: a.summary,
      offers: { '@type': 'Offer', price: '0', priceCurrency: 'JPY' },
    },
  }));
  const s = document.createElement('script');
  s.type = 'application/ld+json';
  s.textContent = JSON.stringify({
    '@context': 'https://schema.org', '@type': 'ItemList',
    name: 'AI / Public Data / Visualization Portfolio', numberOfItems: items.length,
    itemListElement: items,
  });
  document.head.append(s);
}

// ---------------------------------------------------------------- 起動
async function main() {
  await load();
  readHash();
  renderFeatured();
  apply(false);
  renderJsonLd();

  const input = document.getElementById('q');
  input.addEventListener('input', () => { state.q = input.value; apply(false); });
  document.getElementById('clear').addEventListener('click', () => {
    state.q = ''; input.value = '';
    for (const k of FACETS) state.sel[k] = [];
    apply(true);
    input.focus();
  });
  const planned = document.getElementById('toggle-planned');
  planned.addEventListener('click', () => {
    state.showPlanned = !state.showPlanned;
    planned.setAttribute('aria-pressed', state.showPlanned ? 'true' : 'false');
    apply(true);
  });
  // 戻る / 進む と、# を直接書き換えられた場合。読み直して描き直すだけ。
  const reread = () => { readHash(); renderFeatured(); apply(false); };
  addEventListener('popstate', reread);
  addEventListener('hashchange', reread);
}

main().catch(err => {
  document.getElementById('results').textContent =
    'データの読み込みに失敗しました: ' + err.message;
});
