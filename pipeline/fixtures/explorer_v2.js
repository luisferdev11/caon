/* Fixture sintética del contrato explorer.v2 (pipeline/explorer.py build_payload): un DT con dos tenencias. */
const rec = (clave, nombre, unit, value, raw, ci, refPct, over = {}) => ({ id: 'estilo_' + clave, clave, nombre, unit, n: 145,
  source: 'team-stats', window: 'oficial', value, raw, prior_value: value, ci, ref_pct: refPct, ...over });
const METRICS = [
  rec('xg', 'xG a favor', 'xG por partido', 1.4148, 1.4278, [1.3547, 1.4748], 92),
  rec('xga', 'Solidez (xG en contra)', 'xG por partido', 0.8584, 0.846, [0.7984, 0.9185], 88),
  rec('posesion', 'Posesión', '% del balón', 0.538, 0.5397, [0.5282, 0.5477], 76),
  rec('presion', 'Pases rivales por acción defensiva (PPDA)', 'pases por acción defensiva', 11.6906, 11.7187, [11.1794, 12.2019], 41),
  { id: 'estilo_bp_xg', clave: 'bp_xg', nombre: 'xG a balón parado', unit: 'xG por partido', n: 0, source: 'team-stats', window: 'oficial', value: null, motivo: 'sin dato en team-stats para estos partidos' },
];
const IDENTITY = { build: 'Equilibrado', defense: 'Bloque bajo', attack: 'Por dentro', offense_style: 'Dominio vertical', tags: ['Muy vertical'], map: { off: [62, 61, 'Dominio vertical'], dfn: [45, 35, 'Bloque bajo'] } };
const tenure = (team, n, window, prior, desde) => ({ n, confidence: 'alta', confianza: 'alta', small_sample: n < 12, muestra_chica: n < 12,
  window, prior, desde, hasta: desde.replace(/^(\d{4})/, (y) => String(+y + 1)), identity: IDENTITY, metrics: METRICS.map((m) => ({ ...m, n, window })),
  team, label: `${team} · André Jardine` });
const COACH = { n: 145, confidence: 'alta', confianza: 'alta', small_sample: false, muestra_chica: false, window: 'oficial', prior: 'liga',
  desde: '2022-02-06', hasta: '2025-05-26', identity: IDENTITY, metrics: METRICS, key: 'andre-jardine', label: 'André Jardine',
  coach: 'André Jardine', n_total: 183, clubes: ['Atlético San Luis', 'América'],
  tenencias: [tenure('Atlético San Luis', 54, 'oficial', 'liga', '2022-02-06'), tenure('América', 38, 'epilogo', 'carrera', '2025-07-12')] };
const SMALL = { n: 3, confianza: 'muy baja', muestra_chica: true, window: 'temprano', prior: 'liga', identity: null, metrics: [],
  key: 'alejandro-corona', label: 'Alejandro Corona', coach: 'Alejandro Corona', clubes: ['León'] };
const TEAM = { n: 175, confianza: 'alta', muestra_chica: false, window: 'oficial', prior: 'liga', identity: IDENTITY, metrics: METRICS,
  key: 'america', label: 'América', team: 'América', n_total: 223, entrenadores: ['André Jardine', 'Fernando Ortiz'],
  unidades: [{ ...tenure('América', 34, 'oficial', 'carrera', '2023-07-01'), coach: 'André Jardine', temporada: '2023/2024', label: 'América · André Jardine · 2023/2024' }] };
module.exports = { COACH, SMALL, TEAM, METRICS, IDENTITY };
