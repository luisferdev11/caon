/* Vistas explorer/method con DOM mínimo simulado. */
const test = require('node:test');
const assert = require('node:assert/strict');
function fakeRoot() {
  const kids = {};
  return { innerHTML: '', querySelector: (sel) => (kids[sel] = kids[sel] || { innerHTML: '', addEventListener() {} }), kids };
}
async function ctx(payload, mode = 'aficionado', params = []) {
  const fmt = await import('../frontend/js/fmt.js');
  return { fmt, mode, params, api: { tryJSON: async () => payload }, navigate() {} };
}
test('explorer shows construction state when data missing', async () => {
  const v = await import('../frontend/views/explorer.js'); const root = fakeRoot();
  await v.render(root, await ctx(null));
  assert.match(root.kids['#exp-list'].innerHTML, /Datos en construcción/);
});
const strip = (h) => h.replace(/<details[\s\S]*?<\/details>/g, ' ').replace(/<[^>]+>/g, ' ');
const cardsOf = (h) => h.split('<article').slice(1);
const SEASON = (over = {}) => ({ team: 'América', coach: 'André Jardine', temporada: '2023/2024', n: 34, confianza: 'alta', muestra_chica: false,
  ventana: 'oficial', prior: 'carrera', desde: '2023-07-01', hasta: '2024-05-26', metricas: {
    posesion: { id: 'posesion', value: 0.55, bruto: 0.56, n: 34, unit: 'proporción', ci: [0.53, 0.57], source: 'team-stats', window: 'oficial', ref_pct: 81 },
    presion: { id: 'presion', value: 8.1, bruto: 7.9, n: 34, unit: 'pases por acción', ci: [7.5, 8.7], source: 'team-stats', window: 'oficial', ref_pct: 90 },
    contragolpe: { id: 'contragolpe', value: 0.5, bruto: 0.4, n: 34, unit: 'por partido', ci: [0.3, 0.7], source: 'team-stats', window: 'oficial', ref_pct: 45 } }, ...over });
test('explorer lists real coaches (explorer.v1) with confidence, small sample and detail link', async () => {
  const v = await import('../frontend/views/explorer.js'); const root = fakeRoot();
  const data = [{ coach: 'André Jardine', n: 183, confianza: 'alta', muestra_chica: false, clubes: ['Atlético San Luis', 'América', 'América'] },
    { coach: 'Alejandro Corona', n: 1, confianza: 'muy baja', muestra_chica: true, clubes: ['León'] }];
  await v.render(root, await ctx(data, 'aficionado', ['dts']));
  const html = root.kids['#exp-list'].innerHTML;
  assert.match(html, /André Jardine/); assert.match(html, /183 partidos/); assert.match(html, /Confianza muy baja/);
  assert.match(html, /Muestra pequeña/); assert.match(html, /#explorador\/dts\/andre-jardine/); assert.match(html, /Atlético San Luis · América/);
  assert.ok(html.indexOf('André Jardine') < html.indexOf('Alejandro Corona'), 'ordenado por partidos');
  assert.doesNotMatch(html, /undefined|NaN|unknown|sin calcular/);
});
test('explorer team detail: seasons with traits (fan) and full table with interval/raw/prior (DT)', async () => {
  const v = await import('../frontend/views/explorer.js');
  const detail = { team: 'América', n: 223, entrenadores: ['André Jardine'], temporadas: [SEASON(), SEASON({ temporada: '2025/2026', ventana: 'epilogo', desde: '2025-07-12', n: 4, confianza: 'muy baja', muestra_chica: true })] };
  const calls = []; const c = await ctx(detail, 'aficionado', ['equipos', 'america']); c.api.tryJSON = async (p) => { calls.push(p); return p === '/api/framework' ? null : detail; };
  let root = fakeRoot(); await v.render(root, c);
  assert.ok(calls.includes('/api/explorer/team/america'), calls.join());
  let html = root.kids['#exp-body'].innerHTML;
  assert.match(html, /Presiona con intensidad: más que 90 de cada 100 equipos/); assert.match(html, /Fuera de ventana oficial/); assert.match(html, /Muestra pequeña/);
  const q = await import('../frontend/js/qa.js');
  for (const card of cardsOf(html)) assert.ok(q.countNumbers(strip(card)) <= 3, 'Aficionado ≤3 números: ' + strip(card));
  assert.doesNotMatch(html, /8\.7|Intervalo/);
  root = fakeRoot(); c.mode = 'dt'; await v.render(root, c);
  html = root.kids['#exp-body'].innerHTML;
  assert.match(html, /Intervalo 80%/); assert.match(html, /7\.5 – 8\.7/); assert.match(html, /53% – 57%/); assert.match(html, /Referencia previa: su carrera anterior/);
  assert.match(html, /más que 81 de cada 100/); assert.doesNotMatch(html, /undefined|NaN|unknown/);
});
test('explorer detail alias #equipo/<key> and missing seasons fallback', async () => {
  const v = await import('../frontend/views/explorer.js'); const root = fakeRoot();
  const calls = []; const c = await ctx(null, 'aficionado', ['america']);
  c.api.tryJSON = async (p) => { calls.push(p); return p.startsWith('/api/explorer/') ? { team: 'América', n: 223, unidades: 8, entrenadores: ['André Jardine'] } : null; };
  await v.render(root, c);
  assert.ok(calls.includes('/api/explorer/team/america'));
  const html = root.kids['#exp-body'].innerHTML;
  assert.match(html, /América/); assert.match(html, /223 partidos/); assert.match(html, /detalle por temporada/i);
  assert.doesNotMatch(html, /undefined|NaN/);
  const root2 = fakeRoot(); const c2 = await ctx(null, 'dt', ['dts', 'nadie']);
  await v.render(root2, c2);
  assert.match(root2.kids['#exp-body'].innerHTML, /No encontramos/);
});
test('method lists framework definitions with ids', async () => {
  const v = await import('../frontend/views/method.js'); const root = fakeRoot();
  await v.render(root, await ctx({ definitions: { ppda: { nombre: 'PPDA', definicion: 'Pases rivales por acción defensiva', unidad: 'pases', limites: 'Solo campo rival' } } }));
  const html = root.kids['#defs'].innerHTML;
  assert.match(html, /PPDA/); assert.match(html, /ppda/); assert.match(html, /Solo campo rival/);
});
test('charts require title and unit and show n/window badges', async () => {
  const c = await import('../frontend/js/charts.js');
  assert.throws(() => c.barsCI({ unit: 'xG' }, []));
  const html = c.barsCI({ title: 'Genera más que la liga', unit: 'xG por partido', n: 38, window: 'epilogo' }, [{ label: 'América', value: 1.5, ci: [1.2, 1.8], ref: 1.3 }]);
  assert.match(html, /n = 38/); assert.match(html, /Fuera de ventana oficial/);
  assert.match(c.heatGrid({ title: 'Recupera arriba', unit: '% de recuperaciones', n: 10, window: 'oficial' }, new Array(18).fill(1)), /izquierda a derecha/);
});
const V2 = require('./fixtures/explorer_v2.js');
test('explorer.v2 list: names, identity, traits and confidence (fan) · shrunk values with interval (DT)', async () => {
  const v = await import('../frontend/views/explorer.js'); const q = await import('../frontend/js/qa.js');
  let root = fakeRoot(); await v.render(root, await ctx([V2.SMALL, V2.COACH], 'aficionado', ['dts']));
  let html = root.kids['#exp-list'].innerHTML;
  assert.match(html, /André Jardine/); assert.match(html, /145 partidos/); assert.match(html, /Confianza alta/);
  assert.match(html, /Equilibrado/); assert.match(html, /Bloque bajo/); assert.match(html, /Por dentro/);
  assert.match(html, /Genera mucho peligro: más que 92 de cada 100 equipos/);
  assert.doesNotMatch(html, /Sin métricas publicadas|sin calcular|undefined|NaN|null/);
  assert.ok(html.indexOf('André Jardine') < html.indexOf('Alejandro Corona'));
  for (const card of cardsOf(html)) assert.ok(q.countNumbers(strip(card)) <= 3, 'Aficionado ≤3 números: ' + strip(card));
  root = fakeRoot(); await v.render(root, await ctx([V2.COACH], 'dt', ['dts']));
  html = root.kids['#exp-list'].innerHTML;
  assert.match(html, /1\.41/); assert.match(html, /1\.35 – 1\.47/); assert.match(html, /53% – 55%/); assert.match(html, /54%/);
  assert.match(html, /Muy vertical/); assert.match(html, /Valor ajustado/); assert.match(html, /bruto 1\.4/);
  assert.doesNotMatch(html, /undefined|NaN|null/);
});
test('explorer.v2 coach detail: summary, motivo for missing metric and tenures with window and prior', async () => {
  const v = await import('../frontend/views/explorer.js'); const q = await import('../frontend/js/qa.js');
  const calls = []; const c = await ctx(null, 'aficionado', ['dts', 'andre-jardine']);
  c.api.tryJSON = async (p) => { calls.push(p); return p === '/api/explorer/coach/andre-jardine' ? V2.COACH : null; };
  let root = fakeRoot(); await v.render(root, c);
  assert.ok(calls.includes('/api/explorer/coach/andre-jardine'), calls.join());
  let html = root.kids['#exp-body'].innerHTML;
  assert.match(html, /Atlético San Luis · André Jardine/); assert.match(html, /Fuera de ventana oficial/); assert.match(html, /#explorador\/dts"/);
  for (const card of cardsOf(html)) assert.ok(q.countNumbers(strip(card)) <= 3, 'Aficionado ≤3 números: ' + strip(card));
  c.mode = 'dt'; root = fakeRoot(); await v.render(root, c);
  html = root.kids['#exp-body'].innerHTML;
  assert.match(html, /Referencia previa: su carrera anterior/); assert.match(html, /sin dato en team-stats/i);
  assert.match(html, /11\.18 – 12\.2/); assert.match(html, /#metodo\/estilo_presion/);
  assert.doesNotMatch(html, /undefined|NaN|>null</);
});
test('explorer.v2 team detail lists season units', async () => {
  const v = await import('../frontend/views/explorer.js');
  const c = await ctx(null, 'aficionado', ['equipos', 'america']);
  c.api.tryJSON = async (p) => (p === '/api/explorer/team/america' ? V2.TEAM : null);
  const root = fakeRoot(); await v.render(root, c);
  const html = root.kids['#exp-body'].innerHTML;
  assert.match(html, /2023\/2024/); assert.match(html, /André Jardine/); assert.match(html, /Fernando Ortiz/);
});
test('method: #metodo/<id> puts that definition first and marks it; unknown id shows a note', async () => {
  const v = await import('../frontend/views/method.js');
  const payload = { definitions: { coord: { nombre: 'Coordenadas', definicion: 'Campo 120×80' }, ppda: { nombre: 'PPDA', definicion: 'Pases rivales', formula: 'a/b', fuente: 'eventos' } } };
  let root = fakeRoot(); await v.render(root, await ctx(payload, 'dt', ['ppda']));
  let html = root.kids['#defs'].innerHTML;
  assert.ok(html.indexOf('PPDA') < html.indexOf('Coordenadas'), 'la definición pedida va primero');
  assert.match(html, /class="def focus" id="def-ppda"/, 'glosario: entradas de referencia, no tarjetas de datos'); assert.match(html, /Fórmula/); assert.match(html, /Eventos/);
  root = fakeRoot(); await v.render(root, await ctx(payload, 'aficionado', ['estilo_xg']));
  html = root.kids['#defs'].innerHTML;
  assert.match(html, /No hay una definición publicada con el identificador «estilo_xg»/); assert.doesNotMatch(html, /Fórmula/);
});
test('dotPlot: dot survives preserveAspectRatio="none" (round-cap line, not a stretched circle)', async () => {
  const c = await import('../frontend/js/charts.js');
  const html = c.dotPlot({ title: 'Se separa de la liga', unit: 'percentil', n: 10, window: 'oficial' }, [{ label: 'Posesión', pct: 76 }, { label: 'X', pct: 30, side: 'rival' }]);
  assert.doesNotMatch(html, /<circle/); assert.match(html, /<line x1="76" x2="76" y1="6" y2="6" class="ch-dot"\/>/); assert.match(html, /class="ch-dot rival"/);
});
