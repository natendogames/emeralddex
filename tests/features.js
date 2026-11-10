'use strict';
// Checks for the reference pages and trackers (features.js and friends): every page renders without gaps, the
// data they lean on hangs together, and the calculators match known Gen 3 numbers. Run: node tests/features.js
const { loadApp } = require('./harness');
const FILES = require('./files.json');
const fails = [];
const fail = m => fails.push(m);
const strip = h => String(h).replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');

(async () => {
  const app = await loadApp(FILES);
  const g = app.get, state = app.state;
  const render = (hash) => {
    app.ctx.location.hash = hash;
    try { app.route(); } catch (e) { fail(`${hash}: ${e.stack.split('\n').slice(0, 3).join(' ')}`); return ''; }
    const html = app.view.innerHTML || '';
    if (/undefined|NaN|\[object Object\]/.test(strip(html))) fail(`${hash}: shows ${strip(html).match(/.{0,60}(undefined|NaN|\[object Object\]).{0,30}/)[0]}`);
    return html;
  };
  state.regionMap = JSON.parse(require('fs').readFileSync(require('path').join(__dirname, '../data/region-map.json'), 'utf8'));
  for (const V of ['E']) {
    state.progress.version = V;
    for (const r of Object.keys(state.regionMap)) render(`#/map/${encodeURIComponent(r)}`);
    // every Pokémon, TM and location page renders
    for (let n = 1; n <= 386; n++) render(`#/mon/${n}`);
    for (const tm of Object.keys(state.tms)) render(`#/tm/${tm}`);
    for (const l of state.index) render(`#/loc/${l.id}`);
    for (const h of ['#/tms', '#/progress', '#/missing', '#/search', '#/move/Surf', '#/item/Nugget', '#/item/Rare%20Candy', '#/planner', '#/tools', '#/dex', '#/'])
      render(h);
    for (const t of g('TOOLS')) render(t.id.startsWith('#') ? t.id : `#/tools/${t.id}`);
  }
  state.progress.version = 'E';

  // every TM or HM with a source has a checklist row that gives it to you
  for (const [tm, t] of Object.entries(state.tms)) if (t.sources.length && !g('tmKeys')(tm).length) fail(`${tm} has sources but no checklist row`);
  if (!g('tmKeys')('TM24').some(k => k.includes(':buy:'))) fail('TM24 should be a Game Corner prize row');
  // bought TMs count as collected
  const s = app.cur();
  const k = g('tmKeys')('TM15').find(x => x.includes(':buy:'));
  s.checks[k] = true;
  if (!g('hasTM')('TM15')) fail('ticking the TM15 shop row should count as having TM15');
  delete s.checks[k];

  // search finds things by name, number and TM
  for (const [q, want] of [['pika', '#/mon/25'], ['25', '#/mon/25'], ['TM24', '#/tm/TM24'], ['thunderbolt', '#/tm/TM24'], ['nugget', '#/item/Nugget'], ['roxanne', '#/loc/rustboro-city'], ['mauville', '#/loc/mauville-city']])
    if (!g('searchResults')(q).slice(0, 5).some(r => r.h === want)) fail(`search "${q}" should find ${want}`);

  // catch odds: worked by hand from the game's formula (handleballthrow in battle_script_commands.c)
  const cc = g('catchChance');
  for (const [rate, ball, hp, st, want] of [[190, 1, 1, 1, 0.2797], [45, 1, 1, 1, 0.0625], [255, 1, 1, 1, 0.3369], [45, 2, 1 / 300, 2, 0.7846], [3, 1, 1, 1, 0.0042]]) {
    const got = cc(rate, ball, hp, st);
    if (Math.abs(got - want) > 0.0005) fail(`catch rate ${rate} ball ${ball} hp ${hp} status ${st}: ${got.toFixed(4)}, expected ${want}`);
  }
  if (cc(3, 1e9) !== 1) fail('a Master Ball always catches');

  // stats: Gen 3 formula, known values (level 100, IV 31, EV 252, neutral/positive nature)
  const sv = g('statValue');
  for (const [base, i, lvl, iv, ev, nat, want] of [[108, 0, 100, 31, 252, 'Hardy', 420], [130, 1, 100, 31, 252, 'Adamant', 394], [100, 5, 50, 31, 252, 'Timid', 167], [100, 5, 50, 31, 0, 'Timid', 132], [45, 0, 5, 0, 0, 'Hardy', 19], [1, 0, 50, 31, 252, 'Hardy', 1]])
    if (sv(base, i, lvl, iv, ev, nat) !== want) fail(`stat base ${base} slot ${i} Lv ${lvl}: ${sv(base, i, lvl, iv, ev, nat)}, expected ${want}`);
  const ivr = g('ivRange')(130, 1, 100, 394, 252, 'Adamant');
  if (ivr.join() !== '31') fail(`IV range should be 31, got ${ivr}`);
  // EXP tables: level 100 totals per growth rate
  const ea = g('expAt');
  for (const [gr, want] of [['fast', 800000], ['medium-fast', 1000000], ['medium-slow', 1059860], ['slow', 1250000], ['erratic', 600000], ['fluctuating', 1640000]])
    if (ea(gr, 100) !== want) fail(`EXP to Lv 100 (${gr}): ${ea(gr, 100)}, expected ${want}`);
  if (g('levelFor')('medium-slow', g('expAt')('medium-slow', 36)) !== 36) fail('levelFor should invert expAt');
  // a trainer's Lv 14 Onix (base EXP 108): 108 * 14 / 7 = 216, x1.5 = 324
  if (g('expFor')(95, 14, true, 1) !== 324) fail(`Onix EXP ${g('expFor')(95, 14, true, 1)}, expected 324`);

  // save import: build a save the way the game lays it out and read it back
  {
    const map = JSON.parse(require('fs').readFileSync(require('path').join(__dirname, '../data/save-map.json'), 'utf8'));
    const buf = new ArrayBuffer(0x20000), dv = new DataView(buf), SAV = g('SAV');
    // slot B is newer (counter 7); slot A is stale (counter 3) and must be ignored
    const sectorOff = (slot, id) => (slot * 14 + ((id + 5) % 14)) * 0x1000; // sectors are rotated in a real save
    for (const [slot, counter] of [[0, 3], [1, 7]]) for (let id = 0; id < 14; id++) {
      const o = sectorOff(slot, id); dv.setUint16(o + 0xFF4, id, true); dv.setUint32(o + 0xFF8, 0x08012025, true); dv.setUint32(o + 0xFFC, counter, true);
    }
    const sb2 = sectorOff(1, 0);
    const setBit = (base, n) => dv.setUint8(base + (n >> 3), dv.getUint8(base + (n >> 3)) | (1 << (n & 7)));
    setBit(sb2 + SAV.SB2.owned, 24); setBit(sb2 + SAV.SB2.owned, 251); // Pikachu, Treecko
    setBit(sectorOff(0, 0) + SAV.SB2.owned, 0); // Bulbasaur only in the stale slot
    [0xC7, 0xD5, 0xED].forEach((c, i) => dv.setUint8(sb2 + i, c)); dv.setUint8(sb2 + 3, 0xFF); // "May"
    dv.setUint8(sb2 + SAV.SB2.gender, 1); // playing as May
    const sb1At = off => { const id = 1 + Math.floor(off / 3968); return sectorOff(1, id) + off % 3968; };
    const itemKey = Object.keys(map.flags).find(k => k.includes(':item:')), trKey = 'rustboro-city:trainer:roxanne';
    for (const f of [map.flags[itemKey], ...[].concat(map.flags[trKey])].slice(0, 2)) { const off = SAV.SB1.flags + (f >> 3); dv.setUint8(sb1At(off), dv.getUint8(sb1At(off)) | (1 << (f & 7))); }
    dv.setUint8(sb1At(SAV.SB1.partyCount), 1);
    // one party Pokémon: Treecko (internal 277) Lv 17 knowing Pound and Absorb, encrypted with personality ^ OT ID
    const pid = 0x12345679, otid = 0xABCD1234, key = (pid ^ otid) >>> 0, order = g('SUB_ORDER')[pid % 24];
    const plain = new DataView(new ArrayBuffer(48));
    plain.setUint16(order.indexOf('G') * 12, map.species.indexOf(252), true);
    plain.setUint16(order.indexOf('A') * 12, map.moves.indexOf('Pound'), true);
    plain.setUint16(order.indexOf('A') * 12 + 2, map.moves.indexOf('Absorb'), true);
    const p0 = SAV.SB1.party;
    const put32 = (off, v) => { for (let b = 0; b < 4; b++) dv.setUint8(sb1At(off + b), (v >>> (8 * b)) & 0xFF); };
    put32(p0, pid); put32(p0 + 4, otid);
    for (let i = 0; i < 48; i += 4) put32(p0 + 0x20 + i, (plain.getUint32(i, true) ^ key) >>> 0);
    dv.setUint8(sb1At(p0 + 0x54), 17);
    const r = g('parseSave')(buf, map);
    if (r.name !== 'May' || r.player !== 'May') fail(`save name ${r.name} / player ${r.player}`);
    if (r.owned.join() !== '25,252') fail(`save owned ${r.owned}`);
    if (!r.checks.includes(itemKey) || !r.checks.includes(trKey)) fail(`save checks ${r.checks}`);
    if (r.party.length !== 1 || r.party[0].dex !== 252 || r.party[0].level !== 17 || r.party[0].moves.join() !== 'Pound,Absorb') fail(`save party ${JSON.stringify(r.party)}`);
  }
  // every item and trainer row has a save flag
  {
    const map = JSON.parse(require('fs').readFileSync(require('path').join(__dirname, '../data/save-map.json'), 'utf8'));
    for (const l of state.index) {
      const loc = state.locations[l.id];
      for (const i of loc.items) if (map.flags[`${l.id}:item:${i.id}`] === undefined && !/Coins/.test(i.name)) fail(`no save flag for ${l.id} ${i.name}`);
      for (const t of loc.trainers || []) if (!map.flags[`${l.id}:trainer:${t.id}`]?.length) fail(`no save flag for trainer ${l.id} ${t.id}`);
    }
  }

  // the still-missing list puts each uncaught Pokémon in exactly one group
  render('#/missing');

  // shop data: every Lilycove Department Store TM for sale is in tms.json as a buy source
  for (const sh of state.extras.shops['lilycove-city']) for (const it of sh.items) {
    const tm = /^(TM|HM)\d+/.exec(it.name)?.[0];
    if (tm && !state.tms[tm].sources.some(x => x.how === 'buy' || x.how === 'prize')) fail(`${tm} sold at Lilycove but not a buy/prize source`);
  }

  // catch plans: every catchable encounter renders, with and without a team, using only shop balls by then and never
  // the Master Ball; the route page links each one
  {
    const sv = app.cur(), keepTeam = sv.team, keepMeta = sv.teamMeta, keepHere = sv.here;
    delete sv.here;
    const ballsBy = g('ballsBy'), sh = g('ballShops')(), stg = g('stageOf');
    const names = st => ballsBy(st).map(b => b.name);
    if (names(stg('route-101')).join() !== 'Poké Ball') fail(`Route 101 balls: ${names(stg('route-101'))}`);
    if (names(stg('rustboro-city')).some(b => /Repeat|Timer/.test(b))) fail('Repeat/Timer Ball before the Devon Goods are back');
    if (!names(stg('dewford-town')).includes('Timer Ball')) fail('no Timer Ball after Rusturf Tunnel');
    if (names(stg('slateport-city') - 1).includes('Great Ball')) fail('Great Ball before Slateport City');
    if (!names(stg('slateport-city')).includes('Great Ball')) fail('no Great Ball at Slateport City');
    if (names(stg('fortree-city') - 1).includes('Ultra Ball')) fail('Ultra Ball before Fortree City');
    if (!names(stg('verdanturf-town')).includes('Nest Ball')) fail('no Nest Ball at Verdanturf');
    if (names(stg('mossdeep-city') - 1).some(b => /Net|Dive/.test(b))) fail('Net/Dive Ball before Mossdeep City');
    { const bm = g('ballMult');
      if (bm('Net Ball', 129) !== 3 || bm('Net Ball', 25) !== 1) fail('Net Ball should be 3x on Water/Bug only');
      if (bm('Nest Ball', 25, 0, { level: 10 }) !== 3 || bm('Nest Ball', 25, 0, { level: 35 }) !== 1) fail('Nest Ball multiplier');
      if (bm('Dive Ball', 129, 0, { method: 'dive' }) !== 3.5 || bm('Dive Ball', 129, 0, { method: 'surf' }) !== 1) fail('Dive Ball should be 3.5x underwater only'); }
    for (const team of [[], [263, 276, 280, 293, 270]]) {
      sv.team = team; sv.teamMeta = {};
      for (const V of ['E']) {
        state.progress.version = V;
        for (const l of state.index) for (const e of state.locations[l.id].encounters) {
          if (!g('inVersion')(e) || ['gift', 'trade', 'game-corner'].includes(e.method)) continue;
          const h = render(`#/catch/${l.id}/${e.dex}.${e.method}`), txt = strip(h);
          if (/Master Ball/.test(txt)) fail(`catch plan ${l.id}/${e.dex} mentions the Master Ball`);
          const allowed = names(Math.max(g('encStage')(l.id, e), g('currentStage')()));
          for (const b of ['Great Ball', 'Ultra Ball', 'Net Ball', 'Nest Ball', 'Dive Ball', 'Repeat Ball', 'Timer Ball']) if (!allowed.includes(b) && new RegExp(`With ${b}s|Use ${b}s`).test(txt)) fail(`catch plan ${l.id}/${e.dex} plans with ${b} before it's sold`);
          if (l.id !== 'safari-zone' && !/If you only have Poké Balls/.test(txt)) fail(`catch plan ${l.id}/${e.dex} has no Poké Ball plan`);
        }
      }
    }
    state.progress.version = 'E';
    if (!render('#/loc/route-101').includes('#/catch/route-101/263.grass')) fail('Route 101 page has no catch plan link for Zigzagoon');
    // Abra teleports: with no faster sleep move, the plan is to throw at once
    sv.team = []; if (!/Throw on your very first turn/.test(strip(render('#/catch/route-116/63')))) fail('Abra plan should say throw on the first turn');
    // False Swipe on the team takes it to 1 HP
    sv.team = [264]; sv.teamMeta = { 264: { level: 40, moves: ['False Swipe', 'Headbutt', '', ''] } };
    if (!/False Swipe until it's at 1 HP/.test(strip(render('#/catch/route-120/359')))) fail('False Swipe plan missing for Absol');
    // the Safari Zone plan uses Safari Balls and Pokéblocks, not FireRed rocks and bait
    if (!/Pokéblock/.test(strip(render('#/catch/safari-zone/' + state.locations['safari-zone'].encounters[0].dex))) ) fail('Safari Zone plan should mention Pokéblocks');
    sv.team = keepTeam; sv.teamMeta = keepMeta; if (keepHere) sv.here = keepHere;
  }

  // Pokémon rows open the Pokémon page; only the checkbox ticks them (no label wrapping the name, no separate ⓘ)
  { const h = render('#/dex'); if (!h.includes('class="rowlink" href="#/mon/252"') || /class="info"/.test(h) || /<label for="[^"]+"><span>#001/.test(h)) fail('Pokédex rows should link to the Pokémon page and tick only from the checkbox'); }

  // item pages: every item in a checklist, shop or the Bag data renders with a description; shop sellers listed
  for (const it of Object.keys(state.items)) render(`#/item/${encodeURIComponent(it)}`);
  { const h = strip(render('#/item/Pok%C3%A9%20Ball'));
    if (!/catching wild Pokémon/.test(h) || !/Oldale Town/.test(h) || !/Sells for/.test(h)) fail(`Poké Ball page: ${h.slice(0, 200)}`);
    if (!/Held in battle: restores 30 HP/.test(strip(render('#/item/Sitrus%20Berry')))) fail('Sitrus Berry held effect missing');
    if (!/Evolves:.*Skitty/.test(strip(render('#/item/Moon%20Stone')))) fail('Moon Stone page should list Skitty');
    if (!render('#/loc/route-104').includes('class="rowlink" href="#/item/')) fail('Route item rows should open the item page'); }

  // suggestions as you type: prefix first, number matches the Pokédex number
  { const sm = g('suggestMatches'), items = g('monItems')();
    const names = q => sm(items, q).map(x => x.label);
    if (names('pika')[0] !== 'Pikachu') fail(`"pika" suggests ${names('pika')}`);
    if (names('25')[0] !== 'Pikachu') fail(`"25" suggests ${names('25')}`);
    if (names('char')[0] !== 'Charmander' || !names('char').includes('Charizard')) fail(`"char" suggests ${names('char')}`);
    if (names('').length || names('zzzz').length) fail('empty or junk text should suggest nothing');
    if (names('a').length > 8) fail('at most 8 suggestions'); }
  // counters to trainer Pokémon never suggest a legendary, even late in the game
  { const L = g('LEGENDARY'), cs = g('catchSuggestions'), fb = g('foeBattler'), bs = g('battleStage');
    for (const t of state.trainers.filter(t => /pokemon-league|victory-road|sootopolis/.test(t.location) || bs(t, t.location) >= g('stageOf')('pokemon-league')).slice(0, 40)) {
      const party = t.party || Object.values(t.byStarter || {})[0] || [];
      for (const p of party) for (const x of cs(p, fb(p), bs(t, t.location) + 100, party, 6)) if (L.has(x.c.dex) || L.has(x.f.dex)) fail(`${t.name} vs ${p.name}: suggests legendary ${x.f.dex}`);
    } }

  // every either/or pick points at gift rows that exist, so its options never show up as separate checkboxes
  for (const c of g('CHOICES')) for (const [loc, id] of [...(c.gifts || []).map(x => [c.loc, x]), ...c.options.flatMap(o => [o.gift && [c.loc, o.gift], ...(o.linked || []).map(l => l.gift && [l.loc, l.gift])])].filter(Boolean))
    if (!state.locations[loc]?.gifts.some(x => x.id === id)) fail(`choice ${c.id}: no gift ${id} at ${loc}`);
  { const html = render('#/loc/littleroot-town');
    for (const m of ['Chikorita', 'Cyndaquil', 'Totodile']) if (html.includes(`data-key="littleroot-town:gift:mon-professor-birch-s-lab-${m.toLowerCase()}-lv-5"`)) fail(`Littleroot Town lists ${m} as a gift checkbox, not a pick`); }
  // the starters are Hoenn's: Treecko, Torchic and Mudkip from Birch's bag on Route 101, with the rival taking the one
  // that beats yours. The Johto starters stay a separate post-game pick in Littleroot Town.
  { const SB = g('STARTER_BASE'), RO = g('RIVAL_OF'), want = { Treecko: 252, Torchic: 255, Mudkip: 258 }, beats = { Treecko: 'Torchic', Torchic: 'Mudkip', Mudkip: 'Treecko' };
    if (JSON.stringify(SB) !== JSON.stringify(want)) fail(`starters are ${JSON.stringify(SB)}, not Treecko/Torchic/Mudkip`);
    for (const [k, n] of Object.entries(want)) { if (app.get('mon')(n).name !== k) fail(`#${n} is ${app.get('mon')(n).name}, not ${k}`); if (RO[k] !== beats[k]) fail(`rival takes ${RO[k]} against ${k}`); }
    const st = g('CHOICES').find(c => c.id === 'starter'), jo = g('CHOICES').find(c => c.id === 'johto');
    if (st.loc !== 'route-101' || st.options.map(o => `${o.key}:${o.dex}`).join() !== 'Treecko:252,Torchic:255,Mudkip:258') fail(`starter pick is ${st.loc} ${st.options.map(o => o.key)}`);
    if (jo.loc !== 'littleroot-town' || jo.options.map(o => o.key).sort().join() !== 'Chikorita,Cyndaquil,Totodile') fail('Johto starter pick moved or changed');
    for (const t of state.trainers.filter(t => t.byStarter)) for (const [k, party] of Object.entries(t.byStarter)) {
      if (!want[k]) fail(`${t.name}: team keyed by ${k}, not a Hoenn starter`);
      const line = [0, 1, 2].map(i => want[beats[k]] + i);
      if (!party.some(p => line.includes(p.dex))) fail(`${t.name} vs ${k}: rival has no ${beats[k]} line`);
    }
    for (const k of Object.keys(state.teamPlan?.plans || JSON.parse(require('fs').readFileSync(require('path').join(__dirname, '../data/team-plan.json'), 'utf8')).plans)) if (!want[k.split(':')[1]]) fail(`team plan for ${k}`);
    // the Battle plan team follows the pick
    const sv = app.cur(), keep = { team: sv.team, picks: sv.picks, nuz: sv.nuz, here: sv.here, checks: sv.checks };
    sv.team = []; sv.picks = {}; g('setPick')('starter', 'Mudkip');
    if (sv.team[0] !== 258) fail(`picking Mudkip puts ${sv.team} on the team`);
    g('setPick')('starter', 'Treecko');
    if (sv.team.join() !== '252') fail(`switching to Treecko leaves ${sv.team} on the team`);
    // Nuzlocke: at the start no area offers the Johto starters (or Surf/Rod Pokémon), and the starter isn't Route 101's first encounter
    sv.nuz = { on: true, dupes: true, areas: {} }; delete sv.here; sv.checks = {};
    const nz = strip(render('#/nuzlocke'));
    for (const m of ['Chikorita', 'Cyndaquil', 'Totodile', 'Bulbasaur', 'Charmander', 'Squirtle']) if (nz.includes(m)) fail(`Nuzlocke page offers ${m} at the start of the game`);
    const names = id => g('areaOptions')(id).map(e => e.name);
    if (names('route-101').some(n => want[n])) fail(`Route 101 Nuzlocke encounter lists the starter: ${names('route-101')}`);
    if (g('areaOptions')('route-103').some(e => e.method !== 'grass')) fail(`Route 103 Nuzlocke encounter offers Surf/Rod Pokémon on the first visit: ${names('route-103')}`);
    if (strip(render('#/loc/littleroot-town')).match(/Nuzlocke encounter/)) fail('Littleroot Town shows a Nuzlocke encounter at the start');
    // Littleroot Town on the first visit: the Hoenn starter pick is up front, the Johto pick waits under "come back later"
    { sv.nuz = keep.nuz; sv.picks = {};
      const html = render('#/loc/littleroot-town'), cut = html.indexOf('<details class="later"><summary><h2>Choose one: come back later');
      const front = strip(cut < 0 ? html : html.slice(0, cut));
      for (const m of ['Chikorita', 'Cyndaquil', 'Totodile']) if (front.includes(`${m} Grass`) || front.includes(`${m} Fire`) || front.includes(`${m} Water`)) fail(`Littleroot Town offers ${m} as a pick on the first visit`);
      for (const m of ['Treecko', 'Torchic', 'Mudkip']) if (!front.includes(m)) fail(`Littleroot Town doesn't show ${m} on the first visit`);
      if (html.includes('data-pick="starter"')) fail('Littleroot Town has a second starter pick (it belongs on Route 101 only)');
      if (!render('#/loc/route-101').includes('data-pick="starter"')) fail('Route 101 lost the starter pick');
      if (cut < 0) fail('Littleroot Town has no come-back-later Johto pick');
      sv.nuz = { on: true, dupes: true, areas: {} }; }
    sv.here = state.index.find(l => g('stageOf')(l.id) > g('stageOf')('pokemon-league')).id;
    if (names('littleroot-town').sort().join() !== 'Chikorita,Cyndaquil,Totodile') fail(`after the Hall of Fame Littleroot offers ${names('littleroot-town')}`);
    Object.assign(sv, keep); if (!keep.here) delete sv.here;
  }
  if (fails.length) { console.log(`FAIL (${fails.length})\n` + fails.slice(0, 60).map(f => ' - ' + f).join('\n')); process.exit(1); }
  console.log('OK: feature pages and data checks passed');
})().catch(e => { console.error(e); process.exit(1); });
