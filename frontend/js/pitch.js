/* Cancha SVG reutilizable (coordenadas StatsBomb 120x80). El protagonista ataca de izquierda a derecha. */
export const PITCH = { w: 120, h: 80 };
export const PITCH_CAPTION = 'El equipo protagonista ataca de izquierda a derecha.';

/** Devuelve el SVG base de la cancha; `inner` se dibuja encima en coordenadas 120x80. */
export function pitchSVG(inner = '', { label = 'Cancha', cls = 'pitch' } = {}) {
  const l = 'fill="none" stroke="var(--chalk)" stroke-width="0.5"';
  return `<svg class="${cls}" viewBox="-2 -2 124 84" role="img" aria-label="${label}">
  <rect x="0" y="0" width="120" height="80" fill="var(--grass)"/>
  <rect x="0" y="0" width="120" height="80" ${l}/><line x1="60" y1="0" x2="60" y2="80" ${l}/>
  <circle cx="60" cy="40" r="10" ${l}/><rect x="0" y="18" width="18" height="44" ${l}/>
  <rect x="102" y="18" width="18" height="44" ${l}/><rect x="0" y="30" width="6" height="20" ${l}/>
  <rect x="114" y="30" width="6" height="20" ${l}/>
  <path d="M 112 40 l -4 -2 v 4 z" fill="var(--chalk)"/>
  ${inner}</svg>`;
}
export function caption(text = '') {
  return `<p class="caption">${text ? text + ' ' : ''}${PITCH_CAPTION}</p>`;
}
