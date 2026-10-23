# Benchmark: jugadas por texto → play.v1 (A9, AC-10)

Fecha: 2026-10-21 07:19 (America/Mexico_City). Frases: las primeras 25 de
`pipeline/fixtures/nl_phrases.json` (etiquetadas a mano: tipos de paso, zona de cada paso, reanudación, desenlace).
Prompt: esquema play.v1 en el mensaje de sistema + 1 ejemplo (few-shot), `temperature=0`,
`response_format=json_object`, nombres del once de la fixture. Validación con el mismo modelo pydantic que usa la API.
Métrica "tipos" = secuencia exacta de tipos; "zonas" = tipos exactos **y** todas las zonas etiquetadas correctas.
Modelos elegidos por precio listado en `GET https://openrouter.ai/api/v1/models` (no Anthropic, con `response_format`).

| Modelo | Tipos | Zonas | Reanudación | Desenlace | Latencia mediana / p90 | Costo 25 frases | Fallas de esquema/JSON |
|---|---|---|---|---|---|---|---|
| Parser de reglas (propio) | 100% | 100% | 100% | 100% | ~0 s | $0 | 0 |
| mistralai/mistral-small-3.2-24b-instruct | 72% | 52% | 92% | 100% | 4.5 / 6.9 s | $0.0023 | 0 |
| google/gemini-2.5-flash-lite | 68% | 48% | 84% | 92% | 0.8 / 1.1 s | $0.0026 | 2 |
| openai/gpt-4.1-nano | 48% | 28% | 52% | 64% | 1.4 / 2.0 s | $0.0016 | 9 |
| deepseek/deepseek-v4-flash | 0% | 0% | 0% | 0% | 5.1 / 5.4 s | $0 | 25 (contenido vacío: razonamiento sin JSON) |
| qwen/qwen3.5-flash-02-23 | 0% | 0% | 0% | 0% | 0.9 / 1.1 s | $0 | 25 (contenido vacío) |

Gasto total del benchmark: ≈ $0.007 (150 llamadas; costo reportado por `usage.cost`).

## Lectura honesta
- **El 100% de las reglas está sobreajustado**: el léxico se escribió con estas mismas frases a la vista.
  Es la cota superior, no la exactitud esperada con frases nuevas. Falta un conjunto ciego.
- Los LLM fallan sobre todo en convenciones propias del esquema (p. ej. "pared" = dos pases, zona de un
  remate = desde dónde se remata, "córner al primer palo" = centro). Más ejemplos few-shot lo mejorarían.
- DeepSeek v4 flash y Qwen 3.5 flash devolvieron contenido vacío con `max_tokens=700` (probablemente gastan
  el presupuesto en razonamiento); no se investigó más para cuidar el crédito.

## Decisión
- Default `OPENROUTER_MODEL=mistralai/mistral-small-3.2-24b-instruct`: mejor exactitud y 0 fallas de esquema;
  su latencia (p90 6.9 s) cabe en el timeout de 10 s.
- Modo `auto` = **reglas primero**; el LLM solo se consulta si las reglas no entienden (422) o su confianza es
  < 0.6. Modo `llm` fuerza el LLM con respaldo a reglas. Cualquier falla (sin key, timeout, JSON o esquema
  inválido) cae a reglas con el aviso `llm_sin_key` / `llm_fallo`. La key nunca sale en respuestas ni logs.
- Reproducir: script de benchmark de A9 (no versionado); llama `app.openrouter.parse_llm` con las 25 frases.
