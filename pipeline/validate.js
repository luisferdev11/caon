// Validación del motor: (1) liga vs liga contra la realidad, (2) cada equipo vs liga contra sus datos reales,
// (3) firmas de estilo de los equipos de validación.
const E = require('../frontend/engine.js');
const model = require('../model/model.json');
const T = require('./targets.json');
const L = E.leagueEntity(model);
const finite = (x) => typeof x === 'number' && Number.isFinite(x);
const f = (x, d = 2) => finite(x) ? x.toFixed(d) : 'NA';
const pc = (x) => finite(x) ? (x * 100).toFixed(0) + '%' : 'NA';
const N = +(process.argv[2] || 800);
const summary = { evaluated: 0, ok: 0, warnings: 0, errors: 0, unavailable: new Set(), details: [] };
console.log('unidad de tiempo muerto (s):', f(E.deadUnit(model), 1));
function row(name, a, b, tgt) {
  summary.evaluated++;
  let r;
  try {
    r = E.simulateMany(model, [a, b], N, 11);
  } catch (err) {
    summary.errors++;
    summary.details.push(`${name}: error de simulación: ${err.message}`);
    console.error(`[ERROR] ${name}: ${err.message}`);
    return null;
  }
  const missing = ['goals', 'xg', 'shots', 'possession', 'possLen', 'longShare', 'shotsTShare', 'regainHighShare', 'poss']
    .filter((key) => !Array.isArray(r[key]) || r[key].some((value) => !finite(value)));
  if (missing.length) {
    missing.forEach((key) => summary.unavailable.add(key));
    summary.warnings++;
    summary.details.push(`${name}: métricas no disponibles: ${missing.join(', ')}`);
    console.warn(`[WARN] ${name}: métricas no disponibles: ${missing.join(', ')}`);
  } else {
    summary.ok++;
  }
  console.log(`${name.padEnd(44)} G ${f(r.goals[0])}-${f(r.goals[1])} xG ${f(r.xg[0])}-${f(r.xg[1])} tiros ${f(r.shots[0], 1)}-${f(r.shots[1], 1)} pos ${pc(r.possession[0])} | acc/pos ${f(r.possLen[0], 1)} pos≥10 ${pc(r.longShare[0])} tirosTrans ${pc(r.shotsTShare[0])} robosAltos ${pc(r.regainHighShare[0])} posesiones ${f(r.poss[0], 0)} W/D/L ${pc(r.W / N)}/${pc(r.D / N)}/${pc(r.L / N)}`);
  if (tgt) console.log(' '.repeat(44) + ` real G ${f(tgt.goals)}-${f(tgt.goals_conceded)} npxG ${f(tgt.np_xg)}-${f(tgt.np_xg_conceded)} tiros ${f(tgt.np_shots, 1)}-${f(tgt.np_shots_conceded, 1)} pos ${pc(tgt.possession)}`);
  return r;
}
console.time('sims');
row('Liga vs Liga', L, L, T.league);
console.timeEnd('sims');
const only = process.argv[3];
for (const e of model.entities) {
  if (only && !e.id.includes(only)) continue;
  row(`${e.label} (n=${e.n})`, e, L, T[e.id]);
}
console.log('\nResumen de validación');
console.log(`  entidades evaluadas: ${summary.evaluated}`);
console.log(`  evaluadas correctamente: ${summary.ok}`);
console.log(`  advertencias: ${summary.warnings}`);
console.log(`  errores: ${summary.errors}`);
console.log(`  métricas no disponibles: ${summary.unavailable.size ? [...summary.unavailable].join(', ') : 'ninguna'}`);
if (summary.details.length) {
  console.log('  detalles:');
  summary.details.forEach((detail) => console.log(`    - ${detail}`));
}
if (summary.errors > 0) process.exitCode = 1;
