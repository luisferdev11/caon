/* Tema del producto: oscuro por defecto (identidad del laboratorio); claro por prefers-color-scheme o por
   elección del visitante ([data-theme] = dark | light). Script clásico (sin módulos) para aplicarse antes
   de pintar en index.html y lab.html; el laboratorio en iframe sigue al portal por el evento «storage». */
(function (root) {
  'use strict';
  var KEY = 'caon.theme';
  var ORDER = ['auto', 'dark', 'light'];
  var LABELS = { auto: 'Tema: automático', dark: 'Tema: oscuro', light: 'Tema: claro' };

  function read() {
    try { var v = root.localStorage.getItem(KEY); return ORDER.indexOf(v) >= 0 ? v : 'auto'; } catch (e) { return 'auto'; }
  }
  function save(v) {
    try { root.localStorage.setItem(KEY, v); } catch (e) { /* almacenamiento no disponible: solo esta visita */ }
  }
  function apply(v) {
    var el = root.document.documentElement;
    if (v === 'dark' || v === 'light') el.setAttribute('data-theme', v); else el.removeAttribute('data-theme');
    return v;
  }
  function next(v) { return ORDER[(ORDER.indexOf(v) + 1) % ORDER.length]; }
  function cycle() { var v = next(read()); save(v); return apply(v); }

  root.caonTheme = { KEY: KEY, LABELS: LABELS, read: read, apply: apply, next: next, cycle: cycle };
  apply(read());
  if (root.addEventListener) root.addEventListener('storage', function (ev) { if (ev.key === KEY) apply(read()); });
})(typeof window !== 'undefined' ? window : globalThis);
