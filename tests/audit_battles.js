'use strict';
// Battle planner audit. Run with: node tests/audit_battles.js [--report out.txt]
// For every Gym Leader, rival, Team Magma/Aqua boss, Elite Four and Champion battle, for every starter,
// it checks the catch suggestions against an independent brute-force search over the same data and asserts
// known-good answers. It also checks the type chart and move data the damage estimates rely on.
const fs = require('fs');
const { loadApp } = require('./harness');

const GEN3_CHART = {
  Normal: { Rock: 0.5, Ghost: 0, Steel: 0.5 },
  Fire: { Fire: 0.5, Water: 0.5, Grass: 2, Ice: 2, Bug: 2, Rock: 0.5, Dragon: 0.5, Steel: 2 },
  Water: { Fire: 2, Water: 0.5, Grass: 0.5, Ground: 2, Rock: 2, Dragon: 0.5 },
  Electric: { Water: 2, Electric: 0.5, Grass: 0.5, Ground: 0, Flying: 2, Dragon: 0.5 },
  Grass: { Fire: 0.5, Water: 2, Grass: 0.5, Poison: 0.5, Ground: 2, Flying: 0.5, Bug: 0.5, Rock: 2, Dragon: 0.5, Steel: 0.5 },
  Ice: { Fire: 0.5, Water: 0.5, Grass: 2, Ice: 0.5, Ground: 2, Flying: 2, Dragon: 2, Steel: 0.5 },
  Fighting: { Normal: 2, Ice: 2, Poison: 0.5, Flying: 0.5, Psychic: 0.5, Bug: 0.5, Rock: 2, Ghost: 0, Dark: 2, Steel: 2 },
  Poison: { Grass: 2, Poison: 0.5, Ground: 0.5, Rock: 0.5, Ghost: 0.5, Steel: 0 },
  Ground: { Fire: 2, Electric: 2, Grass: 0.5, Poison: 2, Flying: 0, Bug: 0.5, Rock: 2, Steel: 2 },
  Flying: { Electric: 0.5, Grass: 2, Fighting: 2, Bug: 2, Rock: 0.5, Steel: 0.5 },
  Psychic: { Fighting: 2, Poison: 2, Psychic: 0.5, Dark: 0, Steel: 0.5 },
  Bug: { Fire: 0.5, Grass: 2, Fighting: 0.5, Poison: 0.5, Flying: 0.5, Psychic: 2, Ghost: 0.5, Dark: 2, Steel: 0.5 },
  Rock: { Fire: 2, Ice: 2, Fighting: 0.5, Ground: 0.5, Flying: 2, Bug: 2, Steel: 0.5 },
  Ghost: { Normal: 0, Psychic: 2, Ghost: 2, Dark: 0.5, Steel: 0.5 },
  Dragon: { Dragon: 2, Steel: 0.5 },
  Dark: { Fighting: 0.5, Psychic: 2, Ghost: 2, Dark: 0.5, Steel: 0.5 },
  Steel: { Fire: 0.5, Water: 0.5, Electric: 0.5, Ice: 2, Rock: 2, Steel: 0.5 }
};
const chart = (a, d) => GEN3_CHART[a]?.[d] ?? 1;
const chartEff = (a, types) => types.reduce((m, d) => m * chart(a, d), 1);

// Types one of the suggestions must be able to hit with, per battle (any foe Pokémon on that team).
const MUST = {
  Roxanne: ['Water', 'Grass', 'Fighting', 'Ground', 'Steel'],
  Brawly: ['Flying', 'Psychic'],
  Wattson: ['Ground'],
  Flannery: ['Water', 'Ground', 'Rock'],
  Norman: ['Fighting'],
  Winona: ['Electric', 'Ice', 'Rock'],
  'Tate and Liza': ['Water', 'Grass', 'Ghost', 'Dark', 'Ground', 'Steel', 'Bug', 'Ice'],
  Juan: ['Grass', 'Electric', 'Dragon']
};
// Specific catches the planner must offer (empty team), by battle and foe: [species name at the catch, foe name]
const MUST_SPECIES = [
  ['Roxanne', 'Nosepass', ['Lotad', 'Shroomish', 'Marill', 'Wingull', 'Makuhita', 'Machop']],
  ['Wattson', 'Magneton', ['Geodude', 'Makuhita', 'Machop', 'Numel', 'Marshtomp']],
  ['Flannery', 'Torkoal', ['Marill', 'Wingull', 'Tentacool', 'Lotad', 'Geodude', 'Numel', 'Barboach']]
];

const fails = [], report = [], counts = { trainers: 0 };
const fail = msg => fails.push(msg);
const strip = h => h.replace(/<table[\s\S]*?<\/table>/g, ' [duel table] ').replace(/<[^>]+>/g, ' ').replace(/&amp;/g, '&').replace(/\s+/g, ' ').trim();

(async () => {
  const app = await loadApp();
  const { state, mon } = app;

  // ---- type chart ----
  const T = Object.keys(GEN3_CHART);
  for (const a of T) for (const d of T) {
    const got = state.types[a]?.[d] ?? 1;
    if (got !== chart(a, d)) fail(`type chart: ${a} -> ${d} is ${got}, expected ${chart(a, d)}`);
  }

  // ---- move data ----
  const MOVES = { Thundershock: ['Electric', 40], 'Vine Whip': ['Grass', 35], Absorb: ['Grass', 20], 'Water Gun': ['Water', 40], Ember: ['Fire', 40],
    'Low Kick': ['Fighting'], 'Karate Chop': ['Fighting', 50], 'Double Kick': ['Fighting', 30], Dig: ['Ground', 60], Earthquake: ['Ground', 100],
    Psychic: ['Psychic', 90], Confusion: ['Psychic', 50], 'Ice Beam': ['Ice', 95], Surf: ['Water', 95], Thunderbolt: ['Electric', 95], 'Razor Leaf': ['Grass', 55] };
  for (const [n, [t, p]] of Object.entries(MOVES)) {
    const m = state.moves[n];
    if (!m) { fail(`move ${n} missing`); continue; }
    if (m.type !== t || (p && m.power !== p)) fail(`move ${n}: ${m.type} ${m.power}, expected ${t} ${p}`);
  }
  for (const [n, e] of Object.entries({ Solarbeam: 'charge', Fly: 'charge', Dig: 'charge', 'Sky Attack': 'charge', 'Hyper Beam': 'recharge', 'Fake Out': 'fakeout', 'Triple Kick': 'triple', Explosion: 'explode' }))
    if (state.moves[n]?.effect !== e) fail(`move ${n} effect is ${state.moves[n]?.effect}, expected ${e}`);
  for (const p of state.dex) for (const [, mv] of p.learnset || []) if (!state.moves[mv]) fail(`${p.name} learns unknown move ${mv}`);

  // ---- move choice for your side ----
  for (const [dex, lvl, mv] of [[25, 18, 'Thundershock'], [43, 18, 'Absorb'], [69, 18, 'Vine Whip'], [44, 30, 'Absorb'], [56, 18, 'Karate Chop'], [56, 18, 'Low Kick']])
    if (!app.bestMoves(dex, lvl).includes(mv)) fail(`${mon(dex).name} Lv ${lvl} should keep ${mv}; got ${app.bestMoves(dex, lvl).join(', ')}`);

  // ---- story order ----
  const key = n => state.trainers.find(t => t.name === n);
  const bs = t => app.battleStage(t, t.location);
  if (bs(key('Norman')) < app.stageOf('lavaridge-town')) fail('Norman should be planned after Flannery (four badges)');
  if (bs(key('Winona')) < app.stageOf('route-120')) fail('Winona should be planned after the Devon Scope on Route 120');
  if (bs(key('Juan')) < app.stageOf('sky-pillar')) fail('Juan should be planned after Rayquaza at the Sky Pillar');

  // Independent check: could anything catchable by this stage hit this foe super effectively with a level-up move?
  function oracle(foeMon, stage) {
    const out = [];
    for (const c of app.catchableBy(stage)) for (const f of app.evoForms(c.dex, foeMon.level, stage))
      for (const [mv] of app.learnedBy(f.dex, foeMon.level)) {
        const m = state.moves[mv];
        if (m && m.power && !['counter', 'dream', 'ohko', 'explode', 'fakeout'].includes(m.effect) && chartEff(m.type, mon(foeMon.dex).types) >= 2) out.push(`${mon(f.dex).name}:${mv}`);
      }
    return out;
  }

  for (const V of ['E']) for (const starter of ['Treecko', 'Torchic', 'Mudkip']) {
    state.progress.version = V;
    const save = app.cur();
    save.picks = { starter }; save.team = []; save.teamMeta = {}; save.caught = {};
    // key battles (Battle plan tab) plus every trainer on every route, cave and building page
    const all = [...state.trainers.map(t => ({ t, loc: t.location, key: true })),
      ...state.index.flatMap(l => (state.locations[l.id].trainers || []).map(t => ({ t, loc: l.id })))];
    for (const { t, loc, key } of all) {
      const party = t.party || t.byStarter[starter];
      if (!party) continue;
      if (t.party && starter !== 'Treecko') continue; // non-rival teams don't depend on the starter
      const stage = app.battleStage(t, loc);
      if (stage < app.stageOf(loc)) fail(`${t.id} on ${loc} is planned before you can reach ${loc}`);
      const tag = `${V} ${key ? t.name : `${loc} ${t.class} ${t.name}`}${t.byStarter ? ` (${starter})` : ''}`;
      if (!key) counts.trainers++;
      const hitTypes = new Set();
      for (const p of party) {
        save.team = [];
        const foe = app.foeBattler(p);
        const sug = app.catchSuggestions(p, foe, stage, party, 3);
        for (const s of sug) {
          // each suggestion has to be catchable by then, evolve legally by this level and really hit super effectively
          const w = (state.found[s.c.dex] || []).find(x => (!x.versions || x.versions.includes(V)) && x.stage <= stage);
          if (!w) fail(`${tag} vs ${p.name}: ${mon(s.c.dex).name} is not catchable by ${state.index[Math.floor(stage)].name}`);
          if (!app.evoForms(s.c.dex, s.level, stage).some(f => f.dex === s.f.dex)) fail(`${tag} vs ${p.name}: ${mon(s.c.dex).name} can't be ${mon(s.f.dex).name} by Lv ${s.level}`);
          if (s.level < p.level) fail(`${tag} vs ${p.name}: planned below the foe's level`);
          // moves must be ones it really has: from its catch moveset, learned after catching, or (from Fallarbor on) relearned
          const relearn = stage >= app.stageOf('fallarbor-town');
          const legal = app.learnedBy(s.f.dex, s.level, { dex: s.c.dex, level: parseInt(String(s.c.levels || '5'), 10) }, relearn);
          // or taught from a TM/HM you can have by then (and that this species can learn)
          for (const [mv, x] of app.tmMovesBy(s.f.dex, stage)) {
            if (!(mon(s.f.dex).tmhm || []).includes(x.tm) || state.tms[x.tm].move !== mv) fail(`${tag}: ${mon(s.f.dex).name} can't learn ${x.tm}`);
            if (x.src.stage > stage) fail(`${tag}: ${x.tm} planned before you can get it`);
            legal.set(mv, x);
          }
          for (const mv of s.d.me.moves) if (!legal.has(mv)) fail(`${tag} vs ${p.name}: ${mon(s.f.dex).name} (caught as ${mon(s.c.dex).name}) can't know ${mv} at Lv ${s.level}`);
          for (const mv of s.d.se) {
            if (chartEff(state.moves[mv].type, mon(p.dex).types) < 2) fail(`${tag} vs ${p.name}: ${mv} is not super effective`);
            hitTypes.add(state.moves[mv].type);
          }
        }
        const or = oracle(p, stage);
        if (or.length && !sug.length) fail(`${tag} vs ${p.name} Lv ${p.level}: no catch suggested, but ${or.slice(0, 4).join(', ')} would hit it super effectively`);
        report.push(`${tag} vs ${p.name} Lv ${p.level} [planned at ${state.index[Math.floor(stage)].name}]: ${sug.map(s => `${mon(s.f.dex).name}${s.f.dex !== s.c.dex ? ` (from ${mon(s.c.dex).name})` : ''} ${s.d.mine?.name} ${s.d.myHits} turns${s.d.wins ? '' : ' (may lose)'}${s.risk.length ? ' risk' : ''}`).join(' | ') || 'NONE'}`);
        for (const [who, foeName, names] of MUST_SPECIES)
          if (who === t.name && foeName === p.name && !app.catchableBy(stage).some(c => names.includes(mon(c.dex).name))) fail(`${tag}: none of ${names.join('/')} catchable before ${p.name}`);
        for (const [who, foeName, names] of MUST_SPECIES)
          if (who === t.name && foeName === p.name && !sug.some(s => names.includes(mon(s.c.dex).name)) && !app.catchSuggestions(p, foe, stage, party, 20).some(s => names.includes(mon(s.c.dex).name)))
            fail(`${tag} vs ${p.name}: expected ${names.join(' or ')} among the catch options`);

        // with a plausible team (starter line plus Zigzagoon line at the foe's level) the row should still render
        save.team = [app.lineOf(app.STARTER_BASE[starter] + 2)
          .filter(d => app.evoForms(app.lineOf(d)[0], p.level, stage).some(f => f.dex === d)).pop(), p.level >= 20 ? 264 : 263];
        const row = strip(app.foeRow(p, stage, party));
        if (/undefined|NaN/.test(row)) fail(`${tag} vs ${p.name}: row shows undefined/NaN: ${row.slice(0, 200)}`);
        report.push(`   with ${save.team.map(n => mon(n).name).join(' + ')}: ${row.replace(/^.*?Weak to:/, 'Weak to:').slice(0, 400)}`);
      }
      const want = key && MUST[t.name.replace(/ \(.*\)$/, '')];
      if (want && !want.some(x => hitTypes.has(x))) fail(`${tag}: no suggestion hits with ${want.join('/')}`);
    }
  }
  // Trainers you can only reach with an HM or later in the story must not be planned before you can get there
  const AFTER = [[/^(route-105|route-106|route-107|route-108|abandoned-ship|new-mauville|scorched-slab|route-122|route-124|route-125|route-126|route-127|route-128|route-129|route-130|route-131|route-132|route-133|route-134)$/, 'lavaridge-town', 'Surf (after Norman)'],
    [/^(seafloor-cavern)$/, 'mossdeep-city', 'Dive'], [/^(sootopolis-city)$/, 'pacifidlog-town', 'Rayquaza wakes at the Sky Pillar'],
    [/^(battle-frontier|artisan-cave|desert-underpass|sealed-chamber|desert-ruins|island-cave|ancient-tomb|marine-cave|terra-cave)$/, 'pokemon-league', 'the Hall of Fame']];
  for (const l of state.index) for (const t of state.locations[l.id].trainers || []) for (const [re, after, why] of AFTER)
    if (re.test(l.id) && app.battleStage(t, l.id) <= app.stageOf(after)) fail(`${l.id} ${t.id} is planned before ${why}`);
  // Swimmers are only reachable with Surf
  for (const l of state.index) for (const t of state.locations[l.id].trainers || [])
    if (/Swimmer/.test(t.class) && app.battleStage(t, l.id) <= app.stageOf('lavaridge-town')) fail(`${l.id} ${t.id} (Swimmer) is planned before Surf`);

  // Surf encounters must not count before Norman; no fishing before Dewford; nothing caught before your first Poké Balls
  state.progress.version = 'E';
  if (app.catchableBy(bs(key('Flannery'))).some(c => c.method === 'surf')) fail('Surf encounters counted before Norman');
  if (app.catchableBy(bs(key('Roxanne'))).some(c => /rod|surf|rock-smash|dive/.test(c.method))) fail('Fishing, Surf or Rock Smash counted before Roxanne');
  if (app.catchableBy(bs(key('Juan'))).some(c => c.method === 'dive' && c.stage <= app.stageOf('mossdeep-city'))) fail('Dive encounters counted before Mossdeep');
  if (app.catchableBy(app.stageOf('route-103')).length) fail('Pokémon counted as caught before you have Poké Balls');

  const i = process.argv.indexOf('--report');
  if (i > 0) fs.writeFileSync(process.argv[i + 1], report.join('\n') + '\n');
  if (fails.length) { console.log(`FAIL (${fails.length})\n` + fails.map(f => ' - ' + f).join('\n')); process.exit(1); }
  console.log(`OK: ${report.filter(r => !r.startsWith(' ')).length} foe Pokémon checked (key battles plus ${counts.trainers} route trainer battles) for all three starters.`);
})().catch(e => { console.error(e); process.exit(1); });
