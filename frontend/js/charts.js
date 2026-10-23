/* Gráficas SVG pequeñas. Toda gráfica exige título-hallazgo, unidad y la insignia n/ventana.
   Semántica fija de color por `side`: protag (dorado, por defecto), rival (azul), league (gris). */
import { esc, num, windowBadge } from './fmt.js';
import { pitchSVG, caption } from './pitch.js';

const sideCls = (side) => (side === 'rival' || side === 'league' ? ' ' + side : '');

/** Marco común: título (hallazgo), insignias de unidad/n/ventana, cuerpo y nota. */
export function figure({ title, unit, n, window: win, note = '' }, body) {
  if (!title || !unit) throw new Error('Cada gráfica necesita título-hallazgo y unidad');
  const badges = [`<span class="badge">${esc(unit)}</span>`];
  if (Number.isFinite(n)) badges.push(`<span class="badge">n = ${num(n, 0)}</span>`);
  const wb = windowBadge(win);
  if (wb) badges.push(`<span class="badge${win === 'oficial' ? '' : ' out'}">${wb}</span>`);
  return `<figure class="chart"><figcaption><h3>${esc(title)}</h3><div class="badges">${badges.join('')}</div></figcaption>
    ${body}${note ? `<p class="caption">${esc(note)}</p>` : ''}</figure>`;
}

/** Barras horizontales con intervalo opcional: rows = [{label, value, ci?, ref?, side?}]. */
export function barsCI(meta, rows) {
  const max = Math.max(1e-9, ...rows.flatMap((r) => [r.value, r.ci ? r.ci[1] : 0, r.ref || 0].filter(Number.isFinite)));
  const x = (v) => (v / max) * 100;
  const body = rows.map((r) => {
    const ci = r.ci ? `<line x1="${x(r.ci[0])}" x2="${x(r.ci[1])}" y1="6" y2="6" class="ch-ci"/>` : '';
    const ref = Number.isFinite(r.ref) ? `<line x1="${x(r.ref)}" x2="${x(r.ref)}" y1="0" y2="12" class="ch-ref"/>` : '';
    return `<div class="ch-row" title="${esc(r.label)}: ${num(r.value)}"><span>${esc(r.label)}</span>
      <svg viewBox="0 0 100 12" preserveAspectRatio="none" class="ch-svg" aria-hidden="true"><rect x="0" y="2" height="8" rx="2" width="${Number.isFinite(r.value) ? x(r.value) : 0}" class="ch-bar${sideCls(r.side)}"/>${ci}${ref}</svg>
      <span class="ch-val">${num(r.value)}</span></div>`;
  }).join('');
  return figure(meta, `<div class="ch-bars">${body}</div>`);
}

/** Puntos contra la liga: rows = [{label, pct, side?}] en percentiles 0–100 (50 = mediana de la liga). */
export function dotPlot(meta, rows) {
  const body = rows.map((r) => `<div class="ch-row" title="${esc(r.label)}: percentil ${num(r.pct, 0)}"><span>${esc(r.label)}</span>
    <svg viewBox="0 0 100 12" preserveAspectRatio="none" class="ch-svg" aria-hidden="true"><line x1="0" x2="100" y1="6" y2="6" class="ch-track"/>
    <line x1="50" x2="50" y1="1" y2="11" class="ch-ref"/>${Number.isFinite(r.pct) ? `<line x1="${r.pct}" x2="${r.pct}" y1="6" y2="6" class="ch-dot${sideCls(r.side)}"/>` : ''}</svg>
    <span class="ch-val">${Number.isFinite(r.pct) ? num(r.pct, 0) : 's/d'}</span></div>`).join('');
  return figure(meta, `<div class="ch-bars">${body}<p class="caption">Línea gris: mediana de la liga.</p></div>`);
}

/** Línea de tiempo: points = [{x, y}] (x = minuto o índice de partido). */
export function timeline(meta, points, side = 'protag') {
  const pts = points.filter((p) => Number.isFinite(p.x) && Number.isFinite(p.y));
  if (!pts.length) return figure(meta, '<p class="empty">Sin datos para esta gráfica.</p>');
  const xs = pts.map((p) => p.x), ys = pts.map((p) => p.y);
  const x0 = Math.min(...xs), x1 = Math.max(...xs) || 1, y1 = Math.max(...ys, 1e-9);
  const sx = (v) => ((v - x0) / (x1 - x0 || 1)) * 96 + 2, sy = (v) => 38 - (v / y1) * 34;
  const d = pts.map((p, i) => `${i ? 'L' : 'M'}${sx(p.x).toFixed(1)},${sy(p.y).toFixed(1)}`).join(' ');
  return figure(meta, `<svg viewBox="0 0 100 40" class="ch-tsvg" role="img" aria-label="${esc(meta.title)}"><path d="${d}" class="ch-line${sideCls(side)}"/></svg>`);
}

/** Rejilla 6x3 (zonas): vals[zx*3+zy]; protagonista ataca a la derecha. */
export function heatGrid(meta, vals, side = 'protag') {
  const total = vals.reduce((a, b) => a + (b || 0), 0) || 1, mx = Math.max(...vals, 1e-9);
  let cells = '';
  for (let zy = 0; zy < 3; zy++) for (let zx = 0; zx < 6; zx++) {
    const v = vals[zx * 3 + zy] || 0;
    cells += `<rect x="${zx * 20}" y="${(zy * 80 / 3).toFixed(2)}" width="20" height="26.67" class="ch-cell${sideCls(side)}" style="fill-opacity:${((v / mx) * 0.85).toFixed(2)}"><title>${num((v / total) * 100, 0)}%</title></rect>`;
  }
  return figure(meta, pitchSVG(cells, { label: meta.title }) + caption());
}

/** Mapa de tiros: shots = [{x, y, xg, goal}] en coordenadas StatsBomb del protagonista. */
export function shotMap(meta, shots, side = 'protag') {
  const marks = shots.filter((s) => Number.isFinite(s.x) && Number.isFinite(s.y)).map((s) =>
    `<circle cx="${s.x}" cy="${s.y}" r="${(1 + Math.sqrt(s.xg || 0) * 4).toFixed(2)}" class="ch-shot${sideCls(side)}${s.goal ? ' goal' : ''}"><title>xG ${num(s.xg)}${s.goal ? ' · gol' : ''}</title></circle>`).join('');
  return figure(meta, pitchSVG(marks, { label: meta.title }) + caption('Tamaño del círculo = xG; relleno = gol.'));
}
