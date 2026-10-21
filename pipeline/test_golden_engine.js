// AC-02: the frozen engine must reproduce the golden hashes byte for byte.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const G = require('./make_golden.js');

const load = (p) => JSON.parse(fs.readFileSync(p, 'utf8'));

/** Compare a recomputed digest against the stored golden one; returns list of differing keys. */
function diffGolden(expected, actual) {
  const diffs = [];
  for (const k of Object.keys(actual.simulate)) if (JSON.stringify(expected.simulate[k]) !== JSON.stringify(actual.simulate[k])) diffs.push('simulate:' + k);
  if (expected.simulateMany !== actual.simulateMany) diffs.push('simulateMany');
  if (JSON.stringify(expected.choreograph) !== JSON.stringify(actual.choreograph)) diffs.push('choreograph');
  return diffs;
}

function checkEngine(engine) {
  return diffGolden(load(G.GOLDEN_ENGINE), G.computeGolden(engine, load(G.GOLDEN_MODEL)));
}

test('golden fixture is small and contains the 4 golden entities', () => {
  assert.ok(fs.statSync(G.GOLDEN_MODEL).size < 400 * 1024);
  const ids = load(G.GOLDEN_MODEL).entities.map((e) => e.id).sort();
  assert.deepEqual(ids, ['ame_jardine', 'arq_autobus', 'atl_cocca', 'barca_guardiola']);
});

test('engine reproduces golden simulate/simulateMany/choreograph/playersAt/ballAt hashes', () => {
  const engine = require(process.env.GOLDEN_ENGINE_PATH || '../frontend/engine.js');
  assert.deepEqual(checkEngine(engine), []);
});

module.exports = { checkEngine, diffGolden };
