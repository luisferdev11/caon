/* Método: glosario del framework (/api/framework) como entradas de referencia (no tarjetas de datos):
   ID, definición, unidad, límites y, en modo DT, fórmula y fuente. #metodo/<id> pone esa definición primero y la resalta (enlaces «¿Cómo se mide?»). */
import { definitionsOf } from '../js/glossary.js';
import { esc } from '../js/fmt.js';

export { definitionsOf };

function item(d, ctx, focused) {
  const { fmt } = ctx;
  const extra = ctx.mode === 'dt'
    ? `${d.formula ? `<dt>Fórmula</dt><dd><code>${fmt.esc(d.formula)}</code></dd>` : ''}${d.fuente ? `<dt>Fuente</dt><dd>${fmt.esc(fmt.source(d.fuente) || d.fuente)}</dd>` : ''}`
    : '';
  return `<article class="def${focused ? ' focus' : ''}" id="def-${fmt.esc(d.id)}"><header><h3>${fmt.esc(d.nombre || d.id)}</h3><code class="badge">${fmt.esc(d.id)}</code></header>
    <p>${fmt.esc(d.definicion || '')}</p><dl class="defs">${d.unidad ? `<dt>Unidad</dt><dd>${fmt.esc(d.unidad)}</dd>` : ''}
    ${d.limites ? `<dt>Límites</dt><dd>${fmt.esc(d.limites)}</dd>` : ''}${extra}</dl></article>`;
}

const list = (items) => `<ul class="traits">${(items || []).map((t) => `<li>${esc(t)}</li>`).join('')}</ul>`;

/** Supuestos, alcance, límites, los 7 KPIs y (DT) los umbrales: lo que el framework declara antes del glosario. */
export function introHTML(payload, ctx) {
  const p = payload && typeof payload === 'object' ? payload : {};
  const block = (title, items) => (items && items.length ? `<div class="panel"><span class="kicker">${title}</span>${list(items)}</div>` : '');
  const kpis = (p.kpis || []).map((k) => `<li><a href="#metodo/${encodeURIComponent(k.id)}"><strong>${esc(k.nombre)}</strong></a> · ${k.mejor === 'bajo' ? 'menos es mejor' : 'más es mejor'}</li>`);
  const kpiBlock = kpis.length ? `<div class="panel"><span class="kicker">Los siete indicadores</span><ul class="traits">${kpis.join('')}</ul>
    <p class="muted">Cada uno se compara con la liga (percentil) y consigo mismo: el semáforo usa los terciles propios del equipo y la frase «en partidos en verde sumó…» es una asociación, no una causa.</p></div>` : '';
  const rows = Object.entries(p.thresholds || {}).map(([k, v]) => [k, Array.isArray(v) ? v.join(' – ') : String(v)]);
  const table = ctx.mode === 'dt' && rows.length ? `<details class="seedata"><summary>Umbrales con nombre</summary><div class="scroll"><table class="table"><thead><tr><th>Constante</th><th>Valor</th></tr></thead><tbody>${rows.map(([k, v]) => `<tr><th scope="row"><code>${esc(k)}</code></th><td class="num">${esc(v)}</td></tr>`).join('')}</tbody></table></div></details>` : '';
  return `<div class="chart-grid">${block('Alcance', p.scope)}${block('Límites', p.limits)}${block('Supuestos', p.assumptions)}</div>${kpiBlock}${table}`;
}

/** Ordena con la definición pedida primero; devuelve {defs, found}. */
export function focusFirst(defs, id) {
  if (!id) return { defs, found: true };
  const hit = defs.find((d) => d.id === id);
  return hit ? { defs: [hit, ...defs.filter((d) => d !== hit)], found: true } : { defs, found: false };
}

export async function render(root, ctx) {
  const focus = (ctx.params && ctx.params[0]) || '';
  root.innerHTML = `<section class="view"><header class="section-head vhead"><div><div class="eyebrow">Método</div><h2>Cómo medimos cada cosa</h2>
    <p>Cada número del portal tiene un identificador que aparece aquí con su definición. Las conclusiones solo usan la ventana oficial de cada DT; lo demás lleva la insignia «Fuera de ventana oficial».</p></div></header>
    <div id="method-intro"></div>
    <div class="toolbar"><input class="input search" type="search" placeholder="Buscar métrica…" aria-label="Buscar métrica"></div>
    <div class="deflist" id="defs"><p class="muted">Cargando…</p></div></section>`;
  const box = root.querySelector('#defs');
  let payload = null;
  try { payload = await ctx.api.tryJSON('/api/framework'); } catch (e) { payload = null; }
  root.querySelector('#method-intro').innerHTML = introHTML(payload, ctx);
  const all = definitionsOf(payload);
  if (!all.length) { box.innerHTML = '<div class="empty card"><h3>Glosario en construcción</h3><p>El registro de definiciones aún no está publicado.</p></div>'; return; }
  const { defs, found } = focusFirst(all, focus);
  const note = found ? '' : `<div class="card empty"><p>No hay una definición publicada con el identificador «${ctx.fmt.esc(focus)}». Usa el buscador.</p></div>`;
  const paint = (q) => {
    const shown = defs.filter((d) => !q || JSON.stringify(d).toLowerCase().includes(q));
    box.innerHTML = (q ? '' : note) + (shown.length ? shown.map((d) => item(d, ctx, found && d.id === focus)).join('') : '<p class="muted">Ninguna definición coincide.</p>');
  };
  paint('');
  root.querySelector('.search').addEventListener('input', (ev) => paint(ev.target.value.trim().toLowerCase()));
}
