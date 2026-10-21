const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs'), vm = require('node:vm');
const view = require('../frontend/context_view.js');
test('absent context and nullable metrics render without fabricated zero', () => {
  assert.match(view.render({ label: 'América' }), /Sin datos contextuales/);
  const html = view.render({ label: 'América', context: { venue: { home: { minutes: 1, possessions: 1, matches: 1, xg: null, shots: 0 } } } });
  assert.match(html, /s\/d/); assert.match(html, /Muestra insuficiente/); assert.match(html, /América/);
  assert.doesNotMatch(html, /NaN|undefined/);
  assert.equal(view.fmt(0), '0.00'); assert.equal(view.fmt(Infinity), 's/d');
});
test('frontend script parses; incomplete styles do not become balanced', () => {
  const html = fs.readFileSync(require.resolve('../frontend/index.html'), 'utf8');
  const inline = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(x => x[1]).join('\n');
  new vm.Script(inline);
  const start = inline.indexOf('  function fcLabels('), end = inline.indexOf('  /* ---------- selector', start);
  const context = {}; vm.createContext(context); vm.runInContext(inline.slice(start, end) + '\nthis.labels = fcLabels({}); this.emptyTags = tags({linea: null, volumen_presion: null});', context);
  assert.equal(context.labels.build, 'Datos insuficientes'); assert.equal(context.labels.def, 'Datos insuficientes'); assert.equal(context.labels.att, 'Datos insuficientes');
  assert.equal(context.emptyTags.length, 0);
});
