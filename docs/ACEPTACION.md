# Aceptación automática

Generado por `pipeline/acceptance.py` el 2026-10-21 19:33.
✅ cumple · ❌ no cumple · ⏳ pendiente o requiere revisión manual (con motivo).

| AC | Criterio | Estado | Evidencia |
|---|---|---|---|
| AC-01 | Validar modelos | ✅ | secciones Antes y Después presentes |
| AC-02 | La simulación no cambia | ✅ | test_golden_engine.js pasa; git diff main -- frontend/engine.js vacío |
| AC-03 | Datos completos del protagonista | ✅ | Jardine n=91 con mx_/an_/f360_ al 100 %; epílogo n=38; pac_almada con eventos 139/139 |
| AC-04 | Framework explícito | ✅ | framework.py existe; MARCO_ANALITICO.md existe; /api/framework responde |
| AC-05 | Coherencia interna | ✅ | audit_coherence.py rc=0: coherencia: OK {'etiquetas': 0, 'etiquetas_vistas': 0, 'ids_metricas': 0, 'mismo_valor': 0, 'umbrales': 0, 'ventana': 0, 'texto_usuario': 0} avisos {'umbrales': 0, 'insignia_ventana': 0} payloads 117 |
| AC-06 | Componentes del reto | ✅ | 12 capítulos, 46 hallazgos y 28 componentes cubiertos |
| AC-07 | Uso de 360 | ✅ | bloques 360 completos con cobertura y cordura aprobada |
| AC-08 | Errores al perder | ✅ | tipología en payload, historia y UI |
| AC-09 | Jugadas peligrosas en contra | ✅ | top 10 ordenado, con texto, x media 17.5769 y 51 KB |
| AC-10 | Jugadas por texto | ✅ | reglas 100 %; 5 modelos no-Anthropic en el benchmark |
| AC-11 | UI limpia | ⏳ | 0 toFixed(3); escaneo DOM/consola pendiente (revisor R2) |
| AC-12 | Rendimiento por equipo y DT | ✅ | 19 equipos y 102 DTs completos |
| AC-13 | Modo Aficionado / DT | ⏳ | modo Aficionado/DT: archivos presentes, verificación de contenido manual/por revisor |
| AC-14 | Simulación interpretativa | ✅ | repetición con xG (puntos contra xPts) y duelo de estilos rotulado como no pronóstico |
| AC-15 | Ventana oficial | ✅ | conclusiones solo en la ventana oficial; epílogo y evidencia temprana marcados |
| AC-16 | Calidad | ✅ | unittest OK; node --test OK; check_model OK; validate.js 100 OK; referee.js 3 OK; ruff (12 archivos) limpio; /api/model 1.2 MB |
| AC-17 | Entrega | ⏳ | RESUMEN_NOCHE.md falta; /api/health responde |
