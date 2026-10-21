# Informe de corrección prioritaria de CAON

Fecha de trabajo: 20 de octubre de 2026 (America/Mexico_City).

## Entrega para el equipo

Esta entrega se publica en la rama `fix/model`. Incluye las correcciones de datos,
la vista contextual, el modelo regenerado y los módulos de jugadores que ya estaban
integrados localmente y que necesita el constructor. Los respaldos de modelos,
credenciales, cachés StatsBomb y logs del servidor permanecen locales.

Para probar la aplicación con el artefacto incluido no hacen falta credenciales
StatsBomb ni regenerar los datos:

```bash
git fetch origin
git switch fix/model
git pull --ff-only origin fix/model
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Abrir `http://127.0.0.1:8000/`; documentación de API en
`http://127.0.0.1:8000/docs`. La comprobación local de arranque respondió HTTP 200
y `/api/health` informó `ok=true` y 24 entidades. Usar un entorno virtual y el
intérprete instalado en cada equipo; la ruta Windows citada más abajo solo
documenta el entorno donde se ejecutaron las pruebas.

### Próximos pasos propuestos

| Prioridad | Trabajo | Criterio para darlo por terminado |
|---|---|---|
| Alta | Revisar la interfaz en navegador, escritorio y móvil: selección de equipos, comparación contextual, jugadores, mapa y simulación. | Confirmar que valores ausentes, muestras pequeñas y tablas extensas se leen correctamente; registrar incidencias y añadir pruebas de navegador. |
| Alta | Automatizar las pruebas en CI con el modelo incluido, sin credenciales de datos. | Ejecutar invariantes, unittest, pruebas Node y simulación N=100; fallar ante errores invalidantes y conservar reportes. Instalar `httpx` para TestClient. |
| Alta | Probar respaldo y recuperación con espacio limitado en un directorio aislado. | Verificar tanto reemplazo atómico como restauración ante fallos; reservar espacio suficiente en el entorno de construcción. |
| Media | Validar las heurísticas fuera de muestra, separando temporadas y equipos. | Publicar tamaño de muestra, error y estabilidad de calibración; mantener ausentes las métricas que no superen los criterios. |
| Media | Analizar factores de confusión: rival, torneo, expulsiones y ventanas temporales. | Comparaciones con exposición compatible y sensibilidad documentada, sin atribuir causalidad automáticamente. |
| Media | Homogeneizar las definiciones históricas de transición y ritmo entre estilo, temporal, contextos y jugadores. | Proponer una migración explícita con pruebas y comparación antes/después; hoy las diferencias se conservan documentadas. |

Las propuestas de esta tabla quedan pendientes; no son funcionalidades ya
implementadas. La siguiente fase debe acordar criterios metodológicos antes de
cambiar fórmulas o presentar una identidad táctica como validada.

### Comprobación reproducible de la entrega

Antes del commit se ejecutó la suite completa actual: **29 pruebas Python y
6 pruebas JavaScript aprobadas**. La validación estructural del modelo volvió a
reportar 24 entidades, cero errores y la advertencia esperada de Barcelona.

```bash
python -m pip install httpx
python -X utf8 pipeline/check_model.py
python -X utf8 -m unittest discover -s pipeline -p "test_*.py"
node --test pipeline/test_validate.js pipeline/test_frontend.js
node pipeline/validate.js 100
node pipeline/referee.js 3
```

Para reconstruir desde datos locales ya disponibles: ejecutar
`python -X utf8 pipeline/run.py extract` y después
`python -X utf8 pipeline/run.py build`. Las descargas requieren las credenciales
y permisos de datos correspondientes; el modelo incluido permite probar la app
sin ese paso.

## Resultado final verificado

`pipeline/run.py build` terminó con código 0 y publicó el modelo de 19.568.283
bytes. `check_model.py`: 24 entidades, cero errores y una advertencia por las tres
métricas de Barcelona sin calibración suficiente. Jardine conserva 70 IDs únicos,
70 partidos de ataque y 70 de defensa; ninguna entidad observada tiene exclusiones.
La validación **del artefacto final** a N=100 evaluó 25 casos (24 entidades y liga):
25 correctos, cero advertencias, cero errores y cero métricas de simulación ausentes.
`node pipeline/validate.js 0` devolvió código 1, como corresponde.

La suite Python se repitió sobre el artefacto publicado: 28 tests, todos correctos.
Se reforzó después el caso de estructuras inválidas y se ejecutó de nuevo ese test:
pasó. La prueba adicional de codificación de los tres descargadores pasó con respuestas HTTP simuladas (29 pruebas Python en total, ejecutadas como suite de 28 más esa prueba). `git diff --check` no reportó problemas de whitespace. Se comprobó por igualdad
profunda contra el respaldo inicial que todos los agregados usados por el motor,
la referencia de liga (exceptuando contexto), shape, actors, roles y personnel
permanecen iguales. Por eso las 575.758 comprobaciones reglamentarias también
corresponden a los parámetros finales del motor.

El respaldo anterior a las modificaciones permanece recuperable en
`model/model.json.pre-build-20261021T024941265709Z.gz`; los respaldos son locales y
están excluidos de Git. La publicación final utilizó el modo de escritura respaldada
por espacio limitado. No se eliminaron datos de origen ni archivos personales.

Evidencia adicional: `pipeline/validation_report.txt`,
`pipeline/validation_summary.json` y `pipeline/referee_current_report.txt`.

## Diagnóstico y alcance

Se revisaron el estado Git, los generadores, sus consumidores, `research/poc.py`,
la API, el frontend, el motor y las pruebas. Se conservaron los cambios locales
previos de participación de jugadores y análisis temporal. No se modificó
`frontend/engine.js`, ni los archivos de eventos, lineups o metadatos de origen.
No se incorporaron 360, OBV, xT, VAEP ni clustering.

El repositorio recibido ya contenía una corrección parcial de la auditoría:
`ame_jardine` tenía 70 partidos y 14 métricas de estilo; la ejecución inicial de
`node pipeline/validate.js 100` evaluó 25 casos sin excepciones. Tanto el artefacto
actual como el primer commit disponible mostraban 70/70 para esa entidad. **El
caso exacto n=0/129 y el null concreto del fallo histórico no están reproducidos
en estos datos.** No se han reasignado 129 partidos ni inventado su población.

## Causas identificadas y correcciones

1. **Poblaciones distintas:** el generador histórico asignaba `n=len(rs)` desde
   filas team-stats y construía ataque/defensa desde extractos. La corrección
   previa usaba `att.matches`; ahora se registra la evidencia: IDs únicos
   incorporados juntos a ambos agregados, selección solicitada y exclusiones.
   La cobertura por métrica de estilo queda separada y determina el encogimiento.
2. **Ausencia convertida en estadística:** denominadores protegidos con `max(...,1)`
   fabricaban razones cuando no había observaciones; el frontend convertía estilo
   ausente a percentil 50 y etiquetas equilibradas. Ahora hay null, causas y
   etiquetas de datos insuficientes. Cero observado permanece cero.
3. **Calibración frágil:** `polyfit` suponía pares suficientes, varianza y finitud;
   R² no finito podía propagarse. Ahora se verifican esos contratos. Se mantienen
   ausentes las tres métricas de Barcelona cuya calibración no supera R²=0.5:
   verticalidad, saque largo y tiros tras robo alto. No es un error de serialización.
4. **Validación incompleta:** el formateador histórico llamaba `toFixed` directamente.
   La versión recibida ya lo protegía, pero todavía indexaba arrays ausentes,
   no clasificaba referencias incompletas ni verificaba rangos/WDL. Se añadieron
   controles, clasificación, continuidad por entidad y código de salida 1 para
   errores invalidantes. Los casos null/undefined/NaN/infinito se reproducen con
   fixtures, sin atribuir un origen no demostrado al fallo histórico.
5. **Contextos sesgados:** ausencia de metadatos se convertía en visitante; tiempo
   posterior a un gol se asignaba al marcador anterior; intervalos >30 s se
   descartaban; PPDA contextual incluía cualquier duelo; transición contaba
   posesiones con tiro y usaba From Counter en vez de la ventana de 10 s. Se
   corrigieron esos contratos y se unificó la función de resumen con `temporal.py`.
6. **Codificación dependiente de Windows:** en el código histórico, targets y descargadores Open Data
   quedaban lecturas/escrituras sin encoding. Ese patrón puede producir mojibake
   al leer UTF-8 como CP1252 y contaminar comparaciones por nombre. En los archivos
   actuales no se reprodujo AmÃ©rica/Hist�rico/Posesi�n; por ello no se afirma una
   etapa histórica exacta no observada. El pipeline corregido escribe UTF-8,
   rechaza no finitos y detecta indicadores de corrupción al validar. No reemplaza
   silenciosamente caracteres dañados ni modifica cachés de origen.
7. **Falta de espacio:** dos intentos de publicación no finalizaron. El original
   se conservó y se verificaron respaldos gzip. El constructor libera cachés antes
   de serializar, usa reemplazo atómico con espacio suficiente y ofrece escritura
   respaldada con restauración si el espacio solo permite reemplazar el contenido.

## Archivos y responsabilidad de los cambios

| Archivo | Cambio de esta fase |
|---|---|
| `pipeline/build_model.py` | IDs procesados, cobertura de estilo, calibración protegida, referencias documentadas, contexto/comparaciones, validación antes de publicar, respaldo recuperable. Conserva integración de jugadores previa. |
| `pipeline/metric_utils.py` | Contratos de finitud, razones sin imputación, fórmulas de eventos y calibración comprobable. |
| `pipeline/extract.py` | Integra contextos, orden temporal, metadatos MX/Open Data, versión de extractos y cuarentena de partidos incompletos. Mantiene cadenas del simulador. |
| `pipeline/contextual.py` | Reconstrucción de marcador, exposición por periodo, localía, métricas, muestras, tasas y comparaciones. |
| `pipeline/check_model.py` | Recorrido de no finitos/codificación, invariantes de IDs, conteos, percentiles y conservación entre contextos. |
| `pipeline/statsbomb.py`, `download_opendata.py`, `download_lineups.py` | Lectura UTF-8 de respuestas JSON y escritura UTF-8 explícita, también en futuras descargas; verifica HTTP antes de guardar lineups. No se ejecutaron descargas. |
| `pipeline/targets.py` | Importación sin efectos secundarios, UTF-8, medias solo de valores finitos, null y cobertura por métrica. |
| `pipeline/validate.js` | Validación reutilizable, salida segura, errores/warnings separados y comparaciones compatibles. |
| `pipeline/temporal.py` | Reutiliza tasas contextuales y evita contar partidos inexistentes o duplicar matches. |
| `pipeline/run.py` | UTF-8 en subprocesos y check_model obligatorio en build. |
| `app/main.py` | Nuevo endpoint de contextos y compatibilidad con style/shape ausentes. Conserva endpoints de jugadores previos. |
| `frontend/context_view.js` | Tarjetas de exposición y tabla de diferencias; null como s/d; interpretación descriptiva. |
| `frontend/index.html` | Integra vista, causas de ausencia, estimaciones experimentales, protege simulación sin muestra/alineaciones. |
| `pipeline/test_model.py`, `test_contextual.py`, `test_api.py`, `test_frontend.js`, `test_validate.js`, `test_metrics.py`, `test_encoding.py` | Regresiones numéricas, temporales, de formato, API, respaldo y frontend. |
| `model/model.json`, `pipeline/targets.json` | Artefactos derivados regenerados y validados. |
| `docs/METRICAS_TACTICAS.md`, `README.md`, este informe | Fórmulas, unidades, muestras, limitaciones y comandos. |
| `.gitignore` | Evita incorporar respaldos de construcción y temporales al repositorio. |

Los archivos locales previos `pipeline/personnel.py`, `pipeline/test_personnel.py`,
`docs/PERSONAL_JUGADORES.md` y el respaldo `model.json.pre-fix-20261019` se conservan.

## Modelo y API

Se conservan las claves previas. `schema_version=2` y `extract_version=2` indican
la semántica corregida. Nuevos campos: `coverage`, `style_status.valid_matches`,
`context_comparisons`, `context_status`, `meta.style_reference`, diagnósticos de
calibración y campos de exposición/tasas de cada contexto. Hay buckets unknown
para estados o localía no reconstruibles. Los consumidores de contextos deben
aceptar null y no sumar posesiones que atraviesan estados.

`GET /api/teams/{id}/context` expone contextos, comparaciones y cobertura.
`GET /api/model` y `/api/teams/{id}` conservan su función y añaden esos campos.
Los endpoints temporal, personnel, lineups y substitutions se mantienen.

## Pruebas y entorno

- Inicial: 10 tests Python pasaron con el intérprete Python313 instalado; 25
  casos de simulación a N=100 terminaron sin excepción.
- Suite ampliada: 28 tests Python pasaron (incluye API real vía TestClient,
  caracteres UTF-8, respaldo y lectura del artefacto, calibración y fórmulas).
- JavaScript: 6 tests pasaron, incluyendo parsing del script frontend, estilos
  ausentes, formato de métricas y continuidad tras errores.
- Árbitro: `node pipeline/referee.js 3`: 575.758 revisiones, cero infracciones.
- Extracción: 513 partidos regenerados (445 MX y 68 Open Data). Cero advertencias
  de marcador/localía/límites de periodo en esos extractos. Los 48 extractos
  antiguos restantes no pertenecen a la selección actual de construcción.
- No se realizó una revisión visual manual en navegador; la regresión del
  frontend cubre parsing y renderizado de sus funciones con datos incompletos.
- El alias `python` no era ejecutable y `.venv` carecía de requests. Se usó
  `C:\Users\eddym\AppData\Local\Programs\Python\Python313\python.exe` con las
  dependencias ya instaladas. No se descargaron paquetes ni datos.
- TestClient se bloqueaba dentro del sandbox en `socketpair` de Windows. La
  ejecución autorizada fuera del aislamiento pasó. Una prueba de respaldo también
  encontró restricciones sobre el temporal del sandbox y pasó fuera de él.

Los comandos exactos de regeneración y validación están en README. Los descargadores se comprobaron con respuestas simuladas; no se ejecutaron contra
servicios externos ni se alteraron archivos fuente existentes. Para ejecutar
las pruebas HTTP en otro entorno, instalar también `httpx`.

## Limitaciones pendientes

Las fórmulas y cambios de denominador se detallan en METRICAS_TACTICAS.md. Las
heurísticas no han sido validadas fuera de muestra. R² en muestra no valida la
identidad táctica, la transferencia entre épocas o ligas ni una decisión del DT.
La presión y la posesión son proxies; el tiempo contextual incluye interrupciones.
La muestra mínima es descriptiva, no una prueba de significación. Rival, torneo,
expulsiones y selección de partidos pueden explicar diferencias. El resultado
frente a liga promedio no replica el calendario real. No se interpreta el éxito
del script como calibración estadística del simulador.
