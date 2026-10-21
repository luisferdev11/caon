// Pruebas de las funciones puras de frontend/views/playlab.js (A9).
const test = require('node:test');
const assert = require('node:assert');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const MOD = pathToFileURL(path.join(__dirname, '..', 'frontend', 'views', 'playlab.js')).href;
const shape = Array.from({ length: 11 }, (_, j) => ({ pos: j ? 'Center Midfield' : 'Goalkeeper', num: j === 10 ? 9 : j + 1, name: 'J' + j, con: [10 + j * 8, 40], sin: [5 + j * 6, 40] }));
const play = { start: { restart: 'open' }, steps: [
  { type: 'cross', actor: { num: 10 }, zone: 'segundo_palo', height: 'alto' },
  { type: 'header', actor: { num: 9 }, zone: 'segundo_palo', outcome: 'gol' }] };

test('shapeTargets da 22 posiciones dentro de la cancha', async () => {
  const { shapeTargets } = await import(MOD);
  const T = shapeTargets([shape, shape], [100, 20]);
  assert.strictEqual(T[0].length + T[1].length, 22);
  for (const p of T.flat()) assert.ok(p[0] >= 1 && p[0] <= 119 && p[1] >= 1 && p[1] <= 79);
});
test('buildSegments: centro elevado y cabezazo que termina en gol dentro de la portería', async () => {
  const { buildSegments } = await import(MOD);
  const s = buildSegments(play, shape);
  assert.strictEqual(s.length, 2);
  assert.ok(s[0].lofted);
  assert.strictEqual(s[1].actor, shape.findIndex((p) => p.num === 9));
  assert.ok(s[1].to[0] >= 120 && Math.abs(s[1].to[1] - 40) < 3.66);
});
test('pathTypicality = 1 cuando equipo y liga coinciden; zoneXG usa la zona del remate', async () => {
  const { buildSegments, pathTypicality, zoneXG } = await import(MOD);
  const mv = [Array.from({ length: 18 }, () => Array(18).fill(1))];
  assert.ok(Math.abs(pathTypicality(buildSegments(play, shape), mv, mv) - 1) < 1e-9);
  const league = { xg: [Array(18).fill(1)], shot: [Array(18).fill(10)] };
  assert.strictEqual(zoneXG(league, [110, 45]), 0.1);
  assert.strictEqual(zoneXG({}, [110, 45]), null);
});
