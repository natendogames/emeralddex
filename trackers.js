'use strict';
// Completion trackers: one-time encounters and gifts, move tutors, Match Call rematches and the Emerald story and
// post-game checklist. Loaded after tools.js.

// ---------- one-time Pokémon ----------
// Legendaries and other single encounters (miss them and they're gone), plus Pokémon you're given once.
const ONCE_NOTE = { 'route-119': 'Use the Devon Scope on the shimmering spot. Save first.', 'route-120': 'Use the Devon Scope on the shimmering spots. Save first.',
  'aqua-hideout': 'Save first. The Electrode look like item balls.', 'new-mauville': 'Save first. The Voltorb look like item balls.',
  'sky-pillar': 'After the Hall of Fame, at the top (needs the Mach Bike). Save first.', 'desert-ruins': 'Needs the Regi braille puzzle (Relicanth and Wailord in your party at the Sealed Chamber). Save first.',
  'island-cave': 'Needs the Regi braille puzzle. Save first.', 'ancient-tomb': 'Needs the Regi braille puzzle and Flash. Save first.',
  'marine-cave': 'After the Hall of Fame; ask the Weather Institute where the rain is. Needs Dive. Save first.',
  'terra-cave': 'After the Hall of Fame; ask the Weather Institute where the drought is. Save first.',
  'southern-island': 'Event only (Eon Ticket).', 'faraway-island': 'Event only (Old Sea Map).', 'birth-island': 'Event only (Aurora Ticket).', 'navel-rock': 'Event only (Mystic Ticket).' };
function onceList() {
  const out = [];
  for (const l of state.index) {
    const loc = state.locations[l.id];
    for (const e of loc.encounters) {
      if (!inVersion(e)) continue;
      if (e.method === 'static' || e.method === 'roaming' || (e.method === 'gift' && !CHOICE_OF[`${l.id}:dex:${e.dex}`])) out.push({ loc: l.id, name: loc.name, e });
    }
  }
  return out;
}
function renderOnce() {
  const s = cur();
  const rows = onceList();
  const done = rows.filter(r => isCaught(r.e.dex)).length;
  view.innerHTML = `<div class="card"><b>${done}/${rows.length}</b> caught ${bar(done, rows.length)}<p class="note">Legendaries, Kecleon and Pokémon you only get once, in story order. Save before each one: if it faints or you run, it's gone for good.</p></div>
    <div class="card">${rows.map(({ loc, name, e }) => checkRow(`dex:${e.dex}`, isCaught(e.dex), `${esc(e.name)} ${types(e.dex)}`,
      `<a href="#/loc/${loc}">${esc(name)}</a> · ${esc(METHOD_LABEL[e.method] || e.method)}${e.levels ? ` · Lv ${esc(e.levels)}` : ''}${e.notes && e.method === 'roaming' ? ` · ${esc(e.notes)}` : ''}${ONCE_NOTE[loc] ? ` · ${esc(ONCE_NOTE[loc])}` : ''}`, infoA(e.dex))).join('')}</div>`;
  void s;
}

// ---------- move tutors ----------
const tutorKey = t => `${t.loc}:tutor:${t.id}`;
function tutorRow(t) {
  const s = cur(), team = s.team.filter(n => t.learners.includes(n));
  const sub = `${esc(t.where)}${t.note ? ` · ${esc(t.note)}` : ' · one use only'} · ${team.length ? `<span class="good">Your team: ${team.map(n => esc(mon(n).name)).join(', ')}</span>` : s.team.length ? 'nobody on your team can learn it' : `${t.learners.length} Pokémon can learn it`}`;
  return checkRow(tutorKey(t), s.checks[tutorKey(t)], `${esc(t.move)}${state.moves[t.move]?.type ? ` ${typeTag(state.moves[t.move].type)}` : ''}`, sub, ` <span class="tag">Tutor</span>`);
}
function tutorSection(loc) {
  const list = state.extras.tutors.filter(t => t.loc === loc.id);
  const now = list.filter(t => !t.later), later = list.filter(t => t.later);
  return (now.length ? `<h2>Move tutors</h2><div class="card">${now.map(tutorRow).join('')}<p class="note">Tick one off once you've used it.</p></div>` : '')
    + laterSection('Move tutors', later, tutorRow, t => cur().checks[tutorKey(t)]);
}
function renderTutors() {
  const list = state.extras.tutors;
  view.innerHTML = `<div class="card"><p class="note">Each of the tutors around Hoenn teaches its move once per save file, so pick who gets it with care. The Battle Frontier tutors (post-game) charge Battle Points and can teach again.</p></div>
    <div class="card">${list.map(t => `<div class="area"><a href="#/loc/${t.loc}">${esc(state.locations[t.loc].name)}</a></div>${tutorRow(t)}`).join('')}</div>`;
}

// ---------- Match Call rematches ----------
// Trainers you register in the PokéNav call back for rematches once you have five badges; each rematch after the
// first needs the one before it. Gym Leaders call after the Hall of Fame. Draft: the story points per tier are
// estimates (the game also needs you to walk a while between calls).
const TIER_AT = { 'Rematch 1': 'route-105', 'Rematch 2': 'lilycove-city', 'Rematch 3': 'sootopolis-city', 'Rematch 4': 'pokemon-league' };
function rematchBlock(t, locId) {
  const r = (state.extras.rematches[locId] || []).find(x => x.id === t.id);
  if (!r) return '';
  const leader = t.class === 'Leader';
  return `<details class="later rematch"><summary><h2>Match Call rematches (${r.tiers.length})</h2></summary>${r.tiers.map(x => {
    const stage = Math.max(stageOf(locId), stageOf(leader ? 'pokemon-league' : TIER_AT[x.after] || locId));
    return `<div class="area">${esc(x.after)} · Lv ${Math.max(...x.party.map(p => p.level))}</div>${x.party.map(p => foeRow(p, stage, x.party)).join('')}`;
  }).join('')}<p class="note">${leader ? 'Gym Leaders call for rematches after you enter the Hall of Fame.' : 'Register the trainer in your PokéNav after the battle. Once you have five badges they call when they want a rematch; each one after the first needs the one before.'} Rematches are good EXP and money.</p></details>`;
}

// ---------- Emerald story and post-game ----------
const QUESTS = [
  ['Team Magma and Team Aqua', [['q-devon', 'rusturf-tunnel', 'Get the Devon Goods back from the Aqua Grunt in Rusturf Tunnel and return them to Devon.'],
    ['q-letter', 'granite-cave', "Deliver Mr. Stone's letter to Steven in Granite Cave."],
    ['q-goods', 'slateport-city', 'Deliver the Devon Goods to Captain Stern at the Oceanic Museum.'],
    ['q-chimney', 'mt-chimney', 'Stop Team Magma at the top of Mt. Chimney (beat Tabitha and Maxie).'],
    ['q-weather', 'route-119', 'Clear Team Aqua out of the Weather Institute; the scientist gives you Castform.'],
    ['q-pyre', 'mt-pyre', 'Chase Team Aqua to the summit of Mt. Pyre; they take the Blue Orb.'],
    ['q-magma', 'magma-hideout', 'Beat Maxie in the Magma Hideout (Groudon wakes up).'],
    ['q-aqua', 'aqua-hideout', 'Raid the Aqua Hideout in Lilycove; Archie escapes in his submarine.'],
    ['q-space', 'mossdeep-city', 'Beat Maxie and Tabitha with Steven at the Mossdeep Space Center; Steven gives you HM08 Dive.'],
    ['q-seafloor', 'seafloor-cavern', 'Dive on Route 128 and beat Archie in the Seafloor Cavern (Kyogre wakes up).'],
    ['q-skypillar', 'sky-pillar', 'Climb Sky Pillar with the Mach Bike and wake Rayquaza to stop Groudon and Kyogre.']]],
  ['Other things to do', [['q-bikes', 'mauville-city', 'Get a bike from Rydel in Mauville (the Mach Bike and Acro Bike swap any time).'],
    ['q-trickhouse', 'route-110', 'Finish all eight Trick House puzzles on Route 110 (one opens after each badge).'],
    ['q-winstrate', 'route-111', 'Beat the four Winstrates in a row on Route 111 for the Macho Brace.'],
    ['q-newmauville', 'new-mauville', "Fix New Mauville's generator for Wattson (TM24 Thunderbolt)."],
    ['q-feebas', 'route-119', 'Find Feebas on Route 119 and raise its Beauty with Pokéblocks to evolve it into Milotic.'],
    ['q-contests', 'lilycove-city', 'Win the Master Rank of each contest in Lilycove for all five ribbons.'],
    ['q-daycare', 'route-117', 'Breed at the Route 117 Day Care for Pokémon you can only hatch (Azurill, Wynaut, Pichu...).']]],
  ['After you become Champion', [['q-natdex', 'littleroot-town', 'After the Hall of Fame, visit Professor Birch in Littleroot Town for the National Pokédex.'],
    ['q-tidal', 'ss-tidal', 'Get the S.S. Ticket from your father and ride the S.S. Tidal to the Battle Frontier.'],
    ['q-eon', 'roaming', 'Answer the TV question at home: Latias or Latios starts roaming. Catch it (a Master Ball or lots of Repeat Balls help).'],
    ['q-regis', 'sealed-chamber', 'Read the braille in the Sealed Chamber (Route 134, Dive) with Relicanth first and Wailord last in your party to open the three Regi caves.'],
    ['q-rayquaza', 'sky-pillar', 'Catch Rayquaza at the top of Sky Pillar.'],
    ['q-weatherleg', 'terra-cave', 'Watch the TV weather or ask the Weather Institute: Groudon is in Terra Cave and Kyogre in Marine Cave, which move around.'],
    ['q-steven', 'meteor-falls', 'Beat Steven in his cave deep in Meteor Falls (needs Waterfall).'],
    ['q-beldum', 'mossdeep-city', "Pick up Beldum in Steven's house in Mossdeep."],
    ['q-johto', 'littleroot-town', 'See all 202 Hoenn Pokémon, then choose a Johto starter in Professor Birch\'s Lab.'],
    ['q-safari', 'safari-zone', 'Explore the Safari Zone expansion (Johto Pokémon, Pokéblock feeders).'],
    ['q-frontier', 'battle-frontier', 'Earn the silver and gold symbols of the seven Battle Frontier facilities.']]]
];
function renderQuests() {
  const s = cur(), all = QUESTS.flatMap(([, l]) => l), done = all.filter(([id]) => s.checks[`quest:${id}`]).length;
  view.innerHTML = `<div class="card"><b>${done}/${all.length}</b> steps ${bar(done, all.length)}<p class="note">The Team Magma and Team Aqua story, side quests and the post-game, in order.</p></div>
    ${QUESTS.map(([title, list]) => `<h2>${esc(title)}</h2><div class="card">${list.map(([id, loc, text]) => checkRow(`quest:${id}`, s.checks[`quest:${id}`], esc(text), `<a href="#/loc/${loc}">${esc(state.locations[loc]?.name || loc)}</a>`)).join('')}</div>`).join('')}`;
}

LOC_SECTIONS.push(tutorSection);
TOOLS.push({ id: 'once', title: 'One-time Pokémon', desc: 'Legendaries, Snorlax and gift Pokémon you only get one chance at', render: renderOnce },
  { id: 'tutors', title: 'Move tutors', desc: 'All the one-use tutors around Hoenn and the Battle Frontier tutors, and who on your team can learn each move', render: renderTutors },
  { id: 'quests', title: 'Story and post-game', desc: 'Team Magma and Team Aqua, side quests and the post-game, step by step', render: renderQuests });
