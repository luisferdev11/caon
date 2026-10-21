/* Laboratorio de jugadas por texto (A9). Interpreta una jugada escrita en español (POST /api/play/parse),
   la anima sobre una cancha SVG con los 22 jugadores de las formas (shape con/sin) de los equipos y
   da una interpretación: xG de la zona del remate y qué tan típica es la ruta para el equipo.
   Es una interpretación sobre el modelo, no una predicción. engine.js no se toca: las fórmulas de
   colocación se copian (ver shapeTargets más abajo). */
import { pitchSVG, caption, playerDisc, ballSVG, legendHTML } from '../js/pitch.js';

const ZONES = { // = app/play_schema.py ZONES (marco del atacante, ataca hacia x=120)
  campo_propio: [24, 40], medio: [60, 40], zona_alta: [86, 40], banda_izq: [78, 7], banda_der: [78, 73],
  borde_area: [98, 40], area: [106, 40], punto_penal: [108, 40], area_chica: [115, 40],
  primer_palo: [114, 34], segundo_palo: [114, 47],
};
const ZONE_ES = {
  campo_propio: 'campo propio', medio: 'medio campo', zona_alta: 'zona alta', banda_izq: 'banda izquierda',
  banda_der: 'banda derecha', borde_area: 'borde del área', area: 'área', punto_penal: 'punto penal',
  area_chica: 'área chica', primer_palo: 'primer palo', segundo_palo: 'segundo palo',
};
const TYPE_ES = {
  pass: 'Pase', carry: 'Conducción', dribble: 'Regate', cross: 'Centro', shot: 'Remate', header: 'Cabezazo',
  recovery: 'Recuperación', loss: 'Pérdida', clearance: 'Despeje rival',
};
const RESTART_ES = {
  open: 'Juego abierto', goal_kick: 'Saque de meta', corner: 'Tiro de esquina', free_kick: 'Tiro libre',
  throw_in: 'Saque de banda', kickoff: 'Saque inicial', recovery: 'Tras recuperación',
};
const OUTCOME_ES = { gol: '¡Gol!', atajada: 'Atajada', fuera: 'Fuera', poste: 'Al poste', bloqueado: 'Bloqueado' };
const WARN_ES = {
  llm_sin_key: 'No hay modelo de lenguaje configurado: se usó el intérprete de reglas.',
  llm_fallo: 'El modelo de lenguaje no respondió bien: se usó el intérprete de reglas.',
  texto_recortado_500: 'El texto se recortó a 500 caracteres.',
};
const EXAMPLES = [
  'el 10 centra al segundo palo y el 9 cabecea: gol',
  'Salida desde el portero: el 4 pasa al 6, cambio de orientación a la banda derecha y centro al área; remate de cabeza: atajada',
  'Recuperación alta del 6 y contra: pase filtrado al 9 que define: gol',
  'Tiro libre directo del 10: poste',
  'Córner al primer palo y remate de cabeza del 4: fuera',
];
const EXAMPLE_NAMES = ['Centro y cabezazo', 'Salida desde el portero', 'Robo alto y contra', 'Tiro libre', 'Córner al primer palo'];
const DUR = { pass: 0.9, carry: 1.3, dribble: 1.0, cross: 1.3, shot: 0.6, header: 0.6, recovery: 0.6, loss: 0.6, clearance: 0.8 };
const BLOCK_K = 0.45; // sty.blockK de engine.js depende del estilo; aquí un valor medio fijo
const ALPHA = 0.5; // suavizado de Laplace para las transiciones entre zonas
const NY = 3;
const SIMILAR_HI = 1.25; // cociente dentro de [1/1.25, 1.25] = "tan frecuente como la liga"

const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const lerp = (a, b, t) => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t];
const zoneOf = (p) => Math.floor(clamp(p[0], 0, 119.99) / 20) * NY + Math.floor(clamp(p[1], 0, 79.99) / (80 / 3));

/* Copia de las fórmulas de shapeTargets (frontend/engine.js, función shapeTargets ~línea 513),
   sin línea de fuera de juego ni presión. ti=0 posee y ataca a la derecha; ti=1 defiende (marco espejo). */
export function shapeTargets(shapes, ball) {
  const own = shapes[0].map((s) => {
    if (s.pos === 'Goalkeeper') return [clamp(8 + 0.2 * (ball[0] - 20), 4, 26), 40 + 0.15 * (ball[1] - 40)];
    return [s.con[0] + clamp(0.5 * (ball[0] - 55), -24, 22), s.con[1] + clamp(0.2 * (ball[1] - 40), -7, 7)];
  });
  const ob = [120 - ball[0], 80 - ball[1]];
  const opp = shapes[1].map((s) => {
    let p;
    if (s.pos === 'Goalkeeper') p = [clamp(3 + 0.07 * ob[0], 2, 14), 40 + 0.22 * (ob[1] - 40)];
    else p = [s.sin[0] + clamp(BLOCK_K * (ob[0] - 48), -17, 20), s.sin[1] + clamp(0.38 * (ob[1] - 40), -13, 13)];
    return [120 - p[0], 80 - p[1]];
  });
  return [own, opp].map((T) => T.map((p) => [clamp(p[0], 1, 119), clamp(p[1], 1, 79)]));
}

function findPlayer(shape, who) {
  if (!who) return -1;
  const norm = (s) => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
  let j = who.name ? shape.findIndex((p) => norm(p.name) === norm(who.name)) : -1;
  if (j < 0 && who.num != null) j = shape.findIndex((p) => p.num === who.num);
  if (j < 0 && who.pos) j = shape.findIndex((p) => (p.pos || '').includes(who.pos));
  if (j < 0 && who.num === 9) j = shape.findIndex((p) => p.pos === 'Center Forward');
  return j;
}

function startPoint(play) {
  const z0 = play.steps[0] && ZONES[play.steps[0].zone];
  switch (play.start.restart) {
    case 'goal_kick': return [6, 40];
    case 'corner': return [119.5, z0 && z0[1] > 40 ? 79.5 : 0.5];
    case 'kickoff': return [60, 40];
    case 'throw_in': return [80, 79.5];
    case 'free_kick': return [94, 40];
    default: return z0 ? [z0[0] - 6, z0[1]] : [60, 40];
  }
}

function shotEnd(from, outcome) {
  const side = from[1] < 40 ? -1 : 1;
  return {
    gol: [120.5, 40 + side * 2.5], atajada: [118.5, 40 + side], fuera: [121, 40 + side * 7], poste: [120, 40 + side * 3.66],
    bloqueado: lerp(from, [120, 40], 0.35),
  }[outcome] || [120, 40 + side * 2];
}

/** Lista de segmentos {type, from, to, actor, receiver, lofted, label} lista para animar. */
export function buildSegments(play, shape) {
  let ball = startPoint(play), last = -1;
  return play.steps.map((s) => {
    const from = ball;
    let to = ZONES[s.zone] || [Math.min(from[0] + 14, 112), from[1]];
    if (s.type === 'shot' || s.type === 'header') to = shotEnd(from, s.outcome);
    if (s.type === 'clearance') to = [from[0] - 25, from[1] < 40 ? 4 : 76];
    let actor = findPlayer(shape, s.actor);
    if (actor < 0) actor = last;
    const receiver = findPlayer(shape, s.receiver);
    last = receiver >= 0 ? receiver : actor;
    ball = to;
    return { type: s.type, from, to, actor, receiver, lofted: s.type === 'cross' || s.height === 'alto', outcome: s.outcome };
  });
}

/** Probabilidad de transición z→z2 desde la matriz mv (suma de sus canales) con suavizado. */
function transP(mv, z, z2) {
  if (!Array.isArray(mv) || !mv.length) return null;
  let num = ALPHA, den = ALPHA * 18;
  for (const ch of mv) { const row = ch[z] || []; num += row[z2] || 0; den += row.reduce((a, b) => a + b, 0); }
  return num / den;
}

/** Cociente de verosimilitud de la ruta de zonas: equipo vs liga (1 = tan típica como la liga). */
export function pathTypicality(segs, entMv, leagueMv) {
  let logR = 0, n = 0;
  for (const s of segs) {
    if (s.type === 'shot' || s.type === 'header' || s.type === 'clearance') continue;
    const z = zoneOf(s.from), z2 = zoneOf(s.to);
    const pe = transP(entMv, z, z2), pl = transP(leagueMv, z, z2);
    if (pe == null || pl == null) return null;
    logR += Math.log(pe / pl); n++;
  }
  return n ? Math.exp(logR) : null;
}

/** xG medio de la zona del remate en la liga (juego abierto): Σxg / tiros de esa zona. */
export function zoneXG(league, p) {
  const xg = league && league.xg, sh = league && league.shot;
  if (!xg || !sh) return null;
  const z = zoneOf(p), k = 0;
  return sh[k][z] > 0 ? xg[k][z] / sh[k][z] : null;
}

/* Mismo modelo que pipeline/xg_grid.py: p = 1/(1+exp(-(b0 + b1·distancia + b2·ángulo + b3·cabeza))). */
const GOAL = { x: 120, y: 40, post: 4 }, PITCH = { x: 120, y: 80 };

/** xG del modelo propio en el punto del remate (coeficientes de /api/xg_grid); null si no hay rejilla. */
export function gridXG(grid, p, head) {
  const c = grid && grid.coef;
  if (!c || !p) return null;
  const x = Math.min(Math.max(p[0], 0), PITCH.x), y = Math.min(Math.max(p[1], 0), PITCH.y);
  const dx = Math.max(GOAL.x - x, 0);
  const dist = Math.hypot(dx, GOAL.y - y);
  const angle = Math.abs(Math.atan2(GOAL.y + GOAL.post - y, dx) - Math.atan2(GOAL.y - GOAL.post - y, dx));
  return 1 / (1 + Math.exp(-(c.intercepto + c.distancia * dist + c.angulo * angle + c.cabeza * (head ? 1 : 0))));
}

/* ---------- animación ---------- */
function ballAt(seg, t) {
  const p = lerp(seg.from, seg.to, t);
  return seg.lofted ? { p, h: Math.sin(Math.PI * t) * 6 } : { p, h: 0 };
}

function frameSVG(shapes, seg, t, idx, n) {
  const { p, h } = ballAt(seg, t);
  const T = shapeTargets(shapes, p);
  if (seg.actor >= 0) T[0][seg.actor] = seg.type === 'carry' || seg.type === 'dribble' ? p : lerp(seg.from, p, 0);
  if (seg.receiver >= 0) T[0][seg.receiver] = lerp(T[0][seg.receiver], seg.to, Math.min(1, t * 1.4));
  // Semántica fija del producto: equipo elegido = dorado (protagonista), rival = azul.
  const dots = (ti) => T[ti].map((q, j) => {
    const s = shapes[ti][j], hi = ti === 0 && (j === seg.actor || j === seg.receiver);
    return playerDisc({ x: q[0], y: q[1], num: s.num, side: ti === 0 ? 'protag' : 'rival', gk: s.pos === 'Goalkeeper', hi });
  }).join('');
  const arc = seg.lofted ? `<path class="pitch-arc" d="M ${seg.from[0]} ${seg.from[1]} Q ${(seg.from[0] + seg.to[0]) / 2} ${(seg.from[1] + seg.to[1]) / 2 - 12} ${seg.to[0]} ${seg.to[1]}"/>` : `<line class="pitch-arc" x1="${seg.from[0]}" y1="${seg.from[1]}" x2="${seg.to[0]}" y2="${seg.to[1]}"/>`;
  const label = (seg.type === 'header' ? 'Cabezazo' : '') + (t >= 1 && idx === n - 1 && seg.outcome ? ' · ' + OUTCOME_ES[seg.outcome] : '');
  return arc + dots(1) + dots(0) + ballSVG(p[0], p[1], h) +
    (label ? `<text class="pitch-label" x="${clamp(p[0], 12, 108).toFixed(1)}" y="${clamp(p[1] - 5 - h, 4, 76).toFixed(1)}">${label.trim()}</text>` : '');
}

function animate(stage, shapes, segs) {
  let i = 0, t0 = null;
  const token = {};
  stage.__anim = token;
  const tick = (now) => {
    if (stage.__anim !== token || !segs.length) return;
    if (t0 == null) t0 = now;
    const seg = segs[i], d = (DUR[seg.type] || 1) * 1000, t = Math.min(1, (now - t0) / d);
    stage.innerHTML = pitchSVG(frameSVG(shapes, seg, t, i, segs.length), { label: 'Animación de la jugada' });
    if (t >= 1) { if (i === segs.length - 1) return; i++; t0 = now; }
    requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}

/* ---------- vista (controles y colores: css/components.css y css/pitch.css) ---------- */
const teamOptions = (teams, sel) => teams.map((t) => `<option value="${t.id}"${t.id === sel ? ' selected' : ''}>${t.label || t.id}</option>`).join('');

function stepsHTML(play, fmt) {
  const who = (a) => (a ? a.name || (a.num != null ? 'el ' + a.num : '') || fmt.position(a.pos) || '' : '');
  return `<ol class="pl-steps">${play.steps.map((s) => `<li><b>${fmt.esc(TYPE_ES[s.type] || s.type)}</b>` +
    (who(s.actor) ? (who(s.actor).startsWith('el ') ? ' del ' + fmt.esc(who(s.actor).slice(3)) : ` de ${fmt.esc(who(s.actor))}`) : '') + (s.receiver ? ` para ${fmt.esc(who(s.receiver))}` : '') +
    (s.zone ? ` · ${fmt.esc(ZONE_ES[s.zone] || s.zone)}` : '') + (s.outcome ? ` → <b>${fmt.esc(OUTCOME_ES[s.outcome])}</b>` : '') + '</li>').join('')}</ol>`;
}

export function interpHTML(play, segs, ent, league, teamLabel, fmt, grid = null) {
  const shot = [...segs].reverse().find((s) => s.type === 'shot' || s.type === 'header');
  const byGrid = shot ? gridXG(grid, shot.from, shot.type === 'header') : null;
  const xg = byGrid !== null ? byGrid : (shot ? zoneXG(league, shot.from) : null);
  const r = ent && ent.att ? pathTypicality(segs, ent.att.mv, league && league.mv) : null;
  const typ = r == null ? 'sin datos suficientes del equipo'
    : r >= SIMILAR_HI ? `${fmt.num(r, 1)} veces más frecuente que en el promedio de la liga`
      : r <= 1 / SIMILAR_HI ? `${fmt.num(1 / r, 1)} veces menos frecuente que en el promedio de la liga`
        : 'tan frecuente como en el promedio de la liga';
  return `<div class="card pl-interp"><h3>Interpretación (no es una predicción)</h3><ul class="pl-list">
    <li>${shot ? `Un remate desde ese punto vale en promedio <b>${xg == null ? fmt.NA : fmt.num(xg, 2)} xG</b> en la liga (modelo propio de distancia y ángulo, sin penales${shot.type === 'header' ? '; los cabezazos suelen valer menos' : ''}).` : 'La jugada no termina en remate.'}</li>
    <li>¿Qué tan típica es esta ruta para ${fmt.esc(teamLabel)}? La secuencia de zonas es <b>${typ}</b>.</li></ul>
    <p class="muted">Interpretación: <b>${fmt.esc(RESTART_ES[play.start.restart] || '')}</b> · fuente: ${play.source === 'llm' ? 'modelo de lenguaje' : 'intérprete de reglas'} · confianza ${fmt.pct(play.confidence)}.</p></div>`;
}

async function postParse(body) {
  const r = await fetch('/api/play/parse', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  const data = await r.json().catch(() => ({}));
  return { ok: r.ok, status: r.status, data };
}

export async function render(root, ctx) {
  const { api, fmt, params } = ctx;
  const [caps, teams] = await Promise.all([api.tryJSON('/api/play/capabilities'), api.tryJSON('/api/teams')]);
  const list = (teams || []).filter((t) => t.n > 0);
  const sel = (params && params.team) || (list[0] && list[0].id) || '';
  const selTeam = (list.find((t) => t.id === sel) || {}).team;
  const opp = (list.find((t) => t.team !== selTeam) || list.find((t) => t.id !== sel) || {}).id || sel;
  const label = (id) => (list.find((t) => t.id === id) || {}).label || id;
  root.innerHTML = `<div class="pl-grid"><div class="pl-col"><section class="card pl-form" aria-label="Jugada en texto">
    <div class="pl-row"><label class="field protag"><span>Equipo (ataca)</span><select class="select" id="pl-team">${teamOptions(list, sel)}</select></label>
      <label class="field rival"><span>Rival</span><select class="select" id="pl-opp">${teamOptions(list, opp)}</select></label>
      ${caps && caps.llm ? `<label class="field"><span>Intérprete</span><select class="select" id="pl-mode"><option value="auto">Automático</option><option value="rules">Reglas</option><option value="llm">Modelo de lenguaje</option></select></label>` : ''}</div>
    <label class="field"><span>Jugada</span><textarea class="input" id="pl-text" maxlength="500" aria-label="Jugada en texto">${fmt.esc(EXAMPLES[0])}</textarea></label>
    <div class="pl-row pl-ex"><span class="eyebrow">Ejemplos</span><div class="seg">${EXAMPLES.map((e, i) => `<button type="button" class="btn sm" data-ex="${i}" title="${fmt.esc(e)}">${EXAMPLE_NAMES[i]}</button>`).join('')}</div></div>
    <div class="pl-row"><button type="button" class="btn primary" id="pl-go">Interpretar y animar</button><button type="button" class="btn" id="pl-replay">Repetir</button></div>
    </section>
    <section class="panel pl-result" aria-live="polite"><h3 class="kicker">Así la entendimos</h3><div id="pl-out"></div></section></div>
    <section class="pl-view" aria-label="Animación"><div id="pl-legend">${legendHTML([{ side: 'protag', label: label(sel) }, { side: 'rival', label: label(opp) }])}</div>
    <div id="pl-stage" class="pl-stage">${pitchSVG('', { label: 'Cancha' })}</div>${caption('Dorado: equipo elegido; azul: rival.')}<div id="pl-interp"></div></section></div>`;
  const $ = (id) => root.querySelector('#' + id);
  for (const b of root.querySelectorAll('[data-ex]')) b.onclick = () => { $('pl-text').value = EXAMPLES[+b.dataset.ex]; run(); };
  let last = null;
  $('pl-replay').onclick = () => last && animate($('pl-stage'), last.shapes, last.segs);
  $('pl-go').onclick = () => run();
  async function run() {
    const team = $('pl-team').value, oppId = $('pl-opp').value;
    const mode = $('pl-mode') ? $('pl-mode').value : 'rules';
    $('pl-out').innerHTML = '<p class="muted">Interpretando…</p>';
    $('pl-legend').innerHTML = legendHTML([{ side: 'protag', label: label(team) }, { side: 'rival', label: label(oppId) }]);
    const [res, ent, rival, model, grid] = await Promise.all([postParse({ text: $('pl-text').value, team, opponent: oppId, mode }),
      api.tryJSON('/api/teams/' + encodeURIComponent(team)), api.tryJSON('/api/teams/' + encodeURIComponent(oppId)), api.tryJSON('/api/model'),
      api.tryJSON('/api/xg_grid')]);
    if (!res.ok) {
      const d = res.data.detail || {};
      $('pl-out').innerHTML = `<div class="panel err"><p>${fmt.esc(d.mensaje || 'No pudimos interpretar la jugada.')}</p>` +
        (d.sugerencias ? `<p>Prueba algo como:</p><ul>${d.sugerencias.map((s) => `<li>${fmt.esc(s)}</li>`).join('')}</ul>` : '') + '</div>';
      return;
    }
    const play = res.data, shape = (ent && ent.shape) || [], rshape = (rival && rival.shape) || shape;
    if (shape.length < 11 || rshape.length < 11) { $('pl-out').innerHTML = '<p class="panel err">Este equipo no tiene once tipo en el modelo.</p>'; return; }
    const segs = buildSegments(play, shape), shapes = [shape.slice(0, 11), rshape.slice(0, 11)];
    $('pl-out').innerHTML = stepsHTML(play, fmt) +
      (play.assumptions.length ? `<p class="muted">Supuestos: ${play.assumptions.map(fmt.esc).join(' ')}</p>` : '') +
      (play.warnings || []).map((w) => `<p class="muted">${fmt.esc(WARN_ES[w] || '')}</p>`).join('');
    const entFull = model && model.entities ? model.entities.find((e) => e.id === team) : null;
    const teamLabel = (list.find((t) => t.id === team) || {}).label || team;
    $('pl-interp').innerHTML = interpHTML(play, segs, entFull, model && model.league, teamLabel, fmt, grid);
    last = { shapes, segs };
    animate($('pl-stage'), shapes, segs);
  }
  run();
}
