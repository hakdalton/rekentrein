# Rekentrein

Een 3D-rekenspel voor groep 5. Als machinist rijd je met een NS-trein over het echte Nederlandse spoornet. Kies een les, een vertrek- en eindstation en Intercity of Sprinter. Elk sein gaat op groen met een goede som. De sommen volgen de onderwerpen van blok 1 van groep 5: tientallen, aanvullen, rijgen, keersommen, klokkijken, getallen tot 1000 en rekenpuzzels.

Spelen: https://hakdalton.github.io/rekentrein/ (voeg `?naam=Jouwnaam` toe aan de link, dan noemt het spel je bij je naam).

## Hoe het werkt
- Alles staat in `index.html` (Three.js 0.160 via jsDelivr). Voortgang blijft in de browser.
- Spoornet: `data/netwerk.json`, gemaakt met `python3 tools/haal_spoor.py` en `python3 tools/bouw_netwerk.py`, daarna als `<script id="netwerk">` in `index.html` gezet.
- Routes: kortste pad over de sporen, zonder scherpe bochten op wissels; kopmaken alleen op een station. Test: `node tests/routes.mjs`.
- Gebouwen rond de stations worden tijdens het rijden opgehaald uit de 3DBAG.

## Bronnen
- Spoor: © OpenStreetMap-bijdragers, ODbL
- Stations: Rijden de Treinen, CC BY 4.0
- Gebouwen: 3DBAG door 3DGI, CC BY 4.0
