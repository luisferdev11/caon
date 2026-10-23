/* Historia: «cómo juega el América de Jardine» en 12 capítulos, de la portada al epílogo fuera de ventana.
   Aficionado: por capítulo 1 conclusión, 1 visual, 1 dato curioso y los hallazgos como titular + lectura (≤3 números por tarjeta).
   DT: todo el detalle (Hecho observado / Interpretación / Evidencia con n e intervalo, tablas «Ver datos»).
   Datos: /api/story/jardine + analysis, KPIs y estilo del protagonista (los números ya vienen calculados). */
import { esc } from '../js/fmt.js';
import { finding as findingCard, windowBadge } from '../js/cards.js';
import { countNumbers, MAX_FAN_NUMBERS } from '../js/qa.js';
import { visualFor } from './story_visuals.js';

const ENTITY = 'ame_jardine', EPILOGUE = 'ame_jardine_epi';

/** Tarjeta del modo Aficionado: el titular y, si cabe, la lectura; sin el bloque de hechos.
    Un titular con más de 3 números, o uno cuyo detalle ya se dibuja en el visual, se deja para el modo DT (devuelve ''). */
export function fanFinding(f) {
  if (f.detalle || countNumbers(f.titulo) > MAX_FAN_NUMBERS) return '';   // las jugadas ya se ven dibujadas arriba
  const interp = f.interpretacion && countNumbers(`${f.titulo} ${f.interpretacion}`) <= MAX_FAN_NUMBERS ? `<p class="interp">${esc(f.interpretacion)}</p>` : '';
  const out = f.window && f.window !== 'oficial';
  return `<article class="card finding${out ? ' out' : ''}"><header><h3>${esc(f.titulo)}</h3>${out ? `<div class="badges">${windowBadge(f.window)}</div>` : ''}</header>${interp}</article>`;
}

function chapterHTML(ch, data, ctx) {
  const out = ch.id === 'epilogo';
  const a = ch.aficionado || {};
  const cards = ch.hallazgos.map((f) => (ctx.mode === 'dt' ? findingCard(f, ctx) : fanFinding(f))).filter(Boolean).join('');
  const body = ch.hallazgos.length
    ? (cards ? `<div class="grid findings">${cards}</div>` : '')
    : `<div class="empty card"><h3>Sin datos suficientes</h3><p class="muted">${esc(ch.motivo || 'Este capítulo se publica cuando haya datos.')}</p></div>`;
  const visual = a.visual ? visualFor(a.visual, data, ctx, ch) : '';
  return `<section class="chapter${out ? ' out' : ''}" id="cap-${esc(ch.id)}" aria-labelledby="h-${esc(ch.id)}">
    <header class="section-head"><div><span class="eyebrow">Capítulo ${ch.orden}</span><h2 id="h-${esc(ch.id)}">${esc(ch.titulo)}</h2></div>
    ${out ? `<div class="badges">${windowBadge('epilogo')}</div>` : ''}</header>
    ${a.conclusion ? `<p class="lead">${esc(a.conclusion)}</p>` : ''}${visual ? `<div class="visual">${visual}</div>` : ''}
    ${a.curioso ? `<aside class="panel curioso"><span class="kicker">Dato curioso</span><p>${esc(a.curioso)}</p></aside>` : ''}${body}</section>`;
}

export async function render(root, ctx) {
  const { api, mode } = ctx;
  const [story, analysis, kpis, kpisEpi, team] = await Promise.all([api.tryJSON(`/api/story/jardine`),
    api.tryJSON(`/api/entities/${ENTITY}/analysis`), api.tryJSON(`/api/kpis/${ENTITY}`), api.tryJSON(`/api/kpis/${EPILOGUE}`),
    api.tryJSON(`/api/teams/${ENTITY}`)]);
  if (!story || !Array.isArray(story.capitulos)) {
    root.innerHTML = `<section class="view"><header class="vhead"><h2>Historia: cómo jugó el América de Jardine</h2></header>
      <div class="empty card"><h3>Datos en construcción</h3><p>La historia todavía no se ha generado. Corre <code>python pipeline/run.py analysis</code>.</p></div></section>`;
    return;
  }
  const data = { story, analysis, kpis: ((kpis || {}).kpis || {}).oficial || [], kpisEpi: ((kpisEpi || {}).kpis || {}).epilogo || [],
    team, n: story.partidos };
  const nav = story.capitulos.map((c) => `<button type="button" class="btn sm ghost" data-cap="${esc(c.id)}">${c.orden}. ${esc(c.titulo.split(':')[0])}</button>`).join('');
  const hint = mode === 'dt' ? 'Modo DT: todo el detalle, con n, intervalos y el id de cada métrica.' : 'Modo Aficionado: lo esencial de cada capítulo. Cambia a DT para ver todo el detalle.';
  root.innerHTML = `<section class="view story"><header class="section-head vhead"><div>
    <div class="eyebrow">Ventana oficial · Apertura 2023 a Clausura 2025 · ${ctx.fmt.num(story.partidos, 0)} partidos</div>
    <h2>${esc(story.titulo)}</h2><p>Doce capítulos que responden cómo juega este equipo con y sin balón, cuándo cambia y qué tanto se debe al entrenador.</p>
    <p class="caption">${esc(hint)} ${esc(story.nota || '')}</p></div></header>
    <nav class="chapnav" id="chapnav" aria-label="Capítulos">${nav}</nav>
    ${story.capitulos.map((c) => chapterHTML(c, data, ctx)).join('')}</section>`;
  const navEl = root.querySelector('#chapnav');
  if (navEl) {
    navEl.addEventListener('click', (e) => {
      const b = e.target.closest && e.target.closest('[data-cap]');
      const target = b && root.querySelector(`#cap-${b.dataset.cap}`);
      if (target && target.scrollIntoView) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  }
}
