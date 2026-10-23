/* «¿Qué cambia con Almada?»: su huella en el Pachuca (ventana oficial) contra la base de Jardine y sus primeros partidos
   en el América (evidencia temprana, fuera de ventana oficial): valores crudos y ajustados con intervalo del 80 %,
   nunca una conclusión fuerte con pocos partidos. Datos: /api/story/almada, KPIs, estilo y detalle del DT en el explorador. */
import { esc } from '../js/fmt.js';
import { dotPlot, figure } from '../js/charts.js';
import { finding as findingCard, windowBadge } from '../js/cards.js';
import { fanFinding } from './story.js';

const PACHUCA = 'pac_almada', AMERICA = 'ame_almada', BASE = 'ame_jardine';
const SHOWN = ['xg', 'xga', 'posesion', 'verticalidad', 'linea', 'volumen_presion', 'presion', 'contrapresion', 'bp_xg'];
const STYLE_ROWS = [['posesion', 'Posesión'], ['verticalidad', 'Verticalidad'], ['ritmo', 'Ritmo de ataque'], ['linea', 'Altura de línea'],
  ['volumen_presion', 'Volumen de presión'], ['contrapresion', 'Contrapresión'], ['contragolpe', 'Tiros al contragolpe']];
const finite = (v) => typeof v === 'number' && Number.isFinite(v);
const titleOf = (ch, id, fb) => ((ch.hallazgos || []).find((f) => f.id === id) || {}).titulo || fb;

/** Fila de intervalo: punto tenue = crudo, punto sólido = ajustado, línea = intervalo del 80 %, marca gris = valor en el Pachuca. */
function intervalRow(label, m, pac, unit, fmt) {
  const vals = [m.raw, m.value, ...(m.ci || []), pac].filter(finite);
  const lo = Math.min(...vals), hi = Math.max(...vals), pad = (hi - lo) * 0.12 || Math.abs(hi) * 0.1 || 1;
  const x = (v) => ((v - (lo - pad)) / (hi - lo + 2 * pad)) * 100;
  const rec = (v) => ({ value: v, unit, source: 'team-stats' });
  const ci = m.ci ? `<line x1="${x(m.ci[0])}" x2="${x(m.ci[1])}" y1="6" y2="6" class="ch-ci"/>` : '';
  const ref = finite(pac) ? `<line x1="${x(pac)}" x2="${x(pac)}" y1="0.5" y2="11.5" class="ch-ref"/>` : '';
  const raw = finite(m.raw) ? `<line x1="${x(m.raw)}" x2="${x(m.raw)}" y1="6" y2="6" class="ch-dot raw"/>` : '';
  const dot = finite(m.value) ? `<line x1="${x(m.value)}" x2="${x(m.value)}" y1="6" y2="6" class="ch-dot"/>` : '';
  const title = `${label}: crudo ${fmt.metricValue(rec(m.raw))}, ajustado ${fmt.metricValue(rec(m.value))}, Pachuca ${fmt.metricValue(rec(pac))}`;
  return `<div class="ch-row iv" title="${esc(title)}"><span>${esc(label)}</span>
    <svg viewBox="0 0 100 12" preserveAspectRatio="none" class="ch-svg" aria-hidden="true">${ci}${ref}${raw}${dot}</svg>
    <span class="ch-val">${fmt.metricValue(rec(m.value))}</span></div>`;
}

function rawVsShrunk(data, ctx, ch) {
  const { fmt, mode } = ctx, cat = data.catalog, ame = data.tenure(AMERICA), pac = data.tenure(PACHUCA);
  if (!ame || !pac) return '';
  const rows = SHOWN.filter((k) => ame.metrics && ame.metrics[k] && finite(ame.metrics[k].value) && pac.metrics[k])
    .map((k) => intervalRow((cat[k] || {}).nombre || k, ame.metrics[k], pac.metrics[k].value, (cat[k] || {}).unit || '', fmt));
  if (!rows.length) return '';
  const legend = '<p class="caption">Punto tenue = crudo · punto sólido = ajustado hacia su carrera previa · línea = intervalo del 80 % · marca gris = su valor en el Pachuca. Cada fila tiene su propia escala.</p>';
  return figure({ title: titleOf(ch, 'almada_america_temprano', 'Sus primeros partidos en el América'), unit: 'cada fila en su unidad',
    n: ame.n, window: 'temprano', note: mode === 'dt' ? 'El intervalo usa la dispersión entre partidos con n0 = 8 partidos de referencia.' : '' },
  `<div class="ch-bars">${rows.join('')}</div>${legend}`);
}

function identityCompare(data, ctx, ch) {
  const pac = (data.teams[PACHUCA] || {}).style || {}, base = (data.teams[BASE] || {}).style || {};
  const style = [];
  for (const [k, label] of STYLE_ROWS) {
    if (finite(pac[k])) style.push({ label: `${label} · Pachuca`, pct: pac[k] });
    if (finite(base[k])) style.push({ label: `${label} · Jardine`, pct: base[k], side: 'league' });
  }
  const kp = [];
  for (const k of data.kpis[PACHUCA] || []) {
    const o = (data.kpis[BASE] || []).find((x) => x.id === k.id);
    if (finite(k.pct_bueno)) kp.push({ label: `${k.nombre} · Pachuca`, pct: k.pct_bueno });
    if (o && finite(o.pct_bueno)) kp.push({ label: `${k.nombre} · Jardine`, pct: o.pct_bueno, side: 'league' });
  }
  const grid = (...f) => `<div class="chart-grid">${f.filter(Boolean).join('')}</div>`;
  return grid(style.length ? dotPlot({ title: titleOf(ch, 'almada_pachuca', 'Su huella en el Pachuca'), unit: 'percentil 0–100 frente a la liga', n: (data.teams[PACHUCA] || {}).n, window: 'oficial' }, style) : '',
    kp.length ? dotPlot({ title: titleOf(ch, 'almada_vs_jardine', 'Frente a la base de Jardine'), unit: 'percentil 0–100 donde más a la derecha es mejor', n: (data.teams[PACHUCA] || {}).n, window: 'oficial' }, kp) : '');
}

const VISUALS = { identity_compare: identityCompare, raw_vs_shrunk: rawVsShrunk };

function chapterHTML(ch, data, ctx) {
  const early = ch.id === 'almada_america';
  const cards = ch.hallazgos.map((f) => (ctx.mode === 'dt' ? findingCard(f, ctx) : fanFinding(f))).filter(Boolean).join('');
  const make = VISUALS[(ch.aficionado || {}).visual];
  const visual = make ? make(data, ctx, ch) : '';
  return `<section class="chapter${early ? ' out' : ''}" id="cap-${esc(ch.id)}"><header class="section-head"><div><span class="eyebrow">Parte ${ch.orden}</span>
    <h2>${esc(ch.titulo)}</h2></div>${early ? `<div class="badges">${windowBadge('temprano')}</div>` : ''}</header>
    ${(ch.aficionado || {}).conclusion ? `<p class="lead">${esc(ch.aficionado.conclusion)}</p>` : ''}${visual ? `<div class="visual">${visual}</div>` : ''}
    ${cards ? `<div class="grid findings">${cards}</div>` : ''}</section>`;
}

export async function render(root, ctx) {
  const { api, fmt } = ctx;
  const [story, catalog, coaches] = await Promise.all([api.tryJSON('/api/story/almada'), api.tryJSON('/api/explorer/catalog'), api.tryJSON('/api/explorer/coaches')]);
  if (!story || !Array.isArray(story.capitulos)) {
    root.innerHTML = `<section class="view"><header class="vhead"><h2>¿Qué cambia con Almada?</h2></header>
      <div class="empty card"><h3>Datos en construcción</h3><p>Esta sección se publica en cuanto termine su análisis.</p></div></section>`;
    return;
  }
  const key = ((coaches || []).find((c) => /almada/i.test(String(c.key))) || {}).key;
  const [detail, kpiP, kpiB, teamP, teamB] = await Promise.all([key ? api.tryJSON(`/api/explorer/coach/${encodeURIComponent(key)}`) : null,
    api.tryJSON(`/api/kpis/${PACHUCA}`), api.tryJSON(`/api/kpis/${BASE}`), api.tryJSON(`/api/teams/${PACHUCA}`), api.tryJSON(`/api/teams/${BASE}`)]);
  const tenures = (detail && detail.tenencias) || [];
  const data = {
    catalog: Object.fromEntries(((catalog || {}).metricas || []).map((m) => [m.id, m])),
    tenure: (id) => tenures.find((t) => (t.entidades || []).some((e) => e.id === id)),
    kpis: { [PACHUCA]: ((kpiP || {}).kpis || {}).oficial || [], [BASE]: ((kpiB || {}).kpis || {}).oficial || [] },
    teams: { [PACHUCA]: teamP || {}, [BASE]: teamB || {} },
  };
  root.innerHTML = `<section class="view story"><header class="section-head vhead"><div>
    <div class="eyebrow">Pachuca · Cl2022 a Cl2025 (ventana oficial) y América · 2026/27 (evidencia temprana)</div>
    <h2>${esc(story.titulo)}</h2><p>Qué hacía Almada en el Pachuca, en qué se parece o se aparta de la base de Jardine y qué ya se nota en sus primeros ${fmt.num(story.partidos, 0)} partidos en el América.</p></div></header>
    <aside class="panel warn-panel"><span class="kicker">Evidencia temprana</span><p>${esc(story.nota || '')}</p></aside>
    ${story.capitulos.map((c) => chapterHTML(c, data, ctx)).join('')}</section>`;
}
