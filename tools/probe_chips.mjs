// チップ絞り込みを実ブラウザで検品する(被験側)。
//
// 期待値は tools/probe_chips_expect.py が index.html から独立に数えたもの。
// 検査 4 本(check_desc / check_tags / check_src / check_cats)は HTML の構造を
// 見るだけで、**絞り込みが実際に動くかは誰も見ていなかった**。ここが見るのは
//   ・チップの件数が他の軸と自由入力で数え直されているか
//   ・0 件のチップが押せなくなっているか(選択中と「すべて」は残るか)
//   ・キーボードだけで絞り込めるか(チップは <button>)
//
// app-menu には node の環境が無いので **CI には載っていない。手で走らせる検査**。
// playwright は同じ作業机の別プロジェクトのものを借りる:
//
//   python tools/probe_chips_expect.py expect.json
//   PLAYWRIGHT=file:///c:/_ClaudeCode/hoshihata/node_modules/playwright/index.mjs \
//     node tools/probe_chips.mjs expect.json
//
// 第 3 引数に別の HTML を渡せる(陽性対照で壊した複製を当てるため)。
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const { chromium } = await import(process.env.PLAYWRIGHT || 'playwright');

const here = path.dirname(fileURLToPath(import.meta.url));
const target = process.argv[3] || path.join(here, '..', 'index.html');
const INDEX = 'file:///' + target.replace(/\\/g, '/');
const expect = JSON.parse(readFileSync(process.argv[2], 'utf-8'));

const fails = [];
const check = (name, got, want) => {
  const ok = JSON.stringify(got) === JSON.stringify(want);
  if (!ok) fails.push(`${name}\n    got  ${JSON.stringify(got)}\n    want ${JSON.stringify(want)}`);
  console.log(`${ok ? 'ok  ' : 'FAIL'} ${name}`);
};

const browser = await chromium.launch();
const page = await browser.newPage();
await page.goto(INDEX);

const readRow = sel => page.$$eval(sel, els => els.map(e => ({
  v: e.dataset.cat ?? e.dataset.tag ?? e.dataset.src,
  n: Number(e.querySelector('.n').textContent),
  on: e.getAttribute('aria-pressed') === 'true',
  dead: e.disabled,
})));
const shown = () => page.$$eval('.card', els => els.filter(e => !e.classList.contains('hidden')).length);
const shownSections = () => page.$$eval('[data-section]', els => els.filter(e => !e.classList.contains('hidden')).length);

// --- 初期状態 ---
check('初期: 表示カード数', await shown(), expect.total);
check('初期: 主題チップの件数', (await readRow('.chip[data-cat]')).map(c => [c.v, c.n]),
      [['ALL', expect.total], ...expect.cats.map(c => [c.id, c.n])]);
check('初期: 技術チップの件数', (await readRow('.chip[data-tag]')).map(c => [c.v, c.n]),
      [['ALL', expect.total], ...expect.tags.map(t => [t.v, t.n])]);
check('初期: 出典チップの件数', (await readRow('.chip[data-src]')).map(c => [c.v, c.n]),
      [['ALL', expect.total], ...expect.srcs.map(s => [s.v, s.n])]);
check('初期: 死んだチップは無い',
      (await readRow('.chip[data-cat],.chip[data-tag],.chip[data-src]')).filter(c => c.dead).length, 0);
check('初期: 押されているのは 3 つ(各軸の ALL)',
      (await readRow('.chip[data-cat],.chip[data-tag],.chip[data-src]')).filter(c => c.on).map(c => c.v),
      ['ALL', 'ALL', 'ALL']);

// --- 主題を選ぶと、他の軸の件数が数え直される ---
for (const t of expect.probes) {
  await page.click(`.chip[data-cat="${t.cat}"]`);
  check(`${t.cat}: 表示カード数`, await shown(), t.n);
  check(`${t.cat}: 見えているセクションは 1 つ`, await shownSections(), 1);
  // 「すべて」チップは「この軸を外したら何件か」。いまの表示枚数ではない。
  check(`${t.cat}: すべてチップは軸を外したときの件数`,
        (await readRow('.chip[data-cat="ALL"]'))[0].n, expect.total);
  check(`${t.cat}: 絞り込み中の表示枚数が出る`,
        await page.$eval('#shown-count', e => Number(e.textContent)), t.n);
  check(`${t.cat}: 生きている技術チップ`,
        (await readRow('.chip[data-tag]')).filter(c => !c.dead && c.v !== 'ALL').map(c => [c.v, c.n]),
        t.liveTags);
  check(`${t.cat}: 生きている出典チップ`,
        (await readRow('.chip[data-src]')).filter(c => !c.dead && c.v !== 'ALL').map(c => [c.v, c.n]),
        t.liveSrcs);
  check(`${t.cat}: aria-pressed が立っている`,
        (await readRow(`.chip[data-cat="${t.cat}"]`))[0].on, true);
}

// --- 二軸の AND ---
await page.click('.chip[data-cat="ALL"]');
for (const t of expect.pairs) {
  await page.click(`.chip[data-cat="${t.cat}"]`);
  await page.click(`.chip[data-tag="${t.tag}"]`);
  check(`${t.cat} × ${t.tag}: 表示カード数`, await shown(), t.n);
  check(`${t.cat} × ${t.tag}: 主題を外したときの件数`,
        (await readRow('.chip[data-cat="ALL"]'))[0].n, t.tagTotal);
  await page.click('.chip[data-tag="ALL"]');
  await page.click('.chip[data-cat="ALL"]');
}

// --- 0 件はチップだけでは作れない(押せるチップは必ず 1 件以上ある) ---
// これがライブ件数の効き目そのもの。行き止まりが原理的に消える。
{
  await page.click(`.chip[data-tag="${expect.probeTag}"]`);
  const live = (await readRow('.chip[data-cat]')).filter(c => !c.dead);
  check('技術を選ぶと、押せる主題チップは 1 件以上のものだけ', live.every(c => c.n > 0), true);
  check(`${expect.probeTag}: 押せる主題チップ`, live.map(c => [c.v, c.n]),
        [['ALL', expect.quantumTotal], ...expect.quantumLiveCats]);
  await page.click('.chip[data-tag="ALL"]');
}

// --- 選択中のチップは 0 件でも押せる(でないと絞り込みから出られない) ---
{
  await page.click('.chip[data-cat="cat0"]');
  await page.fill('#filter', expect.missQuery);
  const cat0 = (await readRow('.chip[data-cat="cat0"]'))[0];
  check('0 件になった選択中チップ: 押せる状態のまま',
        { on: cat0.on, dead: cat0.dead, n: cat0.n }, { on: true, dead: false, n: 0 });
  check('0 件のとき「該当なし」が出る',
        await page.$eval('#noresult', e => !e.classList.contains('hidden')), true);
  check('0 件のとき見えているセクションは無い', await shownSections(), 0);
  check('0 件のとき押せるのは「すべて」と選択中だけ',
        (await readRow('.chip[data-cat]')).filter(c => !c.dead).map(c => c.v), ['ALL', 'cat0']);
  await page.click('.chip[data-cat="cat0"]');   // 選択中をもう一度押すと解除
  check('解除後: 主題は ALL に戻る', (await readRow('.chip[data-cat="ALL"]'))[0].on, true);
  await page.fill('#filter', '');
  check('全解除後: 表示カード数が戻る', await shown(), expect.total);
  check('全解除後: 絞り込み中の丸は消える',
        await page.$eval('#shown-note', e => e.classList.contains('hidden')), true);
}

// --- 自由入力との AND ---
await page.fill('#filter', expect.query.q);
check(`自由入力「${expect.query.q}」: 表示カード数`, await shown(), expect.query.n);
check(`自由入力「${expect.query.q}」: 主題チップの件数も数え直される`,
      (await readRow('.chip[data-cat]')).filter(c => !c.dead && c.v !== 'ALL').map(c => [c.v, c.n]),
      expect.query.liveCats);

// --- キーボードだけで絞り込める ---
await page.fill('#filter', '');
await page.focus('.chip[data-cat="cat0"]');
await page.keyboard.press('Enter');
check('キーボード(Enter)で主題が切り替わる', await shown(), expect.cat0);
await page.focus('.chip[data-tag="自動更新"]');
await page.keyboard.press('Space');
check('キーボード(Space)で技術が切り替わる', await shown(), expect.cat0AutoUpdate);

await browser.close();
console.log(fails.length ? `\n${fails.length} 件が不一致\n` + fails.join('\n') : '\nすべて一致');
process.exit(fails.length ? 1 : 0);
