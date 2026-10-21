/* Context rendering shared by the page and its regression tests. */
(function(root) {
  const finite = x => typeof x === 'number' && Number.isFinite(x);
  const fmt = (x, digits = 2) => finite(x) ? x.toFixed(digits) : 's/d';
  const esc = x => String(x ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const labels = { winning: 'Ganando', drawing: 'Empatando', losing: 'Perdiendo', home: 'Local', away: 'Visitante', unknown: 'Desconocido' };
  const metrics = { possession_proxy: 'Posesión aproximada por pases (0–1)', action_share: 'Proporción de acciones (0–1)', directness: 'Verticalidad de pases (0–1, aprox.)', pace: 'Ritmo hacia primer tiro (yardas/s, aprox.)', ppda: 'PPDA aproximado', passes_per90: 'Pases / 90 min', shots_per90: 'Tiros / 90 min', xg_per90: 'xG / 90 min', xga_per90: 'xG concedido / 90 min', pressures_per90: 'Presiones / 90 min', recoveries_per90: 'Eventos de recuperación / 90 min', losses_per90: 'Desposesiones y malos controles / 90 min', transition_shots_per90: 'Tiros en transición de 10 s / 90 min' };
  function render(entity) {
    const context = entity.context || {};
    const cards = [];
    for (const dim of ['score_state', 'venue']) {
      for (const [key, c] of Object.entries(context[dim] || {})) {
        if (key === 'unknown' && !c.matches) continue;
        cards.push(`<div class="idcard"><h3>${esc(labels[key] || key)}</h3><dl class="kv">
          <dt>Muestra observada</dt><dd>${fmt(c.matches, 0)} partidos · ${fmt(c.minutes, 1)} min · ${fmt(c.possessions, 0)} posesiones</dd>
          <dt>Calidad</dt><dd>${c.sufficient_sample ? 'Umbral descriptivo alcanzado' : 'Muestra insuficiente'}${c.clock_incomplete ? ' · reloj incompleto' : ''}</dd>
          <dt>Pases / avance hacia delante</dt><dd>${fmt(c.passes, 0)} / ${fmt(c.forward_pass_rate)}</dd>
          <dt>Tiros / xG / xG concedido</dt><dd>${fmt(c.shots, 0)} / ${fmt(c.xg)} / ${fmt(c.xga)}</dd>
          <dt>Presión / contrapresión (eventos)</dt><dd>${fmt(c.pressures, 0)} / ${fmt(c.counterpressures, 0)}</dd>
          <dt>PPDA / verticalidad de pases</dt><dd>${fmt(c.ppda)} / ${fmt(c.directness)}</dd>
          <dt>Minutos con alguna expulsión</dt><dd>${fmt(finite(c.seconds_with_red_card) ? c.seconds_with_red_card / 60 : null, 1)}</dd>
        </dl></div>`);
      }
    }
    if (!cards.length) return `<div><h3>${esc(entity.label)}</h3><p>Sin datos contextuales disponibles.</p></div>`;
    const rows = (entity.context_comparisons || []).map(c => `<tr><td>${esc(labels[c.left])} − ${esc(labels[c.right])}</td><td>${esc(metrics[c.metric] || c.metric)}</td><td>${fmt(c.left_value)}</td><td>${fmt(c.right_value)}</td><td>${fmt(c.absolute_difference)}</td><td>${finite(c.relative_difference) ? fmt(c.relative_difference * 100, 1) + '%' : 's/d'}</td><td>${c.sufficient_sample ? 'Descriptiva' : 'Muestra insuficiente'}</td></tr>`);
    const descriptions = (entity.context_comparisons || []).filter(c => c.metric === 'xg_per90' && finite(c.absolute_difference)).map(c => `${labels[c.left]} registra ${fmt(c.left_value)} xG/90 frente a ${fmt(c.right_value)} ${labels[c.right].toLowerCase()} (diferencia ${fmt(c.absolute_difference)}).`);
    const warnings = Object.entries(entity.context_status?.warnings || {}).map(([reason, n]) => `${esc(reason)}: ${n} partidos`).join(' · ');
    return `<div><h3>${esc(entity.label)}</h3><div class="idcards">${cards.join('')}</div>
      <p class="status">${descriptions.map(esc).join(' ')} Las diferencias no demuestran una adaptación deliberada: pueden intervenir rival, expulsiones, torneo y selección de partidos.</p>
      ${warnings ? `<p class="status">Cobertura: ${warnings}</p>` : ''}
      <details><summary>Comparaciones normalizadas y diferencias</summary><div class="temporal-scroll"><table class="temporal-table"><thead><tr><th>Contextos (A − B)</th><th>Métrica</th><th>A</th><th>B</th><th>Diferencia absoluta</th><th>Relativa a B</th><th>Muestra</th></tr></thead><tbody>${rows.join('')}</tbody></table></div></details>
      <p class="status">Minutos de reloj observado, con interrupciones; no equivalen a tiempo efectivo. Las posesiones que atraviesan estados se cuentan en cada estado visitado y no son aditivas. PPDA, posesión, ritmo y verticalidad son aproximaciones experimentales.</p></div>`;
  }
  const api = { render, fmt };
  if (typeof module !== 'undefined') module.exports = api;
  else root.ContextView = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
