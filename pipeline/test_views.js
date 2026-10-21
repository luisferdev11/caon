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
test('explorer marks small samples, interval in DT mode, coach link', async () => {
  const v = await import('../frontend/views/explorer.js'); const root = fakeRoot();
  const data = { items: [{ key: 'jardine', label: 'André Jardine', n: 5, confidence: 'baja', metrics: [{ id: 'xg_pg', nombre: 'xG por partido', value: 1.234, raw: 1.6, ci: [1.01, 1.45] }] }] };
  await v.render(root, await ctx(data, 'dt', ['dts']));
  const html = root.kids['#exp-list'].innerHTML;
  assert.match(html, /Muestra pequeña/); assert.match(html, /1\.01 – 1\.45/); assert.match(html, /#dt\/jardine/);
  assert.match(html, /Confianza baja/); assert.doesNotMatch(html, /undefined|NaN|unknown/);
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
