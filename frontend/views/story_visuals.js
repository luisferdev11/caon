/* Un visual por capítulo de la historia (id en `aficionado.visual`). Cada gráfica lleva como título el hallazgo del
   capítulo, su unidad, n y ventana; el protagonista va en dorado, el rival en azul y la liga en gris. Los números
   salen de analysis/kpis ya publicados: aquí no se recalcula nada. */
import { barsCI, dotPlot, heatGrid, shotMap } from '../js/charts.js';
import { metricTile, seeData } from '../js/cards.js';
import { esc } from '../js/fmt.js';
import { playsBlock } from './story_plays.js';

const MIN_GROUP_N = 12;   // mismo umbral que el semáforo de KPIs (framework.KPI_MIN_MATCHES)
const FOUR_KPIS = ['field_tilt', 'progresion_limpia', 'npxg_por_tiro', 'perdida_costosa'];
const STYLE_ROWS = [['posesion', 'Posesión'], ['verticalidad', 'Verticalidad'], ['ritmo', 'Ritmo de ataque'], ['linea', 'Altura de línea'],
  ['volumen_presion', 'Volumen de presión'], ['presion', 'Corta pronto el pase (PPDA bajo)'], ['contrapresion', 'Contrapresión'],
  ['saque_largo', 'Saque largo del portero'], ['centros', 'Centros al área'], ['contragolpe', 'Tiros al contragolpe']];
const ZONE_ES = { punto_penal: 'Punto penal', corto: 'Córner corto', primer_palo: 'Primer palo', fuera_area: 'Fuera del área',
  centro_area_chica: 'Centro del área chica', segundo_palo: 'Segundo palo', zona_remate: 'Zona de remate', area_chica: 'Área chica',
  resto_area: 'Resto del área' };
const GROUP_ES = { local: 'De local', visita: 'De visita', alto: 'Rival fuerte', medio: 'Rival medio', bajo: 'Rival débil',
  perdiendo: 'Va perdiendo', ganando: 'Va ganando', empatando: 'Empatando', liguilla: 'Liguilla', regular: 'Torneo regular' };
const CONTEXT_DIMS = [['localia', 'puntos', 'Localía'], ['rival', 'xg', 'Nivel del rival'], ['marcador', 'field_tilt', 'Marcador'],
  ['minuto', 'xg_90', 'Minuto'], ['fase', 'xg', 'Fase del torneo']];

const win = (d, topic) => (((d.analysis || {})[topic] || {}).ventanas || {}).oficial || {};
const finite = (v) => typeof v === 'number' && Number.isFinite(v);
/** Título de la gráfica = el hallazgo del capítulo (o un respaldo explícito). */
const titleOf = (ch, id, fallback) => ((ch.hallazgos || []).find((f) => f.id === id) || {}).titulo || fallback;
const meta = (title, unit, n, window = 'oficial') => ({ title, unit, n, window });
const grid = (...figs) => `<div class="chart-grid">${figs.filter(Boolean).join('')}</div>`;
const zone = (z) => ZONE_ES[z] || String(z || '').replace(/_/g, ' ');
const pairsTable = (headers, rows, ctx) => (ctx.mode === 'dt' ? seeData(headers, rows) : '');

function kpiCards(d, ctx) {
  const rows = FOUR_KPIS.map((id) => (d.kpis || []).find((k) => k.id === id)).filter(Boolean);
  return rows.length ? `<div class="tiles">${rows.map((k) => metricTile(k, k.nombre, ctx)).join('')}</div>` : '';
}

function identityCard(d, ctx, ch) {
  const team = d.team || {}, id = team.identity || {}, style = team.style || {};
  const chips = [id.build, id.attack, id.defense].filter(Boolean).map((t) => `<span class="chip info">${esc(t)}</span>`);
  const tags = (id.tags || []).map((t) => `<span class="tag">${esc(t)}</span>`);
  const rows = STYLE_ROWS.filter(([k]) => finite(style[k])).map(([k, label]) => ({ label, pct: style[k] }));
  return `${chips.length ? `<div class="chips">${chips.join('')}</div>` : ''}${tags.length ? `<div class="tags">${tags.join('')}</div>` : ''}
    ${rows.length ? dotPlot(meta(titleOf(ch, 'identidad_etiquetas', 'Su identidad frente a la liga'), 'percentil 0–100 frente a la liga', team.n), rows) : ''}`;
}

function shotMapView(d, ctx, ch) {
  const off = win(d, 'offense'), mt = (off.ocasiones || {}).mapa_tiros;
  const ix = mt ? Object.fromEntries(mt.cols.map((c, i) => [c, i])) : {};
  const shots = mt ? mt.rows.map((r) => ({ x: r[ix.x], y: r[ix.y], xg: r[ix.xg], goal: !!r[ix.goal] })) : [];
  const obv = (off.obv || {}).por_zona;
  return grid(shots.length ? shotMap(meta(titleOf(ch, 'con_balon_ocasiones', 'Sus tiros'), 'xG por tiro (tamaño del círculo)', mt.n), shots) : '',
    Array.isArray(obv) ? heatGrid(meta(titleOf(ch, 'con_balon_obv', 'Dónde genera valor con el balón'), 'OBV por partido', d.n), obv.map((v) => Math.max(v, 0))) : '');
}

function defenseMap(d, ctx, ch) {
  const def = win(d, 'defense'), rec = (def.recuperaciones || {}).por_zona, mt = (def.concedido || {}).mapa_tiros;
  const ix = mt ? Object.fromEntries(mt.cols.map((c, i) => [c, i])) : {};
  const shots = mt ? mt.rows.map((r) => ({ x: r[ix.x], y: r[ix.y], xg: r[ix.xg], goal: !!r[ix.goal] })) : [];
  return grid(Array.isArray(rec) ? heatGrid(meta(titleOf(ch, 'sin_balon_recuperacion', 'Dónde recupera el balón'), 'robos (total de la ventana)', d.n), rec) : '',
    shots.length ? shotMap(meta(titleOf(ch, 'sin_balon_concedido', 'Los tiros que concede'), 'xG por tiro concedido (tamaño del círculo)', mt.n), shots, 'rival') : '');
}

function lossTypes(d, ctx, ch) {
  const lost = win(d, 'transitions').perdidas || {};
  const types = (lost.por_tipo || []).filter((t) => t.pct && finite(t.pct.value));
  const rate = lost.tasa_costosa && lost.tasa_costosa.value;
  const costly = types.filter((t) => t.n >= 30 && t.tasa_costosa && finite(t.tasa_costosa.value));
  const thirds = (lost.por_tercio || []).filter((t) => t.tasa_costosa && finite(t.tasa_costosa.value));
  const zones = Array(18).fill(0);
  for (const [z, n] of (lost.por_zona || {}).rows || []) zones[z] = n;
  const total = types.length ? types[0].pct.n : d.n;
  const figs = [
    types.length ? barsCI(meta(titleOf(ch, 'transiciones_tipologia', 'Cómo pierde el balón'), '% de las pérdidas en juego', total),
      types.map((t) => ({ label: t.nombre, value: t.pct.value, ref: undefined }))) : '',
    costly.length ? barsCI(meta('Qué tipo de pérdida acaba más en tiro rival', '% que acaba en tiro rival en 15 s (marca: promedio)', total),
      costly.map((t) => ({ label: t.nombre, value: t.tasa_costosa.value, ref: rate }))) : '',
    thirds.length ? barsCI(meta(titleOf(ch, 'transiciones_tercios', 'Dónde cuesta más perder el balón'), '% que acaba en tiro rival en 15 s', total),
      thirds.map((t) => ({ label: t.nombre, value: t.tasa_costosa.value, ref: rate }))) : '',
    zones.some((v) => v > 0) ? heatGrid(meta('Dónde pierde el balón', 'pérdidas (total de la ventana)', total), zones) : ''];
  const table = pairsTable(['Tipo', 'Pérdidas', '% del total', '% costosas'],
    types.map((t) => [t.nombre, String(t.n), `${t.pct.value}`, t.tasa_costosa ? `${t.tasa_costosa.value}` : 's/d']), ctx);
  return grid(...figs) + table;
}

function setPieces(d, ctx, ch) {
  const sp = win(d, 'setpieces'), off = sp.ofensivo || {}, deliver = (off.corners || {}).entrega || [], shots = ((off.corners || {}).remates || {}).por_zona || [];
  const recs = [['A favor (de peligro)', (off.xg_bp || {})], ['En contra (de peligro)', ((sp.defensivo || {}).xg_bp || {})], ['Saldo', sp.diferencial || {}]]
    .filter(([, r]) => finite(r.value)).map(([label, r]) => ({ label, value: r.value, ci: r.ci }));
  const vuln = ((sp.defensivo || {}).zonas_vulnerables || []).map((z) => ({ label: zone(z.zona), value: z.xg }));
  return grid(recs.length ? barsCI(meta(titleOf(ch, 'bp_diferencial', 'El saldo a balón parado'), 'xG por partido (intervalo del 80 %)', d.n), recs) : '',
    deliver.length ? barsCI(meta(titleOf(ch, 'bp_ofensivo_zonas', 'Dónde caen sus córners'), '% de sus córners', (off.corners || {}).n), deliver.map((z) => ({ label: zone(z.zona), value: z.pct }))) : '',
    shots.length ? barsCI(meta('Desde dónde remata tras córner', 'remates (total de la ventana)', (off.corners || {}).remates && off.corners.remates.n),
      shots.map((z) => ({ label: zone(z.zona), value: z.n }))) : '',
    vuln.length ? barsCI(meta(titleOf(ch, 'bp_defensivo_zonas', 'Dónde le rematan a balón parado'), 'xG concedido (total de la ventana)', d.n), vuln) : '');
}

function contextMultiples(d, ctx, ch) {
  const cw = win(d, 'context'), catalog = cw.metricas || {};
  const figs = CONTEXT_DIMS.map(([dim, metric, name]) => {
    const groups = ((cw.dimensiones || {})[dim] || {}).grupos || {};
    const rows = Object.entries(groups).map(([g, body]) => [g, (body || {})[metric]])
      .filter(([, m]) => m && finite(m.valor) && m.n >= MIN_GROUP_N)
      .map(([g, m]) => ({ label: GROUP_ES[g] || `Minutos ${g}`, value: m.valor, ci: m.banda80 }));
    const unit = (catalog[metric] || {}).unidad;
    return rows.length && unit ? barsCI(meta(titleOf(ch, `contexto_${dim}`, `${name}: cómo cambia su rendimiento`), `${unit} (intervalo del 80 %)`, cw.n_partidos), rows) : '';
  });
  return grid(...figs);
}

function lineup(d, ctx, ch) {
  const u = win(d, 'usage'), xi = u.xi_base || [], forms = u.formaciones || [], states = (u.cambios || {}).por_estado || {};
  const stateRows = ['perdiendo', 'empatando', 'ganando'].filter((k) => states[k]).map((k) => ({ label: GROUP_ES[k], value: states[k].minuto_medio }));
  return grid(xi.length ? barsCI(meta(titleOf(ch, 'jugadores_nucleo', 'Quién sostiene el sistema'), '% de los minutos del equipo', u.n_partidos),
    xi.map((p) => ({ label: `${p.jugador} (${String(p.posicion || '').toLowerCase()})`, value: p.share_minutos }))) : '',
  forms.length ? barsCI(meta(titleOf(ch, 'jugadores_alineaciones', 'Con qué formación juega'), '% de los partidos', u.n_partidos), forms.map((f) => ({ label: f.formacion, value: f.pct }))) : '',
  stateRows.length ? barsCI(meta(titleOf(ch, 'jugadores_cambios_marcador', 'Cuándo cambia según el marcador'), 'minuto medio del cambio', (u.cambios || {}).n), stateRows) : '');
}

function replaySummary(d, ctx, ch) {
  const rows = ((d.analysis || {}).replay || {}).por_torneo || [];
  const own = rows.filter((r) => r.window === 'oficial' && finite(r.puntos_por_partido));
  return own.length ? barsCI(meta(titleOf(ch, 'merecio_resultado', 'Puntos contra lo que pedían sus ocasiones'),
    'puntos por partido (la marca es lo esperado por sus ocasiones)', d.n), own.map((r) => ({ label: r.torneo, value: r.puntos_por_partido, ref: r.xpts_por_partido }))) : '';
}

function kpiBoard(d, ctx, ch) {
  const rows = (d.kpis || []).filter((k) => k.value !== null && finite(k.pct_bueno));
  const lights = (d.kpis || []).filter((k) => k.frase).map((k) => `<li><strong>${esc(k.nombre)}:</strong> ${esc(k.frase)}</li>`).join('');
  const table = pairsTable(['Indicador', 'Valor', 'Percentil (mejor = alto)', 'Umbral bajo', 'Umbral alto'],
    rows.map((k) => [k.nombre, ctx.fmt.metricValue(k), String(k.pct_bueno), k.umbrales ? String(k.umbrales.p33) : 's/d', k.umbrales ? String(k.umbrales.p67) : 's/d']), ctx);
  return (rows.length ? dotPlot(meta(titleOf(ch, 'tablero_resumen', 'Los siete indicadores frente a la liga'), 'percentil 0–100 donde más a la derecha es mejor', d.n),
    rows.map((k) => ({ label: k.nombre, pct: k.pct_bueno }))) : '') + (ctx.mode === 'dt' && lights ? `<ul class="evid">${lights}</ul>` : '') + table;
}

function epilogueCompare(d, ctx, ch) {
  const epi = (d.kpisEpi || []).filter((k) => k.value !== null && finite(k.pct_bueno));
  const rows = [];
  for (const k of epi) {
    const o = (d.kpis || []).find((x) => x.id === k.id);
    if (o && finite(o.pct_bueno)) rows.push({ label: `${k.nombre} · Tricampeonato`, pct: o.pct_bueno }, { label: `${k.nombre} · 2025/26`, pct: k.pct_bueno, side: 'league' });
  }
  return rows.length ? dotPlot(meta(titleOf(ch, 'epilogo_cambios', 'El 2025/26 frente al Tricampeonato'), 'percentil 0–100 donde más a la derecha es mejor', (d.kpisEpi[0] || {}).n, 'epilogo'), rows) : '';
}

export const VISUALS = {
  kpi_cards: kpiCards, identity_card: identityCard, shot_map: shotMapView, defense_map: defenseMap, loss_types: lossTypes,
  danger_plays: (d, ctx) => playsBlock(win(d, 'dangerous'), ctx), set_pieces: setPieces, context_small_multiples: contextMultiples,
  xi_lineup: lineup, replay_summary: replaySummary, kpi_board: kpiBoard, epilogue_compare: epilogueCompare,
};

/** HTML del visual de un capítulo ('' si el dato no existe: nunca una gráfica vacía). */
export function visualFor(id, data, ctx, chapter) {
  const make = VISUALS[id];
  return make ? make(data, ctx, chapter) : '';
}
