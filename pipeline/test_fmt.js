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
