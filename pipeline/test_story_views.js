/* Vistas Historia, Almada y Partidos (T-12 a T-14) con payloads sintéticos y un DOM mínimo. */
const test = require('node:test');
const assert = require('node:assert/strict');
function fakeRoot() {
  const kids = {};
  return { innerHTML: '', querySelector: (sel) => (kids[sel] = kids[sel] || { innerHTML: '', addEventListener() {}, querySelectorAll: () => [] }), kids };
}
const strip = (h) => h.replace(/<details[\s\S]*?<\/details>/g, ' ').replace(/<[^>]+>/g, ' ');
async function ctx(routes, mode = 'aficionado', params = []) {
  const fmt = await import('../frontend/js/fmt.js');
  return { fmt, mode, params, api: { tryJSON: async (p) => (p in routes ? routes[p] : null) }, navigate() {} };
}
const EV = { id: 'xg', value: 1.4, n: 91, unit: 'xG por partido', window: 'oficial' };
const F = (id, titulo, extra = {}) => Object.assign({ id, titulo, hecho: 'Hecho 1.4 con n 91.', interpretacion: 'Lectura corta.', evidencia: [EV], accion: 'Vigilar.', window: 'oficial' }, extra);
const STORY = { titulo: 'La historia de André Jardine en el América', partidos: 91, nota: 'Descriptivo.', capitulos: [
  { id: 'portada', orden: 1, titulo: 'Portada', hallazgos: [F('a', 'Sacó 1.93 puntos por partido'), F('b', 'Titular con 1 2 3 4 números')],
    aficionado: { conclusion: 'Conclusión.', curioso: 'Dato curioso uno.', visual: 'kpi_cards' } },
  { id: 'lo_que_mas_dolio', orden: 6, titulo: 'Lo que más dolió', hallazgos: [F('dolor', 'Las 3 jugadas', { detalle: { jugadas: [] } })],
    aficionado: { conclusion: 'Cuesta.', curioso: null, visual: 'danger_plays' } },
  { id: 'epilogo', orden: 12, titulo: 'Epílogo', hallazgos: [F('e', 'Fuera de ventana', { window: 'epilogo' })], aficionado: { conclusion: 'Epílogo.', curioso: null, visual: 'epilogue_compare' } }] };
const KPI = (id, nombre, value, pct, over = {}) => Object.assign({ id, nombre, mejor: 'alto', value, n: 91, unit: '% de acciones en último tercio', source: 'eventos', window: 'oficial', ref_pct: pct, pct_bueno: pct, kpi: 1 }, over);
const PLAY = { match_id: 1, fecha: '2024-04-07', rival: 'Santos Laguna', minuto: 58, gol: true, xg_posesion: 0.58, obv_max: 0.5, duracion_s: 17, etiquetas: ['transicion'],
  hecho: "Min 58' vs Santos Laguna.", interpretacion: 'El rival llegó a tiro en 17 s.', acciones: [{ accion: 'Recuperación', equipo: 'rival', x: 60, y: 30 }, { accion: 'Conducción', equipo: 'propio', x: 20, y: 40, x_fin: 10, y_fin: 40 }],
  tiros: [{ x: 8, y: 40, xg: 0.58, gol: true }] };
const ROUTES = { '/api/story/jardine': STORY, '/api/kpis/ame_jardine': { kpis: { oficial: [KPI('field_tilt', 'Dominio territorial', 59.8, 99)] } },
  '/api/kpis/ame_jardine_epi': { kpis: { epilogo: [KPI('field_tilt', 'Dominio territorial', 63.8, 95, { window: 'epilogo' })] } },
  '/api/entities/ame_jardine/analysis': { dangerous: { ventanas: { oficial: { juego_abierto: [PLAY], balon_parado: [] } } } },
  '/api/teams/ame_jardine': { style: { posesion: 81 }, identity: { build: 'Pase corto', attack: 'Mixto', defense: 'Bloque bajo', tags: [] }, n: 91 } };

test('story: aficionado shows conclusion, visual and curious fact; hides facts and crowded or detail-only cards', async () => {
  const v = await import('../frontend/views/story.js'); const root = fakeRoot();
  await v.render(root, await ctx(ROUTES));
  const h = root.innerHTML;
  assert.match(h, /id="cap-portada"/); assert.match(h, /Dato curioso/); assert.match(h, /Conclusión\./);
  assert.match(h, /Sacó 1\.93 puntos/); assert.doesNotMatch(h, /Titular con 1 2 3 4/);          // más de 3 números → solo DT
  assert.doesNotMatch(h, /Las 3 jugadas/);                                                    // su detalle ya se dibuja
  assert.doesNotMatch(h, /Hecho observado/); assert.doesNotMatch(h, /undefined|NaN|unknown/);
  assert.match(h, /class="tile"/); assert.match(h, /59\.8%/); assert.doesNotMatch(h, /5,979|5979/);   // «% de …» de eventos no se multiplica
  assert.match(h, /Fuera de ventana oficial/);
});
test('story: DT shows Hecho observado / Interpretación with evidence and numbered plays', async () => {
  const v = await import('../frontend/views/story.js'); const root = fakeRoot();
  await v.render(root, await ctx(ROUTES, 'dt'));
  const h = root.innerHTML;
  assert.match(h, /Hecho observado/); assert.match(h, /Interpretación/); assert.match(h, /Evidencia/);
  assert.match(h, /Titular con 1 2 3 4/); assert.match(h, /Las 3 jugadas/); assert.match(h, /<text x="60" y="30">1<\/text>/);
  assert.match(h, /xG de la posesión 0\.58/);
});
test('story: aficionado cards never exceed 3 numbers and the plays have no numbered marks', async () => {
  const v = await import('../frontend/views/story.js'); const q = await import('../frontend/js/qa.js'); const root = fakeRoot();
  await v.render(root, await ctx(ROUTES));
  for (const card of root.innerHTML.split('<article').slice(1)) assert.ok(q.countNumbers(strip(card.split('</article>')[0])) <= 3, strip(card));
  assert.doesNotMatch(root.innerHTML, /<text x="60"/);
});
test('story: missing data shows the construction state, never a broken page', async () => {
  const v = await import('../frontend/views/story.js'); const root = fakeRoot();
  await v.render(root, await ctx({}));
  assert.match(root.innerHTML, /Datos en construcción/); assert.doesNotMatch(root.innerHTML, /undefined|NaN/);
});

const ALMADA = { titulo: '¿Qué cambia con Almada?', partidos: 10, nota: 'Evidencia temprana: pocos partidos.', capitulos: [
  { id: 'almada_pachuca', orden: 1, titulo: 'Almada en el Pachuca', hallazgos: [F('almada_pachuca', 'En el Pachuca armó pase corto')], aficionado: { conclusion: 'Huella.', visual: 'identity_compare' } },
  { id: 'almada_america', orden: 2, titulo: 'Sus primeros partidos', hallazgos: [F('almada_america_temprano', 'Primeros partidos: 1 de 2 rasgos', { window: 'temprano' })],
    aficionado: { conclusion: 'Temprano.', visual: 'raw_vs_shrunk' } }] };
const TENURES = [{ n: 10, entidades: [{ id: 'ame_almada' }], metrics: { xg: { n: 10, value: 1.38, raw: 1.47, prior_value: 1.2, ci: [1.19, 1.57] } } },
  { n: 139, entidades: [{ id: 'pac_almada' }], metrics: { xg: { n: 139, value: 1.1, raw: 1.1 } } }];
const AROUTES = { '/api/story/almada': ALMADA, '/api/explorer/catalog': { metricas: [{ id: 'xg', nombre: 'xG a favor', unit: 'xG por partido' }] },
  '/api/explorer/coaches': [{ key: 'jorge-almada' }], '/api/explorer/coach/jorge-almada': { tenencias: TENURES },
  '/api/kpis/pac_almada': { kpis: { oficial: [KPI('field_tilt', 'Dominio territorial', 53, 69)] } }, '/api/kpis/ame_jardine': { kpis: { oficial: [KPI('field_tilt', 'Dominio territorial', 59.8, 99)] } },
  '/api/teams/pac_almada': { style: { posesion: 68 }, n: 139 }, '/api/teams/ame_jardine': { style: { posesion: 81 }, n: 91 } };

test('almada: early evidence is flagged and raw vs shrunk values are drawn with interval and the Pachuca mark', async () => {
  const v = await import('../frontend/views/almada.js'); const root = fakeRoot();
  await v.render(root, await ctx(AROUTES));
  const h = root.innerHTML;
  assert.match(h, /Evidencia temprana/); assert.match(h, /Fuera de ventana oficial/);
  assert.match(h, /class="ch-ci"/); assert.match(h, /ch-dot raw/); assert.match(h, /class="ch-ref"/);
  assert.match(h, /Posesión · Pachuca/); assert.match(h, /Dominio territorial · Jardine/);
  assert.doesNotMatch(h, /undefined|NaN|unknown/);
});
test('almada: without the story it shows the construction state', async () => {
  const v = await import('../frontend/views/almada.js'); const root = fakeRoot();
  await v.render(root, await ctx({}));
  assert.match(root.innerHTML, /Datos en construcción/);
});

const MATCHES = { partidos: [
  { match_id: 11, fecha: '2024-04-07', torneo: 'Cl2024', rival: 'Santos Laguna', localia: 'visita', actual: 'E', veredicto: 'merecio_ganar', marcador: { propio: 1, rival: 1 }, window: 'oficial' },
  { match_id: 12, fecha: '2024-03-01', torneo: 'Cl2024', rival: 'Toluca', localia: 'local', actual: 'G', veredicto: 'parejo', marcador: { propio: 2, rival: 0 }, window: 'oficial' },
  { match_id: 13, fecha: '2023-08-01', torneo: 'Ap2023', rival: 'Pumas', localia: 'local', actual: 'P', veredicto: 'merecio_perder', marcador: { propio: 0, rival: 1 }, window: 'oficial' }] };
const CARD = { match_id: 11, actual: 'E', points: 1, xpts: 2.03, localia: 'visita', p: { G: 0.6, E: 0.24, P: 0.16 }, p_actual: 0.24, sorpresivo: false, xg: { propio: 1.96, rival: 1.1 },
  penales_xg: { propio: 0, rival: 0 }, dominio: { xg_share: 0.64, field_tilt: 0.8 }, fecha: '2024-04-07', window: 'oficial', torneo: 'Cl2024', equipo: 'América', rival: 'Santos Laguna',
  textos: { veredicto: { merecio_ganar: 'Mereció ganar' }, balance: { por_debajo: 'Mereció más puntos de los que sacó.' }, resultado: { E: 'Empató' } },
  ficha: { marcador: { propio: 1, rival: 1 }, momentos: [{ periodo: 2, minuto: 58, equipo: 'rival', tipo: 'gol', xg: 0.58, jugador: 'X' }],
    xg_acumulado: { periodo: [1, 1, 1, 2], minuto: [0, 20, 48, 45], propio: [0, 0.1, 0.2, 0.5], rival: [0.1, 0.1, 0.3, 0.6] },
    datos_curiosos: ['Uno.', 'Dos.', 'Tres.'], merecio: { veredicto: 'merecio_ganar', texto: 'Con estas ocasiones ganaba 60 de cada 100 veces, empataba 24 y perdía 16.', balance: 'por_debajo' } } };

test('matches list: sorted newest first, filterable list and links to the card', async () => {
  const v = await import('../frontend/views/match.js'); const root = fakeRoot();
  await v.render(root, await ctx({ '/api/entities/ame_jardine/matches': MATCHES, '/api/entities': [{ id: 'ame_jardine', label: 'América · Jardine' }] }));
  const h = root.kids['#m-list'].innerHTML || root.innerHTML;
  const all = root.innerHTML;
  assert.match(all, /#partido\/11/); assert.match(all, /1–1/); assert.match(all, /Empató/); assert.match(all, /Mereció ganar/);
  assert.ok(all.indexOf('Santos Laguna') < all.indexOf('Toluca') && all.indexOf('Toluca') < all.indexOf('Pumas'), 'más reciente primero');
  assert.match(all, /<select id="f-ent"/); assert.doesNotMatch(all, /undefined|NaN/); assert.ok(h);
});
test('match card: score, deserved-to-win block, xG chart with continuing minutes, key moments and 3 curious facts', async () => {
  const v = await import('../frontend/views/match.js'); const root = fakeRoot();
  await v.render(root, await ctx({ '/api/matches/11': CARD }, 'aficionado', ['11']));
  const h = root.innerHTML;
  assert.match(h, /Santos Laguna 1–1 América/); assert.match(h, /¿Mereció ganar\?/); assert.match(h, /Mereció ganar/);
  assert.match(h, /no un pronóstico/); assert.match(h, /ch-line rival/); assert.match(h, /Momentos clave/); assert.match(h, /Datos curiosos/);
  assert.match(h, /xG acumulado: 1\.96 contra 1\.1/); assert.doesNotMatch(h, /Ver datos del partido/);
  const q = await import('../frontend/js/qa.js');
  for (const card of h.split('<article').slice(1)) assert.ok(q.countNumbers(strip(card.split('</article>')[0])) <= 3, strip(card));
  const dt = fakeRoot(); await v.render(dt, await ctx({ '/api/matches/11': CARD }, 'dt', ['11']));
  assert.match(dt.innerHTML, /Ver datos del partido/); assert.match(dt.innerHTML, /60% \/ 24% \/ 16%/);
});
test('match card: unknown match shows a friendly message', async () => {
  const v = await import('../frontend/views/match.js'); const root = fakeRoot();
  await v.render(root, await ctx({}, 'aficionado', ['999']));
  assert.match(root.innerHTML, /No encontramos este partido/);
});

const COACH = { key: 'jorge-almada', label: 'Jorge Almada', n: 158, confidence: 'alta', small_sample: false, window: 'oficial', desde: '2021-07-24', hasta: '2025-05-11', clubes: ['Pachuca', 'América'],
  identity: { build: 'Pase corto', defense: 'Presión alta', attack: 'Mixto', tags: ['Letal al contragolpe'] },
  metrics: { posesion: { id: 'posesion', value: 0.55, raw: 0.56, n: 158, unit: '% del balón', source: 'team-stats', window: 'oficial', ref_pct: 81, ci: [0.53, 0.57] },
    contragolpe: { id: 'contragolpe', value: 0.5, raw: 0.4, n: 158, unit: 'por partido', source: 'team-stats', window: 'oficial', ref_pct: 93, ci: [0.3, 0.7] } },
  tenencias: [{ team: 'Pachuca', n: 138, confidence: 'alta', small_sample: false, window: 'oficial', desde: '2022-01-07', hasta: '2025-05-11', entidades: [{ id: 'pac_almada', window: 'oficial' }] },
    { team: 'América', n: 10, confidence: 'baja', small_sample: true, window: 'temprano', desde: '2026-07-19', hasta: '2026-10-11', entidades: [{ id: 'ame_almada', window: 'temprano' }] }] };
const CROUTES = { '/api/explorer/coach/jorge-almada': COACH,
  '/api/kpis/pac_almada': { kpis: { oficial: [KPI('field_tilt', 'Dominio territorial', 53, 69)] } },
  '/api/kpis/ame_almada': { kpis: { temprano: [KPI('field_tilt', 'Dominio territorial', 60.5, 99, { window: 'temprano' })] } } };

test('coach: header, five traits in plain words (Aficionado) and the career timeline with small-sample warning', async () => {
  const v = await import('../frontend/views/coach.js'); const q = await import('../frontend/js/qa.js'); const root = fakeRoot();
  await v.render(root, await ctx(CROUTES, 'aficionado', ['jorge-almada']));
  const h = root.innerHTML;
  assert.match(h, /Jorge Almada/); assert.match(h, /Cómo juega, en cinco rasgos/); assert.match(h, /Tiene mucho el balón|Remata mucho al contragolpe/);
  assert.match(h, /Pachuca/); assert.match(h, /Muestra pequeña/); assert.match(h, /Fuera de ventana oficial/); assert.match(h, /class="tl-bar"/);
  assert.doesNotMatch(h, /de cada 100 equipos/); assert.doesNotMatch(h, /undefined|NaN|unknown/);
  for (const card of h.split('<article').slice(1)) assert.ok(q.countNumbers(strip(card.split('</article>')[0])) <= 3, strip(card));
  const dt = fakeRoot(); await v.render(dt, await ctx(CROUTES, 'dt', ['jorge-almada']));
  assert.match(dt.innerHTML, /más que 81 de cada 100/); assert.match(dt.innerHTML, /Ver datos de los rasgos/);
});
test('coach: unknown or missing key shows a friendly state', async () => {
  const v = await import('../frontend/views/coach.js');
  let root = fakeRoot(); await v.render(root, await ctx({}, 'aficionado', ['nadie']));
  assert.match(root.innerHTML, /No encontramos a este entrenador/);
  root = fakeRoot(); await v.render(root, await ctx({}, 'aficionado', []));
  assert.match(root.innerHTML, /Elige un entrenador/);
});

const FW = { definitions: { ppda: { nombre: 'PPDA', definicion: 'Pases rivales por acción defensiva', unidad: 'pases', limites: 'Solo campo rival', fuente: 'eventos', formula: 'a/b' },
  field_tilt: { nombre: 'Field tilt', definicion: 'Dominio territorial', unidad: '%', limites: 'x', fuente: 'eventos' } },
  kpis: [{ id: 'field_tilt', nombre: 'Dominio territorial', apoyo: [], mejor: 'alto' }, { id: 'perdida_costosa', nombre: 'Pérdidas costosas por partido', apoyo: ['tipo_error'], mejor: 'bajo' }],
  assumptions: ['La posesión se aproxima con el identificador de StatsBomb.'], scope: ['Ventana oficial: Apertura 2021 a Clausura 2025.'],
  limits: ['Las asociaciones son descriptivas, no causales.'], thresholds: { REC_ALTA_X: 80, CI_LEVEL: 0.8 }, windows: ['oficial', 'epilogo', 'temprano'], official_end: '2025-06-30' };

test('method: assumptions, scope, limits and the seven KPIs sit before the glossary', async () => {
  const v = await import('../frontend/views/method.js'); const root = fakeRoot();
  await v.render(root, await ctx({ '/api/framework': FW }));
  const h = root.innerHTML + root.kids['#defs'].innerHTML + root.kids['#method-intro'].innerHTML;
  assert.match(h, /Supuestos/); assert.match(h, /La posesión se aproxima/); assert.match(h, /Alcance/); assert.match(h, /Las asociaciones son descriptivas/);
  assert.match(h, /Dominio territorial/); assert.match(h, /Pérdidas costosas por partido/); assert.match(h, /#metodo\/field_tilt/);
  assert.match(h, /mejor es tener menos|menos es mejor/i); assert.doesNotMatch(h, /Umbrales con nombre/);
  const dt = fakeRoot(); await v.render(dt, await ctx({ '/api/framework': FW }, 'dt'));
  assert.match(dt.kids['#method-intro'].innerHTML, /Umbrales con nombre/); assert.match(dt.kids['#method-intro'].innerHTML, /REC_ALTA_X/);
});
test('method: old payload without the new blocks still renders the glossary', async () => {
  const v = await import('../frontend/views/method.js'); const root = fakeRoot();
  await v.render(root, await ctx({ '/api/framework': { definitions: FW.definitions } }));
  assert.match(root.kids['#defs'].innerHTML, /PPDA/); assert.doesNotMatch(root.kids['#method-intro'].innerHTML, /undefined|NaN/);
});
