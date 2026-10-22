/* Pruebas de frontend/js/fmt.js (formato es-MX). */
const test = require('node:test');
const assert = require('node:assert/strict');
const load = () => import('../frontend/js/fmt.js');

test('numbers use es-MX with at most 2 decimals and null-safe placeholder', async () => {
  const f = await load();
  assert.equal(f.num(1234.567), '1,234.57');
  assert.equal(f.num(0.1), '0.1');
  assert.equal(f.num(2, 0), '2');
  assert.equal(f.num(null), 's/d');
  assert.equal(f.num(NaN), 's/d');
  assert.equal(f.num(1 / 3, 5), '0.33');
});
test('percent, minutes, dates', async () => {
  const f = await load();
  assert.equal(f.pct(0.456), '46%');
  assert.equal(f.pct(0.456, 1), '45.6%');
  assert.equal(f.pct(null), 's/d');
  assert.equal(f.minutes(90), '90 min');
  assert.equal(f.minute(45.2), "45'");
  assert.equal(f.date('2024-08-03'), '3 ago 2024');
  assert.equal(f.date(null), 's/d');
});
test('percentile phrasing', async () => {
  const f = await load();
  assert.equal(f.percentile(81), 'más que 81 de cada 100');
  assert.equal(f.percentile(81.6), 'más que 82 de cada 100');
  assert.equal(f.percentile(null), 's/d');
});
test('spanish dictionaries hide unknown and raw english', async () => {
  const f = await load();
  assert.equal(f.position('Left Center Back'), 'Central izquierdo');
  assert.equal(f.position('Goalkeeper'), 'Portero');
  assert.equal(f.position('unknown'), '');
  assert.equal(f.scoreState('winning'), 'ganando');
  assert.equal(f.scoreState('drawing'), 'empatando');
  assert.equal(f.scoreState('losing'), 'perdiendo');
  assert.equal(f.scoreState('unknown'), '');
  assert.equal(f.venue('home'), 'local');
  assert.equal(f.venue('away'), 'visitante');
  assert.match(f.warning('small_sample'), /muestra/i);
  assert.equal(f.warning('unknown'), '');
  assert.match(f.warning('codigo_raro'), /Aviso/);
});
test('escape and confidence labels', async () => {
  const f = await load();
  assert.equal(f.esc('<a&"b">'), '&lt;a&amp;&quot;b&quot;&gt;');
  assert.equal(f.confidence('alta'), 'Confianza alta');
  assert.equal(f.confidence('baja'), 'Confianza baja');
  assert.equal(f.interval([0.1, 0.25]), '0.1 – 0.25');
  assert.equal(f.interval(null), 's/d');
});
test('router parses hash routes', async () => {
  const r = await import('../frontend/js/router.js');
  assert.deepEqual(r.parseHash('#partido/123'), { name: 'partido', params: ['123'] });
  assert.deepEqual(r.parseHash('#dt/jardine'), { name: 'dt', params: ['jardine'] });
  assert.deepEqual(r.parseHash(''), { name: 'historia', params: [] });
  assert.deepEqual(r.parseHash('#nada'), { name: 'historia', params: [] });
  assert.equal(r.ROUTES.length >= 9, true);
});
test('confidence bands include "muy baja", prior and source in Spanish', async () => {
  const f = await load();
  assert.equal(f.confidence('muy baja'), 'Confianza muy baja');
  assert.equal(f.confidence('media'), 'Confianza media');
  assert.equal(f.prior('liga'), 'Referencia previa: promedio de la liga');
  assert.equal(f.prior('carrera'), 'Referencia previa: su carrera anterior');
  assert.equal(f.prior(null), '');
  assert.equal(f.source('team-stats'), 'Estadísticas por partido');
  assert.equal(f.source('eventos'), 'Eventos');
  assert.equal(f.source('360'), 'Capturas 360');
  assert.equal(f.source('rara'), '');
});
test('low percentile phrasing and metric values by unit', async () => {
  const f = await load();
  assert.equal(f.percentileLow(15), 'por debajo de 85 de cada 100');
  assert.equal(f.percentileLow(null), 's/d');
  assert.equal(f.metricValue({ value: 0.507, unit: 'proporción' }), '51%');
  assert.equal(f.metricValue({ value: 1.0394, unit: 'xG por partido' }), '1.04');
  assert.equal(f.metricValue({ value: 269.3242, unit: 'por partido' }), '269.32');
  assert.equal(f.metricValue({ value: 0.4848, unit: 'proporción' }, 'value'), '48%');
  assert.equal(f.metricValue({ value: null, unit: 'm' }), 's/d');
  assert.equal(f.metricValue(null), 's/d');
  assert.equal(f.unitLabel('proporción'), '%');
  assert.equal(f.unitLabel('m/s'), 'm/s');
  assert.equal(f.ciByUnit([0.4848, 0.5292], 'proporción'), '48% – 53%');
  assert.equal(f.ciByUnit([8.13, 10.47], 'pases por acción'), '8.13 – 10.47');
});
test('explorer.v2 units: "% del balón" values are shares, unit text without the % sign; confidence from n', async () => {
  const f = await load();
  assert.equal(f.metricValue({ value: 0.538, unit: '% del balón' }), '54%');
  assert.equal(f.metricValue({ value: 0.4754, unit: '% de saques largos' }), '48%');
  assert.equal(f.ciByUnit([0.5282, 0.5477], '% del balón'), '53% – 55%');
  assert.equal(f.unitLabel('% del balón'), '%');
  assert.equal(f.unitText('% del balón'), 'del balón');
  // eventos/360: «% de …» ya viene en 0–100 (no se multiplica por 100); team-stats: proporción 0–1
  assert.equal(f.metricValue({ value: 59.792, unit: '% de acciones en último tercio', source: 'eventos' }), '59.8%');
  assert.equal(f.metricValue({ value: 14.27, unit: '% de pérdidas con ≤2 vigilancias', source: '360' }), '14.3%');
  assert.equal(f.metricValue({ value: 0.538, unit: '% del balón', source: 'team-stats' }), '54%');
  assert.equal(f.ciByUnit([57.63, 62.05], '% de acciones en último tercio', 'eventos'), '57.6% – 62.1%');
  assert.equal(f.ciByUnit([0.5282, 0.5477], '% del balón', 'team-stats'), '53% – 55%');
  assert.equal(f.unitTextOf({ unit: '% de acciones en último tercio', source: 'eventos' }), 'de acciones en último tercio');
  assert.equal(f.unitTextOf({ unit: '% del balón', source: 'team-stats' }), 'del balón');
  assert.equal(f.unitTextOf({ unit: 'xG por tiro', source: 'eventos' }), 'xG por tiro');
  assert.equal(f.unitTextOf({ unit: 'proporción' }), '');
  assert.equal(f.unitText('proporción'), '');
  assert.equal(f.unitText('xG por partido'), 'xG por partido');
  assert.equal(f.metricValue({ value: 313.2046, unit: 'presiones por partido (ajustadas)' }), '313.2');
  assert.equal(f.confidenceOfN(4), 'muy baja'); assert.equal(f.confidenceOfN(5), 'baja');
  assert.equal(f.confidenceOfN(12), 'media'); assert.equal(f.confidenceOfN(25), 'alta'); assert.equal(f.confidenceOfN(null), null);
  assert.equal(f.confidence(f.confidenceOfN(223)), 'Confianza alta');
});
