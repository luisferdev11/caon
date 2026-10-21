/* Cancha SVG única del producto (coordenadas StatsBomb 120x80): mismo verde rayado, líneas y discos
   numerados que el lienzo del laboratorio. La usan playlab, historia, partido y las gráficas.
   El protagonista ataca de izquierda a derecha. Los colores viven en css/pitch.css (tokens). */
import { esc } from './fmt.js';

export const PITCH = { w: 120, h: 80 };
export const PITCH_CAPTION = 'El equipo protagonista ataca de izquierda a derecha.';
/** Semántica fija de color: clase CSS de muestra y texto por defecto de la leyenda. */
export const SIDES = {
  protag: { cls: 'protag', label: 'Protagonista' },
  rival: { cls: 'rival', label: 'Rival' },
  league: { cls: 'league', label: 'Liga' },
  out: { cls: 'hatch', label: 'Fuera de ventana oficial' },
};
const DISC_R = 1.7; // radio del disco en yardas (= laboratorio: 1.7 · escala)
const r1 = (v) => Math.round(v * 10) / 10;
const sideOf = (side) => (side === 'protag' || side === 'rival' ? side : 'league');

function stripes() {
  let out = '';
  for (let i = 0; i < 12; i += 2) out += `<rect class="pitch-stripe" x="${i * 10}" y="0" width="10" height="80"/>`;
  return out;
}

function goals() {
  return [-2.6, 120].map((gx) => {
    let net = '';
    for (let k = 1; k < 8; k++) net += `<line class="pitch-net" x1="${gx}" y1="${36 + k}" x2="${r1(gx + 2.6)}" y2="${36 + k}"/>`;
    return `<rect class="pitch-goal" x="${gx}" y="36" width="2.6" height="8"/>${net}`;
  }).join('');
}

const LINES = '<rect x="0" y="0" width="120" height="80"/><line x1="60" y1="0" x2="60" y2="80"/>' +
  '<circle cx="60" cy="40" r="10"/><rect x="0" y="18" width="18" height="44"/><rect x="102" y="18" width="18" height="44"/>' +
  '<rect x="0" y="30" width="6" height="20"/><rect x="114" y="30" width="6" height="20"/>' +
  '<path d="M 18 32 A 10 10 0 0 1 18 48"/><path d="M 102 32 A 10 10 0 0 0 102 48"/>' +
  '<path d="M 0 1.2 A 1.2 1.2 0 0 0 1.2 0"/><path d="M 118.8 0 A 1.2 1.2 0 0 0 120 1.2"/>' +
  '<path d="M 120 78.8 A 1.2 1.2 0 0 0 118.8 80"/><path d="M 1.2 80 A 1.2 1.2 0 0 0 0 78.8"/>';
const SPOTS = [[60, 40], [12, 40], [108, 40]].map(([x, y]) => `<circle class="pitch-spot" cx="${x}" cy="${y}" r="0.4"/>`).join('');

/** SVG base de la cancha; `inner` se dibuja encima en coordenadas 120x80. */
export function pitchSVG(inner = '', { label = 'Cancha', cls = 'pitch' } = {}) {
  return `<svg class="${esc(cls)}" viewBox="-3 -2 126 84" role="img" aria-label="${esc(label)}">` +
    '<rect class="pitch-bg" x="-3" y="-2" width="126" height="84"/>' +
    `<rect class="pitch-grass" x="0" y="0" width="120" height="80"/>${stripes()}` +
    `<g class="pitch-lines">${LINES}</g>${SPOTS}${goals()}${inner}</svg>`;
}

/** Disco de jugador: lado protag|rival|league, número opcional, portero y resaltado. */
export function playerDisc({ x, y, num = null, side = 'league', gk = false, hi = false, r = DISC_R }) {
  const cls = ['pd', 'pd-' + sideOf(side), gk ? 'pd-gk' : '', hi ? 'pd-hi' : ''].filter(Boolean).join(' ');
  const text = num == null || num === '' ? '' : `<text x="${r1(x)}" y="${r1(y)}">${esc(num)}</text>`;
  return `<g class="${cls}"><circle cx="${r1(x)}" cy="${r1(y)}" r="${r}"/>${text}</g>`;
}

/** Balón con sombra; `h` = altura (yardas) para los balones bombeados. */
export function ballSVG(x, y, h = 0) {
  return `<ellipse class="pitch-ball-shadow" cx="${r1(x)}" cy="${r1(y + 0.6)}" rx="1" ry="0.5"/>` +
    `<circle class="pitch-ball" cx="${r1(x)}" cy="${r1(y - h)}" r="${r1(0.9 + h * 0.08)}"/>`;
}

/** Leyenda con la semántica fija: items = [{side, label}]. */
export function legendHTML(items) {
  const spans = (items || []).map((it) => {
    const s = SIDES[it.side] || SIDES.league;
    return `<span><i class="sw ${s.cls}" aria-hidden="true"></i>${esc(it.label || s.label)}</span>`;
  });
  return `<div class="legend">${spans.join('')}</div>`;
}

export function caption(text = '') {
  return `<p class="caption">${text ? esc(text) + ' ' : ''}${PITCH_CAPTION}</p>`;
}
