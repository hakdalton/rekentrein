# Haalt het Nederlandse spoornet op uit open data en zet het in data/bron/.
# - Spoor uit OpenStreetMap (ODbL) via Overpass, zonder goederenlijnen
# - ProRail-overwegen via PDOK, in RD (EPSG:28992)
# - Stationslijst van Rijden de Treinen (CC BY 4.0) staat al in data/bron/stations-rdt-2023-09.csv
# Draaien: python3 tools/haal_spoor.py
import json, os, urllib.request, urllib.parse

HIER = os.path.dirname(os.path.abspath(__file__))
BRON = os.path.join(HIER, '..', 'data', 'bron')
RD = 'http://www.opengis.net/def/crs/EPSG/0/28992'


def alle_paginas(url):
    feats = []
    while url:
        with urllib.request.urlopen(url, timeout=120) as r:
            d = json.load(r)
        feats += d.get('features', [])
        url = next((l['href'] for l in d.get('links', []) if l.get('rel') == 'next'), None)
        print('  ', len(feats), end='\r')
    return feats


OVERPASS = '''[out:json][timeout:300];
area["ISO3166-1"="NL"][admin_level=2]->.nl;
(
  way["railway"="rail"][!"service"]["usage"!~"industrial|military|tourism|test"]["railway:traffic_mode"!="freight"](area.nl);
  way["railway"="rail"]["service"~"crossover|siding"]["usage"!~"industrial|military|tourism|test"]["railway:traffic_mode"!="freight"](area.nl);
);
out skel geom qt;'''
# curl in plaats van urllib: de Python van Xcode krijgt geen TLS-verbinding met Overpass
import subprocess, time
doel = os.path.join(BRON, 'osm_spoor.json')
for poging in range(6):   # Overpass zit soms vol: wachten en opnieuw (pas overschrijven als het antwoord klopt)
    subprocess.run(['curl', '-s', '--max-time', '400', '-A', 'Rekentrein-leerspel/1.0', '--data-urlencode', 'data=' + OVERPASS,
                    'https://overpass-api.de/api/interpreter', '-o', doel + '.nieuw'], check=True)
    try:
        json.load(open(doel + '.nieuw')); os.replace(doel + '.nieuw', doel); break
    except ValueError:
        print('Overpass bezet, opnieuw over', 20 * 2 ** poging, 's'); time.sleep(20 * 2 ** poging)
else:
    raise SystemExit('Overpass gaf geen geldig antwoord')
print('osm_spoor.json klaar')

# ProRail-lagen (overwegen gebruiken we later voor echte overwegen)
for laag in ['overweg']:
    q = urllib.parse.urlencode({'f': 'json', 'limit': 1000, 'crs': RD})
    feats = alle_paginas(f'https://api.pdok.nl/prorail/spoorwegen/ogc/v1/collections/{laag}/items?{q}')
    json.dump({'type': 'FeatureCollection', 'features': feats}, open(os.path.join(BRON, f'prorail_{laag}.json'), 'w'))
    print(laag, len(feats))

# landsgrens voor het kaartje
q = urllib.parse.urlencode({'f': 'json', 'limit': 10, 'crs': RD})
json.dump({'type': 'FeatureCollection', 'features': alle_paginas(f'https://api.pdok.nl/kadaster/bestuurlijkegebieden/ogc/v1/collections/landgebied/items?{q}')},
          open(os.path.join(BRON, 'landgebied.json'), 'w'))
print('landgebied klaar')
