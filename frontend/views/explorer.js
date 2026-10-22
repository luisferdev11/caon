/* Explorador: rendimiento por equipo y por DT con valores encogidos hacia su referencia previa (prior),
   intervalo al 80% y confianza. Aficionado: identidad en palabras y ≤3 números por tarjeta.
   DT: tabla completa (valor ajustado, intervalo, bruto, prior, percentil) y percentiles contra la liga.
   Rutas: #explorador/{equipos|dts}[/<clave>] y el alias #equipo/<clave>. Los datos vienen de /api/explorer/*. */
import { filterUnits, identityChips, metricRows, seasonsOf, traits, unitsOf } from '../js/explorer_data.js';
import { windowBadge } from '../js/cards.js';
import { dotPlot } from '../js/charts.js';

const KINDS = {
  equipos: { list: '/api/explorer/teams', detail: '/api/explorer/team/', title: 'Por equipo', noun: 'equipo', plural: 'equipos',
    related: 'Entrenadores', seasons: 'Detalle por temporada', back: '← Todos los equipos' },
  dts: { list: '/api/explorer/coaches', detail: '/api/explorer/coach/', title: 'Por entrenador', noun: 'entrenador', plural: 'entrenadores',
    related: 'Clubes', seasons: 'Detalle por equipo y etapa', back: '← Todos los entrenadores' },
};
const LIST_DT_METRICS = ['xg', 'xga', 'posesion', 'presion']; // tabla corta de la tarjeta de lista (modo DT)
const FAN_TRAITS = 2;

/** {kind, key} desde los parámetros: #explorador/dts/<clave>, #explorador/equipos, alias #equipo/<clave>. */
export function routeOf(params) {
  const [a, b] = params || [];
  if (KINDS[a]) return { kind: a, key: b || null };
  return { kind: 'equipos', key: a || null };
}

const hrefOf = (kind, key) => `#explorador/${kind}${key ? '/' + encodeURIComponent(key) : ''}`;

function badgesHTML(u, ctx) {
  const { fmt } = ctx;
  const out = [];
  if (Number.isFinite(u.n)) out.push(`<span class="badge">${fmt.num(u.n, 0)} partidos</span>`);
  if (u.confidence) out.push(`<span class="badge">${fmt.confidence(u.confidence)}</span>`);
  if (u.small) out.push('<span class="badge warn">Muestra pequeña</span>');
  if (u.window && u.window !== 'oficial') out.push(windowBadge(u.window, fmt));
  return `<div class="badges">${out.join('')}</div>`;
}

function chipsHTML(identity, ctx, withTags) {
  const { fmt } = ctx;
  const chips = identityChips(identity).map((t) => `<span class="chip info">${fmt.esc(t)}</span>`);
  const tags = withTags && identity && Array.isArray(identity.tags) ? identity.tags.map((t) => `<span class="tag">${fmt.esc(t)}</span>`) : [];
  if (!chips.length && !tags.length) return '';
  return `${chips.length ? `<div class="chips">${chips.join('')}</div>` : ''}${tags.length ? `<div class="tags">${tags.join('')}</div>` : ''}`;
}

function traitsHTML(unit, ctx, k = FAN_TRAITS) {
  const list = traits(unit, k);
  if (!list.length) return '';
  return `<ul class="traits">${list.map((t) => `<li>${ctx.fmt.esc(t.text)}</li>`).join('')}</ul>`;
}

function valueCell(r, fmt) {
  if (r.value === null) return `<td class="muted" colspan="3">Sin dato${r.motivo ? ': ' + fmt.esc(r.motivo) : ''}</td>`;
  return `<td class="num"><strong>${fmt.metricValue(r.rec)}</strong></td><td class="num">${fmt.ciByUnit(r.ci, r.unit)}</td>` +
    `<td class="num">${fmt.metricValue(r.rec, r.rec.bruto !== undefined ? 'bruto' : 'raw')}</td>`;
}

/** Tabla DT: métrica (enlace a Método), valor ajustado, intervalo 80%, bruto, percentil y unidad. */
function metricsTable(rows, ctx, compact = false) {
  const { fmt } = ctx;
  if (!rows.length) return '';
  if (compact) {   // tarjeta de lista: tres columnas; intervalo 80 % y bruto van apilados bajo el valor ajustado
    const body = rows.map((r) => `<tr><th scope="row"><a href="#metodo/${encodeURIComponent(r.fid)}">${fmt.esc(r.label)}</a></th>` +
      `<td class="num"><strong>${fmt.metricValue(r.rec)}</strong><span class="muted sub">${fmt.ciByUnit(r.ci, r.unit, r.rec.source)} · bruto ${fmt.metricValue(r.rec, r.rec.bruto !== undefined ? 'bruto' : 'raw')}</span></td>` +
      `<td class="num">${r.pct === null ? fmt.NA : fmt.percentile(r.pct)}</td></tr>`).join('');
    return `<table class="table compact"><thead><tr><th>Métrica</th><th class="num">Valor ajustado, intervalo 80% y bruto</th><th class="num">Frente a la liga</th></tr></thead><tbody>${body}</tbody></table>`;
  }
  const body = rows.map((r) => `<tr><th scope="row"><a href="#metodo/${encodeURIComponent(r.fid)}">${fmt.esc(r.label)}</a></th>${valueCell(r, fmt)}` +
    `<td class="num">${r.pct === null ? fmt.NA : fmt.percentile(r.pct)}</td><td class="muted">${fmt.esc(fmt.unitText(r.unit))}</td></tr>`).join('');
  return `<div class="scroll"><table class="table"><thead><tr><th>Métrica</th><th class="num">Valor ajustado</th><th class="num">Intervalo 80%</th>` +
    `<th class="num">Bruto</th><th class="num">Percentil en la liga</th><th>Unidad</th></tr></thead><tbody>${body}</tbody></table></div>`;
}

function relatedHTML(u, kind, ctx) {
  if (!u.related || !u.related.length) return '';
  return `<p class="muted">${KINDS[kind].related}: ${ctx.fmt.esc(u.related.join(' · '))}</p>`;
}

function listCard(u, kind, ctx) {
  const { fmt, mode } = ctx;
  const rows = metricRows(u);
  const hasData = rows.length || identityChips(u.identity).length;
  const detail = mode === 'dt' ? metricsTable(rows.filter((r) => LIST_DT_METRICS.includes(r.id)), ctx, true) : traitsHTML(u, ctx);
  const cls = ['card', u.small ? 'small' : '', u.window && u.window !== 'oficial' ? 'out' : ''].filter(Boolean).join(' ');
  return `<article class="${cls}"><header><h3><a href="${hrefOf(kind, u.key)}">${fmt.esc(u.name)}</a></h3>${badgesHTML(u, ctx)}</header>
    ${relatedHTML(u, kind, ctx)}${kind === 'dts' ? `<p class="muted">Promedio de todos sus clubes en la ventana oficial.</p><p><a class="btn sm ghost" href="#dt/${encodeURIComponent(u.key)}">Ver ficha del entrenador</a></p>` : ''}${chipsHTML(u.identity, ctx, mode === 'dt')}${detail}
    ${hasData ? '' : '<p class="muted">Abre la ficha para ver su detalle por temporada.</p>'}
    <p><a class="btn sm" href="${hrefOf(kind, u.key)}">Ver ficha →</a></p></article>`;
}

function headHTML(kind, title, lead) {
  const nav = Object.entries(KINDS).map(([k, v]) => `<a href="${hrefOf(k)}"${k === kind ? ' aria-current="page"' : ''}>${v.title}</a>`).join('');
  return `<header class="section-head vhead"><div><div class="eyebrow">Explorador · Liga MX</div><h2>${title}</h2><p>${lead}</p></div>
    <nav class="segmented" aria-label="Tipo de unidad">${nav}</nav></header>`;
}

const EMPTY = '<div class="empty card"><h3>Datos en construcción</h3><p>El explorador se publica cuando termine el cálculo de la liga.</p></div>';

async function renderList(root, ctx, kind) {
  const k = KINDS[kind];
  root.innerHTML = `<section class="view">${headHTML(kind, `¿Cómo juega y rinde cada ${k.noun}?`,
    'Todos los equipos y DTs con la misma regla de identidad que la historia. Con pocos partidos, el valor se acerca a su referencia previa (su carrera o la liga) para no exagerar.')}
    <div class="toolbar"><input class="input search" type="search" placeholder="Buscar ${k.noun}…" aria-label="Buscar ${k.noun}">
    <button type="button" class="btn sm" id="exp-small" aria-pressed="false">Ocultar muestras pequeñas</button></div>
    <p class="muted" id="exp-count"></p><div class="grid" id="exp-list"><p class="muted">Cargando…</p></div></section>`;
  const list = root.querySelector('#exp-list');
  let payload = null;
  try { payload = await ctx.api.tryJSON(k.list); } catch (e) { payload = null; }
  const units = unitsOf(payload);
  if (!units.length) { list.innerHTML = EMPTY; return; }
  const state = { q: '', hideSmall: false };
  const paint = () => {
    const shown = filterUnits(units, state.q).filter((u) => !state.hideSmall || !u.small);
    root.querySelector('#exp-count').textContent = `${ctx.fmt.num(shown.length, 0)} de ${ctx.fmt.num(units.length, 0)} ${k.plural}, ordenados por partidos.`;
    list.innerHTML = shown.length ? shown.map((u) => listCard(u, kind, ctx)).join('') : '<p class="muted">Ningún resultado con ese filtro.</p>';
  };
  paint();
  root.querySelector('.search').addEventListener('input', (ev) => { state.q = ev.target.value; paint(); });
  const toggle = root.querySelector('#exp-small');
  toggle.addEventListener('click', () => { state.hideSmall = !state.hideSmall; toggle.setAttribute('aria-pressed', String(state.hideSmall)); paint(); });
}

function seasonCard(s, kind, ctx) {
  const { fmt, mode } = ctx;
  const who = kind === 'equipos' ? s.coach : '';
  const sub = [who, mode === 'dt' && s.from ? `${fmt.date(s.from)} – ${fmt.date(s.to)}` : ''].filter(Boolean).join(' · ');
  const dt = mode === 'dt' ? `${metricsTable(metricRows(s), ctx)}<p class="muted">${fmt.esc(fmt.prior(s.prior))}</p>` : traitsHTML(s, ctx);
  const cls = ['card', s.small ? 'small' : '', s.window && s.window !== 'oficial' ? 'out' : ''].filter(Boolean).join(' ');
  return `<article class="${cls}"><header><h3>${fmt.esc(s.label || 'Temporada')}</h3>${badgesHTML(s, ctx)}</header>
    ${sub ? `<p class="muted">${fmt.esc(sub)}</p>` : ''}${chipsHTML(s.identity, ctx, mode === 'dt')}${dt}</article>`;
}

function summaryCard(u, kind, ctx) {
  const { fmt, mode } = ctx;
  const rows = metricRows(u);
  const body = mode === 'dt'
    ? `${metricsTable(rows, ctx)}${u.prior ? `<p class="muted">${fmt.esc(fmt.prior(u.prior))}</p>` : ''}`
    : traitsHTML(u, ctx);
  return `<article class="card protag"><header><h3>${fmt.esc(u.name)}</h3>${badgesHTML(u, ctx)}</header>
    ${relatedHTML(u, kind, ctx)}${chipsHTML(u.identity, ctx, mode === 'dt')}${body}</article>`;
}

function percentilesFigure(u, ctx) {
  const rows = metricRows(u).filter((r) => r.pct !== null).map((r) => ({ label: r.label, pct: r.pct }));
  if (!rows.length) return '';
  return `<div class="panel">${dotPlot({ title: `Dónde se separa ${u.name} del equipo típico`, unit: 'percentil en la liga (50 = típico)',
    n: u.n, window: u.window || 'oficial' }, rows)}</div>`;
}

function detailHTML(detail, kind, ctx) {
  const [u] = unitsOf([detail]);
  const k = KINDS[kind];
  const seasons = seasonsOf(detail);
  const list = seasons.length
    ? `<div class="grid">${seasons.map((s) => seasonCard(s, kind, ctx)).join('')}</div>`
    : '<div class="card empty"><p>El detalle por temporada se publica cuando termine el cálculo del explorador.</p></div>';
  return `<p><a class="btn sm ghost" href="${hrefOf(kind)}">${k.back}</a></p>
    <p class="caption">Valores ajustados hacia su referencia previa con k = 8 partidos; intervalo central al 80%. Solo la ventana oficial entra en las conclusiones.</p>
    ${summaryCard(u, kind, ctx)}
    ${ctx.mode === 'dt' ? percentilesFigure(u, ctx) : ''}<h3 class="subhead">${k.seasons}</h3>${list}`;
}

async function renderDetail(root, ctx, kind, key) {
  const k = KINDS[kind];
  root.innerHTML = `<section class="view">${headHTML(kind, `Ficha del ${k.noun}`, 'Identidad, rendimiento ajustado por tamaño de muestra y su evolución por etapa.')}
    <div id="exp-body"><p class="muted">Cargando…</p></div></section>`;
  const body = root.querySelector('#exp-body');
  let detail = null;
  try { detail = await ctx.api.tryJSON(k.detail + encodeURIComponent(key)); } catch (e) { detail = null; }
  if (!detail || typeof detail !== 'object') {
    body.innerHTML = `<div class="empty card"><h3>No encontramos «${ctx.fmt.esc(key)}»</h3><p><a href="${hrefOf(kind)}">${k.back}</a></p></div>`;
    return;
  }
  body.innerHTML = detailHTML(detail, kind, ctx);
}

export async function render(root, ctx) {
  const { kind, key } = routeOf(ctx.params);
  if (key) await renderDetail(root, ctx, kind, key);
  else await renderList(root, ctx, kind);
}
