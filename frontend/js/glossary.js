/* Glosario del framework (/api/framework): definiciones y bloque «¿Cómo se mide?». */
import { esc } from './fmt.js';

export const FRAMEWORK_PATH = '/api/framework';

/** Normaliza la respuesta ({definitions: {id: def}} o lista) a una lista [{id, ...def}]. */
export function definitionsOf(payload) {
  if (!payload || typeof payload !== 'object') return [];
  const defs = payload.definitions || payload.DEFINITIONS || payload;
  if (Array.isArray(defs)) return defs.filter((d) => d && d.id);
  return Object.entries(defs).filter(([, v]) => v && typeof v === 'object').map(([id, v]) => ({ id, ...v }));
}

/** Índice {id: def} a partir de la lista de definiciones. */
export function indexDefinitions(defs) {
  const out = {};
  for (const d of defs || []) out[d.id] = d;
  return out;
}

/** Carga el glosario una vez (la caché vive en api.js); si falla devuelve {} para no romper la vista. */
export async function loadGlossary(api) {
  try { return indexDefinitions(definitionsOf(await api.tryJSON(FRAMEWORK_PATH))); } catch (e) { return {}; }
}

/** Bloque desplegable «¿Cómo se mide?» con enlace a Método; vacío si el id no está en el registro. */
export function howMeasured(byId, id) {
  const d = byId && byId[id];
  if (!d) return '';
  const limits = d.limites ? `<p class="muted">Límites: ${esc(d.limites)}</p>` : '';
  return `<details class="how"><summary>¿Cómo se mide?</summary><p>${esc(d.definicion || d.nombre || id)}</p>${limits}
    <a href="#metodo/${encodeURIComponent(id)}">Ver en Método →</a></details>`;
}
