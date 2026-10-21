// Validation reports data errors, simulation errors and unavailable metrics separately.
const E = require('../frontend/engine.js');
const finite = x => typeof x === 'number' && Number.isFinite(x);
const f = (x, d = 2) => finite(x) ? x.toFixed(d) : 'NA';
const pc = x => finite(x) ? (x * 100).toFixed(0) + '%' : 'NA';
const METRICS = ['goals', 'xg', 'shots', 'possession', 'possLen', 'longShare', 'shotsTShare', 'regainHighShare', 'poss'];
const SHARES = ['possession', 'longShare', 'shotsTShare', 'regainHighShare'];
const TARGETS = ['goals', 'goals_conceded', 'np_xg', 'np_xg_conceded', 'np_shots', 'np_shots_conceded', 'possession'];
function inspectResult(result, N) {
  const errors = [], unavailable = [];
  if (!result || typeof result !== 'object') return { errors: ['resultado ausente'], unavailable };
  for (const key of METRICS) {
    const values = result[key];
    if (values == null) { unavailable.push(key); continue; }
    if (!Array.isArray(values) || values.length !== 2) { errors.push(`${key}: estructura inválida`); continue; }
    values.forEach((value, i) => {
      if (value == null) unavailable.push(`${key}[${i}]`);
      else if (!finite(value) || value < 0 || (SHARES.includes(key) && value > 1)) errors.push(`${key}[${i}]: valor inválido`);
    });
  }
  if (![result.W, result.D, result.L].every(x => Number.isInteger(x) && x >= 0) || result.W + result.D + result.L !== N)
    errors.push('W/D/L no suman N');
  if (result.possession?.every(finite) && Math.abs(result.possession[0] + result.possession[1] - 1) > 1e-6)
    errors.push('posesiones no suman 1');
  return { errors, unavailable };
}
function runValidation(model, targets, N, { engine = E, only, log = console.log } = {}) {
  if (!Number.isSafeInteger(N) || N <= 0) throw new Error('N debe ser un entero positivo');
  const summary = { evaluated: 0, ok: 0, warnings: 0, errors: 0, unavailable: [], details: [], comparisons: [] };
  const L = engine.leagueEntity(model);
  log('unidad de tiempo muerto (s): ' + f(engine.deadUnit(model), 1));
  for (const entity of [L, ...model.entities.filter(e => !only || e.id.includes(only))]) {
    summary.evaluated++;
    const issues = [];
    const add = (category, severity, reason) => issues.push({ entity: entity.id, category, severity, reason });
    for (const side of ['att', 'dfn']) {
      if (!entity[side] || !Number.isInteger(entity[side].matches) || entity[side].matches < 0) add('datos', 'error', `${side}: agregado inválido`);
      else if (entity[side].matches === 0) add('datos', 'warning', `${side}: sin partidos observados; simulación omitida`);
      else if (entity.n != null && entity.n !== entity[side].matches) add('datos', 'error', `${side}.matches no coincide con n`);
    }
    const target = targets[entity.id === 'liga' ? 'league' : entity.id];
    if (!target && entity.kind !== 'synthetic' && entity.kind !== 'opendata') add('datos', 'warning', 'referencia real ausente');
    if (target) for (const key of TARGETS) {
      if (target[key] == null) {
        add('no_disponible', 'warning', `referencia.${key}`);
        summary.unavailable.push({ entity: entity.id, source: 'referencia', metric: key });
      } else if (!finite(target[key]) || target[key] < 0 || (key === 'possession' && target[key] > 1)) add('datos', 'error', `referencia.${key}: valor inválido`);
    }
    let r;
    if (!issues.some(i => i.category === 'datos' && (i.severity === 'error' || i.reason.includes('simulación omitida')))) {
      try { r = engine.simulateMany(model, [entity, L], N, 11); }
      catch (err) { add('simulacion', 'error', err.message); }
      if (r !== undefined) {
        const checked = inspectResult(r, N);
        checked.errors.forEach(reason => add('simulacion', 'error', reason));
        checked.unavailable.forEach(metric => {
          add('no_disponible', 'warning', `simulación.${metric}`);
          summary.unavailable.push({ entity: entity.id, source: 'simulacion', metric });
        });
        if (r) {
          log(`${entity.label} (n=${entity.n ?? entity.att?.matches}) G ${f(r.goals?.[0])}-${f(r.goals?.[1])} xG ${f(r.xg?.[0])}-${f(r.xg?.[1])} tiros ${f(r.shots?.[0], 1)}-${f(r.shots?.[1], 1)} pos ${pc(r.possession?.[0])} W/D/L ${pc(r.W / N)}/${pc(r.D / N)}/${pc(r.L / N)}`);
          if (target) {
            log(`  real G ${f(target.goals)}-${f(target.goals_conceded)} npxG ${f(target.np_xg)}-${f(target.np_xg_conceded)} tiros sin penal ${f(target.np_shots)} pos ${pc(target.possession)}`);
            // Only compare matching definitions: simulator shots/xG include penalties.
            for (const [metric, observed, simulated] of [['goals', target.goals, r.goals?.[0]], ['possession', target.possession, r.possession?.[0]]]) {
              if (finite(observed) && finite(simulated)) summary.comparisons.push({ entity: entity.id, metric, observed, simulated, delta: simulated - observed });
            }
          }
        }
      } else if (!issues.some(i => i.category === 'simulacion')) add('simulacion', 'error', 'resultado undefined');
    }
    summary.details.push(...issues);
    if (issues.some(i => i.severity === 'error')) summary.errors++;
    else if (issues.length) summary.warnings++;
    else summary.ok++;
  }
  log(`Resumen: evaluadas=${summary.evaluated}, correctas=${summary.ok}, advertencias=${summary.warnings}, errores=${summary.errors}, métricas no disponibles=${summary.unavailable.length}`);
  summary.details.forEach(i => log(`[${i.severity}] ${i.entity} / ${i.category}: ${i.reason}`));
  log('Coherencia numérica comprobada; las diferencias contra datos reales son descriptivas, sin prueba de ajuste estadístico.');
  return summary;
}
if (require.main === module) {
  try {
    const model = require('../model/model.json');
    const summary = runValidation(model, require('./targets.json'), Number(process.argv[2] || 800), { only: process.argv[3] });
    if (process.argv[4]) require('fs').writeFileSync(process.argv[4], JSON.stringify(summary, null, 2), 'utf8');
    process.exitCode = summary.errors ? 1 : 0;
  } catch (err) { console.error('[ERROR] ' + err.message); process.exitCode = 1; }
}
module.exports = { finite, f, pc, inspectResult, runValidation };
