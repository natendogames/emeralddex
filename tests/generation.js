'use strict';
// Guards against FireRed/LeafGreen data leaking into the Emerald app (it was forked from the FRLG app).
// Checks the Pokédex is the Hoenn dex, the either/or picks are Emerald's, every Pokémon you can meet or be given is
// one Emerald really has, no FRLG-only items are listed, and no Kanto/Sevii places or people appear in the app's text.
// Run: node tests/generation.js
const fs = require('fs'), path = require('path');
const { loadApp } = require('./harness');
const ROOT = path.join(__dirname, '..');
const J = f => JSON.parse(fs.readFileSync(path.join(ROOT, f), 'utf8'));
let failures = 0;
const fail = msg => { failures++; console.log('FAIL', msg); };

// Pokémon outside the Hoenn dex that Emerald itself has: Safari Zone extension (Johto), the Johto starters from
// Birch, Smeargle (Artisan Cave), Ditto (Desert Underpass), Sudowoodo (Battle Frontier), the Meowth in-game trade,
// and the event islands (Mew, Lugia, Ho-Oh).
const EMERALD_NON_HOENN = new Set(['Aipom', 'Teddiursa', 'Ledyba', 'Sunkern', 'Hoothoot', 'Pineco', 'Houndour', 'Miltank',
  'Shuckle', 'Mareep', 'Spinarak', 'Gligar', 'Snubbull', 'Stantler', 'Wooper', 'Quagsire', 'Remoraid', 'Octillery',
  'Chikorita', 'Cyndaquil', 'Totodile', 'Smeargle', 'Ditto', 'Sudowoodo', 'Meowth', 'Mew', 'Lugia', 'Ho-Oh']);

// Items that only exist in Emerald's item table for FRLG link compatibility
const FRLG_ITEMS = ["Oak's Parcel", 'Poké Flute', 'Secret Key', 'Bike Voucher', 'Gold Teeth', 'Old Amber', 'Card Key', 'Lift Key',
  'Helix Fossil', 'Dome Fossil', 'Silph Scope', 'Bicycle', 'Town Map', 'Vs Seeker', 'VS Seeker', 'Fame Checker', 'TM Case',
  'Berry Pouch', 'Teachy TV', 'Tri-pass', 'Rainbow Pass', 'Tea', 'Ruby', 'Sapphire'];

// Kanto and Sevii places and people. "FireRed/LeafGreen" itself is fine (trade sources, the sister app).
const KANTO = /\b(Pallet|Viridian|Pewter|Cerulean|Vermilion|Lavender Town|Celadon|Saffron|Fuchsia|Cinnabar|Indigo Plateau|Sevii|Kanto|Prof\.? Oak|Professor Oak|Oak's|Giovanni|Team Rocket|Silph|Brock|Misty|Lt\. Surge|Erika|Sabrina|Blaine|Koga|Lorelei|Agatha|Lance|Tanoby|One Island|Two Island|Seafoam|Pokémon Tower|Bulbasaur|Charmander|Squirtle)\b/;
// genuine Emerald text that names a Kanto thing
const KANTO_OK = [/A peculiar box made by Silph Co\./];

(async () => {
  const dex = J('data/pokedex.json');
  const byDex = Object.fromEntries(dex.map(p => [p.dex, p]));
  if (dex.length !== 386) fail(`National dex has ${dex.length} entries, expected 386`);
  const hoenn = dex.filter(p => p.hoenn).sort((a, b) => a.hoenn - b.hoenn);
  if (hoenn.length !== 202 || hoenn.some((p, i) => p.hoenn !== i + 1)) fail(`Hoenn dex is not numbered 1-202 (${hoenn.length} entries)`);
  // spot checks against the HOENN_DEX enum in pokeemerald include/constants/pokedex.h
  const expectH = { 1: 'Treecko', 4: 'Torchic', 7: 'Mudkip', 10: 'Poochyena', 14: 'Wurmple', 41: 'Alakazam', 63: 'Zubat', 129: 'Corphish', 151: 'Chimecho', 202: 'Deoxys' };
  for (const [n, name] of Object.entries(expectH)) if (hoenn[n - 1]?.name !== name) fail(`Hoenn #${n} is ${hoenn[n - 1]?.name}, expected ${name}`);
  for (const name of ['Bulbasaur', 'Charmander', 'Squirtle', 'Mewtwo', 'Chikorita']) if (dex.find(p => p.name === name).hoenn) fail(`${name} is marked as a Hoenn dex Pokémon`);

  const app = await loadApp(['features.js', 'tools.js', 'trackers.js', 'modes.js']);
  const CHOICES = app.get('CHOICES');
  const opts = id => CHOICES.find(c => c.id === id).options.map(o => o.key).join(',');
  if (opts('starter') !== 'Treecko,Torchic,Mudkip') fail(`starter options are ${opts('starter')}`);
  if (JSON.stringify(app.STARTER_BASE) !== JSON.stringify({ Treecko: 252, Torchic: 255, Mudkip: 258 })) fail(`STARTER_BASE is ${JSON.stringify(app.STARTER_BASE)}`);
  if (opts('fossil') !== 'Root,Claw') fail(`fossil options are ${opts('fossil')}`);
  if (app.get('HOENN_COUNT') !== 202) fail('HOENN_COUNT is not 202');
  if (app.state.dexFilter.scope !== 'hoenn') fail('the Pokédex does not open on the Hoenn dex');
  const plans = Object.keys(J('data/team-plan.json').plans).sort().join(',');
  if (plans !== 'E:Mudkip,E:Torchic,E:Treecko') fail(`team plans are ${plans}`);

  // every Pokémon you can meet, battle or be given
  const seen = new Map();
  const note = (n, where) => { const p = byDex[n]; if (p && !p.hoenn && !EMERALD_NON_HOENN.has(p.name)) seen.set(p.name, where); };
  for (const l of J('data/locations.json').locations) {
    const loc = J('data/' + l.file);
    for (const e of loc.encounters || []) note(e.dex, `${loc.id} wild`);
    for (const g of loc.gifts || []) if (g.dex) note(g.dex, `${loc.id} gift ${g.name}`);
    for (const t of loc.trainers || []) {
      for (const m of t.party || []) note(m.dex, `${loc.id} trainer ${t.name}`);
      for (const party of Object.values(t.byStarter || {}).concat(Object.values(t.byStarterBrendan || {}))) for (const m of party || []) note(m.dex, `${loc.id} rival`);
    }
    for (const row of [...(loc.items || []), ...(loc.gifts || [])]) if (FRLG_ITEMS.includes(row.name.replace(/ ×\d+$/, ''))) fail(`${loc.id} lists the FRLG item ${row.name}`);
  }
  for (const plan of Object.values(J('data/team-plan.json').plans)) for (const leg of plan.legs) for (const m of leg.team) note(m.dex, 'team plan');
  for (const [name, where] of seen) fail(`${name} (not in Emerald outside trades) appears at ${where}`);

  const items = J('data/items.json');
  for (const it of FRLG_ITEMS) if (items[it]) fail(`items.json has the FRLG-only item ${it}`);
  for (const [loc, shops] of Object.entries(J('data/extras.json').shops)) for (const sh of shops) for (const it of sh.items) if (FRLG_ITEMS.includes(it.name)) fail(`${loc} shop sells ${it.name}`);
  for (const t of J('data/extras.json').tutors || []) if (!t.loc && !t.where) fail(`tutor ${JSON.stringify(t).slice(0, 60)} has no place`);

  // Kanto names in data text and in the app's own strings (comments are skipped)
  const scan = (file, text) => text.split('\n').forEach((line, i) => {
    if (/^\s*(\/\/|#)/.test(line)) return;
    const m = line.match(KANTO);
    if (m && !KANTO_OK.some(re => re.test(line))) fail(`${file}:${i + 1} mentions "${m[0]}": ${line.trim().slice(0, 100)}`);
  });
  const dataFiles = ['data/walkthrough.json', 'data/extras.json', 'data/items.json', 'data/trainers.json', 'data/tms.json', 'data/team-plan.json', 'data/locations.json']
    .concat(J('data/locations.json').locations.map(l => 'data/' + l.file));
  for (const f of dataFiles) scan(f, fs.readFileSync(path.join(ROOT, f), 'utf8'));
  for (const f of ['app.js', 'features.js', 'tools.js', 'trackers.js', 'modes.js', 'map.js', 'catchplan.js', 'saveimport.js', 'index.html', 'manifest.webmanifest']) {
    // drop trailing // comments too, so notes about the sister app don't count
    scan(f, fs.readFileSync(path.join(ROOT, f), 'utf8').split('\n').map(l => l.replace(/\s\/\/ .*$/, '')).join('\n'));
  }

  if (failures) { console.log(`${failures} generation check(s) failed`); process.exit(1); }
  console.log('Generation checks passed: Hoenn dex, Emerald picks, Emerald-only Pokémon, items and text');
})().catch(e => { console.error(e); process.exit(1); });
