/* Renderizador único de cancha (js/pitch.js): mismo verde, líneas, discos numerados y leyenda semántica. */
const test = require('node:test');
const assert = require('node:assert/strict');
const imp = () => import('../frontend/js/pitch.js');

test('pitchSVG: striped grass, chalk lines, goals and inner layer in 120x80 coordinates', async () => {
  const p = await imp();
  const svg = p.pitchSVG('<circle id="x"/>', { label: 'Mapa <de> tiros' });
  assert.match(svg, /viewBox="-3 -2 126 84"/);
  assert.equal((svg.match(/class="pitch-stripe"/g) || []).length, 6, '12 franjas: 6 claras sobre el pasto');
  assert.match(svg, /class="pitch-grass"/); assert.match(svg, /class="pitch-lines"/); assert.match(svg, /class="pitch-goal"/);
  assert.match(svg, /aria-label="Mapa &lt;de&gt; tiros"/);
  assert.ok(svg.indexOf('<circle id="x"/>') > svg.indexOf('pitch-lines'), 'la capa va encima de las líneas');
  assert.doesNotMatch(svg, /#[0-9a-f]{3,6}\b|rgba?\(/i, 'sin colores literales');
  assert.match(p.pitchSVG('', { cls: 'pitch mini' }), /class="pitch mini"/);
});

test('playerDisc: numbered disc with side semantics, goalkeeper and highlight variants', async () => {
  const p = await imp();
  const d = p.playerDisc({ x: 10.04, y: 40, num: 9, side: 'protag' });
  assert.match(d, /<g class="pd pd-protag">/); assert.match(d, /cx="10" cy="40"/); assert.match(d, />9<\/text>/);
  const r = p.playerDisc({ x: 100, y: 20.55, num: 1, side: 'rival', gk: true, hi: true });
  assert.match(r, /class="pd pd-rival pd-gk pd-hi"/); assert.match(r, /cy="20.6"/);
  assert.doesNotMatch(p.playerDisc({ x: 1, y: 1, side: 'rival' }), /<text/);
  assert.match(p.playerDisc({ x: 1, y: 1, num: '<b>', side: 'protag' }), /&lt;b&gt;/);
  assert.match(p.playerDisc({ x: 1, y: 1, side: 'otro' }), /pd-league/, 'lado desconocido = liga/otros');
});

test('ball, legend and caption share the semantics protagonista/rival/liga/fuera de ventana', async () => {
  const p = await imp();
  const b = p.ballSVG(50, 40, 3);
  assert.match(b, /class="pitch-ball-shadow"/); assert.match(b, /class="pitch-ball"/); assert.match(b, /cy="37"/);
  const lg = p.legendHTML([{ side: 'protag', label: 'América' }, { side: 'rival', label: 'Pachuca <x>' }, { side: 'league', label: 'Liga' }, { side: 'out', label: 'Fuera de ventana' }]);
  assert.match(lg, /class="legend"/); assert.match(lg, /sw protag/); assert.match(lg, /sw rival/); assert.match(lg, /sw league/); assert.match(lg, /sw hatch/);
  assert.match(lg, /Pachuca &lt;x&gt;/);
  assert.deepEqual(Object.keys(p.SIDES), ['protag', 'rival', 'league', 'out']);
  assert.match(p.caption(), /izquierda a derecha/);
});
