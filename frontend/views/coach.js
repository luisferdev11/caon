/* Ficha de entrenador (#dt/<clave>): cinco rasgos en palabras sencillas, su carrera por club (línea de tiempo) y los KPIs
   de cada etapa con su confianza. Todo sale del explorador (/api/explorer/coach/<clave>) y de /api/kpis/<entidad>;
   una muestra pequeña se dice en voz alta y nunca se vende como conclusión. */
import { esc } from '../js/fmt.js';
import { dotPlot } from '../js/charts.js';
import { seeData } from '../js/cards.js';
import { METRICS, identityChips, metricRows, normalizeUnit, seasonsOf, traits } from '../js/explorer_data.js';

const FIVE = 5;
const BACK = '<a class="btn sm ghost" href="#explorador/dts">← Todos los entrenadores</a>';
const finite = (v) => typeof v === 'number' && Number.isFinite(v);

function headerHTML(u, ctx) {
  const { fmt } = ctx;
  const badges = [`<span class="badge">${fmt.num(u.n, 0)} partidos</span>`, u.confidence ? `<span class="badge">${fmt.confidence(u.confidence)}</span>` : '',
    u.small ? '<span class="badge warn">Muestra pequeña</span>' : '', u.window && u.window !== 'oficial' ? '<span class="badge out">Fuera de ventana oficial</span>' : ''];
  const clubs = u.related.length ? `<p class="muted">Clubes: ${esc(u.related.join(' · '))}</p>` : '';
  return `<header class="section-head vhead"><div><div class="eyebrow">Entrenador · ventana oficial${u.from ? ` · ${esc(fmt.date(u.from))} a ${esc(fmt.date(u.to))}` : ''}</div>
    <h2>${esc(u.name)}</h2>${clubs}<p><a href="#explorador/dts/${encodeURIComponent(u.key)}">Ver su detalle por temporada en el explorador →</a></p><div class="badges">${badges.join('')}</div></div></header>`;
}

function traitsCard(u, detail, ctx) {
  const items = traits({ metricas: u.metricas }, FIVE);
  const chips = identityChips(u.identity).map((t) => `<span class="chip info">${esc(t)}</span>`).join('');
  const tags = ((u.identity || {}).tags || []).map((t) => `<span class="tag">${esc(t)}</span>`).join('');
  const words = (t) => ((t.high ? (METRICS[t.id] || {}).alto : (METRICS[t.id] || {}).bajo) || t.text);   // Aficionado: sin percentiles
  const list = items.length ? `<ul class="traits">${items.map((t) => `<li>${esc(ctx.mode === 'dt' ? t.text : words(t))}</li>`).join('')}</ul>` : '<p class="muted">Todavía no hay rasgos que destaquen frente a la liga.</p>';
  const table = ctx.mode === 'dt' ? seeData(['Rasgo', 'Valor ajustado', 'Intervalo 80%', 'Bruto', 'Percentil'], metricRows({ metricas: u.metricas, window: u.window }).map((r) => [r.label,
    ctx.fmt.metricValue(r.rec), ctx.fmt.ciByUnit(r.ci, r.unit, r.rec.source), ctx.fmt.metricValue(r.rec, r.rec.bruto !== undefined ? 'bruto' : 'raw'), r.pct === null ? 's/d' : String(Math.round(r.pct))]), 'Ver datos de los rasgos') : '';
  return `<article class="card"><header><h3>Cómo juega, en cinco rasgos</h3></header>${chips ? `<div class="chips">${chips}</div>` : ''}${tags ? `<div class="tags">${tags}</div>` : ''}${list}${table}</article>`;
}

function timelineHTML(tenures, ctx) {
  const { fmt } = ctx;
  if (!tenures.length) return '';
  const max = Math.max(...tenures.map((t) => t.n || 0), 1);
  const items = tenures.map((t) => `<li class="tl"><div class="tl-head"><b>${esc(t.team || t.label)}</b><span class="muted">${esc(fmt.date(t.from))} a ${esc(fmt.date(t.to))}</span></div>
    <div class="tl-bar" style="width:${Math.max(6, Math.round((100 * (t.n || 0)) / max))}%" role="img" aria-label="${fmt.num(t.n, 0)} partidos"></div>
    <div class="badges"><span class="badge">${fmt.num(t.n, 0)} partidos</span>${t.confidence ? `<span class="badge">${fmt.confidence(t.confidence)}</span>` : ''}${t.small ? '<span class="badge warn">Muestra pequeña</span>' : ''}${t.window && t.window !== 'oficial' ? `<span class="badge out">Fuera de ventana oficial</span>` : ''}</div></li>`);
  return `<section class="chapter"><header class="section-head"><div><span class="eyebrow">Su carrera</span><h2>Por dónde ha dirigido</h2></div></header><ol class="timeline">${items.join('')}</ol></section>`;
}

function tenureKpis(t, rows, ctx) {
  const good = (rows || []).filter((k) => k.value !== null && finite(k.pct_bueno));
  if (!good.length) return '';
  const warn = t.small ? '<p class="caption">Muestra pequeña: los percentiles son una lectura inicial, no una conclusión.</p>' : '';
  return `<div class="visual">${dotPlot({ title: `${t.team}: sus siete indicadores frente a la liga`, unit: 'percentil 0–100 donde más a la derecha es mejor', n: t.n, window: t.window || 'oficial' },
    good.map((k) => ({ label: k.nombre, pct: k.pct_bueno })))}${warn}</div>`;
}

export async function render(root, ctx) {
  const { api } = ctx;
  const key = (ctx.params || [])[0];
  if (!key) {
    root.innerHTML = `<section class="view">${BACK}<div class="empty card"><h3>Elige un entrenador</h3><p class="muted">Abre su ficha desde el explorador.</p></div></section>`;
    return;
  }
  const detail = await api.tryJSON(`/api/explorer/coach/${encodeURIComponent(key)}`);
  if (!detail || typeof detail !== 'object') {
    root.innerHTML = `<section class="view">${BACK}<div class="empty card"><h3>No encontramos a este entrenador</h3><p class="muted">Revisa el explorador de entrenadores.</p></div></section>`;
    return;
  }
  const u = normalizeUnit(detail), raw = Array.isArray(detail.tenencias) ? detail.tenencias : [], tenures = seasonsOf({ tenencias: raw });
  const kpis = await Promise.all(raw.map(async (t) => {
    const ent = (t.entidades || []).find((e) => !t.window || e.window === t.window) || (t.entidades || [])[0];
    const data = ent ? await api.tryJSON(`/api/kpis/${encodeURIComponent(ent.id)}`) : null;
    return ((data || {}).kpis || {})[t.window || 'oficial'] || [];
  }));
  const ordered = raw.map((t, i) => ({ t: seasonsOf({ tenencias: [t] })[0], rows: kpis[i] })).sort((a, b) => String(a.t.from || '').localeCompare(String(b.t.from || '')));
  root.innerHTML = `<section class="view story">${BACK}${headerHTML(u, ctx)}${traitsCard(u, detail, ctx)}${timelineHTML(tenures, ctx)}
    ${ordered.map(({ t, rows }) => tenureKpis(t, rows, ctx)).join('')}</section>`;
}
