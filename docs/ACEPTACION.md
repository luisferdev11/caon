# Aceptación automática

Generado por `pipeline/acceptance.py` el 2026-10-21 07:30.
✅ cumple · ❌ no cumple · ⏳ pendiente o requiere revisión manual (con motivo).

| AC | Criterio | Estado | Evidencia |
|---|---|---|---|
| AC-01 | Validar modelos | ⏳ | sección Antes presente; Después pendiente (fin de noche) |
| AC-02 | La simulación no cambia | ✅ | test_golden_engine.js pasa; git diff main -- frontend/engine.js vacío |
| AC-03 | Datos completos del protagonista | ✅ | ame_jardine n=91 official=True; ame_jardine_epi n=38; pac_almada presente; cobertura mx_/an_/f360_ por verificar |
| AC-04 | Framework explícito | ⏳ | framework.py existe; MARCO_ANALITICO.md existe; /api/framework sin respuesta |
| AC-05 | Coherencia interna | ✅ | audit_coherence.py rc=0: coherencia: OK {'etiquetas': 0, 'ids_metricas': 0, 'mismo_valor': 0, 'umbrales': 0} payloads 58 |
| AC-06 | Componentes del reto | ⏳ | pendiente: falta model/story/jardine.json |
| AC-07 | Uso de 360 | ⏳ | métricas 360: archivos presentes, verificación de contenido manual/por revisor |
| AC-08 | Errores al perder | ⏳ | pendiente: falta pipeline/analytics/transitions.py |
| AC-09 | Jugadas peligrosas en contra | ⏳ | pendiente: falta pipeline/analytics/dangerous.py |
| AC-10 | Jugadas por texto | ⏳ | jugadas por texto: archivos presentes, verificación de contenido manual/por revisor |
| AC-11 | UI limpia | ⏳ | 0 toFixed(3); escaneo DOM/consola pendiente (revisor R2) |
| AC-12 | Rendimiento por equipo y DT | ⏳ | explorador: archivos presentes, verificación de contenido manual/por revisor |
| AC-13 | Modo Aficionado / DT | ⏳ | modo Aficionado/DT: archivos presentes, verificación de contenido manual/por revisor |
| AC-14 | Simulación interpretativa | ⏳ | repetición con xG: archivos presentes, verificación de contenido manual/por revisor |
| AC-15 | Ventana oficial | ⏳ | model/story/jardine.json aún no existe |
| AC-16 | Calidad | ✅ | unittest OK; node --test OK; check_model OK; validate.js 100 OK; referee.js 3 OK; ruff (22 archivos) limpio; /api/model 1.2 MB |
| AC-17 | Entrega | ⏳ | RESUMEN_NOCHE.md falta; /api/health responde |
