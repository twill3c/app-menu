/* 実ブラウザ検品(playwright)。画面から読み取った値だけを JSON で吐く。
 *
 * 期待値はここでは持たない —— tools/probe_expect.py が apps.json から独立に
 * 数え直して突き合わせる(二実装照合)。検査が緑でも画面が壊れていることは
 * このフリートで何度も起きているので、DOM を実際に触って測る。
 *
 *   python -m http.server 8099 &
 *   PLAYWRIGHT=file:///c:/_ClaudeCode/hoshihata/node_modules/playwright/index.mjs \
 *     node tools/probe_ui.mjs http://127.0.0.1:8099/ > /tmp/probe.json
 *   python tools/probe_expect.py /tmp/probe.json
 */
const PW = process.env.PLAYWRIGHT
  || 'file:///c:/_ClaudeCode/hoshihata/node_modules/playwright/index.mjs';
const BASE = process.argv[2] || 'http://127.0.0.1:8099/';
const SHOT = process.argv[3] || null;

const { chromium } = await import(PW);
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 1000 } });

const consoleErrors = [];
page.on('console', m => { if (m.type() === 'error') consoleErrors.push(m.text()); });
page.on('pageerror', e => consoleErrors.push(String(e)));

const out = { consoleErrors };
// 「35 件を表示中(全 111 件中)」の先頭の数を採る。数字を全部つないで
// 35111 にしてしまう書き方を一度やった。
const num = s => Number((String(s).match(/\d+/) || [0])[0]);

await page.goto(BASE, { waitUntil: 'networkidle' });
await page.waitForSelector('#results .card', { timeout: 15000 });

// ---- KPI
out.kpi = await page.$$eval('#kpi div', els =>
  Object.fromEntries(els.map(e => [e.querySelector('span').textContent.trim(),
                                   Number(e.querySelector('b').textContent)])));

// ---- Featured
out.featured = await page.$$eval('#featured .card h3', els =>
  els.map(e => e.textContent.trim()));
out.featuredCount = out.featured.length;

// ---- Track ボタン
out.tracks = await page.$$eval('#tracks button', els => els.map(e => ({
  label: e.querySelector('.t').textContent.trim(),
  n: Number(e.querySelector('.t .n').textContent),
  pressed: e.getAttribute('aria-pressed') === 'true',
  disabled: e.disabled,
})));

// ---- ファセットのチップ(詳細条件を開いてから読む)
await page.click('#more > summary');
async function readChips() {
  return await page.$$eval('#facets .row', rows => rows.map(r => ({
    axis: r.querySelector('.lead').textContent.trim(),
    chips: Array.from(r.querySelectorAll('.chip')).map(c => ({
      label: c.firstChild.textContent.trim(),
      n: c.querySelector('.n') ? Number(c.querySelector('.n').textContent) : null,
      pressed: c.getAttribute('aria-pressed') === 'true',
      disabled: c.disabled,
    })),
  })));
}
out.facets = await readChips();

const shownCount = async () => num(await page.textContent('#shown'));
const cardCount = async () => (await page.$$('#results .card')).length;
out.initialShown = await shownCount();
out.initialCards = await cardCount();

// ---- チップを押す(分野=文学・民俗・言語)
async function clickChip(axis, labelPart) {
  const rows = await page.$$('#facets .row');
  for (const r of rows) {
    const lead = (await r.$eval('.lead', e => e.textContent)).trim();
    if (lead !== axis) continue;
    for (const c of await r.$$('.chip')) {
      const t = (await c.evaluate(e => e.firstChild.textContent)).trim();
      if (t.includes(labelPart)) { await c.click(); return true; }
    }
  }
  return false;
}
await clickChip('分野', '文学・民俗・言語');
out.afterDomain = { shown: await shownCount(), cards: await cardCount(), hash: await page.evaluate(() => location.hash) };

// 同じ軸のもう 1 つを足すと OR で増える
await clickChip('分野', '歴史・考古・信仰');
out.afterTwoDomains = { shown: await shownCount(), hash: await page.evaluate(() => location.hash) };

// 違う軸を足すと AND で減る
await clickChip('手法', 'GIS');
out.afterDomainAndMethod = { shown: await shownCount(), hash: await page.evaluate(() => location.hash) };

// 0 件のチップは押せない(選択中と「指定なし」は残る)
out.disabledRule = await page.$$eval('#facets .chip', els => els.every(c =>
  (c.disabled === (Number(c.querySelector('.n') ? c.querySelector('.n').textContent : 1) === 0
                   && c.getAttribute('aria-pressed') !== 'true'
                   && c.firstChild.textContent.trim() !== '指定なし'))));

// ---- リロードで復元(URL 共有)
const deepHash = await page.evaluate(() => location.hash);
await page.goto(BASE + deepHash, { waitUntil: 'networkidle' });
await page.waitForSelector('#results .card');
await page.click('#more > summary').catch(() => {});
out.afterReload = { shown: await shownCount(),
  selected: await page.$$eval('#selected .chip', els => els.map(e => e.textContent.trim())) };

// ---- 条件クリア
await page.click('#clear');
out.afterClear = { shown: await shownCount(), hash: await page.evaluate(() => location.hash) };

// ---- 自由入力
out.searches = {};
for (const q of ['青空文庫 地図', '深層学習', 'deep learning', 'pytorch', 'rust', 'r',
                 '防災', 'ブラウザ内推論', 'ないはずのことば']) {
  await page.fill('#q', q);
  await page.waitForTimeout(120);
  out.searches[q] = { shown: await shownCount(), cards: await cardCount(),
                      noresult: await page.$eval('#noresult', e => !e.classList.contains('hidden')) };
}
await page.fill('#q', '');
await page.waitForTimeout(120);

// ---- 企画中
await page.click('#toggle-planned');
await page.waitForTimeout(120);
out.plannedShown = await shownCount();
out.plannedCards = await cardCount();
await page.click('#toggle-planned');
await page.waitForTimeout(120);

// ---- Track ボタンで絞れるか
await page.click('#tracks button >> nth=4');
await page.waitForTimeout(120);
out.afterTrack = { shown: await shownCount(), hash: await page.evaluate(() => location.hash) };
await page.click('#tracks button >> nth=4');
await page.waitForTimeout(120);

// ---- カードの中身(生タグが出ていないか・必須要素があるか)
out.cardSample = await page.$$eval('#results .card', els => els.slice(0, 400).map(c => ({
  title: c.querySelector('h3') ? c.querySelector('h3').textContent.trim() : '',
  hasLink: !!c.querySelector('a.btn.primary'),
  hasDesc: !!c.querySelector('.desc') && c.querySelector('.desc').textContent.length > 0,
  raw: c.textContent,
})));
out.rawTagLeak = out.cardSample.filter(c => /<\/?(b|i|em|strong|br)>|&amp;|&lt;/.test(c.raw)).map(c => c.title);
out.cardsWithoutLink = out.cardSample.filter(c => !c.hasLink).map(c => c.title);

// ---- アクセシビリティの最低線
out.a11y = await page.evaluate(() => ({
  chipsAreButtons: Array.from(document.querySelectorAll('.chip')).every(e => e.tagName === 'BUTTON'),
  chipsHavePressed: Array.from(document.querySelectorAll('.chip')).every(e => e.hasAttribute('aria-pressed')),
  tracksHavePressed: Array.from(document.querySelectorAll('#tracks button')).every(e => e.hasAttribute('aria-pressed')),
  summaryHasControls: !!document.querySelector('#more > summary[aria-controls]'),
  summaryExpandedSynced: document.querySelector('#more > summary')
    .getAttribute('aria-expanded') === String(document.getElementById('more').open),
  decorativeIconsHidden: Array.from(document.querySelectorAll('#results .card h3 .ic, #tracks .ic'))
    .every(e => e.getAttribute('aria-hidden') === 'true'),
  langIsJa: document.documentElement.lang === 'ja',
  jsonLd: !!document.querySelector('script[type="application/ld+json"]'),
}));

// ---- キーボードだけで畳みの中のチップへ行けるか(V1 で踏んだ罠:
//      畳んだ <details> の中は focus() が効かず、焦点が前のチップに残る)
await page.evaluate(() => { document.getElementById('more').open = true; });
out.keyboard = await page.evaluate(() => {
  const c = document.querySelectorAll('#facets .chip')[3];
  c.focus();
  return document.activeElement === c;
});

// ---- 横スクロールが出ていないか
out.overflow = await page.evaluate(() => ({
  bodyScrollWidth: document.body.scrollWidth,
  innerWidth: window.innerWidth,
}));

if (SHOT) {
  await page.goto(BASE, { waitUntil: 'networkidle' });
  await page.waitForSelector('#results .card');
  await page.screenshot({ path: SHOT, fullPage: false });
  // 絞り込みの盤面そのものも撮る(チップの件数と無効化は目で見ないと分からない)
  await page.click('#more > summary');
  await clickChip('分野', '文学・民俗・言語');
  await page.waitForTimeout(150);
  await page.evaluate(() => document.getElementById('more').scrollIntoView());
  await page.screenshot({ path: SHOT.replace(/\.png$/, '-facets.png'), fullPage: false });
  await page.click('#clear');
  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(200);
  await page.screenshot({ path: SHOT.replace(/\.png$/, '-mobile.png'), fullPage: false });
  out.mobileOverflow = await page.evaluate(() => ({
    bodyScrollWidth: document.body.scrollWidth, innerWidth: window.innerWidth }));
}

await browser.close();
process.stdout.write(JSON.stringify(out, null, 1));
