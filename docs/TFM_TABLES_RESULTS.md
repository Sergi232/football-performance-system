# TFM — Tablas canónicas de resultados

Fecha: 04/10/2026
Estado: tablas académicas listas para integrar en la memoria.

Regla: todas las cifras proceden de gates/validators ya registrados. No recalcular manualmente estos valores para la memoria si no cambia la versión del producto.

---

## Tabla 1. Cobertura del caso profesional de desarrollo

| Indicador | Valor |
|---|---:|
| Partidos | 38 |
| Jugadores en contexto producto | 36 |
| Apariciones jugadas | 590 |
| Registros `player_match` de plantilla/alineación | 835 |
| Suplentes no utilizados | 245 |
| Match Rating disponibles | 590 |
| Porteros con ruta específica | 38 |
| Outfield `PERF18_ANCHORED` | 380 |
| Fallback por rol no fiable | 172 |

Interpretación permitida: cobertura técnica del caso de desarrollo.

No interpretar como: muestra representativa del fútbol amateur.

---

## Tabla 2. Feature Engine

| Etapa | Resultado principal | Estado |
|---|---:|---|
| FEATURE-01 | 28 features base | PASS |
| FEATURE-01 | 23.380 filas de feature | PASS |
| FEATURE-01 | 6.324 valores no nulos | PASS |
| FEATURE-02 | 28 × 7 operadores temporales | PASS |
| FEATURE-02 | 163.660 filas | PASS |
| FEATURE-03 | 117.735 / 117.735 filas | PASS |
| FEATURE-03 | 43.060 valores no nulos | PASS |
| FEATURE-03 | 590 / 835 registros de plantilla/alineación con rol observado y minutos positivos | PASS |

Regla metodológica: FEATURE-02/03 usan pasado estricto.

---

## Tabla 3. Analytics y sistema experto

| Componente | Filas / cobertura | Estado |
|---|---:|---|
| ANALYTICS-01 | 46.760 filas | PASS |
| Motor experto final | 154.475 decision rows / 835 registros | PASS |
| N13000 | 2.505 filas | PASS |
| N13000 `NO_EVIDENCE` | 89 | esperado |
| N13000 `POLICY_UNVALIDATED` | 501 | esperado |
| N13000 `ROLE_UNKNOWN` | 245 | esperado |
| GPS observado no sintético en N9000 | 0 player-match | limitación explícita |

Interpretación: el **motor experto de evaluación y evidencia con gate de recomendación** materializa evidencia y N13000 se abstiene de recomendaciones tácticas finales.

Definición de denominadores: `player_match=835` incluye 590 apariciones jugadas y 245 suplentes no utilizados (`started=false`, minutos 0, rol nulo). Match Rating cubre las 590 apariciones jugadas; el motor experto evalúa los 835 registros.

Para comparaciones de rendimiento por posición observada, las filas con 1–4 apariciones se marcan como **muestra pequeña**: se conservan de forma descriptiva, pero no sostienen una tendencia ni una interpretación fuerte.

---

## Tabla 4. Match Rating V5

| Indicador | Valor |
|---|---:|
| Versión | `match_rating_v0.5-candidate` |
| Cobertura | 590 / 590 |
| Partidos | 38 |
| Media | 6,388 |
| Mediana | 6,257 |
| P10 | 5,757 |
| P90 | 7,216 |
| Mínimo | 3,206 |
| Máximo | 9,554 |
| Nulls | 0 |
| Duplicados | 0 |
| Fuera de rango | 0 |

Interpretación: cobertura y comportamiento técnico del rating en el caso de desarrollo.

No interpretar como: validez universal externa del score.

---

## Tabla 5. GPS sintético de integración

| Indicador | Valor |
|---|---:|
| Generator version | `gps_synthetic_demo_v1.2.0` |
| Imports | 38 |
| Mappings | 590 |
| Observaciones | 38.197 |
| Summaries/latest | 590 |
| Summary version | `gps_physical_summary_v0.1-descriptive` |
| Precedencia REAL > SYNTHETIC | PASS |
| Synthetic excluido de N9000 observado | PASS |

Interpretación: integración técnica GPS.

No interpretar como: validación fisiológica.

---

## Tabla 6. Coach Copilot final

| Indicador | Valor |
|---|---:|
| MVP | Castellano |
| Arquitectura | preflight + deterministic-first + semantic fallback |
| Fallback local | `qwen3.5:4b` |
| Smoke real final | **28 / 28 PASS** |
| Latencia media batería final | **0,4 s** |
| Casos finales con fallback semántico | **0 / 28** |
| Query-space contract en CI | PASS |
| Comparación por posición | PASS |
| Follow-ups ordinal/ventana/evidencia/rol | PASS |
| Ruido / meta / fuera de dominio preflight | PASS |
| Fatiga / lesión / titularidad guards | PASS |
| Criterios globales no validados bloqueados | PASS |
| Numeric / tool grounding | PASS |
| Demo identity boundary | PASS |
| OpenAI BYOK contract | PASS |
| OpenAI live benchmark | NO VALIDADO |

Interpretación: las consultas de alta confianza se resuelven con routing determinista y herramientas FPS; Qwen queda como fallback semántico únicamente para ambigüedad dentro del dominio. La media de 0,4 s corresponde a la batería concreta de 28 casos ejecutada en el PC de desarrollo y no constituye un SLA universal ni mide la latencia del fallback Qwen.

---

## Tabla 7. Producto y delivery

| Gate | Estado |
|---|---|
| Dashboard data contract | PASS |
| Streamlit UI compatibility | PASS |
| Demo presentation | PASS |
| Access control | PASS |
| Attention flags | PASS |
| Match Mode | PASS |
| Reports V6 | PASS |
| Global end-to-end QA | PASS |

Limitación: access control estructural no equivale a autenticación real.

---

## Tabla 8. Demo pública sintética reproducible

| Indicador | Valor |
|---|---:|
| Demo version | `synthetic_public_demo_v0.1.0` |
| Partidos | 12 |
| Jugadores | 18 |
| Player-match | 216 |
| Played | 192 |
| FEATURE-01 | 6.048 |
| FEATURE-02 | 42.336 |
| FEATURE-03 | 30.456 |
| Analytics rows | 12.096 |
| Expert rows | 39.960 |
| N13000 | 648 |
| Ratings | 192 |
| Performance Index | 192 |
| GPS summaries | 192 |
| Professional source rows | 0 |
| App read layer | PASS |
| Report payloads | PASS |
| Redistribution status | `REDISTRIBUTABLE_SYNTHETIC_DEMO` |

Interpretación: reproducibilidad técnica e integración desde datos sintéticos.

No interpretar como: revalidación científica del Match Rating o Performance Index.

---

## Tabla 9. Integración continua

| Paso GitHub Actions | Estado de referencia |
|---|---|
| Checkout limpio | PASS |
| Python 3.13 | PASS |
| Instalación de dependencias | PASS |
| `pytest -q` | PASS |
| Build demo sintética | PASS |
| Validator demo sintética | PASS |
| Coach Copilot query-space contract | PASS |
| Run de referencia | `37167157174` SUCCESS |

Interpretación: el repositorio se valida desde un entorno limpio sin depender de la DuckDB privada. El smoke 28/28 es un gate local adicional sobre la DuckDB profesional y no sustituye al CI sintético reproducible.

---

## Tabla 10. Síntesis de validación técnico-funcional

| Bloque | Evidencia | Resultado | Límite de interpretación |
|---|---|---|---|
| Pipeline y trazabilidad | Traza real hasta dashboard, Coach y PDF | PASS | No mide utilidad percibida. |
| Match Rating | Sensibilidad, rutas observadas y estabilidad descriptiva | PASS | No prueba validez externa. |
| Motor experto | Cobertura, traza y abstención N13000 | PASS | No emite recomendación táctica actual. |
| Consultas funcionales | Seis preguntas contra materializaciones | 6/6 PASS | Espacio de consultas soportado, no lenguaje universal. |
| Robustez | Casos límite y dos abstenciones | PASS | No valida fisiología ni rol óptimo. |
| Privacidad/reproducibilidad | Privacy gate, aliases, demo y CI | PASS | No resuelve licencia de la fuente privada. |

Los logs y casos individuales se remiten al Anexo M.

---

## Regla de uso

En el cuerpo principal usar únicamente las tablas que ayuden a responder la hipótesis. El detalle completo puede pasar a anexos.

Prioridad recomendada para el cuerpo:

1. Tabla 1 — cobertura del caso de desarrollo;
2. Tabla 3 — Analytics/Expert;
3. Tabla 4 — Match Rating;
4. Tabla 6 — Coach Copilot;
5. Tabla 8 — demo sintética reproducible;
6. Tabla 9 — CI.
7. Tabla 10 — síntesis de validación técnico-funcional.
