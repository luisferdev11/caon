/* Piezas de tarjeta compartidas por las vistas: hallazgo (Hecho / Interpretación), mosaico métrico,
   «Ver datos» e insignia de ventana. Todo número pasa por fmt.js. */
import { esc, windowBadge as windowText } from './fmt.js';

/** Insignia de ventana: neutra para la oficial, rayado tenue (fuera de ventana) para epílogo/temprano. */
export function windowBadge(win, fmt) {
  const text = (fmt && fmt.windowBadge ? fmt.windowBadge : windowText)(win);
  if (!text) return '';
  return `<span class="badge${win === 'oficial' ? '' : ' out'}">${text}</span>`;
}

function evidenceList(evidencia, fmt) {
  const items = (evidencia || []).filter((e) => e && e.id).map((e) => {
    const n = Number.isFinite(e.n) ? ` · n = ${fmt.num(e.n, 0)}` : '';
    const ci = e.ci ? ` · IC 80% ${fmt.interval(e.ci)}` : '';
    return `<li><a href="#metodo/${encodeURIComponent(e.id)}"><code>${esc(e.id)}</code></a>${n}${ci}</li>`;
  });
  return items.length ? `<details class="seedata"><summary>Evidencia</summary><ul class="evid">${items.join('')}</ul></details>` : '';
}

/** Hallazgo de la historia: {titulo, hecho, interpretacion, evidencia[], accion?, window}. */
export function finding(f, ctx) {
  const { fmt, mode } = ctx;
  const badge = f.window === 'oficial' ? '' : windowBadge(f.window, fmt);
  const action = f.accion ? `<p class="action"><strong>Qué vigilar:</strong> ${esc(f.accion)}</p>` : '';
  return `<article class="card finding${f.window && f.window !== 'oficial' ? ' out' : ''}">${f.titulo ? `<header><h3>${esc(f.titulo)}</h3>${badge ? `<div class="badges">${badge}</div>` : ''}</header>` : ''}
    <p class="fact"><span class="kicker">Hecho observado</span>${esc(f.hecho || '')}</p>
    ${f.interpretacion ? `<p class="interp"><span class="kicker">Interpretación</span>${esc(f.interpretacion)}</p>` : ''}
    ${action}${mode === 'dt' ? evidenceList(f.evidencia, fmt) : ''}</article>`;
}

/** Tabla plegable «Ver datos»; rows ya formateadas (texto), se escapan aquí. */
export function seeData(headers, rows, summary = 'Ver datos') {
  if (!rows || !rows.length) return '';
  const head = `<tr>${headers.map((h) => `<th>${esc(h)}</th>`).join('')}</tr>`;
  const body = rows.map((r) => `<tr>${r.map((c, i) => `<td${i ? ' class="num"' : ''}>${esc(c)}</td>`).join('')}</tr>`).join('');
  return `<details class="seedata"><summary>${esc(summary)}</summary><div class="scroll"><table class="table">${head}${body}</table></div></details>`;
}

/** Mosaico de un registro métrico del contrato {id, value, n, unit, ref_pct?, ci?, window}.
    Aficionado: valor + percentil (≤3 números). DT: añade intervalo, n y ventana. */
export function metricTile(rec, label, ctx) {
  const { fmt, mode } = ctx;
  const pctText = Number.isFinite(rec.ref_pct) ? `<p class="muted">${fmt.percentile(rec.ref_pct)} de la liga</p>` : '';
  const dt = mode === 'dt'
    ? `<p class="muted">IC 80%: ${fmt.ciByUnit(rec.ci, rec.unit)} · n = ${fmt.num(rec.n, 0)}</p><div class="badges">${windowBadge(rec.window, fmt)}</div>`
    : (rec.window && rec.window !== 'oficial' ? `<div class="badges">${windowBadge(rec.window, fmt)}</div>` : '');
  return `<div class="tile"><span class="tlabel">${esc(label)}</span><strong class="tval">${fmt.metricValue(rec)}</strong>
    <span class="tunit">${esc(fmt.unitText(rec.unit))}</span>${pctText}${dt}</div>`;
}
