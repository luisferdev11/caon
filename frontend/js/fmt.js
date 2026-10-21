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
const CONFIDENCE = { alta: 'alta', media: 'media', baja: 'baja', 'muy baja': 'muy baja', high: 'alta', medium: 'media', low: 'baja', very_low: 'muy baja' };
export function confidence(level) {
  return CONFIDENCE[level] ? 'Confianza ' + CONFIDENCE[level] : 'Confianza sin calcular';
}
const PRIORS = { liga: 'promedio de la liga', carrera: 'su carrera anterior', league: 'promedio de la liga', career: 'su carrera anterior' };
/** Referencia hacia la que se encoge una muestra chica. */
export function prior(kind) { return PRIORS[kind] ? 'Referencia previa: ' + PRIORS[kind] : ''; }
const SOURCES = { 'team-stats': 'Estadísticas por partido', eventos: 'Eventos', 360: 'Capturas 360' };
export function source(kind) { return SOURCES[kind] || ''; }

/** Percentil bajo en palabras: 15 → «por debajo de 85 de cada 100». */
export function percentileLow(p) {
  return finite(p) ? `por debajo de ${Math.round(100 - p)} de cada 100` : NA;
}
const SHARE_UNITS = new Set(['proporción', 'proporcion', 'share', '0-1']);
/** Proporción 0–1: unidades «proporción» y las que empiezan con «%» («% del balón», «% de saques largos»). */
const isShare = (unit) => SHARE_UNITS.has(unit) || /^%/.test(String(unit || ''));
/** Símbolo corto de la unidad para encabezados (las proporciones se muestran como %). */
export function unitLabel(unit) { return isShare(unit) ? '%' : String(unit || ''); }
/** Texto de la unidad junto al valor ya formateado: sin el «%» que ya lleva el valor. */
export function unitText(unit) {
  if (SHARE_UNITS.has(unit)) return '';
  return String(unit || '').replace(/^%\s*/, '');
}
/** Valor de un registro métrico {value, unit} según su unidad (proporción → %). */
export function metricValue(rec, field = 'value') {
  if (!rec || typeof rec !== 'object') return NA;
  const v = rec[field];
  return isShare(rec.unit) ? pct(v) : num(v);
}
/** Intervalo formateado según la unidad del registro. */
export function ciByUnit(ci, unit) {
  if (!Array.isArray(ci) || !finite(ci[0]) || !finite(ci[1])) return NA;
  return isShare(unit) ? `${pct(ci[0])} – ${pct(ci[1])}` : interval(ci);
}
/** Banda de confianza por partidos (= framework.confidence: <5 muy baja, 5–11 baja, 12–24 media, ≥25 alta). */
export function confidenceOfN(n) {
  if (!finite(n)) return null;
  if (n < 5) return 'muy baja';
  if (n < 12) return 'baja';
  return n < 25 ? 'media' : 'alta';
}
export function windowBadge(win) {
  return { oficial: 'Ventana oficial', epilogo: 'Fuera de ventana oficial', temprano: 'Fuera de ventana oficial' }[win] || '';
}
