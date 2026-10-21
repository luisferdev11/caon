# Aceptación automática

Generado por `pipeline/acceptance.py` el 2026-10-21 07:11.
✅ cumple · ❌ no cumple · ⏳ pendiente o requiere revisión manual (con motivo).

| AC | Criterio | Estado | Evidencia |
|---|---|---|---|
| AC-01 | Validar modelos | ⏳ | sección Antes presente; Después pendiente (fin de noche) |
| AC-02 | La simulación no cambia | ⏳ | comandos desactivados (--no-run) |
| AC-03 | Datos completos del protagonista | ❌ | ame_jardine n=70 official=True; ame_jardine_epi ausente; pac_almada ausente; cobertura mx_/an_/f360_ por verificar |
| AC-04 | Framework explícito | ⏳ | pipeline/framework.py aún no existe (agente Framework) |
| AC-05 | Coherencia interna | ❌ | línea base: 8 contradicciones de etiquetas (audit_coherence.py pendiente) |
| AC-06 | Componentes del reto | ⏳ | pendiente: falta model/story/jardine.json |
| AC-07 | Uso de 360 | ⏳ | pendiente: falta pipeline/frames360.py, pipeline/extract_360.py |
| AC-08 | Errores al perder | ⏳ | pendiente: falta pipeline/analytics/transitions.py |
| AC-09 | Jugadas peligrosas en contra | ⏳ | pendiente: falta pipeline/analytics/dangerous.py |
| AC-10 | Jugadas por texto | ⏳ | pendiente: falta app/play_rules.py, app/openrouter.py, docs/NL_BENCHMARK.md |
| AC-11 | UI limpia | ❌ | toFixed(3) en: index.html×1 |
| AC-12 | Rendimiento por equipo y DT | ⏳ | pendiente: falta pipeline/explorer.py |
| AC-13 | Modo Aficionado / DT | ⏳ | pendiente: falta frontend/js/router.js, frontend/views/match.js |
| AC-14 | Simulación interpretativa | ⏳ | pendiente: falta pipeline/analytics/replay.py |
| AC-15 | Ventana oficial | ⏳ | model/story/jardine.json aún no existe |
| AC-16 | Calidad | ⏳ | comandos desactivados (--no-run) |
| AC-17 | Entrega | ⏳ | RESUMEN_NOCHE.md falta; /api/health responde |
