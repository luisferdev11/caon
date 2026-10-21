/* Método: glosario del framework (/api/framework) con IDs, fórmula, alcance y límites. */
export function definitionsOf(payload) {
  if (!payload) return [];
  const defs = payload.definitions || payload.DEFINITIONS || payload;
  if (Array.isArray(defs)) return defs;
  return Object.entries(defs).filter(([, v]) => v && typeof v === 'object').map(([id, v]) => ({ id, ...v }));
}
function item(d, ctx) {
  const { fmt } = ctx;
  const extra = ctx.mode === 'dt'
    ? `${d.formula ? `<dt>Fórmula</dt><dd><code>${fmt.esc(d.formula)}</code></dd>` : ''}${d.fuente ? `<dt>Fuente</dt><dd>${fmt.esc(d.fuente)}</dd>` : ''}`
    : '';
  return `<article class="card" id="def-${fmt.esc(d.id)}"><header><h3>${fmt.esc(d.nombre || d.id)}</h3><span class="badge mono">${fmt.esc(d.id)}</span></header>
    <p>${fmt.esc(d.definicion || '')}</p><dl class="kv">${d.unidad ? `<dt>Unidad</dt><dd>${fmt.esc(d.unidad)}</dd>` : ''}
    ${d.limites ? `<dt>Límites</dt><dd>${fmt.esc(d.limites)}</dd>` : ''}${extra}</dl></article>`;
}
export async function render(root, ctx) {
  root.innerHTML = `<section class="view"><header class="vhead"><h2>Método: cómo medimos cada cosa</h2>
    <p>Cada número del portal tiene un identificador que aparece aquí con su definición. Las conclusiones solo usan la ventana oficial de cada DT; lo demás lleva la insignia «Fuera de ventana oficial».</p>
    <input class="search" type="search" placeholder="Buscar métrica…" aria-label="Buscar métrica"></header>
    <div class="grid" id="defs"><p class="muted">Cargando…</p></div></section>`;
  const box = root.querySelector('#defs');
  let payload = null;
  try { payload = await ctx.api.tryJSON('/api/framework'); } catch (e) { payload = null; }
  const defs = definitionsOf(payload);
  if (!defs.length) { box.innerHTML = '<div class="empty card"><h3>Glosario en construcción</h3><p>El registro de definiciones aún no está publicado.</p></div>'; return; }
  const paint = (q) => { box.innerHTML = defs.filter((d) => !q || JSON.stringify(d).toLowerCase().includes(q)).map((d) => item(d, ctx)).join(''); };
  paint('');
  root.querySelector('.search').addEventListener('input', (ev) => paint(ev.target.value.trim().toLowerCase()));
}
