/* Formato es-MX: única vía para mostrar números y textos del modelo en el portal. */
export const NA = 's/d';
const MONTHS = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
const finite = (x) => typeof x === 'number' && Number.isFinite(x);

export function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}
export function num(x, digits = 2) {
  if (!finite(x)) return NA;
  const d = Math.min(Math.max(digits, 0), 2);
  return x.toLocaleString('es-MX', { maximumFractionDigits: d, minimumFractionDigits: 0 });
}
export function pct(x, digits = 0) {
  return finite(x) ? num(x * 100, digits) + '%' : NA;
}
export function minutes(x) { return finite(x) ? num(x, 0) + ' min' : NA; }
export function minute(x) { return finite(x) ? Math.floor(x) + "'" : NA; }
export function date(iso) {
  if (!iso || typeof iso !== 'string' || iso.length < 10) return NA;
  return `${+iso.slice(8, 10)} ${MONTHS[+iso.slice(5, 7) - 1]} ${iso.slice(0, 4)}`;
}
export function percentile(p) {
  return finite(p) ? `más que ${Math.round(p)} de cada 100` : NA;
}
export function interval(ci) {
  return Array.isArray(ci) && finite(ci[0]) && finite(ci[1]) ? `${num(ci[0])} – ${num(ci[1])}` : NA;
}

const POSITIONS = {
  Goalkeeper: 'Portero', 'Right Back': 'Lateral derecho', 'Left Back': 'Lateral izquierdo',
  'Right Center Back': 'Central derecho', 'Left Center Back': 'Central izquierdo', 'Center Back': 'Central',
  'Right Wing Back': 'Carrilero derecho', 'Left Wing Back': 'Carrilero izquierdo',
  'Right Defensive Midfield': 'Contención derecha', 'Left Defensive Midfield': 'Contención izquierda',
  'Center Defensive Midfield': 'Contención', 'Right Center Midfield': 'Interior derecho',
  'Left Center Midfield': 'Interior izquierdo', 'Center Midfield': 'Mediocampista central',
  'Right Midfield': 'Volante derecho', 'Left Midfield': 'Volante izquierdo',
  'Right Attacking Midfield': 'Mediapunta derecho', 'Left Attacking Midfield': 'Mediapunta izquierdo',
  'Center Attacking Midfield': 'Mediapunta', 'Right Wing': 'Extremo derecho', 'Left Wing': 'Extremo izquierdo',
  'Right Center Forward': 'Delantero derecho', 'Left Center Forward': 'Delantero izquierdo',
  'Center Forward': 'Centro delantero', 'Secondary Striker': 'Segundo delantero',
};
const SCORE_STATES = { winning: 'ganando', drawing: 'empatando', losing: 'perdiendo' };
const VENUES = { home: 'local', away: 'visitante', neutral: 'neutral' };
const WARNINGS = {
  small_sample: 'Muestra pequeña: el valor puede cambiar mucho con pocos partidos más.',
  out_of_window: 'Fuera de la ventana oficial: no se usa para conclusiones.',
  clock_incomplete: 'El reloj de algunos partidos está incompleto.',
  no_360: 'Sin capturas 360 para estos partidos.',
  partial_360: 'Capturas 360 parciales: cobertura incompleta.',
  estimated: 'Valor estimado desde eventos, no medido directamente.',
  missing_data: 'Faltan datos para calcular este valor.',
};
const dict = (table) => (key) => (!key || key === 'unknown' ? '' : table[key] || '');

export const position = (key) => (!key || key === 'unknown' ? '' : POSITIONS[key] || key);
export const scoreState = dict(SCORE_STATES);
export const venue = dict(VENUES);
export function warning(code) {
  if (!code || code === 'unknown') return '';
  return WARNINGS[code] || 'Aviso: revisa la nota de método para este dato.';
}
export function confidence(level) {
  const map = { alta: 'Confianza alta', media: 'Confianza media', baja: 'Confianza baja', high: 'Confianza alta', medium: 'Confianza media', low: 'Confianza baja' };
  return map[level] || 'Confianza sin calcular';
}
export function windowBadge(win) {
  return { oficial: 'Ventana oficial', epilogo: 'Fuera de ventana oficial', temprano: 'Fuera de ventana oficial' }[win] || '';
}
