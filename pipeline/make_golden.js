// Golden fixture for the frozen simulation engine (AC-02).
// `node pipeline/make_golden.js strip`  -> pipeline/fixtures/golden_model.json (after proving identity)
// `node pipeline/make_golden.js`        -> pipeline/fixtures/golden_engine.json (hashes)
'use strict';
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');

const ROOT = path.resolve(__dirname, '..');
const FIX = path.join(__dirname, 'fixtures');
const MODEL_PATH = path.join(ROOT, 'model', 'model.json');
const GOLDEN_MODEL = path.join(FIX, 'golden_model.json');
const GOLDEN_ENGINE = path.join(FIX, 'golden_engine.json');
const ENTITY_IDS = ['ame_jardine', 'atl_cocca', 'barca_guardiola', 'arq_autobus'];
const DROP_KEYS = ['personnel', 'temporal', 'context', 'context_comparisons', 'coverage', 'style_status', 'context_status', 'raw'];
const PAIRS = [['ame_jardine', 'atl_cocca'], ['atl_cocca', 'arq_autobus'], ['barca_guardiola', 'ame_jardine'], ['ame_jardine', 'liga']];
const SIM_SEEDS = 25, CHOREO_SEEDS = 5, SAMPLE_TIMES = 50, MANY_N = 300, MANY_SEED = 7;
const CHOREO_KEYS = ['balls', 'feed', 'toasts', 'dead', 'phases', 'highlights', 'momentum', 'cards', 'sentOff'];

const sha = (value) => crypto.createHash('sha256').update(JSON.stringify(value)).digest('hex');
const simSeed = (s) => s * 7919 + 13;

/** Keep meta, league, map and the four golden entities without non-simulator keys. */
function stripModel(model) {
  const entities = model.entities.filter((e) => ENTITY_IDS.includes(e.id)).map((e) => {
    const out = {};
    for (const [k, v] of Object.entries(e)) if (!DROP_KEYS.includes(k)) out[k] = v;
    return out;
  });
  return { meta: model.meta, league: model.league, map: model.map, entities };
}

function resolveTeams(engine, model, pair) {
  return pair.map((id) => (id === 'liga' ? engine.leagueEntity(model) : model.entities.find((e) => e.id === id)));
}

function simulateHashes(engine, model, pair, seeds) {
  const teams = resolveTeams(engine, model, pair);
  const out = [];
  for (let s = 1; s <= seeds; s++) out.push(sha(engine.simulate(model, teams, { seed: simSeed(s), record: true })));
  return out;
}

function choreoDigest(engine, ch) {
  const d = { frames: sha(ch.frames.map((f) => ({ ...f, P: Array.from(f.P) }))) };
  for (const k of CHOREO_KEYS) d[k] = sha(ch[k] === undefined ? null : ch[k]);
  return d;
}

function sampleDigest(engine, ch) {
  const T = engine.T_TOTAL, samples = [];
  for (let i = 0; i < SAMPLE_TIMES; i++) {
    const t = (T * i) / (SAMPLE_TIMES - 1);
    const P = engine.playersAt(ch, t);
    samples.push({ t, players: Array.from(P), ball: engine.ballAt(ch, t, P) });
  }
  return sha(samples);
}

function choreoHashes(engine, model, pair) {
  const teams = resolveTeams(engine, model, pair), out = [];
  for (let s = 1; s <= CHOREO_SEEDS; s++) {
    const sim = engine.simulate(model, teams, { seed: simSeed(s), record: true });
    const ch = engine.choreograph(model, teams, sim, s);
    out.push({ seed: s, ...choreoDigest(engine, ch), samples: sampleDigest(engine, ch) });
  }
  return out;
}

/** Deterministic digest of the engine's observable behaviour over `model`. */
function computeGolden(engine, model, seeds = SIM_SEEDS) {
  const simulate = {};
  for (const pair of PAIRS) simulate[pair.join('__')] = simulateHashes(engine, model, pair, seeds);
  const many = engine.simulateMany(model, resolveTeams(engine, model, PAIRS[0]), MANY_N, MANY_SEED);
  return { simulate, simulateMany: sha(many), choreograph: choreoHashes(engine, model, PAIRS[0]) };
}

function loadJSON(p) { return JSON.parse(fs.readFileSync(p, 'utf8')); }

function strip(engine) {
  const full = loadJSON(MODEL_PATH), small = stripModel(full);
  const a = computeGolden(engine, full, 5), b = computeGolden(engine, JSON.parse(JSON.stringify(small)), 5);
  if (sha(a) !== sha(b)) throw new Error('el modelo recortado NO simula idéntico al completo');
  fs.writeFileSync(GOLDEN_MODEL, JSON.stringify(small), 'utf8');
  console.log('identidad probada (5 semillas, todas las salidas):', sha(a));
  console.log('golden_model.json bytes:', fs.statSync(GOLDEN_MODEL).size);
}

function main() {
  const engine = require('../frontend/engine.js');
  if (process.argv[2] === 'strip') return strip(engine);
  const golden = computeGolden(engine, loadJSON(GOLDEN_MODEL));
  fs.writeFileSync(GOLDEN_ENGINE, JSON.stringify({ engine_sha256: fileSha(path.join(ROOT, 'frontend', 'engine.js')), ...golden }, null, 1), 'utf8');
  console.log('golden_engine.json escrito');
}

function fileSha(p) { return crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex'); }

module.exports = { stripModel, computeGolden, fileSha, GOLDEN_MODEL, GOLDEN_ENGINE };
if (require.main === module) main();
