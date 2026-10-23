/* Acceso a la API con caché en memoria. Las vistas solo pintan; los datos vienen de aquí. */
const cache = new Map();

export class ApiError extends Error {
  constructor(status, path) { super(`HTTP ${status} en ${path}`); this.status = status; this.path = path; }
}
/** GET JSON con caché por ruta; lanza ApiError con status (404 = datos en construcción). */
export function getJSON(path) {
  if (!cache.has(path)) {
    const p = fetch(path, { headers: { Accept: 'application/json' } }).then((r) => {
      if (!r.ok) throw new ApiError(r.status, path);
      return r.json();
    });
    p.catch(() => cache.delete(path));
    cache.set(path, p);
  }
  return cache.get(path);
}
/** Igual que getJSON pero devuelve null si el recurso no existe todavía. */
export async function tryJSON(path) {
  try { return await getJSON(path); } catch (e) { if (e instanceof ApiError) return null; throw e; }
}
