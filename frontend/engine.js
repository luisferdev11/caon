/* Vestidor Táctico · motor de simulación y coreografía.
 * Un solo archivo para la página y para las pruebas en Node.
 *
 * 1) simulate(): cadena de Markov por zonas (6x3) y fase (E = ataque establecido, T = transición:
 *    primeros 10 s tras recuperar en juego abierto). Para cada equipo, zona y fase los datos dan la
 *    probabilidad de cada desenlace de una acción con balón: tirar, ganar córner, ganar falta peligrosa,
 *    ganar penal, recibir falta, ganar saque de banda, perder en juego, perder con balón muerto (banda,
 *    meta, falta/fuera de juego) o mover el balón a otra zona (pase o conducción).
 *    Un cruce A vs D combina ataque de A y defensa de D contra la liga en escala logit:
 *        logit p = logit pA + logit pD - logit pLiga
 *    Muestras pequeñas se encogen hacia la liga con K pseudo-partidos.
 *    Faltas: quién la comete sale de quién suele estar en esa zona; tarjetas con la tasa de cada equipo;
 *    doble amarilla = roja; con un expulsado el equipo pierde fuerza (ajuste logit por jugador de menos).
 *    Balón parado con detalle por equipo: córner corto o al área, técnica, zona de caída, remate y
 *    cabezazo; falta directa o centrada; penal con lanzador, lado y estirada del portero.
 * 2) choreograph(): convierte cada acción en movimiento de 22 jugadores y el balón. Respeta el
 *    reglamento: reanudaciones con pase, fuera de juego, distancia de 10 yardas, área en saques de meta,
 *    círculo central, área y arco en penales, expulsados fuera del campo.
 * Herramienta para explicar estilos, no para predecir resultados.
 */
(function (root) {
  'use strict';

  const NX = 6, NY = 3, NZ = 18;
  const T_TOTAL = 95 * 60, HALF = T_TOTAL / 2;
  const PEN_XG = 0.78, T_WINDOW = 10;
  const TURN_TIME = 1.0, SHOT_TIME = 1.6, SP_DELIVERY = 3.0;
  const KICKOFF = 2 * NY + 1, OWN_BOX = 1, CLEAR_ZONE = 1 * NY + 1, BOX_CENTER = 5 * NY + 1;
  // pesos relativos de tiempo muerto por tipo de reanudación (se calibra una unidad común)
  const W = { throw: 0.55, gk: 1.0, fk: 0.75, sp: 1.3, goal: 2.0, pen: 2.5, card: 0.6 };
  const OUT = ['shot', 'spC', 'spF', 'pen', 'keepF', 'keepT', 'lossO', 'lossXT', 'lossXG', 'lossXF'];
  const LTO = [['lossO', 'ltoO'], ['lossXT', 'ltoXT'], ['lossXG', 'ltoXG'], ['lossXF', 'ltoXF'], ['keepF', 'ltoKF'], ['keepT', 'ltoKT']];
  const RED_SHOT = 0.2, RED_LOSS = 0.15;     // efecto por jugador de menos (escala logit)
  const CORNER_AGAIN = 0.24;                 // córners que se despejan a otro córner (calibra córners por partido)

  function mulberry32(seed) {
    let a = seed >>> 0;
    return function () {
      a = (a + 0x6D2B79F5) >>> 0;
      let t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  const logit = (p) => Math.log(p / (1 - p));
  const inv = (x) => 1 / (1 + Math.exp(-x));
  const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
  const sum = (a) => a.reduce((x, y) => x + y, 0);
  const colOf = (z) => Math.floor(z / NY), rowOf = (z) => z % NY;
  const mirrorZ = (z) => (NX - 1 - colOf(z)) * NY + (NY - 1 - rowOf(z));
  const norm = (v) => { const t = sum(v); return t > 0 ? v.map((x) => x / t) : v.map(() => 1 / v.length); };
  const comb = (a, d, l) => inv(logit(clamp(a, 1e-4, 0.999)) + logit(clamp(d, 1e-4, 0.999)) - logit(clamp(l, 1e-4, 0.999)));
  function sampleRow(row, r) {
    let c = 0;
    for (let i = 0; i < row.length; i++) { c += row[i]; if (r < c) return i; }
    return row.length - 1;
  }

  /* ---------------------------------------------------------------- parámetros */
  function rates(acc, L, K) {
    const Lm = L.matches, out = { ph: [] };
    for (let ph = 0; ph < 2; ph++) {
      const R = { xg: [], mv: [], carry: [] };
      for (const o of OUT) R[o] = [];
      for (let z = 0; z < NZ; z++) {
        const Ln = Math.max(L.n[ph][z], 1), k = K * L.n[ph][z] / Lm, n = acc.n[ph][z] + k;
        for (const o of OUT) R[o][z] = (acc[o][ph][z] + k * L[o][ph][z] / Ln) / n;
        const ks = K * L.shot[ph][z] / Lm, lxg = L.xg[ph][z] / Math.max(L.shot[ph][z], 1);
        R.xg[z] = (acc.xg[ph][z] + ks * lxg) / Math.max(acc.shot[ph][z] + ks, 1e-9);
        if (acc.mv) {
          const row = [], car = [];
          let tot = 0;
          for (let w = 0; w < NZ; w++) {
            const m = acc.mv[ph][z][w] + k * L.mv[ph][z][w] / Ln, c = acc.mvC[ph][z][w] + k * L.mvC[ph][z][w] / Ln;
            row[w] = m; car[w] = m > 0 ? c / m : 0; tot += m;
          }
          R.mv[z] = row.map((v) => v / Math.max(tot, 1e-9)); R.carry[z] = car;
        }
      }
      const tw = acc.matches / (acc.matches + K);
      R.tau = tw * acc.tau[ph] + (1 - tw) * L.tau[ph];
      out.ph.push(R);
    }
    for (const [o, key] of LTO) {
      out[key] = [];
      for (let z = 0; z < NZ; z++) {
        const lrow = L[key][z], ls = Math.max(sum(lrow), 1), kl = K * (L[o][0][z] + L[o][1][z]) / Lm;
        const row = acc[key][z].map((v, w) => v + kl * lrow[w] / ls), t = sum(row);
        out[key][z] = t > 0 ? row.map((v) => v / t) : null;
      }
    }
    const S = (k) => acc[k] + K * L[k] / Lm;
    const ratio = (num, den, lo, hi) => clamp(S(num) / Math.max(S(den), 1e-9), lo, hi);
    out.corner_short = ratio('corners_short', 'corners', 0, 0.8);
    out.corner_shot = ratio('corner_shots', 'corners', 0.02, 0.9);
    out.corner_xg = ratio('corner_xg', 'corner_shots', 0.02, 0.5);
    out.corner_head = ratio('corner_headers', 'corner_shots', 0, 1);
    out.fk_direct = ratio('fk_direct', 'fk', 0, 0.9);
    out.fk_direct_xg = ratio('fk_direct_xg', 'fk_direct', 0.01, 0.3);
    out.fk_cross_shot = clamp(S('fk_cross_shots') / Math.max(S('fk') - S('fk_direct'), 1e-9), 0.01, 0.9);
    out.fk_cross_xg = ratio('fk_cross_xg', 'fk_cross_shots', 0.02, 0.5);
    out.pen_conv = ratio('pens_scored', 'pens', 0.4, 0.97);
    out.yel_foul = ratio('yellow', 'fouls', 0, 0.6);
    out.red_foul = ratio('red', 'fouls', 0, 0.1);
    out.bb_yellow_pm = S('bb_yellow') / (acc.matches + K);
    out.bb_red_pm = S('bb_red') / (acc.matches + K);
    const dv = (key) => norm(acc[key].map((x, i) => x + K * L[key][i] / Lm));
    out.corner_tech = dv('corner_tech'); out.corner_target = dv('corner_target'); out.pen_place = dv('pen_place');
    const shots = sum(acc.shot[0]) + sum(acc.shot[1]), lshots = sum(L.shot[0]) + sum(L.shot[1]);
    out.sp_after_shot = (acc.sp_after_shot + K * L.sp_after_shot / Lm) / (shots + K * lshots / Lm);
    const chainPen = sum(acc.pen[0]) + sum(acc.pen[1]), lChainPen = sum(L.pen[0]) + sum(L.pen[1]);
    out.pen_sp = clamp((Math.max(0, acc.pens - chainPen) + K * Math.max(0, L.pens - lChainPen) / Lm) / Math.max(S('sp_poss'), 1e-9), 0, 0.1);
    return out;
  }

  const LCACHE = new WeakMap();
  function leagueRates(model) {
    if (!LCACHE.has(model)) LCACHE.set(model, rates(model.league, model.league, 0));
    return LCACHE.get(model);
  }

  /* A atacando contra la defensa de D */
  function matchup(model, A, D) {
    const L = model.league, K = model.meta.k_matches;
    const a = rates(A.att, L, K), d = rates(D.dfn, L, K), l = leagueRates(model);
    const P = { ph: [] };
    for (let ph = 0; ph < 2; ph++) {
      const ap = a.ph[ph], dp = d.ph[ph], lp = l.ph[ph];
      const R = { xg: [], mv: ap.mv, carry: ap.carry, tau: ap.tau };
      for (const o of OUT) R[o] = [];
      for (let z = 0; z < NZ; z++) {
        let tot = 0;
        for (const o of OUT) { R[o][z] = comb(ap[o][z], dp[o][z], lp[o][z]); tot += R[o][z]; }
        if (tot > 0.97) for (const o of OUT) R[o][z] *= 0.97 / tot;
        R.xg[z] = clamp(ap.xg[z] * dp.xg[z] / Math.max(lp.xg[z], 1e-6), 0.005, 0.9);
      }
      P.ph.push(R);
    }
    const blend = (x, y) => (x && y ? x.map((v, w) => 0.5 * v + 0.5 * y[w]) : (x || y));
    for (const [, key] of LTO) P[key] = a[key].map((row, z) => blend(row, d[key][z]));
    P.corner_short = a.corner_short; P.corner_tech = a.corner_tech; P.corner_target = a.corner_target; P.corner_head = a.corner_head;
    P.corner_shot = comb(a.corner_shot, d.corner_shot, l.corner_shot);
    P.corner_xg = clamp(a.corner_xg * d.corner_xg / l.corner_xg, 0.02, 0.5);
    P.fk_direct = a.fk_direct;
    P.fk_direct_xg = clamp(a.fk_direct_xg * d.fk_direct_xg / l.fk_direct_xg, 0.01, 0.3);
    P.fk_cross_shot = comb(a.fk_cross_shot, d.fk_cross_shot, l.fk_cross_shot);
    P.fk_cross_xg = clamp(a.fk_cross_xg * d.fk_cross_xg / l.fk_cross_xg, 0.02, 0.5);
    P.pen_conv = a.pen_conv; P.pen_place = a.pen_place;
    P.pen_sp = clamp(a.pen_sp * d.pen_sp / Math.max(l.pen_sp, 1e-6), 0, 0.15);
    P.sp_after_shot = clamp(a.sp_after_shot * d.sp_after_shot / l.sp_after_shot, 0, 0.6);
    return P;
  }
  function cardRates(model, e) {
    const r = rates(e.att, model.league, model.meta.k_matches);
    return { y: r.yel_foul, r: r.red_foul, bbY: r.bb_yellow_pm, bbR: r.bb_red_pm };
  }

  /* Unidad de tiempo muerto calibrada para que un partido de liga dure ~95 min de reloj. */
  const UCACHE = new WeakMap();
  function deadUnit(model) {
    if (UCACHE.has(model)) return UCACHE.get(model);
    const L = model.league, l = leagueRates(model), m = L.matches;
    const s2 = (k) => (sum(L[k][0]) + sum(L[k][1])) / m;
    const n0 = sum(L.n[0]) / m, n1 = sum(L.n[1]) / m;
    const shots = s2('shot'), xg = (sum(L.xg[0]) + sum(L.xg[1])) / m;
    const sp = L.sp_poss / m, pens = L.pens / m, goals = xg + L.sp_xg / m + pens * PEN_XG;
    const foulMoments = s2('keepF') + s2('spF') + s2('pen') + s2('lossXF');
    const cards = (L.yellow + L.red + L.second_yellow + L.bb_yellow + L.bb_red) / m;
    const inplay = n0 * l.ph[0].tau + n1 * l.ph[1].tau + s2('lossO') * TURN_TIME + shots * SHOT_TIME + sp * SP_DELIVERY + foulMoments * TURN_TIME;
    const gkRestarts = shots * (1 - l.sp_after_shot) - goals * 0.7;
    const weighted = W.throw * (s2('lossXT') + s2('keepT')) + W.gk * (s2('lossXG') + gkRestarts) + W.fk * (s2('lossXF') + s2('keepF'))
      + W.sp * sp + W.goal * goals + W.pen * pens + W.card * cards;
    const u = Math.max(3, (T_TOTAL / 2 - inplay) / weighted);
    UCACHE.set(model, u);
    return u;
  }

  /* ---------------------------------------------------------------- simulación */
  function newStats() {
    return { goals: 0, xg: 0, shots: 0, shotsT: 0, xgT: 0, actions: 0, final3: 0, time: 0, sp: 0, spGoals: 0, pens: 0, pensScored: 0,
      poss: 0, possActs: 0, longPoss: 0, regains: 0, regainsHigh: 0, fouls: 0, yellows: 0, reds: 0, corners: 0, fks: 0, offsides: 0,
      shotZones: new Array(NZ).fill(0), xgZones: new Array(NZ).fill(0), touchZones: new Array(NZ).fill(0), regainZones: new Array(NZ).fill(0) };
  }

  /* teams = [entA, entB]; opts: {seed, record, params, cards} */
  function simulate(model, teams, opts) {
    opts = opts || {};
    const rnd = mulberry32(opts.seed == null ? 1 : opts.seed);
    const P = opts.params || [matchup(model, teams[0], teams[1]), matchup(model, teams[1], teams[0])];
    const C = opts.cards || [cardRates(model, teams[0]), cardRates(model, teams[1])];
    const U = deadUnit(model);
    const st = [newStats(), newStats()];
    const log = opts.record ? [] : null;
    const push = (o) => { if (log) log.push(o); };
    const shapes = teams.map((e) => e.shape || null), acts = teams.map((e) => e.actors || null);
    let t = 0, team = 0, z = KICKOFF, ph = 0, tReg = 0, possActs = 0, half = 1;
    let restart = false;   // la siguiente acción es una reanudación: debe ser un pase (reglamento)
    const reds = [0, 0], yellowed = [new Set(), new Set()], off = [new Set(), new Set()];
    // tarjetas por protestar (no ligadas a faltas): proceso de Poisson por equipo
    const bbT = [[], []];
    for (let i = 0; i < 2; i++) {
      let tt = 0; const lam = (C[i].bbY + C[i].bbR) / T_TOTAL;
      while (lam > 0) { tt += -Math.log(1 - rnd()) / lam; if (tt >= T_TOTAL) break; bbT[i].push(tt); }
    }
    const startPoss = (tm, zz, phase) => {
      if (possActs > 0) { st[team].possActs += possActs; st[team].poss++; if (possActs >= 10) st[team].longPoss++; }
      possActs = 0; team = tm; z = zz; ph = phase; if (phase === 1) tReg = t;
    };
    const pickFouler = (ft, zf) => {
      const sh = shapes[ft]; if (!sh) return -1;
      const share = acts[ft] ? acts[ft][zf] : null;
      const ws = sh.map((s, j) => (s.pos === 'Goalkeeper' || off[ft].has(j) ? 0 : (share ? Math.sqrt(share[j]) + 0.08 : 1) * (yellowed[ft].has(j) ? 0.35 : 1)));
      return sum(ws) > 0 ? sampleRow(norm(ws), rnd()) : -1;
    };
    const booking = (ft, slot, card) => {
      if (!card) return card;
      if (slot < 0) {   // equipo sin once definido (liga promedio): solo se cuenta
        if (card === 'yellow') st[ft].yellows++; else { reds[ft]++; st[ft].reds++; }
        return card;
      }
      if (card === 'yellow') { if (yellowed[ft].has(slot)) card = 'second'; else { yellowed[ft].add(slot); st[ft].yellows++; } }
      if (card === 'red' || card === 'second') { reds[ft]++; off[ft].add(slot); st[ft].reds++; if (card === 'second') st[ft].yellows++; }
      return card;
    };
    const foul = (ft, zf, kind) => {
      const slot = pickFouler(ft, zf); st[ft].fouls++;
      let pY = C[ft].y, pR = C[ft].r;
      if (kind === 'pen') { pR = Math.min(0.3, pR * 4 + 0.06); pY = Math.min(0.9, pY * 1.5); }
      const r = rnd();
      const card = booking(ft, slot, r < pR ? 'red' : (r < pR + pY ? 'yellow' : null));
      return { fouler: slot, card };
    };
    const kickoff = (tm) => { push({ k: 'kickoff', t, team: tm }); t += 1.2; startPoss(tm, KICKOFF, 0); restart = true; };
    const first = rnd() < 0.5 ? 0 : 1;
    kickoff(first);
    const goal = (i, kind, xg) => {
      st[i].goals++;
      push({ k: 'goal', t, team: i, kind, xg, score: [st[0].goals, st[1].goals] });
      t += U * W.goal * (0.85 + 0.3 * rnd());
      kickoff(1 - i);
    };
    const gkRestart = (i) => { push({ k: 'gk', t, team: i }); t += U * W.gk * (0.8 + 0.4 * rnd()); startPoss(i, OWN_BOX, 0); restart = true; };
    const penalty = (i) => {
      const p = P[i], scored = rnd() < p.pen_conv, place = sampleRow(p.pen_place, rnd());
      let dive, miss = false;
      if (scored) dive = rnd() < 0.72 ? (place === 0 ? 2 : place === 2 ? 0 : (rnd() < 0.5 ? 0 : 2)) : place;
      else if (rnd() < 0.72) dive = place;
      else { miss = true; dive = Math.floor(rnd() * 3); }
      st[i].pens++; st[i].shots++; st[i].xg += PEN_XG; st[i].shotZones[BOX_CENTER]++; st[i].xgZones[BOX_CENTER] += PEN_XG;
      if (scored) st[i].pensScored++;
      push({ k: 'pen', t, team: i, goal: scored, xg: PEN_XG, place, dive, miss });
      t += U * W.pen * (0.5 + 0.2 * rnd());
      if (scored) goal(i, 'penal', PEN_XG); else gkRestart(1 - i);
    };
    const spShot = (i, xg, extra) => {
      const scored = rnd() < xg;
      st[i].shots++; st[i].xg += xg; st[i].shotZones[BOX_CENTER]++; st[i].xgZones[BOX_CENTER] += xg;
      push(Object.assign({ k: 'spshot', t, team: i, xg, goal: scored }, extra));
      t += SP_DELIVERY;
      if (scored) { st[i].spGoals++; goal(i, 'balón parado', xg); } else gkRestart(1 - i);
    };
    const clearance = (i, extra) => {
      push(Object.assign({ k: 'clear', t, team: 1 - i }, extra));
      t += SP_DELIVERY;
      startPoss(1 - i, CLEAR_ZONE, 1); st[1 - i].regains++;
    };
    const setPiece = (i, spk, zz, afterShot) => {
      const p = P[i];
      st[i].sp++;
      if (spk === 'corner') {
        st[i].corners++;
        const short = rnd() < p.corner_short, tech = sampleRow(p.corner_tech, rnd());
        const target = short ? 0 : 1 + sampleRow(norm(p.corner_target.slice(1)), rnd());
        const extra = { spk: 'corner', short, tech, target };
        push(Object.assign({ k: 'sp', t, team: i, z: zz, afterShot }, extra));
        t += U * W.sp * (0.85 + 0.3 * rnd());
        if (rnd() < p.pen_sp) {
          const f = foul(1 - i, mirrorZ(BOX_CENTER), 'pen');
          push({ k: 'penfoul', t, team: i, z: BOX_CENTER, fouler: f.fouler, card: f.card, fromSP: true });
          t += TURN_TIME + (f.card ? U * W.card : 0); penalty(i); return;
        }
        if (rnd() < p.corner_shot) { spShot(i, p.corner_xg, Object.assign({ header: rnd() < p.corner_head }, extra)); return; }
        if (rnd() < CORNER_AGAIN) {   // el defensor la despeja por la línea de fondo: otro córner
          push(Object.assign({ k: 'clear', t, team: 1 - i, toCorner: true }, extra)); t += SP_DELIVERY;
          setPiece(i, 'corner', BOX_CENTER, true); return;
        }
        clearance(i, extra); return;
      }
      st[i].fks++;
      push({ k: 'sp', t, team: i, spk: 'fk', z: zz });
      t += U * W.sp * (0.85 + 0.3 * rnd());
      if (rnd() < p.fk_direct) { spShot(i, p.fk_direct_xg, { spk: 'fk', direct: true }); return; }
      if (rnd() < p.fk_cross_shot) { spShot(i, p.fk_cross_xg, { spk: 'fk', direct: false, header: rnd() < p.corner_head }); return; }
      clearance(i, { spk: 'fk' });
    };
    const sampleOr = (row, fallback) => (row ? sampleRow(row, rnd()) : fallback);
    while (t < T_TOTAL) {
      if (half === 1 && t >= HALF) { half = 2; push({ k: 'ht', t }); kickoff(1 - first); continue; }
      for (let i = 0; i < 2; i++) while (bbT[i].length && bbT[i][0] <= t) {
        bbT[i].shift();
        const slot = pickFouler(i, KICKOFF);
        if (slot < 0) continue;
        const card = booking(i, slot, rnd() < C[i].bbR / Math.max(C[i].bbY + C[i].bbR, 1e-9) ? 'red' : 'yellow');
        push({ k: 'card', t, team: i, slot, card, reason: 'protestas' });
      }
      if (ph === 1 && t - tReg > T_WINDOW) ph = 0;
      const p = P[team].ph[ph], s = st[team];
      s.actions++; s.touchZones[z]++; possActs++;
      if (colOf(z) >= 4) s.final3++;
      let pS = p.shot[z], pLO = p.lossO[z];
      const dR = reds[team] - reds[1 - team];
      if (dR !== 0) {
        pS = inv(logit(clamp(pS, 1e-4, 0.999)) - RED_SHOT * dR);
        pLO = inv(logit(clamp(pLO, 1e-4, 0.999)) + RED_LOSS * dR);
      }
      let r = rnd();
      const isRestart = restart; restart = false;
      // en una reanudación no se puede tirar ni provocar balón parado de inmediato: se reparte el resto
      if (isRestart) { const skip = pS + p.spC[z] + p.spF[z] + p.pen[z]; r = skip + r * (1 - skip); }
      let cum = pS;
      if (r < cum) {
        const xg = p.xg[z], scored = rnd() < xg;
        s.shots++; s.xg += xg; s.shotZones[z]++; s.xgZones[z] += xg;
        if (ph === 1) { s.shotsT++; s.xgT += xg; }
        push({ k: 'shot', t, team, ph, z, xg, goal: scored });
        t += SHOT_TIME;
        if (scored) { goal(team, ph === 1 ? 'contragolpe' : 'jugada', xg); continue; }
        if (rnd() < P[team].sp_after_shot) { setPiece(team, 'corner', z, true); continue; }
        gkRestart(1 - team); continue;
      }
      cum += p.spC[z];
      if (r < cum) { push({ k: 'spwon', t, team, ph, z, spk: 'corner' }); t += TURN_TIME; setPiece(team, 'corner', z, false); continue; }
      cum += p.spF[z];
      if (r < cum) {
        const f = foul(1 - team, mirrorZ(z), 'fk');
        push({ k: 'spwon', t, team, ph, z, spk: 'fk', fouler: f.fouler, card: f.card });
        t += TURN_TIME + (f.card ? U * W.card : 0); setPiece(team, 'fk', z, false); continue;
      }
      cum += p.pen[z];
      if (r < cum) {
        const f = foul(1 - team, mirrorZ(z), 'pen');
        push({ k: 'penfoul', t, team, ph, z, fouler: f.fouler, card: f.card });
        t += TURN_TIME + (f.card ? U * W.card : 0); penalty(team); continue;
      }
      cum += p.keepF[z];
      if (r < cum) {
        const f = foul(1 - team, mirrorZ(z), 'foul'), z2 = sampleOr(P[team].ltoKF[z], z);
        push({ k: 'foul', t, team, ph, z, z2, fouler: f.fouler, card: f.card });
        t += U * W.fk * (0.7 + 0.6 * rnd()) + (f.card ? U * W.card : 0);
        startPoss(team, z2, 0); restart = true; continue;
      }
      cum += p.keepT[z];
      if (r < cum) {
        const z2 = sampleOr(P[team].ltoKT[z], z);
        push({ k: 'throw', t, team, ph, z, z2 });
        t += U * W.throw * (0.7 + 0.6 * rnd());
        startPoss(team, z2, 0); restart = true; continue;
      }
      cum += pLO;
      if (r < cum) {
        const z2 = sampleOr(P[team].ltoO[z], mirrorZ(z));
        push({ k: 'lossO', t, team, ph, z, z2 });
        t += TURN_TIME;
        const nt = 1 - team;
        st[nt].regains++; st[nt].regainZones[z2]++; if (colOf(z2) >= 3) st[nt].regainsHigh++;
        startPoss(nt, z2, 1); continue;
      }
      cum += p.lossXT[z];
      if (r < cum) {
        const z2 = sampleOr(P[team].ltoXT[z], mirrorZ(z));
        push({ k: 'lossX', out: 'throw', t, team, ph, z, z2 });
        t += U * W.throw * (0.7 + 0.6 * rnd());
        startPoss(1 - team, z2, 0); restart = true; continue;
      }
      cum += p.lossXG[z];
      if (r < cum) {
        const z2 = sampleOr(P[team].ltoXG[z], OWN_BOX);
        push({ k: 'lossX', out: 'gk', t, team, ph, z, z2 });
        t += U * W.gk * (0.8 + 0.4 * rnd());
        startPoss(1 - team, z2, 0); restart = true; continue;
      }
      cum += p.lossXF[z];
      if (r < cum) {
        const offside = colOf(z) >= 3 && rnd() < 0.4;
        let f = { fouler: -1, card: null };
        if (offside) s.offsides++; else f = foul(team, z, 'foul');
        const z2 = sampleOr(P[team].ltoXF[z], mirrorZ(z));
        push({ k: 'lossX', out: 'fk', offside, fouler: f.fouler, card: f.card, t, team, ph, z, z2 });
        t += U * W.fk * (0.7 + 0.6 * rnd()) + (f.card ? U * W.card : 0);
        startPoss(1 - team, z2, 0); restart = true; continue;
      }
      const w = sampleRow(p.mv[z], rnd()), carry = rnd() < (p.carry[z][w] || 0) && !isRestart;
      push({ k: carry ? 'carry' : 'pass', t, team, ph, z, z2: w, dur: p.tau });
      s.time += p.tau; t += p.tau; z = w;
    }
    startPoss(team, z, 0);
    push({ k: 'end', t: Math.max(t, T_TOTAL) });
    const tot = st[0].time + st[1].time || 1;
    return {
      score: [st[0].goals, st[1].goals],
      possession: [st[0].time / tot, st[1].time / tot],
      fieldTilt: [st[0].final3 / Math.max(st[0].final3 + st[1].final3, 1), st[1].final3 / Math.max(st[0].final3 + st[1].final3, 1)],
      stats: st, log, params: P, deadUnit: U, first
    };
  }

  function simulateMany(model, teams, N, seed) {
    const keys = ['goals', 'xg', 'shots', 'shotsT', 'xgT', 'sp', 'spGoals', 'pens', 'pensScored', 'regains', 'regainsHigh', 'poss', 'possActs', 'longPoss', 'actions',
      'fouls', 'yellows', 'reds', 'corners', 'fks', 'offsides'];
    const res = { W: 0, D: 0, L: 0, N, scores: {}, tilt: [0, 0] };
    for (const k of keys) res[k] = [0, 0];
    for (const k of ['shotZones', 'xgZones', 'regainZones', 'touchZones']) res[k] = [new Array(NZ).fill(0), new Array(NZ).fill(0)];
    const possTime = [0, 0];
    const params = [matchup(model, teams[0], teams[1]), matchup(model, teams[1], teams[0])];
    const cards = [cardRates(model, teams[0]), cardRates(model, teams[1])];
    for (let n = 0; n < N; n++) {
      const m = simulate(model, teams, { seed: (seed || 7) * 100003 + n, params, cards });
      const [a, b] = m.score;
      if (a > b) res.W++; else if (a === b) res.D++; else res.L++;
      const key = Math.min(a, 5) + '-' + Math.min(b, 5); res.scores[key] = (res.scores[key] || 0) + 1;
      for (let i = 0; i < 2; i++) {
        for (const k of keys) res[k][i] += m.stats[i][k];
        possTime[i] += m.possession[i]; res.tilt[i] += m.fieldTilt[i];
        for (const k of ['shotZones', 'xgZones', 'regainZones', 'touchZones']) for (let z = 0; z < NZ; z++) res[k][i][z] += m.stats[i][k][z];
      }
    }
    for (const k of keys.concat(['tilt'])) res[k] = res[k].map((v) => v / N);
    res.possession = possTime.map((v) => v / N);
    for (const k of ['shotZones', 'xgZones', 'regainZones', 'touchZones']) res[k] = res[k].map((arr) => arr.map((v) => v / N));
    res.possLen = res.possActs.map((v, i) => v / Math.max(res.poss[i], 1e-9));
    res.longShare = res.longPoss.map((v, i) => v / Math.max(res.poss[i], 1e-9));
    res.shotsTShare = res.shotsT.map((v, i) => v / Math.max(res.shots[i], 1e-9));
    res.regainHighShare = res.regainsHigh.map((v, i) => v / Math.max(res.regains[i], 1e-9));
    return res;
  }

  function leagueEntity(model) {
    return { id: 'liga', label: 'Liga promedio', att: model.league, dfn: model.league, shape: null, style: {} };
  }

  /* ================================================================ coreografía (solo visual) */
  const V_RUN = 7.6, V_JOG = 4.2, V_GK = 5.5, V_CARRY = 6.2, V_PASS = 21, V_SHOT = 34;
  const TEN = 10.3;     // 10 yardas (las coordenadas StatsBomb están en yardas)
  const CORNER_PTS = [null, [115.5, 35], [115.5, 40], [114.5, 46], [108, 40], [99, 40]];   // primer palo, área chica, segundo palo, punto penal, borde
  const PEN_Y = [37.2, 40, 42.8];

  function choreograph(model, teams, sim, seed) {
    const rnd = mulberry32(((seed || 1) * 2654435761) >>> 0);
    const shapes = teams.map((e) => e.shape);
    const nP = [shapes[0].length, shapes[1].length];
    const isGK = (ti, j) => shapes[ti][j].pos === 'Goalkeeper';
    const isBack = (ti, j) => /Back/.test(shapes[ti][j].pos);
    const gkIdx = shapes.map((s) => Math.max(0, s.findIndex((p) => p.pos === 'Goalkeeper')));
    const actors = teams.map((e) => e.actors || null);
    const roles = teams.map((e) => e.roles || {});
    const sty = teams.map((e) => {
      const s = e.style || {};
      const line = s.linea == null ? 50 : s.linea, vol = s.volumen_presion == null ? 50 : s.volumen_presion;
      return { pressRadius: 7 + 11 * vol / 100, pressReach: 40 + 70 * (0.5 * line + 0.5 * vol) / 100, blockK: 0.22 + 0.28 * line / 100, second: vol >= 62 };
    });
    // marcos: el equipo 0 ataca a la derecha (pantalla = propio); el 1 a la izquierda (pantalla = espejo)
    const toD = (ti, p) => (ti === 0 ? [p[0], p[1]] : [120 - p[0], 80 - p[1]]);
    const toO = toD;
    const zrect = (ti, zz) => {
      const c = colOf(zz), r = rowOf(zz);
      const a = toD(ti, [c * 20, r * 80 / 3]), b = toD(ti, [(c + 1) * 20, (r + 1) * 80 / 3]);
      return [Math.min(a[0], b[0]), Math.min(a[1], b[1]), Math.max(a[0], b[0]), Math.max(a[1], b[1])];
    };
    const inRect = (p, R, m) => [clamp(p[0], R[0] + m, R[2] - m), clamp(p[1], R[1] + m, R[3] - m)];
    const dist = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1]);
    const toward = (a, b, d) => { const L = dist(a, b); if (L <= d || L === 0) return [b[0], b[1]]; return [a[0] + (b[0] - a[0]) * d / L, a[1] + (b[1] - a[1]) * d / L]; };
    const clampPitch = (p) => [clamp(p[0], 0.8, 119.2), clamp(p[1], 0.8, 79.2)];
    const goalX = (ti) => (ti === 0 ? 120 : 0);
    const ownGoalX = (ti) => (ti === 0 ? 0 : 120);
    const off = [new Set(), new Set()];
    const exitPt = (ti, j) => [52 + j * 1.6 + ti * 18, ti === 0 ? -2.6 : 82.6];
    const isOff = (ti, j) => off[ti].has(j);
    const onPitch = (ti) => [...Array(nP[ti]).keys()].filter((j) => !off[ti].has(j));

    let pos = [shapes[0].map(() => [0, 0]), shapes[1].map(() => [0, 0])];
    let tCur = 0;
    const frames = [], balls = [], toasts = [], feed = [], dead = [], phases = [], cards = [], sentOff = [];
    let carrier = null, ball = [60, 40];
    const snap = () => { const P = new Float32Array(44); for (let ti = 0; ti < 2; ti++) for (let j = 0; j < nP[ti]; j++) { P[(ti * 11 + j) * 2] = pos[ti][j][0]; P[(ti * 11 + j) * 2 + 1] = pos[ti][j][1]; } return P; };
    const name = (ti, j) => (j == null || j < 0 ? 'un jugador' : `${shapes[ti][j].num != null ? '#' + shapes[ti][j].num + ' ' : ''}${shapes[ti][j].name}`);
    function minute(t) {
      if (t < HALF) { const m = Math.floor(t / 60); return m >= 45 ? `45+${m - 44}'` : `${m + 1}'`; }
      const m = 45 + Math.floor((t - HALF) / 60); return m >= 90 ? `90+${m - 89}'` : `${m + 1}'`;
    }
    const fixOff = (T) => { for (let ti = 0; ti < 2; ti++) for (const j of off[ti]) T[ti][j] = exitPt(ti, j); return T; };

    function kickoffShape(ti, kicking) {
      const P0 = shapes[ti].map((s, j) => {
        if (off[ti].has(j)) return exitPt(ti, j);
        if (s.pos === 'Goalkeeper') return toD(ti, [3, 40]);
        let x = clamp(s.sin[0] * 0.95, 8, 52), y = s.sin[1];
        if (!kicking) { const d = Math.hypot(x - 60, y - 40); if (d < 10.8) { const k = 10.8 / Math.max(d, 0.1); x = 60 + (x - 60) * k; y = 40 + (y - 40) * k; } x = Math.min(x, 59); }
        return toD(ti, [x, y]);
      });
      if (kicking) {
        let kj = -1, bd = 1e9;
        shapes[ti].forEach((s, j) => { if (s.pos === 'Goalkeeper' || off[ti].has(j)) return; const d = Math.hypot(P0[j][0] - 60, P0[j][1] - 40) - (s.con[0] > 70 ? 15 : 0); if (d < bd) { bd = d; kj = j; } });
        if (kj >= 0) P0[kj] = [ti === 0 ? 59 : 61, 40];
      }
      return P0;
    }
    function offsideLine(ti) {
      // en el marco del atacante: x del penúltimo rival en el campo (portero incluido), al menos medio campo
      const xs = onPitch(1 - ti).map((j) => toO(ti, pos[1 - ti][j])[0]).sort((a, b) => b - a);
      return Math.max(xs[1] == null ? 60 : xs[1], 60);
    }
    function shapeTargets(ctx) {
      const T = [[], []];
      for (let ti = 0; ti < 2; ti++) {
        const ob = toO(ti, ctx.ball);
        for (let j = 0; j < nP[ti]; j++) {
          const s = shapes[ti][j];
          let x, y;
          if (ti === ctx.poss) {
            if (isGK(ti, j)) { x = clamp(8 + 0.2 * (ob[0] - 20), 4, 26); y = 40 + 0.15 * (ob[1] - 40); }
            else {
              x = s.con[0] + clamp(0.5 * (ob[0] - 55), -24, 22);
              y = s.con[1] + clamp(0.2 * (ob[1] - 40), -7, 7);
              if (ctx.ph === 1 && s.con[0] >= 60) { x += 12; y += (s.con[1] - 40) * 0.15; }
            }
          } else {
            const k = sty[ti].blockK;
            if (isGK(ti, j)) { x = clamp(3 + 0.07 * ob[0], 2, 14); y = 40 + 0.22 * (ob[1] - 40); }
            else {
              x = s.sin[0] + clamp(k * (ob[0] - 48), -17, 20);
              y = s.sin[1] + clamp(0.38 * (ob[1] - 40), -13, 13);
              if (isBack(ti, j) && ob[0] > 18) x = Math.min(x, ob[0] - 4);
            }
          }
          T[ti][j] = toD(ti, clampPitch([x, y]));
        }
      }
      if (ctx.poss === 0 || ctx.poss === 1) {
        const at = ctx.poss, line = Math.max(offsideLine(at), toO(at, ctx.ball)[0]);
        for (let j = 0; j < nP[at]; j++) {
          if (isGK(at, j) || (ctx.carrier && ctx.carrier[0] === at && ctx.carrier[1] === j)) continue;
          const o = toO(at, T[at][j]);
          if (o[0] > line - 0.6) T[at][j] = toD(at, [line - 0.6, o[1]]);
        }
      }
      if (ctx.carrier) {
        const dt = 1 - ctx.poss, c = pos[ctx.carrier[0]][ctx.carrier[1]];
        const cOwn = toO(dt, c);
        if (cOwn[0] <= sty[dt].pressReach) {
          const order = onPitch(dt).filter((j) => !isGK(dt, j)).sort((a, b) => dist(pos[dt][a], c) - dist(pos[dt][b], c));
          if (order.length && dist(pos[dt][order[0]], c) <= sty[dt].pressRadius * 1.6) T[dt][order[0]] = toward(c, [ownGoalX(dt), 40], 1.8);
          if (sty[dt].second && order.length > 1 && dist(pos[dt][order[1]], c) <= sty[dt].pressRadius * 2) T[dt][order[1]] = toward(c, [ownGoalX(dt), c[1] > 40 ? 30 : 50], 5);
        }
      }
      return fixOff(T);
    }
    // 10 yardas: los rivales se alejan del balón en tiros libres y córners
    function keepAway(T, tm, spot) {
      const R0 = TEN + 0.4;
      for (const j of onPitch(tm)) {
        const p = T[tm][j];
        if (dist(p, spot) >= R0) continue;
        // empuje radial; si la banda lo impide, el punto válido más cercano alrededor del balón
        let ang = Math.atan2(p[1] - spot[1], p[0] - spot[0]), best = null, bd = 1e9;
        for (let k = 0; k < 36; k++) {
          const a = ang + (k % 2 ? 1 : -1) * Math.ceil(k / 2) * (Math.PI / 18);
          const q = [spot[0] + Math.cos(a) * R0, spot[1] + Math.sin(a) * R0];
          if (q[0] < 0.8 || q[0] > 119.2 || q[1] < 0.8 || q[1] > 79.2) continue;
          const dd = dist(q, p);
          if (dd < bd) { bd = dd; best = q; }
          if (k > 2 && best) break;
        }
        if (best) T[tm][j] = best;
      }
      return T;
    }
    function shapeTargetsSP(ti, isCorner, spot, kj, shortHelper) {
      // balón parado: rematadores del equipo (datos) a los mejores puntos del área; dos atacantes cuidan la contra
      const dtm = 1 - ti, T = [[], []];
      const aer = (roles[ti].aerial || []).filter((j) => !off[ti].has(j) && j !== kj);
      const outfield = onPitch(ti).filter((j) => !isGK(ti, j) && j !== kj && j !== shortHelper);
      const rest = outfield.filter((j) => !aer.includes(j)).sort((a, b) => shapes[ti][a].con[0] - shapes[ti][b].con[0]).slice(0, 2);
      const boxSpots = [[110, 39], [108, 44], [112, 34], [106, 36], [113, 47], [104, 41], [109, 50], [103, 31]];
      const order = aer.concat(outfield.filter((j) => !aer.includes(j) && !rest.includes(j)));
      for (let j = 0; j < nP[ti]; j++) if (isGK(ti, j)) T[ti][j] = toD(ti, [16, 40]);
      rest.forEach((j, k) => { T[ti][j] = toD(ti, [58 + 6 * k, k ? 28 : 52]); });
      order.forEach((j, k) => { const b = boxSpots[k % boxSpots.length]; T[ti][j] = toD(ti, [b[0] + (rnd() - 0.5) * 2, b[1] + (rnd() - 0.5) * 2]); });
      if (kj >= 0 && spot) T[ti][kj] = spot;
      if (shortHelper >= 0 && spot) { const so = toO(ti, spot); T[ti][shortHelper] = toD(ti, [111, so[1] < 40 ? 9 : 71]); }
      const defSpots = [[6, 36], [6, 44], [9, 33], [10, 40], [9, 47], [13, 36], [13, 44], [16, 40], [4, 30], [15, 30]];
      const fw = onPitch(dtm).filter((j) => !isGK(dtm, j)).sort((a, b) => shapes[dtm][b].con[0] - shapes[dtm][a].con[0]);
      let k = 0;
      for (let j = 0; j < nP[dtm]; j++) {
        if (off[dtm].has(j)) continue;
        if (isGK(dtm, j)) T[dtm][j] = toD(dtm, [1, 40]);
        else if (j === fw[0]) T[dtm][j] = toD(dtm, [30, 40]);
        else { const b = defSpots[k++ % defSpots.length]; T[dtm][j] = toD(dtm, [b[0], b[1]]); }
      }
      if (!isCorner && spot) {
        // barrera a 10 yardas en la línea balón-centro de la portería; portero hacia el palo descubierto
        const o = toO(dtm, spot), dx = 0 - o[0], dy = 40 - o[1], L2 = Math.hypot(dx, dy) || 1;
        const wc = [o[0] + dx * TEN / L2, o[1] + dy * TEN / L2];
        const nWall = L2 < 25 ? 4 : (o[1] < 22 || o[1] > 58 ? 2 : 3);
        const px = -dy / L2, py = dx / L2;
        fw.slice(1, 1 + nWall).forEach((j, w) => { const off2 = (w - (nWall - 1) / 2) * 1.3; T[dtm][j] = toD(dtm, [wc[0] + px * off2, wc[1] + py * off2]); });
        const gk = gkIdx[dtm];
        if (!off[dtm].has(gk)) T[dtm][gk] = toD(dtm, [1.2, 40 + (o[1] < 40 ? 2.5 : -2.5)]);
      }
      if (spot) keepAway(T, dtm, spot);
      return fixOff(T);
    }
    function goalKickTargets(ti, spot, caught) {
      // equipo que saca: centrales abiertos en el borde del área, laterales pegados a la banda,
      // medios bajan a ofrecer línea de pase. Rival: fuera del área; alto si presiona, medio si no.
      const dtm = 1 - ti, T = [[], []], so = toO(ti, spot);
      const cbs = [];
      for (let j = 0; j < nP[ti]; j++) {
        const s = shapes[ti][j];
        if (isGK(ti, j)) { T[ti][j] = toD(ti, so); continue; }
        if (/Center Back/.test(s.pos) && !off[ti].has(j)) { cbs.push(j); continue; }
        let x, y;
        if (/(Right|Left) (Back|Wing Back)/.test(s.pos)) { x = 24 + Math.max(0, s.con[0] - 50) * 0.4; y = s.con[1] < 40 ? 5 : 75; }
        else if (/Defensive Midfield/.test(s.pos)) { x = 27; y = 40 + (s.con[1] - 40) * 0.8; }
        else { x = clamp(s.con[0] - 20, 30, 78); y = s.con[1]; }
        T[ti][j] = toD(ti, [x, y]);
      }
      cbs.sort((a, b) => shapes[ti][a].con[1] - shapes[ti][b].con[1]);
      const ys = cbs.length <= 1 ? [40] : cbs.length === 2 ? [21, 59] : [20, 40, 60];
      cbs.forEach((j, k) => { const y = ys[Math.min(k, ys.length - 1)]; T[ti][j] = toD(ti, [y === 40 ? 16 : 12, y]); });
      const high = !caught && (sty[dtm].second || sty[dtm].pressReach >= 95);
      for (let j = 0; j < nP[dtm]; j++) {
        const s = shapes[dtm][j];
        let x, y;
        if (isGK(dtm, j)) { x = high ? 14 : 6; y = 40; }
        else {
          const fwd = s.sin[0] >= 55;
          if (high) { x = fwd ? 99 : s.sin[0] + 22; y = fwd ? 40 + (s.sin[1] - 40) * 1.6 : s.sin[1]; }
          else { x = fwd ? s.sin[0] + 14 : s.sin[0] + 6; y = s.sin[1]; }
          if (x > 100.5 && y > 17 && y < 63) x = 100.5;      // nadie del rival dentro del área
          x = clamp(x, 6, 104); y = clamp(y, 3, 77);
        }
        T[dtm][j] = toD(dtm, [x, y]);
      }
      return fixOff(T);
    }
    function stepTo(tEnd, T, forced, jog) {
      tEnd = Math.max(tEnd, tCur);
      const dt = tEnd - tCur;
      for (let ti = 0; ti < 2; ti++) for (let j = 0; j < nP[ti]; j++) {
        const v = isGK(ti, j) ? V_GK : (jog ? V_JOG : V_RUN);
        pos[ti][j] = toward(pos[ti][j], T[ti][j], v * dt);
      }
      if (forced) for (const [ti, j, p] of forced) if (j >= 0) pos[ti][j] = [p[0], p[1]];
      tCur = tEnd;
      frames.push({ t: tEnd, P: snap() });
    }
    const reach = (ti, j, q, dt, v) => toward(pos[ti][j], q, (v || V_RUN) * Math.max(dt, 0.05) * 0.97);
    function pickReceiver(ti, zz, exclude, T, onside) {
      const R = zrect(ti, zz);
      const line = onside ? Math.max(offsideLine(ti), toO(ti, ball)[0]) + 0.3 : 1e9;
      const share = actors[ti] ? actors[ti][zz] : null;
      const ws = [];
      let best = -1, bw = -1;
      for (let j = 0; j < nP[ti]; j++) {
        if (j === exclude || off[ti].has(j) || (isGK(ti, j) && colOf(zz) > 0) || toO(ti, pos[ti][j])[0] > line) { ws.push(0); continue; }
        const p = T ? T[ti][j] : pos[ti][j];
        const dx = Math.max(R[0] - p[0], 0, p[0] - R[2]), dy = Math.max(R[1] - p[1], 0, p[1] - R[3]);
        const w = (share ? share[j] + 0.02 : 1) * Math.exp(-Math.hypot(dx, dy) / 11);
        ws.push(w); if (w > bw) { bw = w; best = j; }
      }
      const tot = sum(ws);
      if (tot <= 0) return best >= 0 ? best : onPitch(ti).find((j) => j !== exclude && !isGK(ti, j));
      return sampleRow(ws.map((w) => w / tot), rnd());
    }
    function nearest(ti, p, filter) {
      let bj = -1, bd = 1e9;
      for (let j = 0; j < nP[ti]; j++) { if (off[ti].has(j) || (filter && !filter(j))) continue; const d = dist(pos[ti][j], p); if (d < bd) { bd = d; bj = j; } }
      return bj;
    }
    const role = (ti, key, fallback) => { const j = roles[ti][key]; return j != null && !off[ti].has(j) ? j : fallback(); };
    function addBall(t0, t1, from, to, travel, owner, kind, loft, ctrl) {
      balls.push({ t0, t1, from: [from[0], from[1]], to: [to[0], to[1]], travel, owner, kind, loft: !!loft, ctrl: ctrl || null });
      ball = [to[0], to[1]];
    }
    const toast = (t, text, team, dur) => toasts.push({ t, text, team, dur: dur || 3 });
    const setDead = (t0, t1) => { if (t1 > t0 + 0.5) dead.push([t0, t1]); };
    const CARD_TXT = { yellow: 'Amarilla', second: 'Segunda amarilla: expulsado', red: 'Roja directa' };
    function book(t, ft, slot, card, why) {
      if (!card || slot == null || slot < 0) return;
      cards.push({ t, team: ft, slot, card });
      toast(t, `${CARD_TXT[card]} para ${name(ft, slot)}${why ? ' ' + why : ''}`, ft, 3.5);
      feed.push({ t, team: ft, type: 'card', card, text: `${CARD_TXT[card]} para ${name(ft, slot)}${why ? ' ' + why : ''}` });
      if (card === 'red' || card === 'second') { off[ft].add(slot); sentOff.push({ t, team: ft, slot }); }
    }
    // centro con efecto: punto de control de la curva (abierto o cerrado)
    function curveCtrl(from, to, ti, tech) {
      const mid = [(from[0] + to[0]) / 2, (from[1] + to[1]) / 2];
      const gx = goalX(ti), toward = gx > 60 ? 1 : -1;
      if (tech === 2) return null;                             // recto
      const k = tech === 0 ? 7 : -7;                           // cerrado (hacia portería) / abierto (hacia afuera)
      return [mid[0] + toward * k, mid[1]];
    }
    function tackle(t, ft, fj, victim, dur) {
      // el infractor llega al jugador con balón: falta
      const vpos = victim ? pos[victim[0]][victim[1]] : ball;
      const T = shapeTargets({ poss: 1 - ft, ball: vpos, ph: 0, carrier: victim });
      if (fj >= 0) T[ft][fj] = toward(vpos, [ownGoalX(ft), 40], 1.2);
      stepTo(t + dur, T, fj >= 0 ? [[ft, fj, reach(ft, fj, toward(vpos, [ownGoalX(ft), 40], 1.2), dur)]] : null);
    }
    function shootTo(ti, from, outcome, place, t0, tEnd) {
      const dtm = 1 - ti, kgk = gkIdx[dtm], gx = goalX(ti), sgn = ti === 0 ? 1 : -1;
      const gkp = pos[dtm][kgk];
      let target;
      if (outcome === 'goal') target = [gx + 1.6 * sgn, place != null ? toD(ti, [0, PEN_Y[place]])[1] : 37.6 + rnd() * 4.8];
      else if (outcome === 'wide') target = [gx + 2.5 * sgn, rnd() < 0.5 ? 33 + rnd() * 3 : 44 + rnd() * 3];
      else if (outcome === 'parried') target = [gx + 1.0 * sgn, rnd() < 0.5 ? 31 : 49];
      else if (outcome === 'saved') target = toward(gkp, [gx - 1.2 * sgn, clamp(gkp[1] + (rnd() - 0.5) * 3, 36.5, 43.5)], V_GK * 0.5);
      else target = toward(from, [gx, 40], 4);
      const travel = clamp(dist(from, target) / V_SHOT, 0.25, 0.8);
      return { target, travel };
    }

    const L = sim.log;
    pos = [kickoffShape(0, sim.first === 0), kickoffShape(1, sim.first === 1)];
    frames.push({ t: 0, P: snap() });
    let possTeam = sim.first, ph = 0, lastShot = null;
    for (let i = 0; i < L.length; i++) {
      const e = L[i], nx = L[i + 1], tEnd = nx ? nx.t : e.t + 1;
      const dt = Math.max(0.05, tEnd - e.t);
      if (e.t > tCur + 1e-6) stepTo(e.t, shapeTargets({ poss: possTeam, ball, ph, carrier }), null, true);
      const cur = () => (carrier && carrier[0] === e.team && !off[e.team].has(carrier[1]) ? carrier : null);
      switch (e.k) {
        case 'kickoff': {
          possTeam = e.team; ph = 0;
          const ko = [kickoffShape(0, e.team === 0), kickoffShape(1, e.team === 1)];
          let taker = 0, bd0 = 1e9;
          ko[e.team].forEach((p, j) => { if (off[e.team].has(j)) return; const d = Math.hypot(p[0] - 60, p[1] - 40); if (d < bd0) { bd0 = d; taker = j; } });
          if (e.t === 0 || (i > 0 && L[i - 1].k === 'ht')) { pos = ko.map((a) => a.map((p) => [p[0], p[1]])); tCur = Math.max(tCur, e.t); frames.push({ t: tCur, P: snap() }); }
          carrier = [e.team, taker];
          addBall(e.t, e.t, [60, 40], [60, 40], 0, carrier, 'kickoff');
          phases.push({ t: e.t, team: e.team, label: 'Saque inicial' });
          stepTo(Math.min(tEnd, e.t + 0.4), ko, [[e.team, taker, [60, 40]]]);
          break;
        }
        case 'pass': case 'carry': {
          const want = e.ph === 1 ? 'Transición' : 'Ataque elaborado';
          const lastP = phases[phases.length - 1];
          if (e.ph !== ph || e.team !== possTeam || !lastP || lastP.label !== want || lastP.team !== e.team) { ph = e.ph; possTeam = e.team; phases.push({ t: e.t, team: e.team, label: want }); }
          const ti = e.team, c0 = cur();
          const cj = c0 ? c0[1] : pickReceiver(ti, e.z, -1, null);
          const from = c0 ? pos[ti][cj] : ball;
          const R2 = zrect(ti, e.z2);
          if (e.k === 'carry') {
            let q;
            const fo = toO(ti, from);
            if (e.z2 === e.z) q = inRect(toD(ti, [fo[0] + 4 + 5 * rnd(), fo[1] + (rnd() - 0.5) * 6]), R2, 1.2);
            else q = inRect([from[0] + (rnd() - 0.5) * 4, from[1] + (rnd() - 0.5) * 4], R2, 2);
            q = toward(from, q, V_CARRY * dt);
            addBall(e.t, tEnd, from, q, dt, [ti, cj], 'carry');
            stepTo(tEnd, shapeTargets({ poss: ti, ball: q, ph: e.ph, carrier: [ti, cj] }), [[ti, cj, q]]);
            carrier = [ti, cj];
          } else {
            const T0 = shapeTargets({ poss: ti, ball: [(R2[0] + R2[2]) / 2, (R2[1] + R2[3]) / 2], ph: e.ph, carrier: [ti, cj] });
            const rj = pickReceiver(ti, e.z2, cj, T0, true);
            let q = inRect([T0[ti][rj][0] + (rnd() - 0.5) * 5, T0[ti][rj][1] + (rnd() - 0.5) * 5], R2, 1.5);
            q = reach(ti, rj, q, dt);
            const d = dist(from, q), travel = clamp(d / V_PASS, 0.3, dt * 0.85);
            addBall(e.t, tEnd, from, q, travel, [ti, rj], 'pass', d > 30);
            stepTo(tEnd, shapeTargets({ poss: ti, ball: q, ph: e.ph, carrier: [ti, rj] }), [[ti, rj, q]]);
            carrier = [ti, rj];
          }
          break;
        }
        case 'shot': case 'spshot': case 'pen': {
          const ti = e.team, dtm = 1 - ti, kgk = gkIdx[dtm];
          let sj, from, t0 = e.t, label = 'Tiro';
          if (e.k === 'shot') {
            const c0 = cur();
            sj = c0 ? c0[1] : pickReceiver(ti, e.z, -1, null);
            from = pos[ti][sj];
          } else if (e.k === 'pen') {
            sj = role(ti, 'pen', () => pickReceiver(ti, BOX_CENTER, gkIdx[ti], null));
            const spot = toD(ti, [108, 40]);
            const T = [[], []];
            for (let tj = 0; tj < 2; tj++) for (let j = 0; j < nP[tj]; j++) {
              if (tj === ti && j === sj) T[tj][j] = toD(ti, [105.5, 40]);
              else if (tj === dtm && j === kgk) T[tj][j] = toD(dtm, [0.6, 40]);
              else { const a = toO(ti, pos[tj][j]); T[tj][j] = toD(ti, [Math.min(a[0], 97), a[1]]); }
            }
            fixOff(T);
            t0 = e.t + Math.max(1, dt - 1.6);
            setDead(e.t, t0 - 1.2);
            addBall(e.t, t0, ball, spot, 0.01, null, 'place');
            stepTo(t0 - 0.5, T, null, true);
            stepTo(t0, T, [[ti, sj, toD(ti, [106.5, 40])]], true);
            from = spot; label = 'Penal';
          } else {
            const isCorner = e.spk === 'corner';
            const inBox = onPitch(ti).filter((j) => !isGK(ti, j) && !(carrier && carrier[0] === ti && carrier[1] === j) && toO(ti, pos[ti][j])[0] > 100);
            const aer = (roles[ti].aerial || []).filter((j) => inBox.includes(j));
            const tgtPt = isCorner ? deliveryPoint(ti, e.target) : null;
            const pool = aer.length ? aer : inBox;
            sj = pool.length ? (tgtPt ? pool.slice().sort((a, b) => dist(pos[ti][a], tgtPt) - dist(pos[ti][b], tgtPt))[0] : pool[Math.floor(rnd() * pool.length)]) : pickReceiver(ti, BOX_CENTER, gkIdx[ti], null);
            if (isCorner || !e.direct) {
              let fromC = ball, tC = e.t + 0.9;
              if (isCorner && e.short) {   // córner en corto: pase al compañero y centro desde ahí
                const helper = nearest(ti, ball, (j) => !isGK(ti, j) && !(carrier && carrier[1] === j && carrier[0] === ti));
                const hp = pos[ti][helper];
                addBall(e.t, e.t + 0.7, ball, hp, 0.6, [ti, helper], 'pass');
                stepTo(e.t + 0.7, shapeTargetsSP(ti, true, null, -1, -1), [[ti, helper, hp]]);
                fromC = hp; tC = e.t + 1.6;
              }
              const hp = reach(ti, sj, tgtPt ? [tgtPt[0] + (rnd() - 0.5) * 2, tgtPt[1] + (rnd() - 0.5) * 2] : [pos[ti][sj][0] + (rnd() - 0.5) * 3, pos[ti][sj][1] + (rnd() - 0.5) * 3], tC - tCur);
              addBall(tCur, tC, fromC, hp, tC - tCur, [ti, sj], 'cross', true, curveCtrl(fromC, hp, ti, e.tech == null ? 1 : e.tech));
              stepTo(tC, shapeTargetsSP(ti, isCorner, null, -1, -1), [[ti, sj, hp]]);
              from = hp; t0 = tC; label = e.header ? 'Cabezazo' : 'Remate';
            } else {
              sj = carrier && carrier[0] === ti ? carrier[1] : role(ti, 'fk', () => sj);
              from = ball; label = 'Tiro libre directo';
            }
          }
          e._shotT = t0;
          const nk = nx ? nx.k : 'end';
          let outcome;
          if (e.k === 'pen') outcome = e.goal ? 'goal' : (e.miss ? 'wide' : 'saved');
          else outcome = e.goal ? 'goal' : (nk === 'sp' ? (rnd() < 0.6 ? 'parried' : 'blocked') : (rnd() < 0.55 ? 'saved' : 'wide'));
          let { target, travel } = shootTo(ti, from, outcome, e.k === 'pen' ? e.place : null, t0, tEnd);
          if (e.k === 'pen' && outcome === 'saved') target = toD(ti, [118.8, PEN_Y[e.place]]);
          let ctrl = null;
          if (e.k === 'spshot' && e.direct) {  // falta directa: el balón pasa por encima/alrededor de la barrera
            const mid = [(from[0] + target[0]) / 2, (from[1] + target[1]) / 2];
            ctrl = [mid[0], mid[1] + (from[1] < 40 ? 6 : -6)];
          }
          const tShotEnd = Math.min(tEnd, t0 + travel + 0.05);
          addBall(t0, tEnd, from, target, travel, outcome === 'saved' ? [dtm, kgk] : null, 'shot', e.k === 'spshot' && e.direct, ctrl);
          const T = shapeTargets({ poss: ti, ball: from, ph: e.ph || 0, carrier: null });
          if (e.k === 'pen') {   // estirada del portero hacia el lado elegido
            for (let tj = 0; tj < 2; tj++) for (let j = 0; j < nP[tj]; j++) T[tj][j] = pos[tj][j];
            T[dtm][kgk] = toD(ti, [119.4, PEN_Y[e.dive]]);
          } else T[dtm][kgk] = outcome === 'saved' ? target : [goalX(ti) - 1.2 * (ti === 0 ? 1 : -1), clamp(target[1], 37, 43)];
          stepTo(tShotEnd, T, outcome === 'saved' ? [[dtm, kgk, target]] : (e.k === 'pen' ? [[dtm, kgk, toD(ti, [119.4, PEN_Y[e.dive]])]] : null));
          const who = name(ti, sj);
          const how = { saved: 'atajada', wide: 'desviado', parried: 'atajada a córner', blocked: 'bloqueado', goal: '' }[outcome];
          lastShot = { ti, sj, outcome };
          if (e.k === 'pen') {
            const side = ['a la izquierda', 'al centro', 'a la derecha'][e.place];
            const txt = e.goal ? `Penal convertido por ${who}, ${side}` : (e.miss ? `Penal fallado por ${who}` : `Penal atajado por ${name(dtm, kgk)}`);
            toast(t0, txt, e.goal ? ti : dtm, 4);
            feed.push({ t: t0, team: ti, type: 'pen', text: txt, xg: e.xg, goal: e.goal });
          } else if (e.goal) toast(t0, `¡GOL! ${who}`, ti, 6);
          else toast(t0, `${label} de ${who}: ${how}`, ti, 3);
          if (e.k !== 'pen' && !e.goal && e.xg >= 0.15) feed.push({ t: t0, team: ti, type: 'chance', text: `Ocasión de ${who}${e.k === 'spshot' ? (e.spk === 'corner' ? ' tras córner' : ' de tiro libre') : e.ph === 1 ? ' al contragolpe' : ''}: ${how}`, xg: e.xg });
          carrier = outcome === 'saved' ? [dtm, kgk] : null;
          if (tEnd > tShotEnd + 0.05) stepTo(tEnd, shapeTargets({ poss: ti, ball: target, ph: 0, carrier: null }), null, true);
          break;
        }
        case 'goal': {
          const ti = e.team, sj = lastShot && lastShot.ti === ti ? lastShot.sj : 0;
          feed.push({ t: e.t, team: ti, type: 'goal', text: `GOL de ${name(ti, sj)}`, kind: e.kind, xg: e.xg, score: e.score });
          setDead(e.t + 1, tEnd - 2);
          const tCel = e.t + Math.min(9, dt * 0.35);
          const cel = toD(ti, [110, toO(ti, pos[ti][sj])[1] < 40 ? 10 : 70]);
          const T1 = [pos[0].map((p) => [p[0], p[1]]), pos[1].map((p) => [p[0], p[1]])];
          for (const j of onPitch(ti)) if (!isGK(ti, j)) T1[ti][j] = j === sj ? cel : [cel[0] + (rnd() - 0.5) * 8, cel[1] + (rnd() - 0.5) * 8];
          stepTo(tCel, fixOff(T1), null, false);
          stepTo(tEnd, [kickoffShape(0, ti !== 0), kickoffShape(1, ti !== 1)], null, true);
          carrier = null;
          break;
        }
        case 'gk': {
          // saque de meta (o portero que atrapó): el balón sale, se repone en el área chica,
          // todos trotan a su sitio en unos segundos y esperan; el portero saca
          const ti = e.team, gj = gkIdx[ti];
          const caught = lastShot && lastShot.outcome === 'saved';
          goalKick(e, ti, gj, caught, tEnd, dt);
          lastShot = null;
          break;
        }
        case 'lossO': {
          const ti = e.team, nt = 1 - ti, c0 = cur();
          const from = c0 ? pos[ti][c0[1]] : ball;
          const R2 = zrect(nt, e.z2);
          let q = inRect([from[0] + (rnd() - 0.5) * 6, from[1] + (rnd() - 0.5) * 6], R2, 1.5);
          const rj = nearest(nt, q, (j) => !(isGK(nt, j) && colOf(e.z2) > 0));
          q = reach(nt, rj, q, dt);
          const d = dist(from, q), travel = clamp(d / V_PASS, 0.2, dt * 0.9);
          addBall(e.t, tEnd, from, q, travel, [nt, rj], d > 6 ? 'intercept' : 'tackle', d > 30);
          toast(e.t, `${d > 6 ? 'Intercepta' : 'Roba'} ${name(nt, rj)}`, nt, 2.2);
          possTeam = nt; ph = 1; carrier = [nt, rj];
          phases.push({ t: e.t, team: nt, label: 'Transición' });
          stepTo(tEnd, shapeTargets({ poss: nt, ball: q, ph: 1, carrier: [nt, rj] }), [[nt, rj, q]]);
          break;
        }
        case 'throw': case 'lossX': case 'foul': {
          // reanudaciones: saque de banda (a favor o en contra), saque de meta rival, tiro libre (falta o fuera de juego)
          const ti = e.team, c0 = cur(), cj = c0 ? c0[1] : null;
          const from = c0 ? pos[ti][cj] : ball;
          const nt = e.k === 'lossX' ? 1 - ti : ti;
          const kind = e.k === 'throw' ? 'throw' : (e.k === 'foul' ? 'fk' : e.out);
          if (kind === 'gk') { goalKickFromOut(e, ti, nt, from, tEnd, dt); break; }
          let spot, out, label;
          if (kind === 'throw') {
            const R2 = zrect(nt, e.z2), r2 = rowOf(e.z2);
            const sideTop = r2 === 0 ? toD(nt, [0, 0])[1] < 40 : r2 === 2 ? toD(nt, [0, 80])[1] < 40 : from[1] < 40;
            const xo = clamp((R2[0] + R2[2]) / 2 + (rnd() - 0.5) * 10, 3, 117);
            spot = [xo, sideTop ? 0.3 : 79.7]; out = [xo, sideTop ? -1.2 : 81.2];
            label = e.k === 'throw' ? `Saque de banda para ${short(teams[nt])}` : 'Saque de banda';
          } else {
            spot = inRect(from, zrect(nt, e.z2), 1); out = spot;
            const ft = e.k === 'foul' ? 1 - ti : ti;
            if (e.offside) label = `Fuera de juego de ${name(ti, mostAdvanced(ti))}`;
            else label = `Falta de ${name(ft, e.fouler)}${e.k === 'foul' && cj != null ? ' sobre ' + name(ti, cj) : ''}`;
          }
          // el momento de la infracción / salida
          if (kind === 'fk' && !e.offside) {
            const ft = e.k === 'foul' ? 1 - ti : ti;
            const victim = e.k === 'foul' ? (c0 || null) : nearestOpp(ti, from);
            tackle(e.t, ft, ft === ti ? (e.fouler >= 0 ? e.fouler : cj) : e.fouler, victim, Math.min(0.8, dt * 0.2));
            addBall(e.t, e.t + 0.8, from, from, 0, null, 'stop');
            book(e.t + 1, ft, e.fouler, e.card);
          } else {
            const travel = clamp(dist(from, out) / V_PASS, 0.2, 1.6);
            addBall(e.t, e.t + travel + 0.05, from, out, travel, null, 'out');
            stepTo(Math.min(tEnd - 0.1, e.t + travel + 0.05), shapeTargets({ poss: ti, ball: out, ph: 0, carrier: null }), null);
          }
          toast(e.t, label, nt, 2.6);
          const tj = nearest(nt, spot, (j) => !isGK(nt, j) || (kind === 'fk' && toO(nt, spot)[0] < 18));
          setDead(e.t + 1, tEnd - 1.2);
          const Tr = shapeTargets({ poss: nt, ball: spot, ph: 0, carrier: null });
          Tr[nt][tj] = spot;
          if (kind === 'fk') keepAway(Tr, 1 - nt, spot);
          addBall(tEnd - 0.6, tEnd, out, spot, 0.01, [nt, tj], 'place');
          possTeam = nt; ph = 0; carrier = [nt, tj];
          phases.push({ t: e.t, team: nt, label: kind === 'throw' ? 'Saque de banda' : 'Tiro libre' });
          stepTo(tEnd - 0.6, Tr, null, false);
          stepTo(tEnd, Tr, [[nt, tj, spot]], true);
          break;
        }
        case 'spwon': {
          const ti = e.team, c0 = cur();
          const from = c0 ? pos[ti][c0[1]] : ball;
          if (e.spk === 'fk') {
            tackle(e.t, 1 - ti, e.fouler, c0, Math.min(0.8, dt * 0.6));
            toast(e.t, `Falta de ${name(1 - ti, e.fouler)}${c0 ? ' sobre ' + name(ti, c0[1]) : ''}`, ti, 2.4);
            phases.push({ t: e.t, team: ti, label: 'Falta' });
            book(e.t + 0.8, 1 - ti, e.fouler, e.card);
          } else stepTo(Math.min(tEnd, e.t + 0.8), shapeTargets({ poss: ti, ball: from, ph: e.ph, carrier: c0 }), null);
          addBall(e.t, tEnd, from, from, 0, null, 'stop');
          if (tEnd > tCur + 0.05) stepTo(tEnd, shapeTargets({ poss: ti, ball: from, ph: e.ph, carrier: null }), null, true);
          break;
        }
        case 'penfoul': {
          const ti = e.team, c0 = cur();
          const victim = c0 || [ti, pickReceiver(ti, BOX_CENTER, gkIdx[ti], null)];
          tackle(e.t, 1 - ti, e.fouler, victim, Math.min(0.8, dt * 0.6));
          toast(e.t, `¡Penal! Falta de ${name(1 - ti, e.fouler)} sobre ${name(ti, victim[1])}`, ti, 3.5);
          possTeam = ti; phases.push({ t: e.t, team: ti, label: 'Penal' });
          book(e.t + 0.9, 1 - ti, e.fouler, e.card, '');
          addBall(e.t, tEnd, ball, ball, 0, null, 'stop');
          if (tEnd > tCur + 0.05) stepTo(tEnd, shapeTargets({ poss: ti, ball, ph: 0, carrier: null }), null, true);
          break;
        }
        case 'sp': {
          const ti = e.team, isCorner = e.spk === 'corner';
          const yb = toO(ti, ball)[1];
          let spot;
          if (isCorner) spot = toD(ti, [119.4, yb < 40 ? 0.6 : 79.4]);
          else { const o = toO(ti, ball); spot = toD(ti, [clamp(o[0], 82, 100), clamp(o[1], 15, 65)]); }
          toast(e.t, isCorner ? `Córner para ${short(teams[ti])}${e.short ? ' (en corto)' : ''}` : `Tiro libre peligroso para ${short(teams[ti])}`, ti, 3);
          possTeam = ti; ph = 0;
          phases.push({ t: e.t, team: ti, label: isCorner ? 'Córner' : 'Tiro libre' });
          const kj = role(ti, isCorner ? 'corner' : 'fk', () => pickReceiver(ti, isCorner ? (yb < 40 ? 15 : 17) : 13, gkIdx[ti], null));
          const helper = isCorner && e.short ? onPitch(ti).filter((j) => !isGK(ti, j) && j !== kj && !(roles[ti].aerial || []).includes(j))[0] : -1;
          const T = shapeTargetsSP(ti, isCorner, spot, kj, helper == null ? -1 : helper);
          setDead(e.t + 1, tEnd - 1.5);
          addBall(e.t, tEnd, ball, spot, isCorner ? 1.2 : 0.01, [ti, kj], 'place');
          stepTo(tEnd - 0.5, T, null, false);
          stepTo(tEnd, T, [[ti, kj, spot]], true);
          carrier = [ti, kj];
          break;
        }
        case 'clear': {
          const nt = e.team, ti = 1 - nt;
          let fromC = ball, tC = e.t + 0.9;
          if (e.spk === 'corner' && e.short) {
            const helper = nearest(ti, ball, (j) => !isGK(ti, j) && !(carrier && carrier[0] === ti && carrier[1] === j));
            addBall(e.t, e.t + 0.7, ball, pos[ti][helper], 0.6, [ti, helper], 'pass');
            stepTo(e.t + 0.7, shapeTargetsSP(ti, true, null, -1, -1), null);
            fromC = pos[ti][helper]; tC = e.t + 1.6;
          }
          const tgt = e.spk === 'corner' ? deliveryPoint(ti, e.target) : toD(ti, [108, 40]);
          const cands = onPitch(nt).filter((j) => !isGK(nt, j) && toO(nt, pos[nt][j])[0] < 20);
          const hj = cands.length ? cands.sort((a, b) => dist(pos[nt][a], tgt) - dist(pos[nt][b], tgt))[0] : nearest(nt, tgt, (j) => !isGK(nt, j));
          const hp = reach(nt, hj, [tgt[0] + (rnd() - 0.5) * 3, tgt[1] + (rnd() - 0.5) * 3], tC - tCur);
          addBall(tCur, tC, fromC, hp, tC - tCur, null, 'cross', true, curveCtrl(fromC, hp, ti, e.tech == null ? 1 : e.tech));
          stepTo(tC, shapeTargetsSP(ti, true, null, -1, -1), [[nt, hj, hp]]);
          if (e.toCorner) {   // despeje por la línea de fondo: otro córner
            const outP = toD(ti, [121, hp[1] < 40 === (ti === 0) ? 30 : 50]);
            addBall(tC, tEnd, hp, outP, 0.6, null, 'out', true);
            toast(e.t, `Despeja ${name(nt, hj)} a córner`, nt, 2.2);
            if (tEnd > tCur + 0.05) stepTo(tEnd, shapeTargetsSP(ti, true, null, -1, -1), null, true);
            break;
          }
          const R2 = zrect(nt, CLEAR_ZONE);
          let q = inRect([(R2[0] + R2[2]) / 2 + (rnd() - 0.5) * 10, (R2[1] + R2[3]) / 2 + (rnd() - 0.5) * 14], R2, 2);
          const rj = nearest(nt, q, (j) => !isGK(nt, j) && j !== hj);
          q = reach(nt, rj, q, tEnd - tC);
          addBall(tC, tEnd, hp, q, clamp(dist(hp, q) / V_PASS, 0.4, Math.max(0.4, tEnd - tC)), [nt, rj], 'clear', true);
          toast(e.t, `Despeja ${name(nt, hj)}`, nt, 2.2);
          possTeam = nt; ph = 1; carrier = [nt, rj];
          phases.push({ t: tC, team: nt, label: 'Transición' });
          stepTo(tEnd, shapeTargets({ poss: nt, ball: q, ph: 1, carrier: [nt, rj] }), [[nt, rj, q]]);
          break;
        }
        case 'card': {
          book(e.t, e.team, e.slot, e.card, 'por protestar');
          break;
        }
        case 'ht': {
          toast(e.t, 'Medio tiempo', -1, 4);
          feed.push({ t: e.t, team: -1, type: 'ht', text: 'Medio tiempo' });
          break;
        }
        case 'end': {
          stepTo(Math.max(tEnd, e.t + 0.5), shapeTargets({ poss: possTeam, ball, ph: 0, carrier }), null, true);
          break;
        }
      }
    }
    function short(e) { return e.label.split(' (')[0]; }
    function mostAdvanced(ti) { return onPitch(ti).filter((j) => !isGK(ti, j)).sort((a, b) => toO(ti, pos[ti][b])[0] - toO(ti, pos[ti][a])[0])[0]; }
    function nearestOpp(ti, p) { const j = nearest(1 - ti, p, (k) => !isGK(1 - ti, k)); return j >= 0 ? [1 - ti, j] : null; }
    function deliveryPoint(ti, target) {
      // zona de caída del córner (normalizada para el lado del cobro)
      const pt = CORNER_PTS[target || 4] || CORNER_PTS[4];
      const side = toO(ti, ball)[1] < 40;
      return toD(ti, [pt[0], side ? pt[1] : 80 - pt[1]]);
    }
    function goalKick(e, ti, gj, caught, tEnd, dt) {
      const yOut = toO(ti, ball)[1];
      const spot = caught ? pos[ti][gj] : toD(ti, [5.5, yOut < 40 ? 33 : 47]);
      toast(e.t, caught ? 'Atrapa el portero' : 'Saque de meta', ti, 2.5);
      setDead(e.t + 2, tEnd - 1.2);
      const tPlace = e.t + Math.min(2.5, dt * 0.15), tSet = e.t + Math.min(9, dt * 0.45);
      const T1 = goalKickTargets(ti, spot, caught);
      if (caught) addBall(e.t, tEnd, ball, ball, 0, [ti, gj], 'hold');
      else {
        addBall(e.t, tPlace, ball, ball, 0, null, 'out');
        addBall(tPlace, tSet, ball, spot, 0.9, null, 'place');
        addBall(tSet, tEnd, spot, spot, 0, [ti, gj], 'place');
      }
      possTeam = ti; ph = 0; carrier = [ti, gj];
      phases.push({ t: e.t, team: ti, label: caught ? 'Salida desde el portero' : 'Saque de meta' });
      stepTo(tPlace, T1, null, false);
      const gkAt = caught ? pos[ti][gj] : reach(ti, gj, spot, tSet - tCur, V_GK);
      stepTo(tSet, T1, [[ti, gj, gkAt]], false);
      stepTo(tEnd - 0.4, T1, [[ti, gj, caught ? gkAt : spot]], true);
      stepTo(tEnd, T1, [[ti, gj, caught ? gkAt : spot]], true);
    }
    function goalKickFromOut(e, ti, nt, from, tEnd, dt) {
      // el atacante la manda por la línea de fondo: saque de meta del rival
      const out = toD(nt, [-1.5, 28 + rnd() * 24]);
      const travel = clamp(dist(from, out) / V_PASS, 0.2, 1.6);
      addBall(e.t, e.t + travel + 0.05, from, out, travel, null, 'out');
      stepTo(Math.min(tEnd - 0.1, e.t + travel + 0.05), shapeTargets({ poss: ti, ball: out, ph: 0, carrier: null }), null);
      lastShot = null;
      goalKick({ t: e.t + travel + 0.05 }, nt, gkIdx[nt], false, tEnd, Math.max(0.5, tEnd - e.t - travel));
    }
    // momentos destacados: abre con el saque inicial; cada jugada empieza donde empieza su posesión
    // (en una reanudación, 2 s antes del saque; tras un robo, 3 s antes) y como mucho 22 s antes del remate
    const highlights = [[0, 6]];
    let possStart = 0, pending = false;
    for (let i = 0; i < L.length; i++) {
      const e = L[i];
      if (['kickoff', 'gk', 'lossX', 'sp', 'pen', 'foul', 'throw', 'penfoul'].includes(e.k)) { pending = true; continue; }
      if (e.k === 'lossO') { possStart = e.t - 3; pending = false; continue; }
      if (e.k === 'clear') { possStart = e.t - 1; pending = false; continue; }
      if (pending && (e.k === 'pass' || e.k === 'carry' || e.k === 'shot')) { possStart = e.t - 2; pending = false; }
      if (e.k === 'shot' || e.k === 'spshot' || e.k === 'pen') {
        if (!(e.goal || e.xg >= 0.08 || e.k === 'pen')) continue;
        const ts = e._shotT || e.t;
        const t0 = e.k === 'shot' ? Math.max(possStart, ts - 22) : ts - (e.k === 'pen' ? 5 : 3);
        const t1 = ts + (e.goal ? 9 : 3.5);
        const last = highlights[highlights.length - 1];
        if (t0 <= last[1]) last[1] = Math.max(last[1], t1); else highlights.push([t0, t1]);
        pending = false;
      }
      if (e.k === 'card' || (e.card && (e.card === 'red' || e.card === 'second'))) {
        const last = highlights[highlights.length - 1], t0 = e.t - 2, t1 = e.t + 5;
        if (t0 <= last[1]) last[1] = Math.max(last[1], t1); else if (e.card === 'red' || e.card === 'second') highlights.push([t0, t1]);
      }
    }
    const mom = [new Array(96).fill(0), new Array(96).fill(0)];
    for (const e of L) {
      const m = Math.min(95, Math.floor(e.t / 60));
      if ((e.k === 'pass' || e.k === 'carry') && colOf(e.z2) >= 4) mom[e.team][m] += 0.02;
      if (e.k === 'shot' || e.k === 'spshot' || e.k === 'pen') mom[e.team][m] += e.xg;
    }
    return { frames, balls, toasts, feed: feed.sort((a, b) => a.t - b.t), dead, phases, highlights, momentum: mom, minute, cards, sentOff,
      names: shapes.map((s, ti) => s.map((p, j) => name(ti, j))) };
  }

  /* ---------------------------------------------------------------- lectura de la coreografía */
  function bsearch(arr, t, key) {
    let lo = 0, hi = arr.length - 1;
    if (hi < 0 || t < key(arr[0])) return -1;
    while (lo < hi) { const mid = (lo + hi + 1) >> 1; if (key(arr[mid]) <= t) lo = mid; else hi = mid - 1; }
    return lo;
  }
  function playersAt(ch, t, out) {
    const F = ch.frames, k = Math.max(0, bsearch(F, t, (f) => f.t));
    const a = F[k], b = F[Math.min(k + 1, F.length - 1)];
    const u = b.t > a.t ? clamp((t - a.t) / (b.t - a.t), 0, 1) : 1;
    const s = u * u * (3 - 2 * u), w = 0.35 * u + 0.65 * s;
    const res = out || new Float32Array(44);
    for (let i = 0; i < 44; i++) res[i] = a.P[i] + (b.P[i] - a.P[i]) * w;
    return res;
  }
  function ballAt(ch, t, P) {
    const B = ch.balls, k = bsearch(B, t, (b) => b.t0);
    if (k < 0) return { x: 60, y: 40, h: 0, owner: null, kind: 'kickoff', u: 1 };
    const b = B[k];
    const u = b.travel > 0 ? clamp((t - b.t0) / b.travel, 0, 1) : 1;
    if ((u < 1 && b.kind !== 'carry') || !b.owner) {
      const e = 1 - Math.pow(1 - u, 1.6);
      let x, y;
      if (b.ctrl) {   // trayectoria con efecto (curva de Bézier cuadrática)
        const m = 1 - e;
        x = m * m * b.from[0] + 2 * m * e * b.ctrl[0] + e * e * b.to[0];
        y = m * m * b.from[1] + 2 * m * e * b.ctrl[1] + e * e * b.to[1];
      } else { x = b.from[0] + (b.to[0] - b.from[0]) * e; y = b.from[1] + (b.to[1] - b.from[1]) * e; }
      const h = b.loft ? Math.sin(Math.PI * u) * Math.min(1, Math.hypot(b.to[0] - b.from[0], b.to[1] - b.from[1]) / 40) : 0;
      return { x, y, h, owner: null, kind: b.kind, from: b.from, to: b.to, ctrl: b.ctrl, u, target: b.owner };
    }
    const i = (b.owner[0] * 11 + b.owner[1]) * 2, dir = b.owner[0] === 0 ? 1 : -1;
    return { x: P[i] + 0.9 * dir, y: P[i + 1] + 0.3, h: 0, owner: b.owner, kind: b.kind, u: 1 };
  }

  const api = { simulate, simulateMany, matchup, cardRates, leagueEntity, deadUnit, choreograph, playersAt, ballAt, T_TOTAL, HALF, mulberry32, NZ };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.SimEngine = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
