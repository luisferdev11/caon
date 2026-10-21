/* Datos del explorador: normalización pura de equipos, entrenadores, temporadas y tenencias.
   Acepta explorer.v2 (label, identity, metrics[], unidades[]/tenencias[]) y explorer.v1 (resúmenes + metricas{}).
   La vista (views/explorer.js) solo pinta lo que sale de aquí. */
import { confidenceOfN, percentile, percentileLow } from './fmt.js';

/** Igual que pipeline/explorer.py SMALL_SAMPLE_N: «muestra chica» por debajo de confianza media. */
export const SMALL_SAMPLE_N = 12;

/** Métricas de estilo del explorador (= build_model.STY). ref_pct ya viene orientado: alto = más del rasgo.
    `framework` enlaza con el id del registro DEFINITIONS cuando el concepto es el mismo. */
export const METRICS = {
  posesion: { nombre: 'Posesión', alto: 'Tiene mucho el balón', bajo: 'Cede el balón' },
  verticalidad: { nombre: 'Verticalidad', alto: 'Juega directo hacia adelante', bajo: 'Elabora en corto' },
  ritmo: { nombre: 'Velocidad hacia portería', alto: 'Ataca rápido', bajo: 'Ataca con pausa' },
  linea: { nombre: 'Altura de la línea defensiva', alto: 'Defiende con la línea alta', bajo: 'Defiende con la línea baja' },
  volumen_presion: { nombre: 'Volumen de presión', alto: 'Presiona mucho', bajo: 'Presiona poco' },
  presion: { nombre: 'Intensidad de presión (PPDA)', alto: 'Presiona con intensidad', bajo: 'Deja jugar al rival', framework: 'ppda' },
  contrapresion: { nombre: 'Contrapresión', alto: 'Presiona justo después de perder', bajo: 'Repliega al perder', framework: 'contrapresion' },
  saque_largo: { nombre: 'Saque largo del portero', alto: 'Su portero saca largo', bajo: 'Su portero sale en corto' },
  centros: { nombre: 'Centros al área', alto: 'Centra mucho al área', bajo: 'Centra poco' },
  contragolpe: { nombre: 'Tiros al contragolpe', alto: 'Remata mucho al contragolpe', bajo: 'Remata poco al contragolpe', framework: 'contraataque' },
  presion_alta_tiros: { nombre: 'Tiros tras robo alto', alto: 'Remata tras robar arriba', bajo: 'Remata poco tras robar arriba', framework: 'rec_alta' },
  xg: { nombre: 'Peligro generado (xG a favor)', alto: 'Genera mucho peligro', bajo: 'Genera poco peligro' },
  xga: { nombre: 'Solidez (xG en contra)', alto: 'Concede poco peligro', bajo: 'Concede mucho peligro' },
  bp_xg: { nombre: 'Peligro a balón parado', alto: 'Peligroso a balón parado', bajo: 'Poco peligro a balón parado', framework: 'bp_peligro' },
};
const LIST_KEYS = ['items', 'teams', 'coaches', 'equipos', 'entrenadores'];
const SEASON_KEYS = ['tenencias', 'unidades', 'temporadas', 'linea_tiempo', 'carrera', 'seasons'];
const FRAMEWORK_PREFIX = /^estilo_/;
const finite = (x) => typeof x === 'number' && Number.isFinite(x);

/** 'André Jardine' → 'andre-jardine' (igual que app/main.py slug). */
export function slug(text) {
  return String(text || '').normalize('NFKD').replace(/[̀-ͯ]/g, '').toLowerCase()
    .replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
}
const unique = (xs) => [...new Set((xs || []).filter(Boolean))];

function listOf(payload) {
  if (Array.isArray(payload)) return payload;
  if (!payload || typeof payload !== 'object') return [];
  for (const k of LIST_KEYS) if (Array.isArray(payload[k])) return payload[k];
  return [];
}

/** Unidad de lista o ficha: {key, name, n, seasons, related, confidence, small, identity, window, prior, metricas}. */
export function normalizeUnit(u) {
  const name = u.label || u.name || u.team || u.coach || u.key || '';
  const n = finite(u.n) ? u.n : null;
  const flag = u.muestra_chica !== undefined ? u.muestra_chica : u.small_sample;
  const units = Array.isArray(u.unidades) ? u.unidades.length : (Array.isArray(u.tenencias) ? u.tenencias.length : null);
  return {
    key: u.key || slug(name), name, n, nTotal: finite(u.n_total) ? u.n_total : n,
    seasons: finite(u.unidades) ? u.unidades : (units !== null ? units : (Array.isArray(u.temporadas) ? u.temporadas.length : null)),
    related: unique(u.entrenadores || u.clubes || u.related),
    confidence: u.confianza || u.confidence || confidenceOfN(n),
    small: flag !== undefined ? Boolean(flag) : (n !== null && n < SMALL_SAMPLE_N),
    identity: u.identity || null, window: u.ventana || u.window || null, prior: u.prior || null,
    from: u.desde || null, to: u.hasta || null, metricas: u.metricas || u.metrics || {},
  };
}

/** Lista de unidades normalizadas, ordenadas por partidos (desc) y nombre. */
export function unitsOf(payload) {
  return listOf(payload).filter((u) => u && typeof u === 'object').map(normalizeUnit)
    .sort((a, b) => (b.n || 0) - (a.n || 0) || a.name.localeCompare(b.name, 'es'));
}

/** Temporadas o tenencias de una ficha de detalle, en orden cronológico. */
export function seasonsOf(detail) {
  if (!detail || typeof detail !== 'object') return [];
  const key = SEASON_KEYS.find((k) => Array.isArray(detail[k]));
  if (!key) return [];
  return detail[key].filter((s) => s && typeof s === 'object').map((s) => ({
    label: s.temporada || s.season || s.label || '', team: s.team || '', coach: s.coach || '',
    n: finite(s.n) ? s.n : null, confidence: s.confianza || s.confidence || confidenceOfN(s.n),
    small: Boolean(s.muestra_chica || s.small_sample), window: s.ventana || s.window || null, identity: s.identity || null,
    prior: s.prior || null, from: s.desde || null, to: s.hasta || null, metricas: s.metricas || s.metrics || {},
  })).sort((a, b) => String(a.from || '').localeCompare(String(b.from || '')));
}

const humanize = (id) => String(id).replace(/_/g, ' ').replace(/^./, (c) => c.toUpperCase());

/** Métricas como mapa {clave: registro}: v2 trae una lista con `clave` (o id «estilo_<clave>»), v1 un mapa. */
function metricMap(metricas) {
  if (!Array.isArray(metricas)) return metricas || {};
  const out = {};
  for (const r of metricas) if (r && typeof r === 'object') out[r.clave || String(r.id || '').replace(FRAMEWORK_PREFIX, '')] = r;
  return out;
}

/** Filas métricas en el orden de METRICS: {id, fid, label, value, raw, prior, ci, unit, pct, n, window, motivo, rec}. */
export function metricRows(season) {
  const m = metricMap(season && season.metricas);
  const ids = [...Object.keys(METRICS).filter((id) => m[id]), ...Object.keys(m).filter((id) => !METRICS[id])];
  return ids.filter((id) => m[id] && typeof m[id] === 'object').map((id) => {
    const r = m[id];
    return { id, fid: r.id || id, label: (METRICS[id] && METRICS[id].nombre) || r.nombre || humanize(id),
      value: finite(r.value) ? r.value : null, raw: r.bruto !== undefined ? r.bruto : r.raw, prior: r.prior_value,
      ci: r.ci || null, unit: r.unit || '', pct: finite(r.ref_pct) ? r.ref_pct : null, n: r.n,
      window: r.window || season.window, motivo: r.motivo || '', rec: r };
  });
}

/** Rasgos de identidad en palabras (construcción, defensa, ataque) para chips. */
export function identityChips(identity) {
  if (!identity || typeof identity !== 'object') return [];
  return unique([identity.build, identity.defense, identity.attack]);
}

/** Los k rasgos más marcados (percentil más lejos de 50) en palabras. */
export function traits(season, k = 2) {
  return metricRows(season).filter((r) => r.pct !== null && METRICS[r.id])
    .sort((a, b) => Math.abs(b.pct - 50) - Math.abs(a.pct - 50)).slice(0, k)
    .map((r) => {
      const high = r.pct >= 50, def = METRICS[r.id];
      const text = high ? `${def.alto}: ${percentile(r.pct)} equipos` : `${def.bajo}: ${percentileLow(r.pct)} equipos`;
      return { id: r.id, pct: r.pct, high, text };
    });
}

const fold = (s) => slug(s).replace(/-/g, ' ');
/** Filtro sin acentos ni mayúsculas por nombre o por relacionados (DTs del equipo, clubes del DT). */
export function filterUnits(units, query) {
  const q = fold(query);
  if (!q) return units;
  return units.filter((u) => [u.name, ...(u.related || [])].some((s) => fold(s).includes(q)));
}
