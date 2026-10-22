/* Jugadas peligrosas en contra (capítulo 6): cada una dibujada en la cancha con «Hecho observado / Interpretación».
   Marco del dato: el protagonista defiende la portería IZQUIERDA (x = 0); sus acciones van en dorado y las del rival en azul.
   Aficionado: cancha + interpretación (≤3 números). DT: además el hecho completo, xG, OBV y duración. */
import { esc } from '../js/fmt.js';
import { pitchSVG, legendHTML } from '../js/pitch.js';
import { countNumbers } from '../js/qa.js';

const TAGS = { transicion: 'Transición', tras_perdida_costosa: 'Tras pérdida costosa', ataque_establecido: 'Ataque establecido',
  corner: 'Córner', fk: 'Tiro libre', throw: 'Saque de banda' };
const SHOW_FAN = 3;

const sideOf = (a) => (a && a.equipo === 'propio' ? 'protag' : 'rival');
const tag = (t) => TAGS[t] || String(t || '').replace(/_/g, ' ');

/** SVG de una jugada: acciones numeradas (flecha si hay destino) y los tiros con su xG. */
export function playSVG(play, label, numbered = true) {
  let marks = '';
  (play.acciones || []).forEach((a, i) => {
    const s = sideOf(a);
    if (Number.isFinite(a.x_fin) && Number.isFinite(a.y_fin)) {
      marks += `<line class="play-line ${s}" x1="${a.x}" y1="${a.y}" x2="${a.x_fin}" y2="${a.y_fin}"><title>${esc(a.accion)}</title></line>`;
    }
    marks += `<g class="play-pt ${s}"><circle cx="${a.x}" cy="${a.y}" r="1.4"/>${numbered ? `<text x="${a.x}" y="${a.y}">${i + 1}</text>` : ''}<title>${esc(a.accion)}</title></g>`;
  });
  for (const t of play.tiros || []) {
    marks += `<circle class="ch-shot rival${t.gol ? ' goal' : ''}" cx="${t.x}" cy="${t.y}" r="${(1.2 + Math.sqrt(t.xg || 0) * 4).toFixed(2)}"><title>xG ${esc(String(t.xg))}</title></circle>`;
  }
  return pitchSVG(marks, { label });
}

function header(play, ctx) {
  const { fmt } = ctx;
  const out = play.gol ? 'terminó en gol' : 'terminó en tiro';
  return `Minuto ${fmt.num(play.minuto, 0)} · ${esc(play.rival)} · ${out}`;
}

function chips(play) {
  const items = [...(play.etiquetas || []), ...(play.bp_tipo ? [play.bp_tipo] : [])];
  return items.length ? `<div class="badges">${items.map((t) => `<span class="chip">${esc(tag(t))}</span>`).join('')}</div>` : '';
}

/** Tarjeta de una jugada. Aficionado: título, cancha e interpretación (si no pasa de 3 números). */
export function playCard(play, ctx) {
  const { fmt, mode } = ctx;
  const title = header(play, ctx);
  const svg = playSVG(play, `Jugada: ${title}`, mode === 'dt');
  if (mode !== 'dt') {
    const interp = play.interpretacion && countNumbers(title + ' ' + play.interpretacion) <= SHOW_FAN ? `<p class="interp">${esc(play.interpretacion)}</p>` : '';
    return `<article class="card play"><header><h3>${title}</h3></header>${svg}${interp}</article>`;
  }
  const meta = `xG de la posesión ${fmt.num(play.xg_posesion)} · OBV máximo ${fmt.num(play.obv_max)} · ${fmt.num(play.duracion_s, 0)} s · ${esc(fmt.date(play.fecha))}`;
  return `<article class="card play"><header><h3>${title}</h3></header>${chips(play)}${svg}
    <p class="fact"><span class="kicker">Hecho observado</span>${esc(play.hecho)}</p>
    <p class="interp"><span class="kicker">Interpretación</span>${esc(play.interpretacion)}</p><p class="muted">${meta}</p></article>`;
}

/** Bloque del capítulo: top 3 de juego abierto y de balón parado (10 en modo DT), con leyenda y pie de cancha. */
export function playsBlock(win, ctx) {
  const limit = ctx.mode === 'dt' ? 10 : 3;
  const block = (key, name) => {
    const plays = (win[key] || []).slice(0, limit);
    return plays.length ? `<div class="plays"><h3 class="subhead">${name}</h3><div class="grid">${plays.map((p) => playCard(p, ctx)).join('')}</div></div>` : '';
  };
  const body = block('juego_abierto', 'Las que más dolieron en juego abierto') + block('balon_parado', 'Las que más dolieron a balón parado');
  if (!body) return '';
  return `${legendHTML([{ side: 'protag', label: 'Acciones del equipo' }, { side: 'rival', label: 'Acciones y tiros del rival' }])}${body}
    <p class="caption">Orden: gol, luego xG de la posesión y luego OBV. ${ctx.mode === 'dt' ? 'Los números son el orden de las acciones. ' : ''}En esta vista el equipo defiende la portería de la izquierda.</p>`;
}

