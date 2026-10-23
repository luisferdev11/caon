/* Sistema de diseño único (portal + laboratorio + playlab): tokens, componentes, semántica de color. */
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const FE = path.join(__dirname, '..', 'frontend');
const read = (p) => fs.readFileSync(path.join(FE, p), 'utf8');
const exists = (p) => fs.existsSync(path.join(FE, p));
const LAB_GOLD = '#C0870E', LAB_BLUE = '#3D8FD6';
const REQUIRED = ['--bg', '--surface', '--surface-2', '--line', '--ink', '--ink-2', '--muted',
  '--protag', '--protag-ink', '--on-protag', '--rival', '--rival-ink', '--on-rival', '--league', '--hatch',
  '--warn', '--warn-ink', '--danger', '--grass', '--grass-2', '--chalk', '--font-display', '--font-body',
  '--fs-sm', '--fs-md', '--fs-lg', '--fs-xl', '--space-2', '--space-4', '--radius-md', '--radius-pill', '--shadow-1',
  '--chart-protag', '--chart-rival', '--chart-league'];
const LAB_ALIASES = ['--ground', '--panel', '--panel-2', '--home', '--home-ink', '--away', '--away-ink'];
// Colores literales: hex, rgb()/rgba()/hsl() (los anclajes #ruta no son hex de 3/4/6/8).
const COLOR_RE = /(?<![\w&/-])#(?:[0-9a-f]{8}|[0-9a-f]{6}|[0-9a-f]{3,4})(?![\w-])|\b(?:rgba?|hsla?)\(/gi;
const colorsIn = (s) => s.match(COLOR_RE) || [];
const block = (css, head) => {
  const i = css.indexOf(head); if (i < 0) return '';
  let depth = 0, j = css.indexOf('{', i);
  for (let k = j; k < css.length; k++) { if (css[k] === '{') depth++; if (css[k] === '}' && --depth === 0) return css.slice(j, k + 1); }
  return '';
};
const styleBlocks = (html) => [...html.matchAll(/<style>([\s\S]*?)<\/style>/g)].map((m) => m[1]).join('\n');
const markup = (html) => html.replace(/<script[\s\S]*?<\/script>/g, '').replace(/<style>[\s\S]*?<\/style>/g, '');

test('tokens.css: dark default from the lab identity, light variant by media query and [data-theme]', () => {
  const css = read('css/tokens.css');
  const root = block(css, ':root {');
  for (const t of [...REQUIRED, ...LAB_ALIASES]) assert.match(root, new RegExp(`${t}\\s*:`), t);
  assert.match(root, new RegExp(`--protag:\\s*${LAB_GOLD}`, 'i'), 'protagonista = dorado del laboratorio');
  assert.match(root, new RegExp(`--rival:\\s*${LAB_BLUE}`, 'i'), 'rival = azul del laboratorio');
  assert.match(root, /Barlow Condensed/); assert.match(root, /--font-body:[^;]*Barlow/);
  assert.match(css, /@media \(prefers-color-scheme: light\)\s*{\s*:root:not\(\[data-theme="dark"\]\)/);
  const light = block(css, ':root[data-theme="light"]');
  assert.ok(light.length > 40, 'bloque [data-theme="light"]');
  for (const t of ['--bg', '--surface', '--ink', '--protag-ink', '--rival-ink']) assert.match(light, new RegExp(`${t}\\s*:`), 'claro redefine ' + t);
  for (const t of ['--protag:', '--rival:', '--grass:', '--grass-2:']) assert.ok(!light.includes(t), `rellenos de equipo y cancha iguales en ambos temas (${t})`);
});

test('every page imports tokens.css and components.css with the same fonts', () => {
  const fonts = /fonts\.googleapis\.com\/css2\?family=Barlow\+Condensed[^"]*family=Barlow:/;
  for (const page of ['index.html', 'lab.html']) {
    const html = read(page);
    assert.match(html, /href="(?:\/)?css\/tokens\.css"/, page + ' importa tokens.css');
    assert.match(html, /href="(?:\/)?css\/components\.css"/, page + ' importa components.css');
    assert.ok(html.indexOf('tokens.css') < html.indexOf('components.css'), page + ': tokens antes que componentes');
    assert.match(html, fonts, page + ' carga Barlow Condensed + Barlow');
  }
});

test('no hard-coded colors outside tokens.css (CSS, módulos, vistas, estilos y markup del laboratorio)', () => {
  const files = [
    ...fs.readdirSync(path.join(FE, 'css')).filter((f) => f.endsWith('.css') && f !== 'tokens.css').map((f) => 'css/' + f),
    ...fs.readdirSync(path.join(FE, 'js')).filter((f) => f.endsWith('.js')).map((f) => 'js/' + f),
    ...fs.readdirSync(path.join(FE, 'views')).filter((f) => f.endsWith('.js')).map((f) => 'views/' + f),
  ];
  for (const f of files) assert.deepEqual(colorsIn(read(f)), [], f);
  const lab = read('lab.html');
  assert.deepEqual(colorsIn(styleBlocks(lab)), [], 'lab.html <style>');
  assert.deepEqual(colorsIn(markup(lab)), [], 'lab.html markup');
  assert.deepEqual(colorsIn(markup(read('index.html'))), [], 'index.html markup');
  assert.doesNotMatch(styleBlocks(lab), /:root\s*{/, 'el laboratorio no redefine tokens');
});

test('components.css: shared controls so no native unstyled control remains', () => {
  const css = read('css/components.css');
  for (const sel of ['.btn', '.btn.primary', '.btn[aria-pressed="true"]', '.btn.sm', '.seg', '.segmented', 'select',
    'input', 'textarea', '.chip', '.badge', '.badge.warn', '.card', '.section', '.section-head', '.eyebrow', '.table',
    'dl.kv', '.tip', 'details.how', '.legend', '.sw.protag', '.sw.rival', '.sw.league', '.hatch']) {
    assert.ok(css.includes(sel), 'falta ' + sel);
  }
  assert.match(block(css, 'select, .select {'), /appearance:\s*none/);
  assert.match(css, /h1, h2, h3[^{]*{[^}]*font-family:\s*var\(--font-display\)[^}]*text-transform:\s*uppercase/);
  assert.match(css, /body\s*{[^}]*font-family:\s*var\(--font-body\)/);
  assert.match(css, /button, select, input, textarea\s*{[^}]*font:\s*inherit/);
  assert.match(css, /:focus-visible/);
  for (const t of ['var(--protag)', 'var(--rival)', 'var(--league)', 'var(--hatch)']) assert.ok(css.includes(t), t);
});

test('playlab follows the lab semantics: protagonist gold, rival blue, shared pitch and styled controls', () => {
  const js = read('views/playlab.js');
  assert.doesNotMatch(js, /naranja|Azul: equipo elegido|<style>/i);
  assert.match(js, /playerDisc\(/); assert.match(js, /from '\.\.\/js\/pitch\.js'/);
  assert.match(js, /class="select"/); assert.match(js, /class="btn primary"/); assert.match(js, /class="input"/);
  assert.match(js, /legendHTML\(/);
  assert.doesNotMatch(js, /\$\{i \+ 1\}<\/button>/, 'ejemplos con nombre, no números sueltos');
  assert.match(js, /<section class="panel pl-result"/, 'pasos interpretados fuera de la tarjeta del formulario');
  assert.ok(exists('css/pitch.css'), 'estilos de cancha en css/pitch.css');
  const pitch = read('css/pitch.css');
  assert.match(pitch, /\.pd-protag[^{]*{[^}]*fill:\s*var\(--protag\)/); assert.match(pitch, /\.pd-rival[^{]*{[^}]*fill:\s*var\(--rival\)/);
  assert.match(pitch, /\.pitch-grass[^{]*{[^}]*fill:\s*var\(--grass\)/);
});

test('portal shell uses the shared components (segmented mode toggle, theme switch, mobile-safe nav)', () => {
  const html = read('index.html');
  assert.match(html, /class="segmented"[^>]*aria-label="Nivel de detalle"/);
  assert.match(html, /href="css\/pitch\.css"/);
  assert.match(html, /data-theme-toggle/);
  const portal = read('css/portal.css');
  assert.match(portal, /@media \(max-width: 640px\)/);
  assert.match(portal, /overflow-x:\s*auto/, 'las pestañas se desplazan dentro de su barra, no la página');
  assert.doesNotMatch(portal, /--page:|--s1:|--s2:/, 'portal.css ya no define tokens');
});
