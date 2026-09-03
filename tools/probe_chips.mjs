// チップ絞り込みを実ブラウザで検品する(被験側)。
//
// 期待値は tools/probe_chips_expect.py が index.html から独立に数えたもの。
// 検査 4 本(check_desc / check_tags / check_src / check_cats)は HTML の構造を
// 見るだけで、**絞り込みが実際に動くかは誰も見ていなかった**。ここが見るのは
//   ・チップの件数が他の軸と自由入力で数え直されているか
//   ・0 件のチップが押せなくなっているか(選択中と「すべて」は残るか)
//   ・分野 → 棚の二段が開くか(棚チップは選んだ分野のものだけ)
//   ・「自作・合成」で出典を持たないカードが引けるか
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
  // 棚チップは data-cat と data-group の両方を持つので、cat を先に見る。
  v: e.dataset.cat ?? e.dataset.tag ?? e.dataset.src ?? e.dataset.group,
  n: Number(e.querySelector('.n').textContent),
  on: e.getAttribute('aria-pressed') === 'true',
  dead: e.disabled,
  shown: !e.classList.contains('hidden'),
})));
const GROUPS = '#groups .chip[data-group]';
const shown = () => page.$$eval('.card', els => els.filter(e => !e.classList.contains('hidden')).length);
const shownSections = () => page.$$eval('[data-section]', els => els.filter(e => !e.classList.contains('hidden')).length);
const shownCount = () => page.$eval('#shown-count', e => Number(e.textContent));
const hidden = sel => page.$eval(sel, e => e.classList.contains('hidden'));
const openMore = () => page.$eval('#more', e => { e.open = true; });

// --- 初期状態 ---
check('初期: 表示カード数', await shown(), expect.total);
check('初期: 分野チップの件数', (await readRow(GROUPS)).map(c => [c.v, c.n]),
      [['ALL', expect.total], ...expect.groups.map(g => [g.id, g.n])]);
check('初期: 棚の行は畳まれている', await hidden('#cats'), true);
check('初期: 技術チップの件数', (await readRow('.chip[data-tag]')).map(c => [c.v, c.n]),
      [['ALL', expect.total], ...expect.tags.map(t => [t.v, t.n])]);
check('初期: 出典チップの件数(自作・合成を含む)',
      (await readRow('.chip[data-src]')).map(c => [c.v, c.n]),
      [['ALL', expect.total], ...expect.srcs.map(s => [s.v, s.n])]);
check('初期: 死んだチップは無い',
      (await readRow(`${GROUPS},.chip[data-cat],.chip[data-tag],.chip[data-src]`)).filter(c => c.dead).length, 0);
check('初期: 押されているのは 4 つ(各軸の ALL)',
      (await readRow(`${GROUPS},.chip[data-cat],.chip[data-tag],.chip[data-src]`)).filter(c => c.on).map(c => c.v),
      ['ALL', 'ALL', 'ALL', 'ALL']);
check('初期: 絞り込み中の丸は出ていない', await hidden('#shown-note'), true);

// --- 分野 → 棚の二段 ---
await openMore();
for (const t of expect.probes) {
  await page.click(`${GROUPS.split(',')[0]}[data-group="${t.group}"]`);
  check(`${t.group}: 表示カード数`, await shown(), t.groupN);
  check(`${t.group}: 棚の行が開く`, await hidden('#cats'), false);
  check(`${t.group}: 見えている棚チップはこの分野のものだけ`,
        (await readRow('.chip[data-cat]')).filter(c => c.shown && c.v !== 'ALL').map(c => [c.v, c.n]),
        t.shelves);

  await page.click(`.chip[data-cat="${t.cat}"]`);
  check(`${t.cat}: 表示カード数`, await shown(), t.n);
  check(`${t.cat}: 見えているセクションは 1 つ`, await shownSections(), 1);
  // 「すべて」チップは「この軸を外したら何件か」。いまの表示枚数ではない。
  check(`${t.cat}: 分野の「すべて」は軸を外したときの件数`,
        (await readRow(`${GROUPS.split(',')[0]}[data-group="ALL"]`))[0].n, expect.total);
  check(`${t.cat}: 棚の「この分野すべて」は分野の件数`,
        (await readRow('.chip[data-cat="ALL"]'))[0].n, t.groupN);
  check(`${t.cat}: 絞り込み中の表示枚数が出る`, await shownCount(), t.n);
  check(`${t.cat}: 生きている技術チップ`,
        (await readRow('.chip[data-tag]')).filter(c => !c.dead && c.v !== 'ALL').map(c => [c.v, c.n]),
        t.liveTags);
  check(`${t.cat}: 生きている出典チップ`,
        (await readRow('.chip[data-src]')).filter(c => !c.dead && c.v !== 'ALL' && c.v !== expect.sentinel.v).map(c => [c.v, c.n]),
        t.liveSrcs);
  check(`${t.cat}: aria-pressed が立っている`,
        (await readRow(`.chip[data-cat="${t.cat}"]`))[0].on, true);

  // 分野を切り替えたら棚の選択は外れる(その棚は新しい分野の中に無い)
  await page.click(`${GROUPS.split(',')[0]}[data-group="ALL"]`);
  check(`${t.cat}: 分野を外すと棚の選択も外れる`,
        { cards: await shown(), catsHidden: await hidden('#cats') },
        { cards: expect.total, catsHidden: true });
}

// --- 二軸の AND(棚 × 技術) ---
for (const t of expect.pairs) {
  const g = expect.probes.find(p => p.cat === t.cat)?.group
        ?? (await page.$eval(`.chip[data-cat="${t.cat}"]`, e => e.dataset.group));
  await page.click(`${GROUPS.split(',')[0]}[data-group="${g}"]`);
  await page.click(`.chip[data-cat="${t.cat}"]`);
  await page.click(`.chip[data-tag="${t.tag}"]`);
  check(`${t.cat} × ${t.tag}: 表示カード数`, await shown(), t.n);
  check(`${t.cat} × ${t.tag}: 畳んでも分かるように summary に出る`,
        await page.$eval('#more-note', e => e.textContent.trim()), '· ' + t.tag);
  await page.click('.chip[data-tag="ALL"]');
  await page.click(`${GROUPS.split(',')[0]}[data-group="ALL"]`);
}
check('技術を外すと summary の印も消える',
      await page.$eval('#more-note', e => e.textContent.trim()), '');

// --- 自作・合成(出典を持たないカード) ---
{
  await page.click(`.chip[data-src="${expect.sentinel.v}"]`);
  check(`${expect.sentinel.label}: 表示カード数`, await shown(), expect.sentinel.n);
  check(`${expect.sentinel.label}: summary に出る`,
        await page.$eval('#more-note', e => e.textContent.trim()), '· ' + expect.sentinel.label);
  // 同じ軸のチップは互いに選択肢なので、他の出典は自分の件数を出したまま
  // 押せる(切り替えられる)。数え直されるのは他の軸。
  check(`${expect.sentinel.label}: 他の出典チップは選択肢として残る`,
        (await readRow('.chip[data-src]')).filter(c => !c.dead).length,
        expect.srcs.length + 1);   // 語彙 10 + 自作・合成 + 指定なし
  check(`${expect.sentinel.label}: 分野チップは出典なしの中で数え直される`,
        (await readRow(GROUPS)).filter(c => !c.dead && c.v !== 'ALL').map(c => [c.v, c.n]),
        expect.sentinel.liveGroups);
  await page.click(`.chip[data-src="${expect.sentinel.v}"]`);
  check(`${expect.sentinel.label}: 解除で戻る`, await shown(), expect.total);
}

// --- 0 件はチップだけでは作れない(押せるチップは必ず 1 件以上ある) ---
// これがライブ件数の効き目そのもの。行き止まりが原理的に消える。
{
  await page.click(`.chip[data-tag="${expect.probeTag}"]`);
  const live = (await readRow(GROUPS)).filter(c => !c.dead);
  check('技術を選ぶと、押せる分野チップは 1 件以上のものだけ', live.every(c => c.n > 0), true);
  check(`${expect.probeTag}: 押せる分野チップ`, live.map(c => [c.v, c.n]),
        [['ALL', expect.quantumTotal], ...expect.quantumLiveGroups]);
  await page.click('.chip[data-tag="ALL"]');
}

// --- 選択中のチップは 0 件でも押せる(でないと絞り込みから出られない) ---
{
  const g = expect.firstGroup.id;
  await page.click(`${GROUPS.split(',')[0]}[data-group="${g}"]`);
  await page.fill('#filter', expect.missQuery);
  const chip = (await readRow(`${GROUPS.split(',')[0]}[data-group="${g}"]`))[0];
  check('0 件になった選択中チップ: 押せる状態のまま',
        { on: chip.on, dead: chip.dead, n: chip.n }, { on: true, dead: false, n: 0 });
  check('0 件のとき「該当なし」が出る', await hidden('#noresult'), false);
  check('0 件のとき見えているセクションは無い', await shownSections(), 0);
  check('0 件のとき押せるのは「すべて」と選択中だけ',
        (await readRow(GROUPS)).filter(c => !c.dead).map(c => c.v), ['ALL', g]);
  await page.click(`${GROUPS.split(',')[0]}[data-group="${g}"]`);   // もう一度押すと解除
  check('解除後: 分野は ALL に戻る',
        (await readRow(`${GROUPS.split(',')[0]}[data-group="ALL"]`))[0].on, true);
  await page.fill('#filter', '');
  check('全解除後: 表示カード数が戻る', await shown(), expect.total);
  check('全解除後: 絞り込み中の丸は消える', await hidden('#shown-note'), true);
}

// --- 自由入力との AND ---
await page.fill('#filter', expect.query.q);
check(`自由入力「${expect.query.q}」: 表示カード数`, await shown(), expect.query.n);
check(`自由入力「${expect.query.q}」: 分野チップの件数も数え直される`,
      (await readRow(GROUPS)).filter(c => !c.dead && c.v !== 'ALL').every(c => c.n > 0), true);
await page.fill('#filter', '');

// --- キーボードだけで絞り込める ---
await page.focus(`${GROUPS.split(',')[0]}[data-group="${expect.firstGroup.id}"]`);
await page.keyboard.press('Enter');
check('キーボード(Enter)で分野が切り替わる', await shown(), expect.firstGroup.n);
await page.keyboard.press('Enter');   // もう一度で解除
await page.focus('.chip[data-tag="自動更新"]');
await page.keyboard.press('Space');
check('キーボード(Space)で技術が切り替わる', await shown(), expect.autoUpdate);

await browser.close();
console.log(fails.length ? `\n${fails.length} 件が不一致\n` + fails.join('\n') : '\nすべて一致');
process.exit(fails.length ? 1 : 0);
