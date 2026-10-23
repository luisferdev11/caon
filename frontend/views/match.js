/* Partidos: lista filtrable (#partidos) y ficha de un partido real (#partido/<id>), al estilo de una ficha de resultados.
   Ficha: marcador, «¿mereció ganar?» (probabilidad de ganar/empatar/perder con el xG de sus tiros y puntos contra xPts),
   momentos clave, xG acumulado minuto a minuto y 3 datos curiosos. DT: además el detalle en una tabla.
   Datos: /api/entities/{id}/matches y /api/matches/{id}. La repetición es una interpretación, no un pronóstico. */
import { esc } from '../js/fmt.js';
import { barsCI, figure } from '../js/charts.js';
import { legendHTML } from '../js/pitch.js';
import { seeData, windowBadge } from '../js/cards.js';

const ENTITIES = ['ame_jardine', 'ame_jardine_epi', 'ame_almada', 'pac_almada', 'ame_solari', 'ame_ortiz', 'slp_jardine', 'san_almada'];
const DEFAULT_ENTITY = 'ame_jardine';
const LABELS = { ame_jardine: 'América · Jardine (Tricampeonato)', ame_jardine_epi: 'América · Jardine (2025/26)', ame_almada: 'América · Almada',
  pac_almada: 'Pachuca · Almada', ame_solari: 'América · Solari', ame_ortiz: 'América · Ortiz', slp_jardine: 'San Luis · Jardine', san_almada: 'Santos · Almada' };
const RESULT = { G: 'Ganó', E: 'Empató', P: 'Perdió' };
const VERDICT = { merecio_ganar: 'Mereció ganar', parejo: 'Partido parejo', merecio_perder: 'Mereció perder' };
const BALANCE = { por_encima: 'Sacó más puntos de lo que generó.', acorde: 'El resultado fue acorde a las ocasiones.', por_debajo: 'Mereció más puntos de los que sacó.' };
const MOMENT = { gol: 'Gol', gran_ocasion: 'Gran ocasión', autogol: 'Autogol' };
const FILTERS = [['', 'Todos'], ['G', 'Ganados'], ['E', 'Empatados'], ['P', 'Perdidos']];
const PROB_LABELS = [['G', 'Ganar'], ['E', 'Empatar'], ['P', 'Perder']];

const finite = (v) => typeof v === 'number' && Number.isFinite(v);
const score = (m) => (m && finite(m.propio) ? `${m.propio}–${m.rival}` : 's/d');

// ---------------------------------------------------------------- lista
function rowHTML(r, fmt) {
  const local = r.localia === 'local' ? 'Local' : 'Visita';
  return `<tr><td>${esc(fmt.date(r.fecha))}</td><td>${esc(r.torneo || '')}</td><th scope="row"><a href="#partido/${encodeURIComponent(r.match_id)}">${esc(r.rival)}</a></th>
    <td>${local}</td><td class="num">${score(r.marcador)}</td><td>${esc(RESULT[r.actual] || '')}</td><td class="muted">${esc(VERDICT[r.veredicto] || '')}</td></tr>`;
}

function listBody(rows, f, fmt) {
  const shown = rows.filter((r) => (!f.torneo || r.torneo === f.torneo) && (!f.result || r.actual === f.result))
    .sort((a, b) => String(b.fecha).localeCompare(String(a.fecha)));
  if (!shown.length) return '<div class="empty card"><h3>Sin partidos con este filtro</h3><p class="muted">Cambia el torneo o el resultado.</p></div>';
  const count = (k) => shown.filter((r) => r.actual === k).length;
  const out = shown.some((r) => r.window && r.window !== 'oficial') ? '<span class="badge out">Fuera de ventana oficial</span>' : '';
  return `<p class="muted">${fmt.num(shown.length, 0)} partidos: ${count('G')} ganados, ${count('E')} empatados, ${count('P')} perdidos. ${out}</p>
    <div class="scroll"><table class="table"><thead><tr><th>Fecha</th><th>Torneo</th><th>Rival</th><th>Condición</th><th class="num">Marcador</th><th>Resultado</th><th>¿Mereció ganar?</th></tr></thead>
    <tbody>${shown.map((r) => rowHTML(r, fmt)).join('')}</tbody></table></div>`;
}

async function renderList(root, ctx, entity) {
  const { api, fmt } = ctx;
  const data = await api.tryJSON(`/api/entities/${entity}/matches`);
  const rows = (data && data.partidos) || [];
  const f = { torneo: '', result: '' };
  const entities = await api.tryJSON('/api/entities');
  const label = (id) => ((entities || []).find((e) => e.id === id) || {}).label || LABELS[id] || id;
  const torneos = [...new Set(rows.map((r) => r.torneo).filter(Boolean))];
  const opt = (v, t, sel) => `<option value="${esc(v)}"${sel ? ' selected' : ''}>${esc(t)}</option>`;
  root.innerHTML = `<section class="view"><header class="section-head vhead"><div><div class="eyebrow">Partidos reales · repetición con xG</div>
    <h2>Cada partido, con lo que pedían sus ocasiones</h2><p>Elige un equipo y entra a la ficha de cualquier partido: marcador, momentos clave y si el resultado fue justo.</p></div></header>
    <div class="toolbar" id="m-filters"><label class="field"><span class="visually-hidden">Equipo</span><select id="f-ent" aria-label="Equipo">${ENTITIES.map((id) => opt(id, label(id), id === entity)).join('')}</select></label>
    <label class="field"><span class="visually-hidden">Torneo</span><select id="f-torneo" aria-label="Torneo">${opt('', 'Todos los torneos', true)}${torneos.map((t) => opt(t, t)).join('')}</select></label>
    <div class="segmented" role="group" aria-label="Resultado" id="f-result">${FILTERS.map(([v, t]) => `<button type="button" data-r="${v}" aria-pressed="${v === ''}">${t}</button>`).join('')}</div></div>
    <div id="m-list">${rows.length ? listBody(rows, f, fmt) : '<div class="empty card"><h3>Datos en construcción</h3><p class="muted">Todavía no hay partidos publicados para este equipo.</p></div>'}</div></section>`;
  const list = root.querySelector('#m-list'), bar = root.querySelector('#m-filters');
  const paint = () => { list.innerHTML = listBody(rows, f, fmt); };
  bar.addEventListener('change', (e) => {
    if (e.target.id === 'f-ent') { ctx.navigate(`#partidos/${e.target.value}`); return; }
    if (e.target.id === 'f-torneo') { f.torneo = e.target.value; paint(); }
  });
  bar.addEventListener('click', (e) => {
    const b = e.target.closest && e.target.closest('[data-r]');
    if (!b) return;
    f.result = b.dataset.r;
    for (const x of bar.querySelectorAll('[data-r]')) x.setAttribute('aria-pressed', String(x === b));
    paint();
  });
}

// ---------------------------------------------------------------- ficha
/** xG acumulado: dos escalones (equipo en dorado, rival en azul); los minutos del 2.º tiempo continúan tras el añadido. */
function xgChart(f, fmt) {
  const a = (f.ficha || {}).xg_acumulado;
  if (!a || !a.minuto || !a.minuto.length) return '';
  let offset = 0, prev = 0;
  const xs = a.minuto.map((m) => { if (m < prev) offset += prev - m; prev = m; return m + offset; });
  const xmax = Math.max(90, ...xs), ymax = Math.max(0.5, ...a.propio, ...a.rival) * 1.1;
  const X = (v) => (v / xmax) * 96 + 2, Y = (v) => 48 - (v / ymax) * 44;
  const path = (ys) => xs.reduce((d, x, i) => `${d}${i ? `H${X(x).toFixed(1)}V${Y(ys[i]).toFixed(1)}` : `M${X(x).toFixed(1)},${Y(ys[i]).toFixed(1)}`}`, '') + `H${X(xmax).toFixed(1)}`;
  const half = `<line x1="${X(45)}" x2="${X(45)}" y1="2" y2="48" class="ch-ref"/>`;
  const svg = `<svg viewBox="0 0 100 50" preserveAspectRatio="none" class="ch-tsvg xgline" role="img" aria-label="xG acumulado por minuto">${half}
    <path d="${path(a.rival)}" class="ch-line rival"/><path d="${path(a.propio)}" class="ch-line"/></svg>
    <div class="axis"><span>0'</span><span>45'</span><span>90'</span></div>`;
  return figure({ title: `xG acumulado: ${fmt.num(f.xg.propio)} contra ${fmt.num(f.xg.rival)}`, unit: 'xG sin tanda de penales', window: f.window },
    `${legendHTML([{ side: 'protag', label: f.equipo }, { side: 'rival', label: f.rival }])}${svg}`);
}

function probChart(f) {
  const rows = PROB_LABELS.map(([k, label]) => ({ label: `${label}${k === f.actual ? ' (lo que pasó)' : ''}`, value: 100 * f.p[k]}));
  return barsCI({ title: `${(f.ficha.merecio || {}).texto || 'Probabilidad de cada resultado'}`, unit: '% de 20,000 repeticiones del partido', window: f.window }, rows);
}

function momentsHTML(f, fmt) {
  const items = ((f.ficha || {}).momentos || []).map((m) => {
    const who = m.equipo === 'propio' ? f.equipo : f.rival;
    return `<li><b>${fmt.minute(m.minuto)}</b> <span class="chip${m.equipo === 'propio' ? ' protag' : ' rival'}">${esc(MOMENT[m.tipo] || m.tipo)}</span> ${esc(who)}${m.jugador ? ` · ${esc(m.jugador)}` : ''} <span class="muted">xG ${fmt.num(m.xg)}</span></li>`;
  });
  return items.length ? `<div class="panel"><span class="kicker">Momentos clave</span><ul class="moments">${items.join('')}</ul></div>` : '';
}

function detailTable(f, fmt) {
  const rows = [['Probabilidad de ganar / empatar / perder', `${fmt.num(100 * f.p.G, 0)}% / ${fmt.num(100 * f.p.E, 0)}% / ${fmt.num(100 * f.p.P, 0)}%`],
    ['Puntos reales / esperados (xPts)', `${f.points} / ${fmt.num(f.xpts)}`], ['Probabilidad del resultado que ocurrió', `${fmt.num(100 * f.p_actual, 0)}%`],
    ['Resultado sorpresivo (menos de 20 %)', f.sorpresivo ? 'Sí' : 'No'], ['xG del equipo / del rival', `${fmt.num(f.xg.propio)} / ${fmt.num(f.xg.rival)}`],
    ['xG de penales (equipo / rival)', `${fmt.num((f.penales_xg || {}).propio)} / ${fmt.num((f.penales_xg || {}).rival)}`],
    ['Participación en el xG total', fmt.pct((f.dominio || {}).xg_share)], ['Field tilt', fmt.pct((f.dominio || {}).field_tilt)]];
  return seeData(['Dato', 'Valor'], rows, 'Ver datos del partido');
}

async function renderCard(root, ctx, id) {
  const { api, fmt, mode } = ctx;
  const f = await api.tryJSON(`/api/matches/${encodeURIComponent(id)}`);
  const back = '<a class="btn sm ghost" href="#partidos">← Todos los partidos</a>';
  if (!f || !f.ficha) {
    root.innerHTML = `<section class="view">${back}<div class="empty card"><h3>No encontramos este partido</h3><p class="muted">Revisa la lista de partidos.</p></div></section>`;
    return;
  }
  const m = f.ficha.merecio || {}, tx = f.textos || {};
  const home = f.localia === 'local';
  const head = home ? `${esc(f.equipo)} ${score(f.ficha.marcador)} ${esc(f.rival)}` : `${esc(f.rival)} ${score({ propio: f.ficha.marcador.rival, rival: f.ficha.marcador.propio })} ${esc(f.equipo)}`;
  const verdict = (tx.veredicto || VERDICT)[m.veredicto] || VERDICT[m.veredicto] || '';
  const out = f.window && f.window !== 'oficial' ? `<div class="badges">${windowBadge(f.window)}</div>` : '';
  const curiosos = ((f.ficha || {}).datos_curiosos || []).slice(0, 3).map((t) => `<li>${esc(t)}</li>`).join('');
  root.innerHTML = `<section class="view match">${back}<header class="section-head vhead"><div>
    <div class="eyebrow">${esc(f.torneo || '')} · ${esc(fmt.date(f.fecha))} · ${home ? 'Local' : 'Visita'} · ${esc((tx.resultado || RESULT)[f.actual] || '')}</div>
    <h2>${head}</h2>${out}</div></header>
    <article class="card verdict"><header><div><span class="kicker">¿Mereció ganar?</span><h3>${esc(verdict)}</h3></div></header><p>${esc(m.texto || '')}</p>
    <p class="interp">${esc((tx.balance || BALANCE)[m.balance] || BALANCE[m.balance] || '')} <span class="muted">Es una interpretación con el xG de sus tiros, no un pronóstico.</span></p>
    ${mode === 'dt' ? detailTable(f, fmt) : ''}</article>
    <div class="chart-grid">${probChart(f)}${xgChart(f, fmt)}</div>${momentsHTML(f, fmt)}
    ${curiosos ? `<aside class="panel curioso"><span class="kicker">Datos curiosos</span><ul class="moments">${curiosos}</ul></aside>` : ''}</section>`;
}

export async function render(root, ctx) {
  const id = (ctx.params || [])[0];
  if (id && /^\d+$/.test(id)) return renderCard(root, ctx, id);
  return renderList(root, ctx, ENTITIES.includes(id) ? id : DEFAULT_ENTITY);
}
