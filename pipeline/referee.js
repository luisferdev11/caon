// Árbitro automático: simula y coreografía partidos y revisa el reglamento en cada momento relevante.
// uso: node build/referee.js [partidos_por_cruce]
const E = require('../frontend/engine.js');
const model = require('../model/model.json');
const N = +(process.argv[2] || 6);
const ents = model.entities;
const pairs = [];
for (let i = 0; i < ents.length; i++) pairs.push([ents[i], ents[(i + 7) % ents.length]]);
const R = {};
const rule = (k, desc) => (R[k] = R[k] || { desc, checks: 0, bad: 0, ex: [] });
const check = (k, desc, ok, info) => { const r = rule(k, desc); r.checks++; if (!ok) { r.bad++; if (r.ex.length < 3) r.ex.push(info); } };
const own = (ti, p) => (ti === 0 ? [p[0], p[1]] : [120 - p[0], 80 - p[1]]);
const d = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1]);

for (const [A, B] of pairs) for (let s = 1; s <= N; s++) {
  const teams = [A, B];
  const sim = E.simulate(model, teams, { seed: s * 7919 + 13, record: true });
  const ch = E.choreograph(model, teams, sim, s);
  const L = sim.log, tag = `${A.id} vs ${B.id} #${s}`;
  const P = (t) => E.playersAt(ch, t);
  const pl = (Pa, ti, j) => [Pa[(ti * 11 + j) * 2], Pa[(ti * 11 + j) * 2 + 1]];
  const offAt = (ti, j, t) => ch.sentOff.some((x) => x.team === ti && x.slot === j && x.t <= t);
  const onP = (ti, t) => [...Array(teams[ti].shape.length).keys()].filter((j) => !offAt(ti, j, t));
  // 1. reanudación: el primer toque es un pase (sin conducción ni tiro)
  L.forEach((e, i) => {
    if (!['kickoff', 'gk', 'lossX', 'foul', 'throw'].includes(e.k)) return;
    const nx = L.slice(i + 1).find((x) => x.k !== 'card');
    if (!nx || nx.k === 'end' || nx.k === 'ht') return;
    check('reanudacion', 'Las reanudaciones (saque inicial, de meta, de banda, tiro libre) se juegan con un pase',
      ['pass', 'lossO', 'lossX', 'foul', 'throw', 'keepF'].includes(nx.k), `${tag} ${e.k}→${nx.k} t=${e.t.toFixed(0)}`);
  });
  // 2. saque inicial
  L.forEach((e) => {
    if (e.k !== 'kickoff') return;
    const Pa = P(e.t + 0.2);
    for (let ti = 0; ti < 2; ti++) for (const j of onP(ti, e.t)) {
      const p = pl(Pa, ti, j);
      check('saque_inicial_campo', 'Saque inicial: cada equipo en su campo', ti === 0 ? p[0] <= 60.6 : p[0] >= 59.4, `${tag} t=${e.t.toFixed(0)}`);
      if (ti !== e.team) check('saque_inicial_circulo', 'Saque inicial: el rival fuera del círculo central', d(p, [60, 40]) >= 9.8, `${tag} t=${e.t.toFixed(0)} d=${d(p, [60, 40]).toFixed(1)}`);
    }
  });
  // 3. saques de meta: balón en el área y rivales fuera del área
  L.forEach((e, i) => {
    const gk = e.k === 'gk' || (e.k === 'lossX' && e.out === 'gk');
    if (!gk) return;
    const kt = L[i + 1].t - 0.15, tm = e.k === 'gk' ? e.team : 1 - e.team, Pa = P(kt), b = E.ballAt(ch, kt, Pa), bo = own(tm, [b.x, b.y]);
    check('meta_balon', 'Saque de meta: el balón se patea desde dentro del área', bo[0] <= 18.5 && bo[1] >= 17.5 && bo[1] <= 62.5, `${tag} t=${kt.toFixed(0)} balón ${bo.map((v) => v.toFixed(1))}`);
    for (const j of onP(1 - tm, kt)) {
      const p = own(tm, pl(Pa, 1 - tm, j));
      check('meta_rivales', 'Saque de meta: los rivales fuera del área', !(p[0] < 18 && p[1] > 18 && p[1] < 62), `${tag} t=${kt.toFixed(0)}`);
    }
  });
  // 4. tiros libres: rivales a 10 yardas
  L.forEach((e, i) => {
    const fk = e.k === 'foul' || (e.k === 'lossX' && e.out === 'fk') || (e.k === 'sp' && e.spk === 'fk');
    if (!fk) return;
    const kt = L[i + 1].t - 0.05, tm = e.k === 'lossX' ? 1 - e.team : e.team, Pa = P(kt), b = E.ballAt(ch, kt, Pa);
    for (const j of onP(1 - tm, kt)) check('falta_10', 'Tiro libre: los rivales a 10 yardas del balón', d(pl(Pa, 1 - tm, j), [b.x, b.y]) >= 9.5, `${tag} t=${kt.toFixed(0)} d=${d(pl(Pa, 1 - tm, j), [b.x, b.y]).toFixed(1)}`);
  });
  // 5. córners: balón en la esquina y rivales a 10 yardas
  L.forEach((e, i) => {
    if (!(e.k === 'sp' && e.spk === 'corner')) return;
    const kt = L[i + 1].t - 0.05, Pa = P(kt), b = E.ballAt(ch, kt, Pa);
    check('corner_balon', 'Córner: el balón en la esquina', (b.x <= 1.2 || b.x >= 118.8) && (b.y <= 1.2 || b.y >= 78.8), `${tag} t=${kt.toFixed(0)} balón ${b.x.toFixed(1)},${b.y.toFixed(1)}`);
    for (const j of onP(1 - e.team, kt)) check('corner_10', 'Córner: los rivales a 10 yardas', d(pl(Pa, 1 - e.team, j), [b.x, b.y]) >= 9.5, `${tag} t=${kt.toFixed(0)}`);
  });
  // 6. penales
  L.forEach((e) => {
    if (e.k !== 'pen') return;
    const kt = (e._shotT || e.t) - 0.05, Pa = P(kt), ti = e.team;
    const gkj = teams[1 - ti].shape.findIndex((p) => p.pos === 'Goalkeeper');
    const gko = own(ti, pl(Pa, 1 - ti, gkj));
    check('penal_portero', 'Penal: el portero sobre la línea de gol', gko[0] >= 118.5, `${tag} t=${kt.toFixed(0)} x=${gko[0].toFixed(1)}`);
    let taker = -1, best = 1e9;
    for (const j of onP(ti, kt)) { const dd = d(own(ti, pl(Pa, ti, j)), [108, 40]); if (dd < best) { best = dd; taker = j; } }
    for (let tt = 0; tt < 2; tt++) for (const j of onP(tt, kt)) {
      if ((tt === ti && j === taker) || (tt === 1 - ti && j === gkj)) continue;
      const p = own(ti, pl(Pa, tt, j));
      check('penal_area', 'Penal: los demás fuera del área y del arco', p[0] <= 102.2 && d(p, [108, 40]) >= 9.8, `${tag} t=${kt.toFixed(0)} ${p.map((v) => v.toFixed(1))}`);
    }
  });
  // 7. saques de banda: desde la línea
  L.forEach((e, i) => {
    const th = e.k === 'throw' || (e.k === 'lossX' && e.out === 'throw');
    if (!th) return;
    const kt = L[i + 1].t - 0.05, Pa = P(kt), b = E.ballAt(ch, kt, Pa);
    check('banda', 'Saque de banda: el balón sale desde la línea', b.y <= 1.5 || b.y >= 78.5, `${tag} t=${kt.toFixed(0)} y=${b.y.toFixed(1)}`);
  });
  // 8. fuera de juego en el momento del pase · 9. doble toque en reanudación · 10. expulsados no juegan
  const restartT = new Set(L.filter((e) => ['kickoff', 'gk', 'lossX', 'foul', 'throw', 'sp'].includes(e.k)).map((e, i) => e.t));
  for (const bl of ch.balls) {
    if (bl.owner && bl.t0 > 0) check('expulsado', 'Un expulsado no vuelve a tocar el balón', !offAt(bl.owner[0], bl.owner[1], bl.t0 - 0.5), `${tag} t=${bl.t0.toFixed(0)}`);
    if (bl.kind !== 'pass' || !bl.owner) continue;
    const [ti, rj] = bl.owner, Pa = P(bl.t0 + 1e-3);
    const rx = own(ti, pl(Pa, ti, rj))[0];
    const dx = onP(1 - ti, bl.t0).map((j) => own(ti, pl(Pa, 1 - ti, j))[0]).sort((a, b) => b - a);
    const line = Math.max(dx[1] == null ? 60 : dx[1], 60, own(ti, bl.from)[0]);
    check('fuera_de_juego', 'Nadie recibe un pase en fuera de juego', rx <= line + 1.0, `${tag} t=${bl.t0.toFixed(0)} x=${rx.toFixed(1)} línea=${line.toFixed(1)}`);
    check('doble_toque', 'Quien reanuda no se la pasa a sí mismo', d(pl(Pa, ti, rj), bl.from) > 0.5 || !restartT.has(bl.t0), `${tag} t=${bl.t0.toFixed(0)}`);
  }
  // 11. tarjetas: segunda amarilla = roja; nadie recibe tarjeta después de expulsado
  const cardsBy = {};
  for (const c of ch.cards) {
    const k = c.team + ':' + c.slot; cardsBy[k] = cardsBy[k] || [];
    check('tarjeta_tras_roja', 'Nadie recibe tarjeta después de ser expulsado', !cardsBy[k].some((x) => x === 'red' || x === 'second'), `${tag} ${k}`);
    if (c.card === 'second') check('doble_amarilla', 'La segunda amarilla llega solo tras una primera', cardsBy[k].includes('yellow'), `${tag} ${k}`);
    if (c.card === 'yellow') check('doble_amarilla', 'La segunda amarilla llega solo tras una primera', !cardsBy[k].includes('yellow'), `${tag} ${k} dos amarillas sin expulsión`);
    cardsBy[k].push(c.card);
  }
  // 12. velocidad física
  const htT = (L.find((e) => e.k === 'ht') || { t: -1 }).t;
  for (let k = 1; k < ch.frames.length; k++) {
    const a = ch.frames[k - 1], b = ch.frames[k], dt = b.t - a.t;
    if (dt < 0.05 || (a.t <= htT + 2 && b.t >= htT - 2)) continue;
    let mx = 0; for (let i = 0; i < 44; i += 2) mx = Math.max(mx, Math.hypot(b.P[i] - a.P[i], b.P[i + 1] - a.P[i + 1]) / dt);
    check('velocidad', 'Ningún jugador corre más rápido que un humano (≤ 9.5 yd/s)', mx <= 9.5, `${tag} t=${a.t.toFixed(0)} v=${mx.toFixed(1)}`);
  }
  // 13. marcador y saques tras gol / segundo tiempo
  const goals = ch.feed.filter((f) => f.type === 'goal');
  check('marcador', 'La crónica y el marcador coinciden', goals.filter((g) => g.team === 0).length === sim.score[0] && goals.filter((g) => g.team === 1).length === sim.score[1], `${tag}`);
  L.forEach((e, i) => {
    if (e.k !== 'goal') return;
    const ko = L.slice(i + 1).find((x) => x.k === 'kickoff');
    if (ko) check('saque_tras_gol', 'Tras un gol saca el equipo que lo recibió', ko.team === 1 - e.team, `${tag} t=${e.t.toFixed(0)}`);
  });
  const kos = L.filter((e) => e.k === 'kickoff'), ht = L.findIndex((e) => e.k === 'ht');
  if (ht >= 0) check('segundo_tiempo', 'El segundo tiempo lo saca el equipo que no sacó el primero', L[ht + 1].k === 'kickoff' && L[ht + 1].team !== kos[0].team, `${tag}`);
  // 14. portero con las manos solo dentro de su área
  for (const bl of ch.balls) {
    if (bl.kind !== 'hold' || !bl.owner) continue;
    const Pa = P(bl.t0 + 0.05), p = own(bl.owner[0], pl(Pa, bl.owner[0], bl.owner[1]));
    check('portero_manos', 'El portero solo usa las manos dentro de su área', p[0] <= 18.5 && p[1] >= 17.5 && p[1] <= 62.5, `${tag} t=${bl.t0.toFixed(0)}`);
  }
  // 15. balón dentro del campo mientras se juega (pases y conducciones)
  for (const bl of ch.balls) {
    if (bl.kind !== 'pass' && bl.kind !== 'carry') continue;
    check('balon_en_campo', 'Durante pases y conducciones el balón está dentro del campo', bl.to[0] >= 0 && bl.to[0] <= 120 && bl.to[1] >= 0 && bl.to[1] <= 80, `${tag} t=${bl.t0.toFixed(0)}`);
  }
}
let total = 0, totalBad = 0;
console.log(`Árbitro automático · ${pairs.length} cruces × ${N} partidos = ${pairs.length * N} partidos\n`);
for (const [k, r] of Object.entries(R)) {
  total += r.checks; totalBad += r.bad;
  console.log(`${r.bad === 0 ? 'OK ' : 'MAL'} ${r.desc.padEnd(86)} ${String(r.checks).padStart(7)} revisiones  ${r.bad} faltas${r.ex.length ? '  ej: ' + r.ex.join(' | ') : ''}`);
}
console.log(`\nTotal: ${total} revisiones, ${totalBad} infracciones`);
