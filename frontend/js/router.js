/* Router por hash del portal: #nombre/param1/param2. */
export const ROUTES = [
  { name: 'historia', label: 'Historia', view: 'story', tab: true },
  { name: 'almada', label: 'Almada', view: 'almada', tab: true },
  { name: 'partidos', label: 'Partidos', view: 'match', tab: true },
  { name: 'partido', label: 'Partido', view: 'match', tab: false },
  { name: 'dt', label: 'Entrenador', view: 'coach', tab: false },
  { name: 'explorador', label: 'Explorador', view: 'explorer', tab: true },
  { name: 'equipo', label: 'Equipo', view: 'explorer', tab: false },
  { name: 'laboratorio', label: 'Laboratorio', view: 'playlab', tab: true },
  { name: 'metodo', label: 'Método', view: 'method', tab: true },
];
export const DEFAULT_ROUTE = 'historia';

/** Convierte "#partido/123" en {name, params}; rutas desconocidas caen en la portada. */
export function parseHash(hash) {
  const parts = String(hash || '').replace(/^#\/?/, '').split('/').filter(Boolean).map(decodeURIComponent);
  const name = parts[0];
  if (!name || !ROUTES.some((r) => r.name === name)) return { name: DEFAULT_ROUTE, params: [] };
  return { name, params: parts.slice(1) };
}
export function routeFor(name) {
  return ROUTES.find((r) => r.name === name) || ROUTES[0];
}
export function hrefFor(name, ...params) {
  return '#' + [name, ...params.map((p) => encodeURIComponent(p))].join('/');
}
