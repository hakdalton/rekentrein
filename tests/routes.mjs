// Routetest: rekent een paar vaste reizen door met de code uit index.html. Draaien: node tests/routes.mjs
import fs from 'node:fs';
const html = fs.readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const data = html.match(/<script type="application\/json" id="netwerk">(.*?)<\/script>/s)[1];
const a = html.indexOf('/* =========================================================\n   Spoornet van Nederland'), b = html.indexOf('/* ---------- sprongen op de getallenlijn');
globalThis.window = {NETWERK: JSON.parse(data)};
const f = new Function('clamp', 'R', 'SIGSP', 'RITTEN', 'prog', '$', html.slice(a, b) + '; return {NET, maakReis};');
const {NET, maakReis} = f((x, lo, hi) => Math.max(lo, Math.min(hi, x)), lo => lo, 700, [], {}, () => null);
const st = n => NET.opNaam.get(n.toLowerCase());
let fout = 0;
const verwacht = [
  ['Den Haag Centraal', 'Amersfoort Centraal', true, ['Gouda', 'Utrecht Centraal'], 75, 90],
  ['Den Haag Centraal', 'Groningen', true, ['Zwolle'], 230, 280],
  ['Den Haag Centraal', 'Maastricht', true, ['Eindhoven Centraal'], 210, 245],
  ['Roosendaal', 'Vlissingen', false, ['Goes'], 65, 85],
];
for (const [van, naar, ic, via, kmMin, kmMax] of verwacht){
  const r = maakReis(st(van), st(naar), ic), namen = r ? r.stops.map(s => s.naam) : [];
  const ok = r && via.every(v => namen.includes(v)) && r.km >= kmMin && r.km <= kmMax && r.S.every((s, i) => i === 0 || s - r.S[i-1] >= 2800);
  if (!ok) fout++;
  console.log(ok ? 'ok  ' : 'FOUT', van, '->', naar, r ? `${Math.round(r.km)} km, ${namen.length - 1} ritten: ${namen.join(', ')}` : 'geen route');
}
let geen = 0; for (let i = 0; i < 150; i++){ const a = NET.ST[(i*37) % NET.ST.length], b = NET.ST[(i*101 + 7) % NET.ST.length]; if (a !== b && !maakReis(a, b, false)) geen++; }
console.log(geen ? `FOUT ${geen} van 150 willekeurige reizen zonder route` : 'ok   150 willekeurige reizen hebben een route');
process.exit(fout || geen ? 1 : 0);
