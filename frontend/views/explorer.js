/* Explorador: rendimiento por equipo y por DT con valores encogidos al prior, intervalo 80% y confianza. */
const KINDS = { equipos: { path: '/api/explorer/teams', title: 'Por equipo' }, dts: { path: '/api/explorer/coaches', title: 'Por entrenador' } };

/** Normaliza la respuesta (lista o {items|teams|coaches}) a una lista de unidades. */
export function unitsOf(payload) {
  if (Array.isArray(payload)) return payload;
  if (!payload || typeof payload !== 'object') return [];
  return payload.items || payload.teams || payload.coaches || [];
}
function metricsOf(u) {
  const m = u.metrics || [];
  return Array.isArray(m) ? m : Object.entries(m).map(([id, v]) => ({ id, ...(typeof v === 'object' ? v : { value: v }) }));
}
function card(u, kind, ctx) {
  const { fmt } = ctx;
  const key = u.key || u.id || '';
  const name = u.label || u.name || key;
  const small = u.small_sample || (Number.isFinite(u.n) && u.n < 10);
  const metrics = metricsOf(u).slice(0, ctx.mode === 'dt' ? 8 : 3);
  const rows = metrics.map((m) => `<tr><th>${fmt.esc(m.nombre || m.label || m.id)}</th>
    <td class="num">${fmt.num(m.shrunk ?? m.value)}</td>
    ${ctx.mode === 'dt' ? `<td class="num muted">${fmt.interval(m.ci || m.interval)}</td><td class="num muted">${fmt.num(m.raw)}</td>` : ''}</tr>`).join('');
  const head = ctx.mode === 'dt' ? '<tr><th>Métrica</th><th>Valor ajustado</th><th>Intervalo 80%</th><th>Crudo</th></tr>' : '';
  const link = kind === 'dts' ? `<a href="#dt/${encodeURIComponent(key)}">Ver ficha del DT →</a>` : `<a href="#equipo/${encodeURIComponent(key)}">Ver equipo →</a>`;
  const identity = u.identity ? `<p>${fmt.esc([u.identity.build, u.identity.defense, u.identity.attack].filter(Boolean).join(' · '))}</p>` : '';
  return `<article class="card${small ? ' small' : ''}"><header><h3>${fmt.esc(name)}</h3>
    <div class="badges"><span class="badge">${fmt.num(u.n, 0)} partidos</span>
    <span class="badge">${fmt.confidence(u.confidence)}</span>${small ? '<span class="badge warn">Muestra pequeña</span>' : ''}</div></header>
    ${identity}${rows ? `<table class="kv">${head}${rows}</table>` : '<p class="muted">Sin métricas publicadas todavía.</p>'}
    <p class="caption">Valores ajustados hacia su referencia previa (prior) para no exagerar muestras chicas.</p>${link}</article>`;
}
export async function render(root, ctx) {
  const kind = ctx.params && ctx.params[0] === 'dts' ? 'dts' : 'equipos';
  const tabs = Object.entries(KINDS).map(([k, v]) => `<a class="seg${k === kind ? ' on' : ''}" href="#explorador/${k}">${v.title}</a>`).join('');
  root.innerHTML = `<section class="view"><header class="vhead"><h2>Explorador: ¿cómo rinde cada ${kind === 'dts' ? 'entrenador' : 'equipo'}?</h2>
    <p>Todos los equipos y DTs de la liga con la misma regla de identidad que la historia. Con pocos partidos el valor se acerca a su referencia previa.</p>
    <nav class="segs">${tabs}</nav></header><div class="grid" id="exp-list"><p class="muted">Cargando…</p></div></section>`;
  const list = root.querySelector('#exp-list');
  let payload = null;
  try { payload = await ctx.api.tryJSON(KINDS[kind].path); } catch (e) { payload = null; }
  const units = unitsOf(payload);
  if (!units.length) { list.innerHTML = '<div class="empty card"><h3>Datos en construcción</h3><p>El explorador se publica cuando termine el cálculo de la liga.</p></div>'; return; }
  list.innerHTML = units.map((u) => card(u, kind, ctx)).join('');
}
