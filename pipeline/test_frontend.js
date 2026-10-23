/* Laboratorio (lab.html) y portal (index.html): estructura y presentación. */
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs'), vm = require('node:vm');
const read = (p) => fs.readFileSync(require.resolve(p), 'utf8');
const inlineScripts = (html) => [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(x => x[1]).join('\n');

test('context view renders absent data without fabricated zero', () => {
  const view = require('../frontend/context_view.js');
  assert.match(view.render({ label: 'América' }), /Sin datos contextuales/);
  const html = view.render({ label: 'América', context: { venue: { home: { minutes: 1, possessions: 1, matches: 1, xg: null, shots: 0 } } } });
  assert.match(html, /s\/d/); assert.doesNotMatch(html, /NaN|undefined/);
});
test('lab script parses and keeps fallback labels', () => {
  const inline = inlineScripts(read('../frontend/lab.html'));
  new vm.Script(inline);
  const start = inline.indexOf('  function fcLabels('), end = inline.indexOf('  /* ---------- selector', start);
  const ctx = {}; vm.createContext(ctx);
  vm.runInContext(inline.slice(start, end) + `
    this.fallback = idFor({ style: {} });
    this.withId = idFor({ style: {}, identity: { build: 'Elabora', defense: 'Presión alta', attack: 'Por bandas', tags: ['Muy vertical'] } });`, ctx);
  assert.equal(ctx.fallback.build, 'Datos insuficientes'); assert.equal(ctx.fallback.tags.length, 0);
  assert.equal(ctx.withId.def, 'Presión alta'); assert.deepEqual([...ctx.withId.tags], ['Muy vertical']);
});
test('lab presentation: identity used, duel framed, no raw labels or moved sections', () => {
  const html = read('../frontend/lab.html');
  assert.match(html, /Duelo de estilos en el modelo \(no es un pronóstico\)/);
  assert.match(html, /frecuencia en 1,500 partidos del modelo/);
  assert.match(html, /simulado/);
  assert.doesNotMatch(html, /fcLabels\(e\.style\)|quadName\('off', e\.map\.off\)/);
  assert.doesNotMatch(html, /id="temporal"|id="personnel"|id="contextA"/);
  assert.ok(html.indexOf('id="qBars"') < html.indexOf('id="wdl"'), 'W/D/L va debajo de las barras');
});
test('lab simulation code is verbatim from engine contract', () => {
  const html = read('../frontend/lab.html');
  assert.match(html, /<script src="engine\.js"><\/script>/);
});
test('portal shell: router routes, mode toggle, no toFixed(3)', () => {
  const html = read('../frontend/index.html');
  assert.match(html, /type="module"/);
  for (const r of ['historia', 'almada', 'partidos', 'explorador', 'laboratorio', 'metodo']) assert.match(html, new RegExp('#' + r));
  assert.match(html, /Aficionado/); assert.match(html, /DT/);
  for (const f of ['js/fmt.js', 'js/api.js', 'js/router.js', 'js/charts.js', 'js/pitch.js', 'views/explorer.js', 'views/method.js']) {
    assert.doesNotMatch(read('../frontend/' + f), /toFixed\(3\)/, f);
  }
});
test('lab has no 3-decimal formatting nor moved context renderers', () => {
  const html = read('../frontend/lab.html');
  assert.doesNotMatch(html, /toFixed\(3\)|renderTemporal|renderPersonnel|ContextView/);
});
test('theme script: dark default, cycles auto → dark → light, persists and survives blocked storage', () => {
  const src = read('../frontend/js/theme.js');
  const mk = (store) => {
    const attrs = {};
    const el = { setAttribute: (k, v) => { attrs[k] = v; }, removeAttribute: (k) => { delete attrs[k]; } };
    const win = { document: { documentElement: el }, localStorage: store, addEventListener() {} };
    vm.runInNewContext(src, { window: win, globalThis: win });
    return { t: win.caonTheme, attrs };
  };
  const mem = {}; const store = { getItem: (k) => (k in mem ? mem[k] : null), setItem: (k, v) => { mem[k] = v; } };
  const { t, attrs } = mk(store);
  assert.equal(t.read(), 'auto'); assert.equal(attrs['data-theme'], undefined, 'sin elección: oscuro por defecto vía tokens');
  assert.equal(t.cycle(), 'dark'); assert.equal(attrs['data-theme'], 'dark'); assert.equal(mem['caon.theme'], 'dark');
  assert.equal(t.cycle(), 'light'); assert.equal(attrs['data-theme'], 'light');
  assert.equal(t.cycle(), 'auto'); assert.equal(attrs['data-theme'], undefined);
  const broken = { getItem() { throw new Error('bloqueado'); }, setItem() { throw new Error('bloqueado'); } };
  const b = mk(broken); assert.equal(b.t.read(), 'auto'); assert.equal(b.t.cycle(), 'dark');
  for (const page of ['index.html', 'lab.html']) assert.match(read('../frontend/' + page), /<script src="(?:\/)?js\/theme\.js"><\/script>/, page);
});
