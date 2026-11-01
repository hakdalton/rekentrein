# Bouwt het spoornetwerk voor de Rekentrein uit open data in data/bron/.
# - Spoor: OpenStreetMap (ODbL), elk spoor apart met echte wissels, via Overpass (zie haal_spoor.py)
# - Stations: Rijden de Treinen (CC BY 4.0)
# Uitvoer data/netwerk.json, compact genoeg om in index.html mee te bakken:
#   knopen:   [[x, y], ...] in hele meters RD (EPSG:28992)
#   lijnen:   [[a, b, lengte, x0, y0, dx1, dy1, ...], ...]  (a/b = knoopnummers, punten als verschillen)
#   stations: [[code, naam, type, [knopen...]], ...]
# Draaien: python3 tools/bouw_netwerk.py
import csv, json, math, os, collections

HIER = os.path.dirname(os.path.abspath(__file__))
BRON = os.path.join(HIER, '..', 'data', 'bron')
UIT = os.path.join(HIER, '..', 'data', 'netwerk.json')
STATION_MAX = 140     # sporen binnen 140 m van het stationspunt horen bij het station
VEREENVOUDIG = 2.0


def wgs_naar_rd(lat, lon):   # benadering van Schreutelkamp en Strang van Hees, ruim binnen een meter
    dphi, dlam = 0.36 * (lat - 52.15517440), 0.36 * (lon - 5.38720621)
    x = (190094.945 * dlam - 11832.228 * dphi * dlam - 114.221 * dphi**2 * dlam - 32.391 * dlam**3
         - 0.705 * dphi - 2.340 * dphi**3 * dlam - 0.608 * dphi * dlam**3 - 0.008 * dlam**2 + 0.148 * dphi**2 * dlam**3)
    y = (309056.544 * dphi + 3638.893 * dlam**2 + 73.077 * dphi**2 - 157.984 * dphi * dlam**2 + 59.788 * dphi**3
         + 0.433 * dlam - 6.439 * dphi**2 * dlam**2 - 0.032 * dphi * dlam + 0.092 * dlam**4 - 0.054 * dphi * dlam**4)
    return 155000 + x, 463000 + y


def lengte(l):
    return sum(math.dist(l[i], l[i + 1]) for i in range(len(l) - 1))


def dp(pts, tol):   # Douglas-Peucker, iteratief
    houd = [False] * len(pts); houd[0] = houd[-1] = True
    stapel = [(0, len(pts) - 1)]
    while stapel:
        i0, i1 = stapel.pop()
        a, b = pts[i0], pts[i1]
        dx, dy = b[0] - a[0], b[1] - a[1]
        n = math.hypot(dx, dy) or 1e-9
        best, bi = -1, 0
        for i in range(i0 + 1, i1):
            d = abs(dy * (pts[i][0] - a[0]) - dx * (pts[i][1] - a[1])) / n
            if d > best:
                best, bi = d, i
        if best > tol:
            houd[bi] = True
            stapel += [(i0, bi), (bi, i1)]
    return [p for p, h in zip(pts, houd) if h]


# ---------- OSM-sporen inlezen ----------
ways = json.load(open(os.path.join(BRON, 'osm_spoor.json')))['elements']
pos = {}
gebruik = collections.Counter()
for w in ways:
    for nid, g in zip(w['nodes'], w['geometry']):
        if g and nid not in pos:
            pos[nid] = wgs_naar_rd(g['lat'], g['lon'])
    for nid in w['nodes']:
        gebruik[nid] += 1
    gebruik[w['nodes'][0]] += 1; gebruik[w['nodes'][-1]] += 1

# ruwe lijnstukken tussen knooppunten (wissels, eindpunten)
stukken = []
for w in ways:
    ns = [n for n in w['nodes'] if n in pos]
    huidig = [ns[0]]
    for n in ns[1:]:
        huidig.append(n)
        if gebruik[n] > 1:
            stukken.append(huidig); huidig = [n]
    if len(huidig) > 1:
        stukken.append(huidig)

print('sporen', len(stukken), 'km', round(sum(lengte([pos[n] for n in s]) for s in stukken) / 1000))

# ---------- stations op de sporen zetten ----------
rdt = [r for r in csv.DictReader(open(os.path.join(BRON, 'stations-rdt-2023-09.csv'))) if r['country'] == 'NL' and r['type'] != 'facultatiefStation']
# rooster voor snel zoeken
CEL = 300
rooster = collections.defaultdict(set)
for i, s in enumerate(stukken):
    for n in s:
        p = pos[n]; rooster[(int(p[0] // CEL), int(p[1] // CEL))].add(i)
splitsen = collections.defaultdict(list)   # stuk -> [(index, t, punt, stationnr)]
st_pt = []
for si, r in enumerate(rdt):
    p = wgs_naar_rd(float(r['geo_lat']), float(r['geo_lng'])); st_pt.append(p)
    kand = set()
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            kand |= rooster.get((int(p[0] // CEL) + dx, int(p[1] // CEL) + dy), set())
    gevonden = []
    for i in kand:
        pts = [pos[n] for n in stukken[i]]
        best = None
        for k in range(len(pts) - 1):
            a, b = pts[k], pts[k + 1]
            dx, dy = b[0] - a[0], b[1] - a[1]
            L2 = dx * dx + dy * dy or 1e-9
            t = max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
            q = (a[0] + t * dx, a[1] + t * dy); d = math.dist(p, q)
            if best is None or d < best[0]:
                best = (d, k, t, q)
        if best[0] < 450:
            gevonden.append((best[0], i, best))
    if not gevonden:
        print('geen spoor bij', r['name_long']); continue
    dmin = min(g[0] for g in gevonden)
    for d, i, (_, k, t, q) in gevonden:
        if d < max(dmin + 60, STATION_MAX):
            splitsen[i].append((k, t, q, si))

# lijnen opbouwen als puntenlijsten met knoop-sleutels; stations knippen de lijnen
knoop_id, knopen = {}, []
def knoop(sleutel, p):
    if sleutel not in knoop_id:
        knoop_id[sleutel] = len(knopen); knopen.append(p)
    return knoop_id[sleutel]

station_knopen = collections.defaultdict(set)
lijnen = []
for i, s in enumerate(stukken):
    pts = [pos[n] for n in s]
    sleutels = [('osm', s[0])] + [None] * (len(s) - 2) + [('osm', s[-1])]
    # knippunten invoegen (achterstevoren zodat indexen kloppen)
    for k, t, q, si in sorted(splitsen.get(i, []), key=lambda x: (x[0], x[1]), reverse=True):
        pts.insert(k + 1, q); sleutels.insert(k + 1, ('st', i, si, k, round(t, 4)))
    begin = 0
    for j in range(1, len(pts)):
        if sleutels[j] is None:
            continue
        deel = pts[begin:j + 1]
        a = knoop(sleutels[begin], pts[begin]); b = knoop(sleutels[j], pts[j])
        if a != b:   # ook stukjes van 0 m bewaren, anders valt het net uit elkaar
            lijnen.append((a, b, dp(deel, VEREENVOUDIG)))
        begin = j
    for j, sl in enumerate(sleutels):
        if sl and sl[0] == 'st':
            station_knopen[sl[2]].add(knoop_id[sl])

# doorgaande knopen (precies twee lijnen, geen station) samenvoegen
st_alle = set(k for ks in station_knopen.values() for k in ks)
lijst = {i: [a, b, pts] for i, (a, b, pts) in enumerate(lijnen)}
aan = collections.defaultdict(set)
for i, (a, b, _) in lijst.items():
    aan[a].add(i); aan[b].add(i)
for n in list(aan):
    if n in st_alle or len(aan[n]) != 2:
        continue
    i, j = aan[n]
    a1, b1, p1 = lijst[i]; a2, b2, p2 = lijst[j]
    if a1 != n: a1, b1, p1 = b1, a1, p1[::-1]      # i loopt nu van n weg: draai om zodat i naar n loopt
    else: pass
    # i moet eindigen in n, j moet beginnen in n
    if lijst[i][1] == n: a1, b1, p1 = lijst[i]
    else: a1, b1, p1 = lijst[i][1], lijst[i][0], lijst[i][2][::-1]
    if lijst[j][0] == n: a2, b2, p2 = lijst[j]
    else: a2, b2, p2 = lijst[j][1], lijst[j][0], lijst[j][2][::-1]
    if a1 == b2 and a1 == n:
        continue
    lijst[i] = [a1, b2, p1 + p2[1:]]
    del lijst[j]
    aan[b2].discard(j); aan[b2].add(i)
    aan[a1].add(i)
    del aan[n]
lijnen = [(a, b, dp(pts, VEREENVOUDIG)) for a, b, pts in lijst.values() if a != b or len(pts) > 2]

# samenhang
buren = collections.defaultdict(set)
for a, b, _ in lijnen:
    buren[a].add(b); buren[b].add(a)
comp = {}
for s in buren:
    if s in comp:
        continue
    comp[s] = s; stapel = [s]
    while stapel:
        k = stapel.pop()
        for n in buren[k]:
            if n not in comp:
                comp[n] = s; stapel.append(n)
grootte = collections.Counter(comp.values())
hoofd = grootte.most_common(1)[0][0]
stations = []
for si, r in enumerate(rdt):
    ks = sorted(k for k in station_knopen.get(si, ()) if comp.get(k) == hoofd)
    if not ks:
        print('niet op het hoofdnet:', r['name_long']); continue
    stations.append([r['code'], r['name_long'], r['type'], ks])
# alleen het hoofdnet bewaren, knopen opnieuw nummeren
houd = sorted({k for a, b, _ in lijnen if comp.get(a) == hoofd for k in (a, b)})
nieuw = {k: i for i, k in enumerate(houd)}
uit_l = []
for a, b, pts in lijnen:
    if comp.get(a) != hoofd:
        continue
    rij = [nieuw[a], nieuw[b], round(lengte(pts))]
    vorige = (0, 0)
    for p in pts:
        x, y = round(p[0]), round(p[1])
        rij += [x - vorige[0], y - vorige[1]]; vorige = (x, y)
    uit_l.append(rij)
uit_s = [[c, n, t, [nieuw[k] for k in ks]] for c, n, t, ks in stations]
graad = collections.Counter()
for a, b, _ in lijnen:
    graad[a] += 1; graad[b] += 1
keer = []
for k in houd:
    if graad[k] == 1 and any(math.dist(knopen[k], p) < 500 for p in st_pt):
        keer.append(nieuw[k])
# landsgrens voor het kaartje (PDOK bestuurlijke gebieden, landgebied), grof vereenvoudigd, in hectometers
grens = []
for poly in json.load(open(os.path.join(BRON, 'landgebied.json')))['features'][0]['geometry']['coordinates']:
    for ring in poly:
        if abs(sum(ring[i][0]*ring[i+1][1] - ring[i+1][0]*ring[i][1] for i in range(len(ring)-1)))/2 < 8e6:
            continue
        pts = [tuple(q[:2]) for q in ring]; h = len(pts)//2   # gesloten ring: in twee helften vereenvoudigen
        r = dp(pts[:h+1], 250) + dp(pts[h:], 250)[1:]
        grens.append([v for q in r for v in (round(q[0]/100), round(q[1]/100))])
json.dump({'bron': 'Spoor: OpenStreetMap-bijdragers (ODbL). Stations: Rijden de Treinen (CC BY 4.0). Grens: PDOK bestuurlijke gebieden.', 'grens': grens,
           'knopen': [[round(knopen[k][0]), round(knopen[k][1])] for k in houd], 'lijnen': uit_l, 'stations': uit_s, 'keer': keer},
          open(UIT, 'w'), separators=(',', ':'), ensure_ascii=False)
print('keerpunten', len(keer), 'knopen', len(houd), 'lijnen', len(uit_l), 'stations', len(uit_s), 'grootte', os.path.getsize(UIT) // 1024, 'KB')
