/* Pruebas de los módulos compartidos del portal: glosario, tarjetas, QA de DOM y datos del explorador. */
const test = require('node:test');
const assert = require('node:assert/strict');
const imp = (p) => import('../frontend/js/' + p);
const fmtP = imp('fmt.js');

test('glossary: definitions from payload and "¿Cómo se mide?" block', async () => {
  const g = await imp('glossary.js');
  const defs = g.definitionsOf({ definitions: { ppda: { nombre: 'PPDA', definicion: 'Pases rivales <x>', formula: 'a/b' } } });
  assert.equal(defs.length, 1); assert.equal(defs[0].id, 'ppda');
  assert.deepEqual(g.definitionsOf(null), []);
  const byId = g.indexDefinitions(defs);
  const html = g.howMeasured(byId, 'ppda');
  assert.match(html, /¿Cómo se mide\?/); assert.match(html, /Pases rivales &lt;x&gt;/); assert.match(html, /#metodo\/ppda/);
  assert.equal(g.howMeasured(byId, 'no_existe'), '');
  const calls = []; const api = { tryJSON: async (p) => { calls.push(p); return { definitions: { a: { nombre: 'A' } } }; } };
  const m = await g.loadGlossary(api); assert.equal(m.a.nombre, 'A'); assert.deepEqual(calls, ['/api/framework']);
  const failing = { tryJSON: async () => { throw new Error('red'); } };
  assert.deepEqual(await g.loadGlossary(failing), {});
});

test('cards: finding separates hecho and interpretación, badges window, evidence', async () => {
  const c = await imp('cards.js'); const fmt = await fmtP;
  const ctx = { fmt, mode: 'dt' };
  const html = c.finding({ titulo: 'Presiona arriba', hecho: 'Roba 5 balones', interpretacion: 'Quiere recuperar pronto', evidencia: [{ id: 'rec_alta', n: 91 }], accion: 'Vigilar', window: 'epilogo' }, ctx);
  assert.match(html, /Hecho observado/); assert.match(html, /Interpretación/); assert.match(html, /Fuera de ventana oficial/);
  assert.match(html, /rec_alta/); assert.match(html, /n = 91/); assert.match(html, /Vigilar/);
  const fan = c.finding({ titulo: 'T', hecho: 'H', interpretacion: 'I', evidencia: [{ id: 'x', n: 3 }], window: 'oficial' }, { fmt, mode: 'aficionado' });
  assert.doesNotMatch(fan, /n = 3/, 'el detalle de evidencia es solo para DT');
  assert.doesNotMatch(fan, /Fuera de ventana/);
});

test('cards: "Ver datos" table, metric tile and window badge', async () => {
  const c = await imp('cards.js'); const fmt = await fmtP;
  const t = c.seeData(['Métrica', 'Valor'], [['xG', '1.2'], ['<b>', 's/d']]);
  assert.match(t, /<details class="seedata"><summary>Ver datos<\/summary>/); assert.match(t, /&lt;b&gt;/);
  assert.equal(c.seeData(['a'], []), '');
  const tile = c.metricTile({ id: 'xg', value: 1.0394, n: 27, unit: 'xG por partido', ref_pct: 37, ci: [0.9, 1.18], window: 'oficial' }, 'xG a favor', { fmt, mode: 'aficionado' });
  assert.match(tile, /1\.04/); assert.match(tile, /más que 37 de cada 100/); assert.doesNotMatch(tile, /0\.9 – 1\.18/);
  const tileDt = c.metricTile({ id: 'xg', value: 1.0394, n: 27, unit: 'xG por partido', ci: [0.9, 1.18], window: 'temprano' }, 'xG a favor', { fmt, mode: 'dt' });
  assert.match(tileDt, /0\.9 – 1\.18/); assert.match(tileDt, /n = 27/); assert.match(tileDt, /Fuera de ventana oficial/);
  assert.equal(c.windowBadge('oficial', fmt), '<span class="badge">Ventana oficial</span>');
  assert.match(c.windowBadge('epilogo', fmt), /badge out/, 'fuera de ventana = rayado tenue');
  assert.equal(c.windowBadge(null, fmt), '');
});

test('qa: DOM text scan flags english tokens, unknown, NaN and long decimals', async () => {
  const q = await imp('qa.js');
  assert.deepEqual(q.scanText('Presiona alto y roba 1.25 balones · 48%').issues, []);
  const r = q.scanText('Goalkeeper unknown NaN undefined 0.123 home Pass');
  const kinds = r.issues.map((i) => i.token);
  for (const t of ['Goalkeeper', 'unknown', 'NaN', 'undefined', '0.123', 'home', 'Pass']) assert.ok(kinds.includes(t), t);
  assert.deepEqual(q.scanText('Pase al área · casa · Pachuca').issues, []);
  assert.deepEqual(q.scanText('Igual a high_press_shots de extract').issues, [], 'identificadores de código no son texto crudo');
  assert.equal(q.countNumbers('n = 27 · 1.04 xG · más que 37 de cada 100'), 3, '«de cada 100» es parte de la frase');
  assert.equal(q.countNumbers('Sin números aquí'), 0);
  assert.equal(q.countNumbers('Temporada 2023/2024 · 34 partidos · desde 2021'), 1, 'años y temporadas son etiquetas');
});

test('explorer data: units from list payloads in both contracts', async () => {
  const d = await imp('explorer_data.js');
  const teams = d.unitsOf([{ team: 'América', n: 223, unidades: 8, entrenadores: ['André Jardine'] }], 'equipos');
  assert.equal(teams[0].name, 'América'); assert.equal(teams[0].key, 'america'); assert.equal(teams[0].n, 223);
  assert.equal(teams[0].seasons, 8); assert.deepEqual(teams[0].related, ['André Jardine']);
  const coaches = d.unitsOf([{ coach: 'André Jardine', n: 4, confianza: 'muy baja', muestra_chica: true, clubes: ['América', 'América'] }], 'dts');
  assert.equal(coaches[0].key, 'andre-jardine'); assert.equal(coaches[0].confidence, 'muy baja');
  assert.equal(coaches[0].small, true); assert.deepEqual(coaches[0].related, ['América']);
  const legacy = d.unitsOf({ items: [{ key: 'x', label: 'X', n: 30, confidence: 'alta', small_sample: false }] }, 'dts');
  assert.equal(legacy[0].name, 'X'); assert.equal(legacy[0].small, false);
  assert.deepEqual(d.unitsOf(null, 'dts'), []);
  assert.equal(d.slug('Jorge Guillermo Almada Álves'), 'jorge-guillermo-almada-alves');
});

test('explorer data: seasons, metric rows, traits and filter', async () => {
  const d = await imp('explorer_data.js');
  const metricas = { posesion: { id: 'posesion', value: 0.507, bruto: 0.5091, n: 27, unit: 'proporción', ci: [0.48, 0.53], ref_pct: 59 },
    presion: { id: 'presion', value: 9.3, bruto: 8.77, n: 27, unit: 'pases por acción', ci: [8.1, 10.5], ref_pct: 80 },
    contragolpe: { id: 'contragolpe', value: 0.71, bruto: 0.59, n: 27, unit: 'por partido', ci: [0.46, 0.96], ref_pct: 6 } };
  const detail = { team: 'América', temporadas: [{ temporada: '2021/2022', coach: 'Solari', n: 27, confianza: 'alta', ventana: 'oficial', prior: 'liga', desde: '2021-07-23', metricas }] };
  const seasons = d.seasonsOf(detail);
  assert.equal(seasons.length, 1); assert.equal(seasons[0].window, 'oficial');
  assert.equal(d.seasonsOf({ unidades: 8 }).length, 0, 'unidades numérico no son temporadas');
  assert.equal(d.seasonsOf({ linea_tiempo: [{ n: 1, metricas: {} }] }).length, 1);
  const rows = d.metricRows(seasons[0]);
  assert.equal(rows[0].id, 'posesion'); assert.equal(rows[0].raw, 0.5091); assert.ok(rows[0].label.length > 3);
  const traits = d.traits(seasons[0], 2);
  assert.deepEqual(traits.map((t) => t.id), ['contragolpe', 'presion']);
  assert.equal(traits[0].high, false); assert.equal(traits[1].high, true);
  assert.match(traits[1].text, /Presiona/);
  const list = [{ name: 'América', related: ['André Jardine'] }, { name: 'Pachuca', related: ['Almada'] }];
  assert.equal(d.filterUnits(list, 'jardin').length, 1); assert.equal(d.filterUnits(list, '').length, 2);
  assert.equal(d.filterUnits(list, 'PACH')[0].name, 'Pachuca');
});
const V2 = require('./fixtures/explorer_v2.js');
test('explorer data v2: units carry label, metrics list and identity; tenures and season units', async () => {
  const d = await imp('explorer_data.js');
  const [u] = d.unitsOf([V2.COACH]);
  assert.equal(u.name, 'André Jardine'); assert.equal(u.key, 'andre-jardine'); assert.equal(u.confidence, 'alta');
  assert.equal(u.identity.build, 'Equilibrado'); assert.equal(u.window, 'oficial');
  const rows = d.metricRows(u);
  assert.deepEqual(rows.slice(0, 3).map((r) => r.id), ['posesion', 'presion', 'xg'], 'orden de METRICS por clave');
  const px = rows.find((r) => r.id === 'presion');
  assert.equal(px.raw, 11.7187); assert.equal(px.fid, 'estilo_presion'); assert.equal(px.label, 'Intensidad de presión (PPDA)');
  const bp = rows.find((r) => r.id === 'bp_xg'); assert.equal(bp.value, null); assert.match(bp.motivo, /sin dato/);
  assert.deepEqual(d.traits(u, 2).map((t) => t.id), ['xg', 'xga']);
  const ten = d.seasonsOf(V2.COACH);
  assert.equal(ten.length, 2); assert.equal(ten[0].label, 'Atlético San Luis · André Jardine'); assert.equal(ten[1].window, 'epilogo');
  assert.equal(ten[1].prior, 'carrera'); assert.equal(d.metricRows(ten[1]).length, 5);
  const seasons = d.seasonsOf(V2.TEAM);
  assert.equal(seasons.length, 1); assert.equal(seasons[0].label, '2023/2024'); assert.equal(seasons[0].coach, 'André Jardine');
  assert.equal(d.unitsOf([{ team: 'Atlante', n: 11 }])[0].confidence, 'baja', 'confianza por n si el payload no la trae');
  assert.deepEqual(d.identityChips(V2.IDENTITY), ['Equilibrado', 'Bloque bajo', 'Por dentro']);
  assert.deepEqual(d.identityChips(null), []);
});
