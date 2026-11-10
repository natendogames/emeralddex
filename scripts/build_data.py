"""Build Emerald Completion Dex data files from the pret/pokeemerald decompilation.

Usage: python3 -I build_data.py <pokeemerald-dir> <app-data-dir>

Same output shape as the FireRed/LeafGreen app (natendogames/frlgdex), so the app code is shared. Emerald is a
single version, so rows carry no `versions` list.
"""
import json, re, sys, os, glob, collections

SRC, OUT = sys.argv[1], sys.argv[2]
P = lambda *a: os.path.join(SRC, *a)
SOURCE_URL = 'https://github.com/pret/pokeemerald'
read = lambda *a: open(P(*a), encoding='utf-8').read()

# ---------- names ----------
SPECIAL_NAMES = {'NIDORAN_F': 'Nidoran♀', 'NIDORAN_M': 'Nidoran♂', 'MR_MIME': 'Mr. Mime', 'FARFETCHD': "Farfetch'd",
                 'HO_OH': 'Ho-Oh', 'PORYGON2': 'Porygon2'}

def title(s):
    s = s.replace('POKéMON', 'Pokémon').replace('POKé', 'Poké')
    return ' '.join(w if w in ('Pokémon', 'TM', 'HM', 'PP', 'HP', 'S.S.', 'SS', 'TV', 'PC') or re.match(r'^(TM|HM)\d+$', w) else w.capitalize()
                    for w in s.split(' '))

species_const = {}
for m in re.finditer(r'\[SPECIES_(\w+)\]\s*=\s*_\("(.*)"\)', read('src/data/text/species_names.h')):
    if m.group(1) != 'NONE':
        species_const[m.group(1)] = SPECIAL_NAMES.get(m.group(1)) or title(m.group(2))

natdex, hoenn = {}, {}
pdh = read('include/constants/pokedex.h')
nat_enum, hoenn_enum = re.findall(r'enum\s*\{(.*?)\};', pdh, re.S)[:2]
n = 0
for k in re.findall(r'NATIONAL_DEX_(\w+)', nat_enum):
    if k == 'NONE': continue
    n += 1; natdex[k] = n
n = 0
for k in re.findall(r'HOENN_DEX_(\w+)', hoenn_enum):
    if k == 'NONE': continue
    n += 1
    if n <= 202: hoenn[k] = n

def mon(const):
    key = const.replace('SPECIES_', '')
    return {'dex': natdex[key], 'name': species_const[key]}

# TMs and HMs: Emerald names the items after their move (ITEM_TM_ROCK_TOMB is TM39)
tmh = read('include/constants/tms_hms.h')
TM_LIST = re.findall(r'F\((\w+)\)', re.search(r'FOREACH_TM\(F\)(.*?)#define', tmh, re.S).group(1))
HM_LIST = re.findall(r'F\((\w+)\)', re.search(r'FOREACH_HM\(F\)(.*?)#define', tmh, re.S).group(1))
TM_ITEM = {f'ITEM_TM_{mv}': f'TM{i + 1:02d}' for i, mv in enumerate(TM_LIST)}
TM_ITEM.update({f'ITEM_HM_{mv}': f'HM{i + 1:02d}' for i, mv in enumerate(HM_LIST)})

# items.h: name, price, hold effect, pocket, description
desc_src = read('src/data/text/item_descriptions.h')
descs = {k: ''.join(re.findall(r'"(.*?)"', body)) for k, body in re.findall(r'static const u8 (s\w+)\[\]\s*=\s*_\((.*?)\);', desc_src, re.S)}
items = {}
for k, body in re.findall(r'\[(ITEM_\w+)\]\s*=\s*\{(.*?)\n    \},', read('src/data/items.h'), re.S):
    g = lambda pat, d=None: (re.search(pat, body).group(1) if re.search(pat, body) else d)
    items[k] = {'english': g(r'\.name = _\("(.*?)"\)', ''), 'price': int(g(r'\.price = (\d+)', '0')),
                'holdEffect': g(r'\.holdEffect = (\w+)', 'HOLD_EFFECT_NONE'), 'holdEffectParam': int(g(r'\.holdEffectParam = (\d+)', '0')),
                'pocket': g(r'\.pocket = (\w+)', ''), 'description_english': descs.get(g(r'\.description = (\w+)', ''), '')}
ITEM_FIX = {'ITEM_PARALYZE_HEAL': 'Parlyz Heal', 'ITEM_COIN': 'Coins', 'ITEM_SS_TICKET': 'S.S. Ticket',
            'ITEM_DEVON_GOODS': 'Devon Goods', 'ITEM_DEVON_SCOPE': 'Devon Scope', 'ITEM_KINGS_ROCK': "King's Rock",
            'ITEM_BLACK_GLASSES': 'BlackGlasses', 'ITEM_SILVER_POWDER': 'SilverPowder', 'ITEM_TWISTED_SPOON': 'TwistedSpoon', 'ITEM_NEVER_MELT_ICE': 'NeverMeltIce',
            'ITEM_BRIGHT_POWDER': 'BrightPowder', 'ITEM_THUNDER_STONE': 'Thunderstone', 'ITEM_GO_GOGGLES': 'Go-Goggles', 'ITEM_POKEBLOCK_CASE': 'Pokéblock Case',
            'ITEM_UP_GRADE': 'Up-Grade', 'ITEM_EXP_SHARE': 'Exp. Share', 'ITEM_HP_UP': 'HP Up', 'ITEM_PP_UP': 'PP Up',
            'ITEM_PP_MAX': 'PP Max', 'ITEM_X_SPECIAL': 'X Special', 'ITEM_EON_TICKET': 'Eon Ticket', 'ITEM_TM_CASE': 'TM Case',
            'ITEM_DEEP_SEA_TOOTH': 'DeepSeaTooth', 'ITEM_DEEP_SEA_SCALE': 'DeepSeaScale', 'ITEM_SILK_SCARF': 'Silk Scarf', 'ITEM_MACHO_BRACE': 'Macho Brace',
            'ITEM_LAVA_COOKIE': 'Lava Cookie', 'ITEM_POKE_BALL': 'Poké Ball', 'ITEM_POKE_DOLL': 'Poké Doll', 'ITEM_POKE_FLUTE': 'Poké Flute'}

def item_name(c):
    if c in ITEM_FIX: return ITEM_FIX[c]
    if c in TM_ITEM: return TM_ITEM[c]
    if c in items and items[c]['english'] and '?' not in items[c]['english']: return title(items[c]['english'])
    return title(c.replace('ITEM_', '').replace('_', ' '))

move_names = {m.group(1): title(m.group(2)) for m in re.finditer(r'\[MOVE_(\w+)\]\s*=\s*_\("(.*)"\)', read('src/data/text/move_names.h'))}
MOVE_FIX = {'DOUBLE_EDGE': 'Double-Edge', 'SELF_DESTRUCT': 'Selfdestruct', 'SOFT_BOILED': 'Softboiled', 'LOCK_ON': 'Lock-On',
            'WILL_O_WISP': 'Will-O-Wisp'}
for k, v in MOVE_FIX.items():
    if k in move_names: move_names[k] = v
move_types, move_effects, move_power = {}, {}, {}
for k, body in re.findall(r'\[MOVE_(\w+)\]\s*=\s*\{(.*?)\n    \},', read('src/data/battle_moves.h'), re.S):
    m = re.search(r'\.type = TYPE_(\w+)', body)
    if m: move_types[k] = m.group(1).capitalize()
    m = re.search(r'\.power = (\d+)', body)
    if m: move_power[k] = int(m.group(1))
    m = re.search(r'\.effect = EFFECT_(\w+)', body)
    if m: move_effects[k] = m.group(1)

# ---------- pokedex ----------
def species_blocks():
    src = read('src/data/pokemon/species_info.h')
    return {k: body for k, body in re.findall(r'\[SPECIES_(\w+)\]\s*=\s*\{[ \t]*\n(.*?)\n    \},?', src, re.S)}
info = {}
for cur, body in species_blocks().items():
    i = info[cur] = {}
    for k, v in re.findall(r'\.(base\w+)\s*=\s*(\d+)', body): i[k] = int(v)
    m = re.search(r'\.types = \{\s*TYPE_(\w+),\s*TYPE_(\w+)\s*\}', body)
    if m: i['types'] = list(dict.fromkeys(x.capitalize() for x in m.groups()))
    m = re.search(r'\.eggGroups = \{\s*EGG_GROUP_(\w+),\s*EGG_GROUP_(\w+)', body)
    if m: i['eggGroups'] = list(dict.fromkeys(g.replace('_', ' ').title() for g in m.groups()))
    m = re.search(r'\.genderRatio = (.*?),\n', body)
    if m:
        g = m.group(1)
        i['gender'] = 'genderless' if 'GENDERLESS' in g else 'male' if g == 'MON_MALE' else 'female' if g == 'MON_FEMALE' else re.sub(r'PERCENT_FEMALE\((.*)\)', r'\1', g) + '% F'
    m = re.search(r'\.eggCycles = (\d+)', body)
    if m: i['eggCycles'] = int(m.group(1))

evos = collections.defaultdict(list)
for k, body in re.findall(r'\[SPECIES_(\w+)\]\s*=\s*\{(\{.*?\})\}', read('src/data/pokemon/evolution.h'), re.S):
    for method, param, target in re.findall(r'\{EVO_(\w+),\s*(\w+),\s*SPECIES_(\w+)\}', body):
        p = param
        if p.startswith('ITEM_'): p = item_name(p)
        elif p.isdigit(): p = int(p)
        evos[k].append({'method': method.lower().replace('_', '-'), 'param': p, 'into': natdex[target]})

pokedex = []
for key, dex in sorted(natdex.items(), key=lambda kv: kv[1]):
    if dex > 386: continue
    i = info.get(key, {})
    pokedex.append({'dex': dex, 'name': species_const[key], 'types': i.get('types'),
                    **({'hoenn': hoenn[key]} if key in hoenn else {}),
                    'stats': [i.get(k) for k in ('baseHP', 'baseAttack', 'baseDefense', 'baseSpAttack', 'baseSpDefense', 'baseSpeed')],
                    'eggGroups': i.get('eggGroups'), 'gender': i.get('gender'), 'eggCycles': i.get('eggCycles'),
                    'evolutions': evos.get(key, [])})
prevo = {}
for p in pokedex:
    for e in p['evolutions']: prevo[e['into']] = p['dex']
for p in pokedex:
    if p['dex'] in prevo: p['evolvesFrom'] = prevo[p['dex']]

# ---------- type chart ----------
bm = read('src/battle_main.c')
chart = re.search(r'gTypeEffectiveness\[\d+\]\s*=\s*\{(.*?)\};', bm, re.S).group(1)
MUL = {'TYPE_MUL_NO_EFFECT': 0, 'TYPE_MUL_NOT_EFFECTIVE': 0.5, 'TYPE_MUL_SUPER_EFFECTIVE': 2}
type_chart = collections.defaultdict(dict)
for a, d, mul in re.findall(r'TYPE_(\w+), TYPE_(\w+), (TYPE_MUL_\w+)', chart):
    if a in ('FORESIGHT', 'ENDTABLE', 'MYSTERY') or d in ('FORESIGHT', 'ENDTABLE', 'MYSTERY'): continue
    type_chart[a.capitalize()][d.capitalize()] = MUL[mul]

# ---------- locations ----------
mapsec_name = {s['id']: s.get('name') for s in json.load(open(P('src/data/region_map/region_map_sections.json')))['map_sections']}
maps = {}
for f in glob.glob(P('data/maps/*/map.json')):
    m = json.load(open(f)); m['_dir'] = os.path.dirname(f)
    if re.search(r'Unused|Prototype', m['name']): continue
    maps[m['name']] = m
by_const = {m['id']: m for m in maps.values()}

SKIP = {'MAPSEC_DYNAMIC', 'MAPSEC_SECRET_BASE', 'MAPSEC_TRAINER_HILL', 'MAPSEC_NONE'}
LEAGUE_MAPS = re.compile(r'^EverGrandeCity_(\w+sRoom|Hall\d|HallOfFame|PokemonLeague_\w+)$')
# The Battle Frontier and Battle Tents run their own randomised battles; only their gifts and items are listed.
NO_TRAINERS = re.compile(r'^BattleFrontier_|BattleTent|^TrainerHill')

def map_loc(mapname):
    """App location id for a map. Underwater maps belong to the route or place above them; the League is its own place."""
    if LEAGUE_MAPS.match(mapname): return 'pokemon-league'
    if mapname == 'InsideOfTruck': return 'littleroot-town'
    if mapname.startswith('SSTidal'): return 'ss-tidal'
    m = re.match(r'Underwater_Route(\d+)$', mapname)
    if m: return f'route-{m.group(1)}'
    sec = maps[mapname]['region_map_section']
    fixed = {'MAPSEC_UNDERWATER_SEAFLOOR_CAVERN': 'seafloor-cavern', 'MAPSEC_UNDERWATER_SEALED_CHAMBER': 'sealed-chamber',
             'MAPSEC_UNDERWATER_MARINE_CAVE': 'marine-cave', 'MAPSEC_UNDERWATER_SOOTOPOLIS': 'sootopolis-city'}
    if sec in fixed: return fixed[sec]
    return sec.replace('MAPSEC_', '').lower().replace('_', '-')

def map_skipped(mapname):
    return maps[mapname]['region_map_section'] in SKIP and not mapname.startswith('SSTidal')

def area_name(map_name):
    """Human name for a sub-map, e.g. GraniteCave_B1F -> 'B1F', RustboroCity_Gym -> 'Gym'."""
    if map_name.startswith('Underwater_'): return 'Underwater'
    if map_name == 'InsideOfTruck': return 'Moving truck'
    parts = map_name.split('_')
    words = [re.sub(r'(?<=[a-z])(?=[A-Z0-9])|(?<=[0-9])(?=[A-Z][a-z])', ' ', p) for p in parts[1:]] if len(parts) > 1 else []
    s = ' '.join(words).replace('Pokemon', 'Pokémon')
    s = re.sub(r'\b(B?\d) F\b', r'\1F', s)
    # possessives the map names drop: CuttersHouse -> Cutter's House (Stevens -> Steven's)
    s = re.sub(r"\b(Cutter|Cozmo|Berry Master|Brendan|May|Fossil Maniac|Scott|Steven|Wally|Winstrate Family|Captain|Champion|Drake|Glacia|Phoebe|Sidney|Professor Birch|Mr Briney|Lanette|Rydel)s\b(?= (House|Lab|Room|Office|Cottage|Cycles))", r"\1's", s)
    return s or 'Outside'

NAME_FIX = {'ss-tidal': 'S.S. Tidal', 'pokemon-league': 'Pokémon League', 'mt-chimney': 'Mt. Chimney', 'mt-pyre': 'Mt. Pyre',
            'sealed-chamber': 'Sealed Chamber', 'marine-cave': 'Marine Cave', 'seafloor-cavern': 'Seafloor Cavern', 'roaming': 'Roaming Legendary'}
locs = {}
def L(lid):
    if lid not in locs:
        sec = 'MAPSEC_' + lid.upper().replace('-', '_')
        nm = NAME_FIX.get(lid) or title(mapsec_name.get(sec) or lid.replace('-', ' ').upper())
        locs[lid] = {'id': lid, 'name': nm, 'encounters': [], 'items': [], 'gifts': [], '_enc': {}}
    return locs[lid]

# wild encounters. Emerald fills extra tables for Altering Cave that only Mystery Events switch on, so only the first counts.
we = json.load(open(P('src/data/wild_encounters.json')))['wild_encounter_groups'][0]
rates = {f['type']: f for f in we['fields']}
ROD = {'old_rod': 'old-rod', 'good_rod': 'good-rod', 'super_rod': 'super-rod'}
METH = {'land_mons': 'grass', 'water_mons': 'surf', 'rock_smash_mons': 'rock-smash'}
# Parts of a place you can only reach later than your first visit: location id that opens them, and why.
AREA_AFTER = {
    ('route-111', 'grass'): ('lavaridge-town', 'The desert needs the Go-Goggles from your rival in Lavaridge Town.'),
    'MirageTower_1F': ('lavaridge-town', 'In the desert (Go-Goggles from Lavaridge Town). Gone once you take a fossil.'),
    'MirageTower_2F': ('lavaridge-town', 'Needs the Mach Bike.'), 'MirageTower_3F': ('lavaridge-town', 'Needs Rock Smash and the Mach Bike.'),
    'MirageTower_4F': ('lavaridge-town', 'Needs Rock Smash and the Mach Bike.'),
    'SafariZone_Northeast': ('pokemon-league', 'Safari Zone expansion: opens after you enter the Hall of Fame.'),
    'SafariZone_Southeast': ('pokemon-league', 'Safari Zone expansion: opens after you enter the Hall of Fame.'),
    'MeteorFalls_1F_2R': ('ever-grande-city', 'Needs Waterfall.'), 'MeteorFalls_B1F_1R': ('ever-grande-city', 'Needs Waterfall.'),
    'MeteorFalls_B1F_2R': ('ever-grande-city', 'Needs Waterfall.'),
    'AbandonedShip_HiddenFloorCorridors': ('seafloor-cavern', 'Below deck: needs Dive.'),
}
NOTES_FOR = {('route-130', 'grass'): 'Mirage Island only: it appears on random days.'}
for e in we['encounters']:
    if re.search(r'AlteringCave[2-9]|Unused', e['base_label']): continue
    m = by_const.get(e['map'])
    if not m or m['name'] not in maps or map_skipped(m['name']): continue
    lid = map_loc(m['name']); loc = L(lid)
    area = area_name(m['name'])
    under = m['name'].startswith('Underwater_')
    for field, data in e.items():
        if not field.endswith('_mons'): continue
        slots = data['mons']; r = rates[field]['encounter_rates']
        for idx, slot in enumerate(slots):
            method = 'dive' if under and field == 'water_mons' else METH.get(field)
            if field == 'fishing_mons':
                method = next(ROD[k] for k, v in rates[field]['groups'].items() if idx in v)
            sp = slot['species'].replace('SPECIES_', '')
            key = (area, method, sp, m['name'])
            agg = loc['_enc'].setdefault(key, {'rate': 0, 'min': 999, 'max': 0})
            agg['rate'] += r[idx]; agg['min'] = min(agg['min'], slot['min_level']); agg['max'] = max(agg['max'], slot['max_level'])

# item balls
balls = {}
cur = None
for line in open(P('data/scripts/item_ball_scripts.inc')):
    m = re.match(r'(\w+)::', line)
    if m: cur = m.group(1)
    m = re.match(r'\s*finditem (ITEM_\w+)(?:,\s*(\d+))?', line)
    if m and cur: balls[cur] = (m.group(1), int(m.group(2) or 1))

item_flags = {}  # checklist key -> the save flag set when you pick it up (for save file import)
item_pos = {}  # (location id, item id) -> where it sits on the map, for the reachability walk
def add_item(loc, name, qty, hidden, where, ident, flag=None, pos=None):
    loc['items'].append({'id': ident, 'name': name + (f' ×{qty}' if qty > 1 else ''), 'hidden': hidden, 'where': where})
    if pos: item_pos[(loc['id'], ident)] = pos
    if flag: item_flags[f"{loc['id']}:item:{ident}"] = flag

seen_ids = collections.Counter()
def uid(loc, base):
    base = re.sub(r'[^a-z0-9]+', '-', base.lower()).strip('-')
    seen_ids[(loc['id'], base)] += 1
    c = seen_ids[(loc['id'], base)]
    return base if c == 1 else f'{base}-{c}'

for name in sorted(maps):
    m = maps[name]
    if map_skipped(name): continue
    loc = L(map_loc(name)); area = area_name(name)
    for ev in m.get('object_events') or []:
        if ev.get('script') in balls:
            it, q = balls[ev['script']]
            add_item(loc, item_name(it), q, False, area, uid(loc, f'{area}-{item_name(it)}'), ev.get('flag'), (name, ev['x'], ev['y'], ev.get('elevation') or 0, False))
    for ev in m.get('bg_events') or []:
        if ev.get('type') == 'hidden_item':
            add_item(loc, item_name(ev['item']), int(ev.get('quantity') or 1), True,
                     area + (' (underfoot)' if ev.get('underfoot') else ''), uid(loc, f'hidden-{area}-{item_name(ev["item"])}'), ev.get('flag'),
                     (name, ev['x'], ev['y'], ev.get('elevation') or 0, bool(ev.get('underfoot'))))

# NPC gifts, static encounters, trades
trades = {}
for k, body in re.findall(r'\[(INGAME_TRADE_\w+)\]\s*=\s*\{(.*?)\n    \}', read('src/data/trade.h'), re.S):
    trades[k] = (re.search(r'\.species = SPECIES_(\w+)', body).group(1), re.search(r'\.requestedSpecies = SPECIES_(\w+)', body).group(1),
                 re.search(r'\.nickname = _\("(.*?)"\)', body).group(1))

LEADERS = {'RustboroCity_Gym': 'Roxanne', 'DewfordTown_Gym': 'Brawly', 'MauvilleCity_Gym': 'Wattson', 'LavaridgeTown_Gym_1F': 'Flannery',
           'PetalburgCity_Gym': 'Norman', 'FortreeCity_Gym': 'Winona', 'MossdeepCity_Gym': 'Tate and Liza', 'SootopolisCity_Gym_1F': 'Juan'}
def who(label, mapname):
    if mapname in LEADERS: return LEADERS[mapname] + ' (after winning)'
    s = label.split('EventScript_')[-1] if 'EventScript_' in label else label
    s = re.sub(r'(?<=[a-z])(?=[A-Z0-9])', ' ', s)
    return s

gifts = collections.OrderedDict()  # (lid, kind, name, area, from, species?) -> True
statics = collections.OrderedDict()
for name in sorted(maps):
    m = maps[name]
    if map_skipped(name) or name == 'Route110_TrickHouseEntrance': continue  # the entrance only re-offers Trick House prizes your bag had no room for
    f = os.path.join(m['_dir'], 'scripts.inc')
    if not os.path.exists(f): continue
    lid = map_loc(name); area = area_name(name)
    label = ''
    for line in open(f, encoding='utf-8'):
        lm = re.match(r'(\w+)::', line)
        if lm: label = lm.group(1); continue
        s = line.strip()
        gm = re.match(r'(?:giveitem|giveitem_msg)\s+(ITEM_\w+)(?:,\s*(\d+))?', s)
        if gm:
            it, q = gm.group(1), int(gm.group(2) or 1)
            nm = item_name(it) + (f' ×{q}' if q > 1 else '')
            gifts.setdefault((lid, 'item', nm, area, who(label, name)), True); continue
        mm = re.match(r'givemon SPECIES_(\w+), (\d+)', s)
        if mm:
            gifts.setdefault((lid, 'mon', f'{species_const[mm.group(1)]} (Lv {mm.group(2)})', area, who(label, name), mm.group(1)), True); continue
        mm = re.match(r'giveegg SPECIES_(\w+)', s)
        if mm:
            gifts.setdefault((lid, 'mon', f'{species_const[mm.group(1)]} Egg', area, who(label, name), mm.group(1)), True); continue
        mm = re.match(r'(?:setwildbattle|seteventmon) SPECIES_(\w+), (\d+)', s)
        if mm:
            statics.setdefault((lid, area, mm.group(1), mm.group(2)), True); continue
        mm = re.match(r'setvar VAR_0x8008, (INGAME_TRADE_\w+)', s)
        if mm:
            get, give, nick = trades[mm.group(1)]
            gifts.setdefault((lid, 'trade', f'Trade: give {species_const[give]}, get {species_const[get]} ("{title(nick)}")', area, who(label, name), get), True)
# Kecleon hiding on Routes 119 and 120 share one script in data/scripts/kecleon.inc
for lid in ('route-119', 'route-120'):
    statics.setdefault((lid, 'Outside', 'KECLEON', '30'), True)

EXTRA_GIFTS = [
    ('route-101', 'mon', 'Starter Pokémon (Treecko, Torchic or Mudkip)', 'Outside', "Professor Birch's bag", None),
    ('littleroot-town', 'item', 'Pokédex', "Professor Birch's Lab", 'Professor Birch (after your first rival battle)', None),
    ('littleroot-town', 'item', 'Potion (in your PC)', 'Your house 2F', 'Your bedroom PC', None),
    # gifts from shared scripts (data/scripts/*.inc), which the map pass doesn't see
    ('littleroot-town', 'item', 'Running Shoes', 'Outside', 'Mom (as you leave with the Pokédex)', None),
    ('littleroot-town', 'item', 'Amulet Coin', 'Your house 1F', "Mom (once you have Dad's badge, the fifth)", None),
    ('littleroot-town', 'item', 'S.S. Ticket', 'Your house 1F', 'Dad (after you enter the Hall of Fame)', None),
    ('lilycove-city', 'item', 'Pokéblock Case', 'Contest Lobby', 'Contest receptionist', None),
    ('route-111', 'item', 'TM43', 'Outside', 'Boy by the Secret Base tree', None),
    ('rustboro-city', 'item', 'PokéNav', 'Devon Corp 3F', 'Mr. Stone (return the Devon Goods)', None),
]
for k in EXTRA_GIFTS: gifts[k] = True
FROM_FIX = {'Give Red Scarf': 'Fan Club chairman (lead Pokémon with high Cool)', 'Give Blue Scarf': 'Fan Club chairman (lead Pokémon with high Beauty)',
    'Give Pink Scarf': 'Fan Club chairman (lead Pokémon with high Cute)', 'Give Green Scarf': 'Fan Club chairman (lead Pokémon with high Smart)',
    'Give Yellow Scarf': 'Fan Club chairman (lead Pokémon with high Tough)', 'Give Soothe Bell': 'Woman (if your lead Pokémon is very friendly)',
    **{f'Give {b} Berry': f"Berry Master's wife (tell her \"{p}\")" for b, p in (('Spelon', 'GREAT BATTLE'), ('Pamtre', 'CHALLENGE CONTEST'),
       ('Watmel', 'OVERWHELMING LATIAS'), ('Durin', 'COOL LATIOS'), ('Belue', 'SUPER HUSTLE'))},
    'Give Figy Berry': 'Kiri (daily berry)', 'Give Iapapa Berry': 'Kiri (daily berry)', 'Give Waterfall': 'Wallace (after Rayquaza calms Groudon and Kyogre)',
'Accept Trade': 'Trader (Harbor Mail for the Coin Case)', 'Attract Giver': 'Woman', 'Big Seedot': 'Man (show him a big Seedot)', 'Brick Break Black Belt': 'Black Belt',
    'Buy Soda Pop': 'Seashore House', 'Check Gold Symbols': 'Battle Frontier (all gold symbols)', 'Check Silver Symbols': 'Battle Frontier (all silver symbols)',
    'Claw Fossil': 'Top of Mirage Tower (choose one)', 'Root Fossil': 'Top of Mirage Tower (choose one)', 'Give Claw Fossil': 'The fossil you left behind (post-game)',
    'Give Root Fossil': 'The fossil you left behind (post-game)', 'Clear Tunnel Scene': "Wanda's boyfriend (once the tunnel is open)",
    'Completed New Mauville': 'Wattson (after you fix New Mauville)', 'Defeated Trainers': 'Seashore House owner (beat the three trainers)',
    'Devon Researcher Post Battle': 'Devon researcher (after you beat the Aqua Grunt)', 'Egg Woman': 'Old woman by the hot springs',
    'Expert F': 'Woman', 'Explain Pokemon Mart': 'Poké Mart employee', 'Familiar Grunt': 'Aqua Grunt (after you beat him)',
    'Get Acro Bike': 'Rydel (pick the Acro Bike; swap any time)', 'Get Mach Bike': 'Rydel (pick the Mach Bike; swap any time)',
    'Give Beldum': "Steven's house (after you enter the Hall of Fame)", 'Give Chikorita': 'Professor Birch (complete the Hoenn Pokédex; choose one)',
    'Give Cyndaquil': 'Professor Birch (complete the Hoenn Pokédex; choose one)', 'Give Totodile': 'Professor Birch (complete the Hoenn Pokédex; choose one)',
    'Give Exp Share': 'Mr. Stone (after you deliver the letter)', 'Give Fly HM': 'Your rival (after battling)', 'Give HMSurf': "Wally's father (after you beat Norman)",
    'Give Old Rod': 'Fisherman', 'Receive Good Rod': 'Fisherman', 'Super Rod Fisherman': 'Fisherman', 'Give Waterfall': 'Wallace', 'Steven Gives Dive': 'Steven',
    'Steven Give Decon Scope': 'Steven (after the Kecleon on the bridge)', 'May Give Go Goggles': 'Your rival', 'May Give Poke Balls': 'Your rival',
    'Receive Castform': 'Weather Institute scientist (after you beat Shelly)', 'Receive Lileep': 'Devon scientist (revives the Root Fossil)',
    'Receive Anorith': 'Devon scientist (revives the Claw Fossil)', 'Return Goods': 'Devon employee (return the Devon Goods)', 'Meet President': 'Mr. Stone',
    'Give Itemfinder': 'Your rival', 'Give Wailmer Pail': 'Flower shop owner', 'Give Repeat Ball': 'Devon researcher', 'Give Return': 'Woman (if your lead Pokémon is friendly)',
    'Give Frustration': 'Woman (if your lead Pokémon is unfriendly)', 'Wingull Returned': 'Girl (after her Wingull delivers the mail)',
    'Player Has Meteorite': 'Professor Cozmo (return the Meteorite)', 'Meteorite Machine': 'The machine at the summit (after Maxie leaves)',
    'Team Aqua Exits': 'Old couple at the summit (after Team Aqua leaves)', 'Shoal Salt 1': 'On the ground at low tide', 'Shoal Salt 3': 'On the ground at low tide',
    'Shoal Salt 4': 'On the ground at low tide', 'Shoal Shell 1': 'On the ground at low tide', 'Shell Bell Expert': 'Old man (bring 4 Shoal Salt and 4 Shoal Shells)',
    'Grunt': 'Aqua Grunt (after you beat him)', 'Victoria': 'Victoria (after you beat the Winstrate family)', 'Lava Cookie Lady': 'Lava Cookie seller (₽200)',
    'Wattson': 'Wattson', 'Hiker': 'Hiker', 'Steven': 'Steven', 'Trader': 'Trader', 'Deep Sea Tooth': 'Captain Stern (choose one; swap later)',
    'Deep Sea Scale': 'Captain Stern (choose one; swap later)', 'Fossil Maniacs Brother': "Fossil Maniac's brother", 'Kings Rock Boy': 'Boy (trade a Big Pearl)',
    'Cleanse Tag Woman': 'Old woman', 'Sun Stone Man': 'Scientist', 'Sludge Bomb Man': 'Man', 'Snatch Giver': 'Man in the cabin', 'Torment Giver': 'Man',
    'Roar Gentleman': 'Gentleman', 'Hidden Power Giver': 'Old woman (guess the coin)', 'Giga Drain Girl': 'Girl (if your lead knows a Grass move)',
    'Soft Sand Girl': 'Girl', 'White Herb Florist': 'Florist', 'Rock Smash Dude': 'Rock Smash Guy', 'Glass Worker': 'Glass Workshop (trade volcanic ash)'}
GIFT_AFTER = {'CHIKORITA': 'pokemon-league', 'CYNDAQUIL': 'pokemon-league', 'TOTODILE': 'pokemon-league', 'BELDUM': 'pokemon-league',
              'LILEEP': 'mirage-tower', 'ANORITH': 'mirage-tower'}
GMETHOD = {'mon': 'gift', 'trade': 'trade'}
seen_gift = set()
for k in gifts:
    lid, kind, nm, area, frm = k[:5]
    if (lid, nm, area) in seen_gift: continue
    seen_gift.add((lid, nm, area))
    loc = L(lid)
    frm = FROM_FIX.get(frm) or re.sub(r'^(Give|Receive|Get) .*', 'Gift', frm)
    loc['gifts'].append({'id': uid(loc, f'{kind}-{area}-{nm}'), 'name': nm, 'from': frm, 'where': area})
    if kind in GMETHOD and len(k) > 5 and k[5]:
        lv = re.search(r'Lv (\d+)', nm)
        lvl = lv.group(1) if lv else '5' if 'Egg' in nm else None  # eggs hatch at Lv 5
        loc['encounters'].append({**mon('SPECIES_' + k[5]), 'method': GMETHOD[kind], 'area': area,
                                  **({'levels': lvl} if lvl else {}), 'notes': nm + ' · ' + frm,
                                  **({'after': GIFT_AFTER[k[5]]} if k[5] in GIFT_AFTER else {})})
for sp in ('TREECKO', 'TORCHIC', 'MUDKIP'):
    locs['route-101']['encounters'].append({**mon('SPECIES_' + sp), 'method': 'gift', 'levels': '5', 'area': 'Outside',
                                            'notes': "Starter: choose one from Professor Birch's bag. Get the other two by trading."})
STATIC_AFTER = {('route-119', 'KECLEON'): ('route-120', 'Invisible until you have the Devon Scope from Steven on Route 120.'),
               ('route-120', 'KECLEON'): ('route-120', 'Invisible until you have the Devon Scope from Steven on the bridge.'),
               'RAYQUAZA': ('sootopolis-city', 'Asleep at the top until the story wakes it; back at the top and catchable once it has calmed Groudon and Kyogre in Sootopolis. Needs the Mach Bike. Save first.')}
for (lid, area, sp, lvl) in statics:
    a = STATIC_AFTER.get((lid, sp)) or STATIC_AFTER.get(sp)
    locs[lid]['encounters'].append({**mon('SPECIES_' + sp), 'method': 'static', 'levels': lvl, 'area': area, 'notes': a[1] if a else 'One chance: save first',
                                    **({'after': a[0]} if a else {})})
# Feebas lives on six random water tiles of Route 119 (any rod); the tiles change when the trendy phrase changes.
locs['route-119']['encounters'].append({**mon('SPECIES_FEEBAS'), 'method': 'old-rod', 'levels': '20-25', 'area': 'Outside', 'rate': '50%',
                                        'notes': 'Feebas: only on 6 random water tiles along the river. Fish each tile a few times with any rod.'})

# collapse wild encounters
for loc in locs.values():
    wild = []
    for (area, method, sp, mapname), a in loc.pop('_enc').items():
        lv = str(a['min']) if a['min'] == a['max'] else f"{a['min']}-{a['max']}"
        row = {**mon('SPECIES_' + sp), 'method': method, 'levels': lv, 'rate': f"{a['rate']}%", 'area': area}
        gate = AREA_AFTER.get(mapname) or AREA_AFTER.get((loc['id'], method))
        if gate:
            row['after'] = gate[0]
            if gate[1]: row['notes'] = gate[1]
        if NOTES_FOR.get((loc['id'], method)): row['notes'] = NOTES_FOR[(loc['id'], method)]
        wild.append(row)
    order = ['grass', 'surf', 'old-rod', 'good-rod', 'super-rod', 'rock-smash', 'dive']
    wild.sort(key=lambda e: (e['area'], order.index(e['method']), -int(e['rate'][:-1]), e['dex']))
    loc['encounters'] = wild + loc['encounters']

# ---------- trainers ----------
tsrc = read('src/data/trainers.h')
psrc = read('src/data/trainer_parties.h')
parties = {k: body for k, body in re.findall(r'static const struct \w+ (sParty_\w+)\[\] = \{\n(.*?)\n\};', psrc, re.S)}
tdefs = {k: body for k, body in re.findall(r"\[(TRAINER_\w+)\] =\s*\{(.*?)\n    \},", tsrc, re.S)}
class_names = {}
for line in open(P('src/data/text/trainer_class_names.h'), encoding='utf-8'):
    m = re.match(r'\s*\[(TRAINER_CLASS_\w+)\]\s*=\s*_\("(.*)"\)', line)
    if m: class_names[m.group(1)] = m.group(2)
CLASS_FIX = {'TRAINER_CLASS_PKMN_BREEDER': 'Pokémon Breeder', 'TRAINER_CLASS_PKMN_RANGER': 'Pokémon Ranger', 'TRAINER_CLASS_COOLTRAINER': 'Cool Trainer',
             'TRAINER_CLASS_ELITE_FOUR': 'Elite Four', 'TRAINER_CLASS_SWIMMER_M': 'Swimmer', 'TRAINER_CLASS_SWIMMER_F': 'Swimmer',
             'TRAINER_CLASS_POKEMANIAC': 'Poké Maniac', 'TRAINER_CLASS_LEADER': 'Leader', 'TRAINER_CLASS_CHAMPION': 'Champion',
             'TRAINER_CLASS_RIVAL': 'Rival', 'TRAINER_CLASS_TEAM_AQUA': 'Team Aqua', 'TRAINER_CLASS_TEAM_MAGMA': 'Team Magma',
             'TRAINER_CLASS_AQUA_ADMIN': 'Aqua Admin', 'TRAINER_CLASS_MAGMA_ADMIN': 'Magma Admin', 'TRAINER_CLASS_AQUA_LEADER': 'Aqua Leader',
             'TRAINER_CLASS_MAGMA_LEADER': 'Magma Leader', 'TRAINER_CLASS_PKMN_TRAINER_3': 'Pokémon Trainer', 'TRAINER_CLASS_SIS_AND_BRO': 'Sis and Bro',
             'TRAINER_CLASS_SR_AND_JR': 'Sr. and Jr.', 'TRAINER_CLASS_INTERVIEWER': 'Interviewer', 'TRAINER_CLASS_HEX_MANIAC': 'Hex Maniac',
             'TRAINER_CLASS_RICH_BOY': 'Rich Boy', 'TRAINER_CLASS_BUG_MANIAC': 'Bug Maniac', 'TRAINER_CLASS_RUIN_MANIAC': 'Ruin Maniac',
             'TRAINER_CLASS_PARASOL_LADY': 'Parasol Lady', 'TRAINER_CLASS_NINJA_BOY': 'Ninja Boy', 'TRAINER_CLASS_BATTLE_GIRL': 'Battle Girl',
             'TRAINER_CLASS_TRIATHLETE': 'Triathlete', 'TRAINER_CLASS_DRAGON_TAMER': 'Dragon Tamer', 'TRAINER_CLASS_BIRD_KEEPER': 'Bird Keeper',
             'TRAINER_CLASS_BUG_CATCHER': 'Bug Catcher', 'TRAINER_CLASS_SCHOOL_KID': 'School Kid', 'TRAINER_CLASS_YOUNG_COUPLE': 'Young Couple',
             'TRAINER_CLASS_OLD_COUPLE': 'Old Couple', 'TRAINER_CLASS_LADY': 'Lady', 'TRAINER_CLASS_TWINS': 'Twins', 'TRAINER_CLASS_PSYCHIC': 'Psychic'}
money_table = {c: int(v) for c, v in re.findall(r'\{(TRAINER_CLASS_\w+), (\d+)\}', bm)}

learnset_ptr = dict(re.findall(r'\[SPECIES_(\w+)\] = (s\w+LevelUpLearnset)', read('src/data/pokemon/level_up_learnset_pointers.h')))
learnsets = {k: [(int(l), mv) for l, mv in re.findall(r'LEVEL_UP_MOVE\(\s*(\d+),\s*MOVE_(\w+)\)', body)]
             for k, body in re.findall(r'static const u16 (s\w+LevelUpLearnset)\[\] = \{(.*?)\};', read('src/data/pokemon/level_up_learnsets.h'), re.S)}

def default_moves(sp, lvl):
    """The game fills a trainer Pokémon's moves with the last four it learns by level up at or below its level."""
    moves = []
    for l, mv in learnsets[learnset_ptr[sp]]:
        if l > lvl: break
        if mv in moves: continue
        if len(moves) == 4: moves.pop(0)
        moves.append(mv)
    return moves

def move_info(x):
    return {'name': move_names[x], 'type': move_types.get(x), **({'power': move_power[x]} if move_power.get(x) else {})}

def trainer_party(tconst):
    t = tdefs[tconst]
    pk = re.search(r'\.party = \w+\((sParty_\w+)\)', t).group(1)
    mons = []
    for body in re.findall(r'\{(.*?)\n    \}', parties[pk], re.S):
        sp = re.search(r'\.species = SPECIES_(\w+)', body)
        if not sp: continue
        lvl = int(re.search(r'\.lvl = (\d+)', body).group(1))
        mv = re.search(r'\.moves = \{(.*?)\}', body)
        held = re.search(r'\.heldItem = (ITEM_\w+)', body)
        moves = [x.strip().replace('MOVE_', '') for x in mv.group(1).split(',')] if mv else default_moves(sp.group(1), lvl)
        iv = re.search(r'\.iv = (\d+)', body)
        mons.append({**mon('SPECIES_' + sp.group(1)), 'level': lvl, 'iv': int(iv.group(1)) * 31 // 255 if iv else 0,
                     'moves': [move_info(x) for x in moves if x and x != 'NONE'],
                     **({'item': item_name(held.group(1))} if held and held.group(1) != 'ITEM_NONE' else {})})
    return mons

def trainer_record(tconst):
    t = tdefs[tconst]
    cls = re.search(r'\.trainerClass = (TRAINER_CLASS_\w+)', t).group(1)
    name = re.search(r'\.trainerName = _\("(.*?)"\)', t).group(1)
    double = '.doubleBattle = TRUE' in t
    im = re.search(r'\.items = \{(.*?)\}', t)
    used = [item_name(i) for i in re.findall(r'(ITEM_\w+)', im.group(1) if im else '') if i != 'ITEM_NONE']
    pty = trainer_party(tconst)
    prize = 4 * pty[-1]['level'] * money_table.get(cls, 1) * (2 if double else 1)
    rec = {'class': CLASS_FIX.get(cls) or title(class_names.get(cls, cls.replace('TRAINER_CLASS_', '').replace('_', ' '))),
           'name': title(re.sub(r'\s*&\s*', ' & ', name)), 'prize': prize, 'party': pty}
    if double: rec['double'] = True
    if used: rec['uses'] = [f'{n} ×{c}' if c > 1 else n for n, c in collections.Counter(used).items()]
    return rec

# Scan scripts: label -> lines, and which trainer battles each label starts.
labels, label_map = {}, {}
for f in glob.glob(P('data/maps/*/scripts.inc')):
    mapname = os.path.basename(os.path.dirname(f))
    cur_label = None
    for line in open(f, encoding='utf-8'):
        lm = re.match(r'(\w+)::', line)
        if lm:
            cur_label = lm.group(1); labels[cur_label] = []
            label_map[cur_label] = mapname
            continue
        if cur_label: labels[cur_label].append(line.strip())
# Gabby & Ty's battles live in a shared script; they first battle you on Route 111
# (later rounds move between Routes 111, 118 and 120 and count as rematches).
cur_label = None
for line in open(P('data/scripts/gabby_and_ty.inc'), encoding='utf-8'):
    lm = re.match(r'(\w+)::', line)
    if lm:
        cur_label = lm.group(1); labels[cur_label] = []; label_map[cur_label] = 'Route111'
        continue
    if cur_label: labels[cur_label].append(line.strip())

# trainerbattle_single/double/no_intro TRAINER_X, ...  and  trainerbattle TRAINER_BATTLE_<kind>, TRAINER_X, ...
BATTLE_RE = re.compile(r'trainerbattle(?:_(single|double|no_intro)\s+|\s+TRAINER_BATTLE_(\w+),\s*)(TRAINER_\w+)(.*)')
BATTLE_KINDS = {'CONTINUE_SCRIPT', 'CONTINUE_SCRIPT_NO_MUSIC', 'SINGLE', 'DOUBLE', 'CONTINUE_SCRIPT_DOUBLE', 'SET_TRAINER_A', 'SET_TRAINER_B', 'SINGLE_NO_INTRO_TEXT'}
BADGE_NAMES = ['Stone', 'Knuckle', 'Dynamo', 'Heat', 'Balance', 'Feather', 'Mind', 'Rain']
def label_rewards(label, depth=0, seen=None):
    """Items handed over in a trainer's script and the scripts it jumps to (gym TMs and badges)."""
    seen = seen if seen is not None else set()
    if label in seen or label not in labels or depth > 2: return []
    seen.add(label)
    out = []
    for s in labels[label]:
        gm = re.match(r'(?:giveitem|giveitem_msg)\s+(ITEM_\w+)(?:,\s*(\d+))?', s)
        if gm: out.append(item_name(gm.group(1)) + (f' ×{gm.group(2)}' if gm.group(2) and gm.group(2) != '1' else ''))
        bm_ = re.match(r'setflag FLAG_BADGE0(\d)_GET', s)
        if bm_: out.append(BADGE_NAMES[int(bm_.group(1)) - 1] + ' Badge')
        for target in re.findall(r'(?:goto|call)(?:_if\w*)?\s+(?:[^,]+,\s*)*?(\w+_EventScript_\w+)', s):
            out += label_rewards(target, depth + 1, seen)
        bt = BATTLE_RE.match(s)
        if bt:
            for target in re.findall(r'(\w+_EventScript_\w+)', bt.group(4)):
                out += label_rewards(target, depth + 1, seen)
    return out

STARTERS = ('TREECKO', 'TORCHIC', 'MUDKIP')
RIVAL_RE = re.compile(r'TRAINER_(?:MAY|BRENDAN)_(\w+)_(TREECKO|TORCHIC|MUDKIP)$')  # suffix = the starter YOU picked
def is_rematch(c):
    """Later Match Call rematches (TRAINER_ROSE_2..5, TRAINER_WALLY_VR_2..5) aren't first battles."""
    m = re.match(r'(TRAINER_\w+?)_([2-9])$', c)
    return bool(m and (m.group(1) + '_1') in battled)  # TRAINER_MIKE_2 is a first battle: MIKE_1 is never used
battled = {b.group(3) for ls in labels.values() for x in ls for b in [BATTLE_RE.match(x)] if b}
WALK = {'Route101': 'N', 'Route103': 'N', 'Route102': 'W', 'Route104': 'N', 'Route116': 'E', 'Route105': 'S', 'Route106': 'E',
        'Route107': 'E', 'Route108': 'E', 'Route109': 'N', 'Route110': 'N', 'Route117': 'W', 'Route111': 'N', 'Route112': 'W',
        'Route113': 'W', 'Route114': 'N', 'Route115': 'N', 'Route118': 'E', 'Route119': 'N', 'Route120': 'S', 'Route121': 'E',
        'Route122': 'S', 'Route123': 'W', 'Route124': 'E', 'Route125': 'E', 'Route126': 'S', 'Route127': 'S', 'Route128': 'E',
        'Route129': 'W', 'Route130': 'W', 'Route131': 'W', 'Route132': 'W', 'Route133': 'W', 'Route134': 'W', 'PetalburgWoods': 'N',
        'JaggedPass': 'N'}
AREA_ORDER = {'pokemon-league': ['Sidneys Room', 'Phoebes Room', 'Glacias Room', 'Drakes Room', 'Champions Room']}
# Battles that happen later in the story than your first visit to the location.
STAGE = {'PetalburgCity_Gym': 'lavaridge-town', 'MeteorFalls_StevensCave': 'pokemon-league'}

found_battles = collections.OrderedDict()  # (map, key) -> info
for label, lines in labels.items():
    mapname = label_map.get(label)
    if not mapname or mapname not in maps or map_skipped(mapname) or NO_TRAINERS.search(mapname): continue
    for s in lines:
        bt = BATTLE_RE.match(s)
        if not bt or (bt.group(1) is None and bt.group(2) not in BATTLE_KINDS): continue
        tconst = bt.group(3)
        if tconst not in tdefs or is_rematch(tconst): continue
        rm = RIVAL_RE.match(tconst)
        key = 'RIVAL_' + rm.group(1) if rm else tconst
        if mapname == 'Route104' and key == 'RIVAL_RUSTBORO': continue  # the same battle, if you meet your rival on the way out of Rustboro
        b = found_battles.setdefault((mapname, key), {'consts': {}, 'labels': [], 'rival': bool(rm), 'multi': bt.group(2) in ('SET_TRAINER_A', 'SET_TRAINER_B')})
        if rm:
            if 'MAY' in tconst or rm.group(2) not in b['consts']: b['consts'][rm.group(2)] = tconst
        else:
            b['consts'][None] = tconst
        b['labels'].append(label)

def position(mapname, lbls):
    m = maps[mapname]
    for ev in (m.get('object_events') or []) + (m.get('coord_events') or []):
        if ev.get('script') in lbls: return ev['x'], ev['y']
    for ev in (m.get('object_events') or []) + (m.get('coord_events') or []):
        body = ' '.join(labels.get(ev.get('script'), []))
        if any(l in body for l in lbls): return ev['x'], ev['y']
    return None

ENTRY = {}
layout_info = {l['id']: l for l in json.load(open(P('data/layouts/layouts.json')))['layouts'] if l.get('id')}
_dist = {}
def walk_dist(mapname):
    """Walking distance from where you come in, on the map's own tile grid (collision and elevation from map.bin)."""
    if mapname in _dist: return _dist[mapname]
    m = maps[mapname]; lay = layout_info.get(m['layout'])
    if not lay: _dist[mapname] = None; return None
    w, h = lay['width'], lay['height']
    raw = open(P(lay['blockdata_filepath']), 'rb').read()
    cells = [int.from_bytes(raw[i:i + 2], 'little') for i in range(0, len(raw), 2)]
    col = lambda x, y: (cells[y * w + x] >> 10) & 3
    elev = lambda x, y: cells[y * w + x] >> 12
    d = WALK.get(mapname)
    if d:
        edge = {'N': [(x, h - 1) for x in range(w)], 'S': [(x, 0) for x in range(w)], 'E': [(0, y) for y in range(h)], 'W': [(w - 1, y) for y in range(h)]}[d]
    else:
        warps = m.get('warp_events') or []
        def other(wp):
            dm = by_const.get(wp['dest_map'])
            return dm and dm['name'] in maps and map_loc(dm['name']) != map_loc(mapname)
        outside = [wp for wp in warps if other(wp)] or warps
        edge = [ENTRY[mapname]] if mapname in ENTRY else [max(((wp['x'], wp['y']) for wp in outside), key=lambda p: p[1])] if outside else []
    start = [(x, y) for x, y in edge if 0 <= x < w and 0 <= y < h and col(x, y) == 0 and elev(x, y) not in (1,)] or [(x, y) for x, y in edge if 0 <= x < w and 0 <= y < h and col(x, y) == 0]
    dist = {p: 0 for p in start}
    q = collections.deque(start)
    while q:
        x, y = q.popleft()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if not (0 <= nx < w and 0 <= ny < h) or (nx, ny) in dist or col(nx, ny): continue
            e1, e2 = elev(x, y), elev(nx, ny)
            if e1 != e2 and e1 not in (0, 15) and e2 not in (0, 15): continue
            dist[(nx, ny)] = dist[(x, y)] + 1; q.append((nx, ny))
    _dist[mapname] = dist
    return dist

def sort_key(mapname, pos):
    if pos is None: return (1, 0, 0)
    dist = walk_dist(mapname)
    if dist:
        x, y = pos
        near = [dist[p] for p in ((x, y), (x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)) if p in dist]
        if near: return (0, min(near), 0)
    x, y = pos
    d = WALK.get(mapname, 'N')
    return (0, {'N': -y, 'S': y, 'E': x, 'W': -x}[d], {'N': x, 'S': x, 'E': y, 'W': y}[d])

def area_sort(lid, area):
    order = AREA_ORDER.get(lid)
    if order and area in order: return (0, order.index(area), '')
    if area == 'Outside': return (0, -1, '')
    m = re.match(r'(B?)(\d+)F', area)
    if m: return (1, (100 if m.group(1) else 0) + int(m.group(2)), area)
    return (2, 0, area)

def tid_of(key):
    k = key.replace('TRAINER_', '')
    if key in tdefs and re.search(r'_1$', key) and (key[:-2] + '_2') in tdefs: k = k[:-2]  # ROXANNE_1 -> roxanne
    return re.sub(r'[^a-z0-9]+', '-', k.lower()).strip('-')

per_loc = collections.defaultdict(list)
trainer_consts = {}
rival_mismatch = []
for (mapname, key), b in found_battles.items():
    lid = map_loc(mapname); area = area_name(mapname)
    first = next(iter(b['consts'].values()))
    rec = trainer_record(first)
    if b['rival']:
        rec.pop('party'); rec['name'] = 'May or Brendan'; rec['class'] = 'Rival'
        rec['byStarter'] = {mine.capitalize(): trainer_party(c) for mine, c in sorted(b['consts'].items(), key=lambda kv: STARTERS.index(kv[0]))}
        # Brendan (your rival if you play as May) sometimes has a different team member
        bren = {mine.capitalize(): trainer_party(c.replace('MAY', 'BRENDAN')) for mine, c in b['consts'].items() if c.replace('MAY', 'BRENDAN') in tdefs}
        if any(bren[k] != rec['byStarter'][k] for k in bren):
            rec['byStarterBrendan'] = {k: bren[k] for k in rec['byStarter'] if k in bren}
            rival_mismatch.append(key)
        trainer_consts_extra = [c.replace('MAY', 'BRENDAN') for c in b['consts'].values() if c.replace('MAY', 'BRENDAN') in tdefs]
        rec['prize'] = 4 * max(p[-1]['level'] for p in rec['byStarter'].values()) * money_table.get('TRAINER_CLASS_RIVAL', 15)
    if rec['class'] == 'Rival' and not b['rival']: rec['class'] = 'Pokémon Trainer'  # Wally uses the rival class
    if b['multi']: rec['note'] = 'Multi battle: Steven fights alongside you.'
    rewards = list(dict.fromkeys(r for l in b['labels'] for r in label_rewards(l)))
    if rewards: rec['rewards'] = rewards
    rec['id'] = tid_of(key)
    trainer_consts[(lid, rec['id'])] = list(b['consts'].values()) + (trainer_consts_extra if b['rival'] else [])
    rec['area'] = area
    st = STAGE.get(mapname)
    if st: rec['stage'] = st
    leader_last = rec['class'] in ('Leader', 'Elite Four', 'Champion')
    per_loc[lid].append((area_sort(lid, area), leader_last, sort_key(mapname, position(mapname, b['labels'])), rec))
print('rival parties that differ between May and Brendan:', rival_mismatch)
for lid, lst in per_loc.items():
    lst.sort(key=lambda t: t[:3])
    L(lid)['trainers'] = [t[3] for t in lst]
for loc in locs.values():
    loc.setdefault('trainers', [])
    if {t['area'] for t in loc['trainers']} <= {'Outside'} and len({e.get('area') for e in loc['encounters'] if e.get('area')}) <= 1:
        for t in loc['trainers']: t.pop('area', None)
    if all(e.get('area') in (None, 'Outside') for e in loc['encounters']) and all('area' not in t for t in loc['trainers']):
        for e in loc['encounters']: e.pop('area', None)

# ---------- key battles for the Battle plan tab (same records as the route pages) ----------
def find_trainer(lid, tid):
    found = [t for t in locs[lid]['trainers'] if t['id'] == tid]
    assert found, (lid, tid, [t['id'] for t in locs[lid]['trainers']])
    return found[0]
KEY_BATTLES = [
    ('route-103', 'rival-route-103', 'Rival (Route 103)', None, 'Mixed'),
    ('rustboro-city', 'roxanne', 'Roxanne', 'Stone Badge', 'Rock'),
    ('rustboro-city', 'rival-rustboro', 'Rival (Rustboro City)', None, 'Mixed'),
    ('dewford-town', 'brawly', 'Brawly', 'Knuckle Badge', 'Fighting'),
    ('route-110', 'rival-route-110', 'Rival (Route 110)', None, 'Mixed'),
    ('mauville-city', 'wally-mauville', 'Wally (Mauville City)', None, 'Mixed'),
    ('mauville-city', 'wattson', 'Wattson', 'Dynamo Badge', 'Electric'),
    ('mt-chimney', 'tabitha-mt-chimney', 'Tabitha (Mt. Chimney)', None, 'Mixed'),
    ('mt-chimney', 'maxie-mt-chimney', 'Maxie (Mt. Chimney)', None, 'Mixed'),
    ('lavaridge-town', 'flannery', 'Flannery', 'Heat Badge', 'Fire'),
    ('petalburg-city', 'norman', 'Norman', 'Balance Badge', 'Normal'),
    ('route-119', 'shelly-weather-institute', 'Shelly (Weather Institute)', None, 'Mixed'),
    ('route-119', 'rival-route-119', 'Rival (Route 119)', None, 'Mixed'),
    ('fortree-city', 'winona', 'Winona', 'Feather Badge', 'Flying'),
    ('lilycove-city', 'rival-lilycove', 'Rival (Lilycove City)', None, 'Mixed'),
    ('magma-hideout', 'tabitha-magma-hideout', 'Tabitha (Magma Hideout)', None, 'Mixed'),
    ('magma-hideout', 'maxie-magma-hideout', 'Maxie (Magma Hideout)', None, 'Mixed'),
    ('aqua-hideout', 'matt', 'Matt (Aqua Hideout)', None, 'Mixed'),
    ('mossdeep-city', 'tate-and-liza', 'Tate and Liza', 'Mind Badge', 'Psychic'),
    ('mossdeep-city', 'maxie-mossdeep', 'Maxie (Space Center)', None, 'Mixed'),
    ('seafloor-cavern', 'shelly-seafloor-cavern', 'Shelly (Seafloor Cavern)', None, 'Mixed'),
    ('seafloor-cavern', 'archie', 'Archie (Seafloor Cavern)', None, 'Mixed'),
    ('sootopolis-city', 'juan', 'Juan', 'Rain Badge', 'Water'),
    ('victory-road', 'wally-vr', 'Wally (Victory Road)', None, 'Mixed'),
    ('pokemon-league', 'sidney', 'Sidney', None, 'Dark'),
    ('pokemon-league', 'phoebe', 'Phoebe', None, 'Ghost'),
    ('pokemon-league', 'glacia', 'Glacia', None, 'Ice'),
    ('pokemon-league', 'drake', 'Drake', None, 'Dragon'),
    ('pokemon-league', 'wallace', 'Champion Wallace', None, 'Water'),
]
trainers = []
for lid, tid, nm, badge, spec in KEY_BATTLES:
    t = find_trainer(lid, tid)
    trainers.append({**t, 'id': tid, 'name': nm, 'trainerName': t['name'], 'where': (locs[lid]['name'] + (f" {t['area']}" if t.get('area') and t['area'] != 'Outside' else '')),
                     'badge': badge, 'specialty': spec, 'location': lid,
                     **({'note': 'Your rival takes the starter that beats yours.'} if 'byStarter' in t else {})})

# ---------- level-up learnsets, weights, moves ----------
weights = {natdex[k]: int(w) for k, w in re.findall(r'\[NATIONAL_DEX_(\w+)\]\s*=\s*\{[^}]*?\.weight = (\d+)', read('src/data/pokemon/pokedex_entries.h'), re.S) if k in natdex}
dex_key = {v: k for k, v in natdex.items()}
for p in pokedex:
    p['weight'] = weights.get(p['dex'])
    p['learnset'] = [[l, move_names[mv]] for l, mv in learnsets[learnset_ptr[dex_key[p['dex']]]]]
EFFECT_KEEP = {'LEVEL_DAMAGE': 'level', 'SONICBOOM': 'fixed20', 'DRAGON_RAGE': 'fixed40', 'SUPER_FANG': 'half', 'OHKO': 'ohko',
               'MULTI_HIT': 'multi', 'DOUBLE_HIT': 'double', 'TWINEEDLE': 'double', 'PSYWAVE': 'level', 'COUNTER': 'counter', 'MIRROR_COAT': 'counter',
               'EXPLOSION': 'explode', 'RECHARGE': 'recharge', 'SOLAR_BEAM': 'charge', 'SEMI_INVULNERABLE': 'charge', 'FUTURE_SIGHT': 'charge', 'RAZOR_WIND': 'charge', 'SKY_ATTACK': 'charge', 'SKULL_BASH': 'charge',
               'DREAM_EATER': 'dream', 'FLAIL': 'varies', 'RETURN': 'varies', 'FRUSTRATION': 'varies', 'HIDDEN_POWER': 'varies', 'MAGNITUDE': 'varies',
               'PRESENT': 'varies', 'LOW_KICK': 'varies', 'SPIT_UP': 'varies', 'ERUPTION': 'varies', 'REVENGE': 'varies', 'FOCUS_PUNCH': 'varies',
               'FAKE_OUT': 'fakeout', 'SNORE': 'dream', 'TRIPLE_KICK': 'triple'}
moves_out = {}
for k, nm in move_names.items():
    if k == 'NONE': continue
    e = EFFECT_KEEP.get(move_effects.get(k))
    moves_out[nm] = {'type': move_types.get(k), 'power': move_power.get(k, 0), **({'effect': e} if e else {})}

# ---------- roaming legendary + story order ----------
locs['roaming'] = {'id': 'roaming', 'name': 'Roaming Legendary', 'encounters': [
    {**mon('SPECIES_LATIOS'), 'method': 'roaming', 'levels': '40', 'notes': 'If you answer "blue" about the TV report after the Hall of Fame'},
    {**mon('SPECIES_LATIAS'), 'method': 'roaming', 'levels': '40', 'notes': 'If you answer "red" about the TV report after the Hall of Fame'}],
    'notes': "After you enter the Hall of Fame, your mom asks what color the Pokémon on the TV was. Your answer decides whether Latias (red) or Latios (blue) roams Hoenn's routes.",
    'items': [], 'gifts': [], 'trainers': []}

ORDER = [('Hoenn: Badge 1', 'littleroot-town route-101 oldale-town route-103 route-102 petalburg-city route-104 petalburg-woods rustboro-city'),
         ('Hoenn: Badges 2–3', 'route-116 rusturf-tunnel dewford-town granite-cave route-109 slateport-city route-110 mauville-city'),
         ('Hoenn: Badge 4', 'route-117 verdanturf-town route-111 route-112 fiery-path route-113 fallarbor-town route-114 meteor-falls route-115 mt-chimney jagged-pass lavaridge-town'),
         ('Hoenn: Badges 5–6', 'mirage-tower route-105 route-106 route-107 route-108 abandoned-ship new-mauville route-118 route-119 fortree-city route-120 scorched-slab'),
         ('Hoenn: Badge 7', 'route-121 safari-zone lilycove-city route-122 mt-pyre route-123 magma-hideout aqua-hideout route-124 mossdeep-city route-125 shoal-cave'),
         ('Hoenn: Badge 8 & League', 'route-127 route-128 seafloor-cavern route-126 sootopolis-city cave-of-origin route-129 route-130 route-131 pacifidlog-town sky-pillar route-132 route-133 route-134 ever-grande-city victory-road pokemon-league'),
         ('Post-game', 'roaming ss-tidal battle-frontier artisan-cave desert-underpass altering-cave sealed-chamber desert-ruins island-cave ancient-tomb marine-cave terra-cave'),
         ('Event islands', 'southern-island faraway-island birth-island navel-rock')]
walk = json.load(open(os.path.join(OUT, 'walkthrough.json')))
index = []
for region, ids in ORDER:
    for i in ids.split():
        assert i in locs, i
        index.append({'id': i, 'name': locs[i]['name'], 'region': region, 'file': f'locations/{i}.json'})
missing = set(locs) - {x['id'] for x in index}
assert not missing, missing
for i in walk:
    assert i.startswith('_') or i in locs, i

# ---------- when you actually fight each trainer ----------
# Place each trainer at the first key battle whose ace is within 5 levels of the trainer's own ace, never before the
# location itself. Trainers placed past the next key battle after the location are 'later' (collapsed in the app).
order_pos = {x['id']: i for i, x in enumerate(index)}
def ace_of(t):
    ps = [t['party']] if 'party' in t else list(t['byStarter'].values())
    return max(p['level'] for pty in ps for p in pty)
keys = sorted(((order_pos[t.get('stage') or t['location']], ace_of(t), t.get('stage') or t['location']) for t in trainers))
# Route 103's east side is only reached from Route 110 (or by Surf), so its trainers wait until then
MIN_STAGE = {'route-103': 'route-110'}
for loc in locs.values():
    here = order_pos[loc['id']]
    nxt = next((k for k in keys if k[0] >= here), None)
    for t in loc['trainers']:
        if t.get('stage'):
            t['later'] = order_pos[t['stage']] > here
            continue
        ace = ace_of(t)
        base = order_pos[MIN_STAGE[loc['id']]] if loc['id'] in MIN_STAGE and t['class'] != 'Rival' else here
        fit = next((k for k in keys if k[0] >= base and k[1] >= ace - 5), None)
        nb = next((k for k in keys if k[0] >= base), None)
        if fit and nb and fit[0] > nb[0] and fit[2] != loc['id']:
            t['stage'], t['later'] = fit[2], True
        elif base > here:
            t['stage'], t['later'] = MIN_STAGE[loc['id']], True
        elif not fit and here < order_pos['pokemon-league']:
            t['stage'], t['later'] = 'pokemon-league', True  # stronger than anything before the League: a post-game battle
# Swimmers are out on the water: you can't reach them before Surf (after Norman), whatever their level
SURF_AT = order_pos['lavaridge-town']
for loc in locs.values():
    for t in loc['trainers']:
        if 'Swimmer' in t['class'] and order_pos[t.get('stage') or loc['id']] <= SURF_AT:
            t['stage'], t['later'], t['need'] = 'lavaridge-town', order_pos[loc['id']] <= SURF_AT, 'surf'

# ---------- when can you reach each item? ----------
# A walk over the real map tiles (scripts/reach.py): water, ledges, Cut trees, Rock Smash rocks, Strength boulders,
# bike slopes and rails, dive spots, warps and boats, with each map opening when the story reaches its location.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reach
def stage_after(lid, plus=0.5): return order_pos[lid] + plus
# Field moves: when the HM and the badge to use it are both in hand (as a stage in the story order)
ABILITIES = {
    'cut': (stage_after('rustboro-city'), "Cut (HM01 from the Cutter's House in Rustboro City, used with the Stone Badge)"),
    'mach-bike': (stage_after('mauville-city', 0), 'the Mach Bike (from Rydel in Mauville City; he swaps it for the Acro Bike any time)'),
    'acro-bike': (stage_after('mauville-city', 0), 'the Acro Bike (from Rydel in Mauville City; he swaps it for the Mach Bike any time)'),
    'rock-smash': (stage_after('mauville-city'), 'Rock Smash (HM06 from the Rock Smash Guy in Mauville City, used with the Dynamo Badge)'),
    'strength': (stage_after('lavaridge-town'), 'Strength (HM04 from Rusturf Tunnel, used with the Heat Badge)'),
    'surf': (stage_after('lavaridge-town'), "Surf (HM03 from Wally's father after you beat Norman in Petalburg City)"),
    'devon-scope': (stage_after('route-120', 0), 'the Devon Scope (from Steven on the Route 120 bridge) to reveal the hidden Kecleon'),
    'dive': (stage_after('mossdeep-city'), 'Dive (HM08 from Steven in Mossdeep City, after the Mind Badge)'),
    'waterfall': (stage_after('sky-pillar'), 'Waterfall (HM07 from Wallace, used with the Rain Badge from Juan)'),
}
OBSTACLES = {'OBJ_EVENT_GFX_CUTTABLE_TREE': 'cut', 'OBJ_EVENT_GFX_BREAKABLE_ROCK': 'rock-smash',
             'OBJ_EVENT_GFX_PUSHABLE_BOULDER': 'strength', 'OBJ_EVENT_GFX_KECLEON': 'devon-scope'}
TILE_NEEDS = {'MB_MUDDY_SLOPE': 'mach-bike', 'MB_CRACKED_FLOOR': 'mach-bike', 'MB_BUMPY_SLOPE': 'acro-bike', 'MB_ISOLATED_VERTICAL_RAIL': 'acro-bike',
              'MB_ISOLATED_HORIZONTAL_RAIL': 'acro-bike', 'MB_VERTICAL_RAIL': 'acro-bike', 'MB_HORIZONTAL_RAIL': 'acro-bike'}
# Scripted blockers that live in coord events: the desert's sandstorm turns you back until the Go-Goggles.
GATES = [('Route111', 'Route111_EventScript_ViciousSandstormTriggerDown', stage_after('lavaridge-town'), 'the Go-Goggles from your rival in Lavaridge Town'),
         ('Route111', 'Route111_EventScript_ViciousSandstormTriggerLeft', stage_after('lavaridge-town'), 'the Go-Goggles from your rival in Lavaridge Town')]
# Mr. Briney's boat (Route 104 <-> Dewford <-> Route 109) sails rather than warps; the cable car is code, not script.
TRANSPORTS = [('Route104_MrBrineysHouse', 'DewfordTown', 12, 8), ('Route104', 'DewfordTown', 12, 8), ('DewfordTown', 'Route104', 12, 54),
              ('DewfordTown', 'Route109', 21, 26), ('Route109', 'DewfordTown', 12, 8),
              ('Route112_CableCarStation', 'MtChimney_CableCarStation', 6, 10), ('MtChimney_CableCarStation', 'Route112_CableCarStation', 6, 10),
              ('Route121_SafariZoneEntrance', 'SafariZone_South', 32, 32)]
# Maps that open at a different story point from the rest of their location, and why.
BADGE_AT = {3: stage_after('mauville-city'), 4: stage_after('lavaridge-town'), 5: stage_after('lavaridge-town'),
            6: stage_after('route-120'), 7: stage_after('mossdeep-city'), 8: stage_after('sky-pillar')}
BADGE_NAMES = {3: 'Dynamo Badge', 4: 'Heat Badge', 5: 'Balance Badge', 6: 'Feather Badge', 7: 'Mind Badge', 8: 'Rain Badge'}
MAP_OPEN = {
    # Granite Cave's entrance is on Route 106's beach, a short walk from Dewford; the rest of Route 106 is open sea.
    'Route106': (order_pos['dewford-town'], None),
    'SafariZone_Northeast': (order_pos['pokemon-league'], 'After the Hall of Fame (the Safari Zone expansion opens then)'),
    'SafariZone_Southeast': (order_pos['pokemon-league'], 'After the Hall of Fame (the Safari Zone expansion opens then)'),
    'AbandonedShip_HiddenFloorCorridors': (ABILITIES['dive'][0], ABILITIES['dive'][1]),
    'AbandonedShip_HiddenFloorRooms': (ABILITIES['dive'][0], ABILITIES['dive'][1]),
}
# The Trick Master opens puzzle n (n >= 2) once you have badge n + 1 (Route110_TrickHouseEntrance scripts)
for n in range(2, 9):
    b = min(n + 1, 8)
    MAP_OPEN[f'Route110_TrickHousePuzzle{n}'] = (BADGE_AT[b], f'the {BADGE_NAMES[b]} (the Trick Master sets this puzzle once you have it)')
def map_stage(name):
    if map_skipped(name) or name not in maps: return None
    if name in MAP_OPEN: return MAP_OPEN[name][0]
    lid = map_loc(name)
    return order_pos.get(lid)
world = reach.World(SRC, 'emerald', maps, map_stage, ABILITIES, OBSTACLES, GATES, TRANSPORTS, TILE_NEEDS)
world.solve(('LittlerootTown', 5, 8))
key_stages = sorted({k[0] for k in keys})
def first_visit_until(lid):
    """Everything up to the next key battle at or after a place counts as the first visit (Route 104's north end
    via Petalburg Woods), so an item is 'later' only when it needs a later story point than that."""
    here = order_pos[lid]
    return next((k for k in key_stages if k >= here), here)
unreachable = []
def describe(loc, st, kind, what):
    if kind == 'ability': return ABILITIES[what][1], index[int(ABILITIES[what][0])]['id']
    if kind == 'gate': return what, index[int(st)]['id']
    if what in MAP_OPEN and MAP_OPEN[what][1]: return MAP_OPEN[what][1], index[int(st)]['id']
    via = map_loc(what) if what in maps else what
    if via != loc['id'] and via in locs: return f"Come in from {locs[via]['name']}", via
    return f"After {index[int(st)]['name']}", index[int(st)]['id']
for loc in locs.values():
    for it in loc['items']:
        pos = item_pos.get((loc['id'], it['id']))
        if not pos: continue
        mapname, x, y, el, under = pos
        r = world.item_reach(mapname, x, y, el, under)
        if r is None:
            # puzzles the walk can't solve (Trick House switches, New Mauville doors, tides): open with the map
            unreachable.append(f"{loc['id']}: {it['name']} ({mapname} {x},{y})")
            st = map_stage(mapname)
            r = (st, ('map', mapname))
        st, (kind, what) = r
        if st <= first_visit_until(loc['id']): continue
        it['later'] = True
        it['need'], it['after'] = describe(loc, st, kind, what)
        it['stage'] = st
# for tests/item_reach.js: when each field move opens, and where a location's first visit ends
json.dump({'_about': 'Written by scripts/build_data.py from the reachability walk (scripts/reach.py). Read by tests/item_reach.js.',
           'abilities': {k: {'stage': v[0], 'need': v[1]} for k, v in ABILITIES.items()},
           'firstVisitUntil': {x['id']: first_visit_until(x['id']) for x in index},
           'puzzles': unreachable},
          open(os.path.join(OUT, 'verify', 'item-reach.json'), 'w'), ensure_ascii=False, indent=1)
if unreachable:
    print(f'reach: {len(unreachable)} items behind puzzles the walk cannot solve (timed by their map):', *unreachable, sep='\n  ', file=sys.stderr)

# ---------- TMs and HMs ----------
tm_moves = {TM_ITEM[f'ITEM_TM_{mv}']: move_names[mv] for mv in TM_LIST}
tm_moves.update({TM_ITEM[f'ITEM_HM_{mv}']: move_names[mv] for mv in HM_LIST})
tm_of_move = {mv: TM_ITEM.get(f'ITEM_TM_{mv}') or TM_ITEM[f'ITEM_HM_{mv}'] for mv in TM_LIST + HM_LIST}
by_species = {k: [tm_of_move[mv] for mv in re.findall(r'\.(\w+) = TRUE', body)]
              for k, body in re.findall(r'\[SPECIES_(\w+)\]\s*=\s*\{\s*\.learnset = \{(.*?)\}\s*\}', read('src/data/pokemon/tmhm_learnsets.h'), re.S)}
for p in pokedex:
    p['tmhm'] = sorted(set(by_species.get(dex_key[p['dex']], [])))
tms = {k: {'move': tm_moves[k], 'reusable': k.startswith('HM'), 'sources': []} for k in sorted(tm_moves)}
for x in index:
    for kind in ('items', 'gifts'):
        for it in locs[x['id']].get(kind, []):
            m = re.match(r'((?:TM|HM)\d+)\b', it['name'])
            if m and m.group(1) in tms:
                tms[m.group(1)]['sources'].append({'loc': x['id'], 'how': 'gift' if kind == 'gifts' else 'found', 'where': it.get('where'),
                                                   **({'from': it['from']} if it.get('from') else {}),
                                                   **({'stage': it['stage'], 'need': it['need']} if it.get('later') else {})})

# ---------- shops ----------
shops = collections.defaultdict(list)
SHOP_NOTE = {'OldaleTown_Mart_Pokemart_Basic': 'Before you get the Pokédex', 'OldaleTown_Mart_Pokemart_Expanded': 'Poké Mart',
             'PetalburgCity_Mart_Pokemart_Basic': 'Poké Mart', 'PetalburgCity_Mart_Pokemart_Expanded': 'After you earn four badges',
             'RustboroCity_Mart_Pokemart_Basic': 'Poké Mart', 'RustboroCity_Mart_Pokemart_Expanded': 'After you meet the Devon employee on Route 116',
             'SlateportCity_Pokemart_EnergyGuru': 'Market: Energy Guru (vitamins)', 'SlateportCity_Pokemart_PowerTMs': 'Market: TM stall',
             'LilycoveCity_DepartmentStore_2F_Pokemart1': 'Department Store 2F (left clerk)', 'LilycoveCity_DepartmentStore_2F_Pokemart2': 'Department Store 2F (right clerk)',
             'LilycoveCity_DepartmentStore_3F_Pokemart_Vitamins': 'Department Store 3F (vitamins)', 'LilycoveCity_DepartmentStore_3F_Pokemart_StatBoosters': 'Department Store 3F (battle items)',
             'LilycoveCity_DepartmentStore_4F_Pokemart_AttackTMs': 'Department Store 4F (TMs)', 'LilycoveCity_DepartmentStore_4F_Pokemart_DefenseTMs': 'Department Store 4F (TMs)',
             'LavaridgeTown_HerbShop_Pokemart': 'Herb Shop', 'EverGrandeCity_PokemonLeague_1F_Pokemart': 'Pokémon League Poké Mart'}
for name in sorted(maps):
    f = os.path.join(maps[name]['_dir'], 'scripts.inc')
    if not os.path.exists(f) or map_skipped(name): continue
    raw = open(f, encoding='utf-8').read()
    for lbl in re.findall(r'^\s*pokemart (\w+)', raw, re.M):
        body = re.search(re.escape(lbl) + r':+(.*?)pokemartlistend', raw, re.S).group(1)
        lst = [{'name': item_name(c), 'price': items[c]['price']} for c in re.findall(r'(ITEM_\w+)', body) if c != 'ITEM_NONE']
        where = SHOP_NOTE.get(lbl) or (area_name(name) if area_name(name) != 'Mart' else 'Poké Mart')
        shops[map_loc(name)].append({'id': re.sub(r'[^a-z0-9]+', '-', lbl.lower()), 'where': where, 'items': lst})
        for it in lst:
            mm = re.match(r'((?:TM|HM)\d+)$', it['name'])
            if mm:
                tms[mm.group(1)]['reusable'] = True
                tms[mm.group(1)]['sources'].append({'loc': map_loc(name), 'how': 'buy', 'where': where, 'cost': f"₽{it['price']:,}"})
shops['lilycove-city'].append({'id': 'rooftop-vending', 'where': 'Department Store Rooftop (vending machines)', 'items': [
    {'name': 'Fresh Water', 'price': 200}, {'name': 'Soda Pop', 'price': 300}, {'name': 'Lemonade', 'price': 350}]})
gc = read('data/maps/MauvilleCity_GameCorner/scripts.inc')
prize_items = [(tm_of_move[mv], int(c)) for mv, c in re.findall(r'\.set TM_(\w+)_COINS, (\d+)', gc)]
for tm, coins in prize_items:
    tms[tm]['reusable'] = True
    tms[tm]['sources'].append({'loc': 'mauville-city', 'how': 'prize', 'where': 'Game Corner prize counter', 'cost': f'{coins:,} coins'})
shops['mauville-city'].append({'id': 'game-corner-prizes', 'where': 'Game Corner prize counter', 'coins': True,
    'items': [{'name': tm, 'price': c} for tm, c in prize_items]})
for t in tms.values():
    t['sources'].sort(key=lambda s: order_pos[s['loc']])

# ---------- extra species data: abilities, catch rate, EXP, EV yield, growth rate, wild held items ----------
ability_names = {k: title(v) for k, v in re.findall(r'\[ABILITY_(\w+)\] = _\("(.*?)"\)', read('src/data/text/abilities.h'))}
GROWTH = {'MEDIUM_FAST': 'medium-fast', 'ERRATIC': 'erratic', 'FLUCTUATING': 'fluctuating', 'MEDIUM_SLOW': 'medium-slow', 'FAST': 'fast', 'SLOW': 'slow'}
extra = {}
for cur, body in species_blocks().items():
    x = extra[cur] = {}
    for k, v in re.findall(r'\.(catchRate|expYield|friendship|safariZoneFleeRate|evYield_\w+)\s*=\s*(\d+)', body): x[k] = int(v)
    m = re.search(r'\.growthRate = GROWTH_(\w+)', body)
    if m: x['growth'] = GROWTH[m.group(1)]
    m = re.search(r'\.abilities = \{\s*ABILITY_(\w+),\s*ABILITY_(\w+)\s*\}', body)
    if m: x['abilities'] = [ability_names[a] for a in dict.fromkeys(m.groups()) if a != 'NONE']
    for kind, it in re.findall(r'\.item(Common|Rare)\s*=\s*(ITEM_\w+)', body):
        if it != 'ITEM_NONE': x.setdefault('held', {})[kind.lower()] = item_name(it)
tutor_src = read('src/data/pokemon/tutor_learnsets.h')
tutor_by_species = {k: [move_names[mv] for mv in re.findall(r'TUTOR\(MOVE_(\w+)\)', body)]
                    for k, body in re.findall(r'\[SPECIES_(\w+)\]\s*=\s*(\([^;]*?\)|0)\s*,\s*\n', tutor_src, re.S)}
for p in pokedex:
    x = extra.get(dex_key[p['dex']], {})
    p['abilities'] = x.get('abilities', [])
    p['catchRate'] = x.get('catchRate'); p['expYield'] = x.get('expYield'); p['growth'] = x.get('growth')
    p['ev'] = [x.get(f'evYield_{s}', 0) for s in ('HP', 'Attack', 'Defense', 'SpAttack', 'SpDefense', 'Speed')]
    if x.get('held'): p['held'] = x['held']
    if x.get('safariZoneFleeRate'): p['safariFlee'] = x['safariZoneFleeRate']
    if tutor_by_species.get(dex_key[p['dex']]): p['tutor'] = tutor_by_species[dex_key[p['dex']]]

# ---------- move tutors and Match Call rematches ----------
# Each of Emerald's 15 overworld tutors teaches its move once. The Battle Frontier tutors cost Battle Points (post-game).
TUTOR_LOC = {'SlateportCity': 'slateport-city', 'MauvilleCity': 'mauville-city', 'VerdanturfTown': 'verdanturf-town', 'LavaridgeTown': 'lavaridge-town',
             'FallarborTown': 'fallarbor-town', 'FortreeCity': 'fortree-city', 'LilycoveCity': 'lilycove-city', 'MossdeepCity': 'mossdeep-city',
             'SootopolisCity': 'sootopolis-city', 'PacifidlogTown': 'pacifidlog-town'}
mt_src = read('data/scripts/move_tutors.inc')
tutors = []
for lbl in re.findall(r'^(\w+_EventScript_\w+Tutor)::', mt_src, re.M):
    mapname = lbl.split('_EventScript_')[0]
    lid = TUTOR_LOC[re.match(r'[A-Z][a-z]+[A-Z][a-z]+', mapname).group(0)]
    mv = re.search(re.escape(lbl) + r'::.*?\bTUTOR_MOVE_(\w+)', mt_src, re.S).group(1)
    tutors.append({'id': 'tutor-' + mv.lower().replace('_', '-'), 'move': move_names[mv], 'loc': lid, 'where': area_name(mapname),
                   'learners': [p['dex'] for p in pokedex if move_names[mv] in p.get('tutor', [])], 'note': 'Teaches the move once.'})
taught = {t['move'] for t in tutors}
all_tutor = re.findall(r'\[TUTOR_MOVE_\w+\] = MOVE_(\w+)', tutor_src)
for mv in all_tutor:
    if move_names[mv] in taught: continue
    tutors.append({'id': 'tutor-' + mv.lower().replace('_', '-'), 'move': move_names[mv], 'loc': 'battle-frontier', 'where': 'Battle Frontier',
                   'learners': [p['dex'] for p in pokedex if move_names[mv] in p.get('tutor', [])], 'note': 'Costs Battle Points; can be taught again.'})
tutors.sort(key=lambda t: order_pos[t['loc']])

rematches = collections.defaultdict(list)
rm_block = re.search(r'gRematchTable\[REMATCH_TABLE_ENTRIES\]\s*=\s*\{(.*?)\n\};', read('src/battle_setup.c'), re.S).group(1)
TIER = ['First battle', 'Rematch 1', 'Rematch 2', 'Rematch 3', 'Rematch 4']
for ids, mp in re.findall(r'REMATCH\(((?:TRAINER_\w+,\s*)+)(MAP_\w+)\)', rm_block):
    consts = [c.strip() for c in ids.split(',') if c.strip()]
    m = by_const.get(mp)
    if not m or m['name'] not in maps: continue
    lid = map_loc(m['name'])
    base = tid_of(consts[0])
    tiers, seen_c = [], {consts[0]}
    for i, c in enumerate(consts[1:], 1):
        if c in seen_c or c not in tdefs: continue
        seen_c.add(c)
        tiers.append({'after': TIER[i], 'party': trainer_party(c)})
    if tiers: rematches[lid].append({'id': base, 'tiers': tiers})

# ---------- item descriptions ----------
KEEP_CAPS = {'HP', 'PP', 'TM', 'HM', 'S.S.', 'EXP.', 'EXP', 'PC', 'TV'}
def desc_text(d):
    d = d.replace('\\n', ' ').replace('POKéMON', 'Pokémon').replace('POKé', 'Poké').replace('{POKEBLOCK}', 'Pokéblock')
    return re.sub(r"\b[A-Zé][A-Zé'.\-]+\b\.?", lambda m: m.group(0) if m.group(0).rstrip('.') in KEEP_CAPS else m.group(0).capitalize(), d)
POCKET = {'POCKET_ITEMS': 'Items', 'POCKET_KEY_ITEMS': 'Key Items', 'POCKET_POKE_BALLS': 'Poké Balls', 'POCKET_BERRIES': 'Berries', 'POCKET_TM_HM': 'TMs & HMs'}
STATUS_CURE = {'CURE_PAR': 'paralysis', 'CURE_SLP': 'sleep', 'CURE_PSN': 'poison', 'CURE_BRN': 'a burn', 'CURE_FRZ': 'freezing', 'CURE_CONFUSION': 'confusion', 'CURE_STATUS': 'any status problem or confusion'}
PINCH = {'ATTACK_UP': 'Attack', 'DEFENSE_UP': 'Defense', 'SPEED_UP': 'Speed', 'SP_ATTACK_UP': 'Sp. Atk', 'SP_DEFENSE_UP': 'Sp. Def'}
def held_text(i):
    e, n = i['holdEffect'].replace('HOLD_EFFECT_', ''), i['holdEffectParam']
    if i['pocket'] != 'POCKET_BERRIES': return None
    if e == 'RESTORE_HP': return f'Held in battle: restores {n} HP once its HP falls below half.'
    if e in STATUS_CURE: return f'Held in battle: cures {STATUS_CURE[e]} straight away.'
    if e == 'RESTORE_PP': return f'Held in battle: restores {n} PP to a move that runs out.'
    if e.startswith('CONFUSE_'): return 'Held in battle: restores 1/8 of max HP when HP is low, but confuses a Pokémon that dislikes the flavor.'
    if e in PINCH: return f'Held in battle: raises {PINCH[e]} when HP is low.'
    if e == 'CRITICAL_UP': return 'Held in battle: raises the critical-hit ratio when HP is low.'
    if e == 'RANDOM_STAT_UP': return 'Held in battle: sharply raises a random stat when HP is low.'
    if e == 'RESTORE_STATS': return 'Held in battle: restores lowered stats.'
    return None
# items.h keeps a "FireRed/LeafGreen key items" block (Oak's Parcel, Poké Flute, Tri-pass...) that Emerald never hands out.
# Leave those out of the item pages and search. Emerald does use three items from that block: the two event tickets
# and the Powder Jar (Berry Crush).
_ih = read('src/data/items.h')
_frlg = _ih[_ih.index('// FireRed/LeafGreen key items'):_ih.index('// Emerald-specific key items')]
FRLG_ONLY_ITEMS = set(re.findall(r'\[(ITEM_\w+)\]\s*=', _frlg)) - {'ITEM_MYSTIC_TICKET', 'ITEM_AURORA_TICKET', 'ITEM_POWDER_JAR'}
item_info = {}
for c, i in items.items():
    if c in FRLG_ONLY_ITEMS: continue
    if c == 'ITEM_NONE' or not i['english'] or '?' in i['english'] or i['pocket'] == 'POCKET_TM_HM': continue
    x = {'desc': desc_text(i['description_english']), 'price': i['price'], 'pocket': POCKET.get(i['pocket'], '')}
    h = held_text(i)
    if h: x['held'] = h
    item_info[item_name(c)] = x

# ---------- save file import map ----------
def defines(*files):
    out = {}
    for f in files:
        for name, val in re.findall(r'^#define\s+(\w+)\s+(.+?)\s*(?://.*)?$', read(f), re.M): out[name] = val
    return out
DEF = defines('include/constants/flags.h', 'include/constants/opponents.h', 'include/constants/species.h', 'include/constants/moves.h')
_ev = {}
def ev(name):
    if name in _ev: return _ev[name]
    expr = DEF[name]
    expr = re.sub(r'\b([A-Za-z_]\w*)\b', lambda m: str(ev(m.group(1))) if m.group(1) in DEF else m.group(1), expr)
    _ev[name] = int(eval(expr.replace('/', '//'), {'__builtins__': {}}))
    return _ev[name]
flag_map = {}
for k, f in item_flags.items():
    if f in DEF: flag_map[k] = ev(f)
TFS = ev('TRAINER_FLAGS_START')
for (lid, tid), consts in trainer_consts.items():
    flag_map[f'{lid}:trainer:{tid}'] = [TFS + ev(c) for c in consts if c in DEF]
species_index = [0] * (max(ev(k) for k in DEF if k.startswith('SPECIES_') and re.match(r'^\d+$', DEF[k])) + 1)
for k in DEF:
    if k.startswith('SPECIES_') and k[8:] in natdex and re.match(r'^\d+$', DEF[k]): species_index[ev(k)] = natdex[k[8:]]
moves_by_id = {}
for k in DEF:
    if k.startswith('MOVE_') and k[5:] in move_names and re.match(r'^\d+$', DEF[k]): moves_by_id[ev(k)] = move_names[k[5:]]
move_list = [moves_by_id.get(i, '') for i in range(max(moves_by_id) + 1)]
badges = [ev(f'FLAG_BADGE0{i}_GET') for i in range(1, 9)]

# ---------- region map grid (for the tappable map) ----------
src = read('src/data/region_map/region_map_layout.h')
cells = []
for y, row in enumerate(re.findall(r'\{(MAPSEC_[^{}]*)\}', src)):
    for x, sec in enumerate(c.strip() for c in row.split(',') if c.strip()):
        if sec == 'MAPSEC_NONE': continue
        lid = sec.replace('MAPSEC_', '').lower().replace('_', '-')
        if lid in locs: cells.append([x, y, lid, 'map'])
# Caves and buildings aren't on the town-map grid; region_map_sections.json gives each one's square.
placed = {c[2] for c in cells}
for s_ in json.load(open(P('src/data/region_map/region_map_sections.json')))['map_sections']:
    lid = {'MAPSEC_UNDERWATER_SEALED_CHAMBER': 'sealed-chamber', 'MAPSEC_UNDERWATER_MARINE_CAVE': 'marine-cave'}.get(s_['id'], s_['id'].replace('MAPSEC_', '').lower().replace('_', '-'))
    if lid in locs and lid not in placed and 'x' in s_:
        cells.append([s_['x'], s_['y'], lid, 'dungeon']); placed.add(lid)
league = next(c for c in cells if c[2] == 'ever-grande-city')
cells.append([league[0], league[1], 'pokemon-league', 'dungeon'])
region_maps = {'Hoenn': cells}

# ---------- write ----------
os.makedirs(os.path.join(OUT, 'locations'), exist_ok=True)
for f in glob.glob(os.path.join(OUT, 'locations', '*.json')): os.remove(f)
for loc in locs.values():
    loc.setdefault('trainers', [])
    loc['verified'] = True
    loc['sources'] = [SOURCE_URL]
    json.dump(loc, open(os.path.join(OUT, 'locations', loc['id'] + '.json'), 'w'), ensure_ascii=False, indent=1)
json.dump({'locations': index}, open(os.path.join(OUT, 'locations.json'), 'w'), ensure_ascii=False, indent=1)
json.dump(moves_out, open(os.path.join(OUT, 'moves.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
json.dump(pokedex, open(os.path.join(OUT, 'pokedex.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
json.dump(type_chart, open(os.path.join(OUT, 'types.json'), 'w'), indent=1)
json.dump(trainers, open(os.path.join(OUT, 'trainers.json'), 'w'), ensure_ascii=False, indent=1)
json.dump(tms, open(os.path.join(OUT, 'tms.json'), 'w'), ensure_ascii=False, indent=1)
json.dump(item_info, open(os.path.join(OUT, 'items.json'), 'w'), ensure_ascii=False, indent=0)
json.dump({'shops': shops, 'tutors': tutors, 'rematches': rematches, 'unown': {}},
          open(os.path.join(OUT, 'extras.json'), 'w'), ensure_ascii=False, indent=1)
json.dump({'flags': flag_map, 'species': species_index, 'moves': move_list, 'badges': badges},
          open(os.path.join(OUT, 'save-map.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
json.dump(region_maps, open(os.path.join(OUT, 'region-map.json'), 'w'), separators=(',', ':'))
print(len(locs), 'locations;', sum(len(l['items']) for l in locs.values()), 'items;', sum(len(l['gifts']) for l in locs.values()), 'gifts;',
      sum(len(l['encounters']) for l in locs.values()), 'encounter rows;', sum(len(l['trainers']) for l in locs.values()), 'trainers')
print('shops', sum(len(v) for v in shops.values()), 'tutors', len(tutors), 'rematch trainers', sum(len(v) for v in rematches.values()))
print('tms', len(tms), 'without a source:', [k for k, v in tms.items() if not v['sources']])
print('items', len(item_info), '; save map:', len(flag_map), 'flags')
print('region map: unplaced locations', sorted(set(x['id'] for x in index) - {c[2] for c in cells}))
