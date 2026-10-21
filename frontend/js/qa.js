/* Control de calidad del texto visible (AC-11/AC-13): tokens en inglés, valores ausentes crudos,
   decimales largos y números por tarjeta en modo Aficionado. Se activa con ?qa=1 en el portal. */

/** Palabras crudas que nunca deben llegar a la pantalla (vocabulario StatsBomb/código). */
export const RAW_TOKENS = [
  'unknown', 'undefined', 'NaN', 'null', 'Infinity', 'true', 'false',
  'home', 'away', 'winning', 'losing', 'drawing', 'high', 'medium', 'low',
  'Goalkeeper', 'Defender', 'Midfielder', 'Forward', 'Midfield', 'Center', 'Back', 'Wing', 'Striker',
  'Pass', 'Carry', 'Shot', 'Pressure', 'Dribble', 'Recovery', 'Interception', 'Clearance', 'Miscontrol',
  'Dispossessed', 'Duel', 'Foul', 'Block', 'Corner', 'Free Kick', 'Throw-in', 'Goal Kick', 'Kick Off',
  'Open Play', 'Regular Play', 'From Counter', 'Penalty', 'Header', 'Saved', 'Wayward', 'Incomplete',
];
export const MAX_FAN_NUMBERS = 3;
const LONG_DECIMAL = /(?<![\d.])\d+\.\d{3,}(?![\d])/gu;
const NUMBER = /\d+(?:[.,]\d+)*/gu;
const PERCENTILE_TAIL = /de cada 100/gu;
const YEARS = /(?<![\d.,])(?:19|20)\d{2}(?:\/(?:19|20)?\d{2})?(?![\d.,])/gu; // años y temporadas son etiquetas
const escapeRe = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
// Un token dentro de un identificador de código (high_press_shots) no es texto crudo visible.
const TOKEN_RES = RAW_TOKENS.map((t) => [t, new RegExp(`(?<![\\p{L}\\-_])${escapeRe(t)}(?![\\p{L}\\-_])`, 'u')]);

/** Revisa un texto y devuelve {issues: [{token, kind}]}. */
export function scanText(text) {
  const s = String(text || '');
  const issues = [];
  for (const [token, re] of TOKEN_RES) if (re.test(s)) issues.push({ token, kind: 'crudo' });
  for (const m of s.matchAll(LONG_DECIMAL)) issues.push({ token: m[0], kind: 'decimales' });
  return { issues };
}

/** Cuenta los números visibles de un texto. No cuentan «de cada 100» (frase del percentil) ni años o temporadas. */
export function countNumbers(text) {
  const s = String(text || '').replace(PERCENTILE_TAIL, '').replace(YEARS, '');
  return (s.match(NUMBER) || []).length;
}

/** Reporte del documento: problemas de texto y, en modo Aficionado, tarjetas con más de 3 números. */
export function scanDocument(doc, mode) {
  const root = doc.getElementById('view') || doc.body;
  const report = { mode, route: doc.location ? doc.location.hash : '', issues: scanText(root.innerText).issues, crowdedCards: [] };
  if (mode === 'aficionado') {
    for (const card of root.querySelectorAll('.card')) {
      const n = countNumbers(card.innerText);
      if (n > MAX_FAN_NUMBERS) {
        const h = card.querySelector('h3');
        report.crowdedCards.push({ title: h ? h.textContent.trim() : '', numbers: n });
      }
    }
  }
  return report;
}
