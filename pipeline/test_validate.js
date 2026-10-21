const test = require('node:test');
const assert = require('node:assert/strict');
const { f, inspectResult, runValidation } = require('./validate.js');
const complete = () => ({ goals: [1, 1], xg: [1, 1], shots: [10, 10], possession: [.5, .5], possLen: [4, 4], longShare: [.1, .1], shotsTShare: [.2, .2], regainHighShare: [.1, .1], poss: [100, 100], W: 4, D: 2, L: 4 });
const target = { goals: 1, goals_conceded: 1, np_xg: 1, np_xg_conceded: 1, np_shots: 10, np_shots_conceded: 10, possession: .5 };
test('complete result and genuine zero', () => {
  assert.equal(inspectResult(complete(), 10).errors.length, 0);
  assert.equal(f(0), '0.00');
});
test('null undefined NaN Infinity are never formatted as zero', () => {
  for (const x of [null, undefined, NaN, Infinity]) assert.equal(f(x), 'NA');
  const r = complete(); r.possLen = null;
  assert.deepEqual(inspectResult(r, 10).unavailable, ['possLen']);
  r.xg[0] = NaN; r.shots[0] = Infinity;
  assert.equal(inspectResult(r, 10).errors.length, 2);
});
test('invalid shares, results and WDL are errors', () => {
  const r = complete(); r.W = 0; r.possession = [.6, .6];
  assert.equal(inspectResult(r, 10).errors.length, 2);
  assert.equal(inspectResult(null, 10).errors.length, 1);
});
test('incomplete entity does not prevent evaluating the rest', () => {
  const entity = id => ({ id, label: id, n: 1, att: { matches: 1 }, dfn: { matches: 1 } });
  const entities = [entity('missing'), entity('bad'), entity('throws'), entity('empty'), entity('ok')];
  entities[3].n = entities[3].att.matches = entities[3].dfn.matches = 0;
  const engine = { leagueEntity: () => entity('liga'), deadUnit: () => 30, simulateMany: (_, [e]) => {
    if (e.id === 'throws') throw new Error('fallo simulado');
    const r = complete(); if (e.id === 'missing') r.xg = undefined; if (e.id === 'bad') r.xg[0] = Infinity; return r;
  }};
  const targets = Object.fromEntries(['league', ...entities.map(e => e.id)].map(id => [id, { ...target }]));
  targets.missing.np_xg = null;
  const report = runValidation({ entities }, targets, 10, { engine, log: () => {} });
  assert.equal(report.evaluated, 6); assert.equal(report.errors, 2); assert.equal(report.warnings, 2); assert.equal(report.ok, 2);
  assert.equal(report.unavailable.length, 2);
  assert.throws(() => runValidation({ entities }, targets, 0, { engine }), /entero positivo/);
});
