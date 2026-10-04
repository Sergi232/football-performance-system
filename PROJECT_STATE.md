# PROJECT_STATE

Última actualización: 04/10/2026

Fuente de verdad operativa del proyecto junto con el código actual de `main`. Si contradice un chat antiguo, prevalece este archivo.

---

# ESTADO EJECUTIVO

```text
PRODUCTO FUNCIONAL                    CERRADO / VALIDADO
GLOBAL END-TO-END QA                  PASS
REPRODUCIBILIDAD                      PASS
CI AUTOMÁTICO                         ACTIVO / PASS
DEMO PÚBLICA SINTÉTICA                PASS / REDISTRIBUIBLE
UI FINAL PRESENTATION AUDIT           CERRADO / CORREGIDO
COACH COPILOT LOCAL                   CERRADO / REAL SMOKE 22/22 PASS
COACH COPILOT OPENAI BYOK             IMPLEMENTADO / CONTRACT + CI PASS / LIVE API NO VALIDADA
MEMORIA ACADÉMICA INTEGRADA           BORRADOR COMPLETO
MARCO TEÓRICO / BIBLIOGRAFÍA          BORRADOR COMPLETO
METODOLOGÍA                           BORRADOR COMPLETO
RESULTADOS                            BORRADOR COMPLETO
DISCUSIÓN / LIMITACIONES              BORRADOR COMPLETO
CONCLUSIONES / TRABAJO FUTURO         BORRADOR COMPLETO
TABLAS ACADÉMICAS                     CREADAS
FIGURAS TÉCNICAS                      5 SVG CREADOS
ANEXOS                                BORRADOR CREADO
GUION DEFENSA                         CREADO
CAPTURAS REALES PRODUCTO              EN CURSO — ÚLTIMO GATE VISUAL
PLANTILLA / RÚBRICA UNIVERSIDAD       PENDIENTE EXTERNO
PUBLIC DEPLOYMENT                     NO HACER — licencia dataset real no resuelta
```

No añadir nueva funcionalidad deportiva salvo defecto real o nueva evidencia. Prioridad actual: cierre visual, documental y entrega.

---

# HIPÓTESIS PRINCIPAL

> **Un equipo de fútbol amateur o semiprofesional puede disponer de un sistema integral y auditable de soporte a la decisión a partir de datos de vídeo y GPS opcional, capaz de transformarlos en información sobre rendimiento, evolución, rol y comportamiento físico de los jugadores y del equipo.**

Contraste actual:

```text
viabilidad técnica / arquitectónica     FAVORABLEMENTE CONTRASTADA
mejora decisiones entrenador            NO DEMOSTRADA
mejora rendimiento deportivo            NO DEMOSTRADA
fatiga / readiness / lesión             NO DEMOSTRADO / NO IMPLEMENTADO
impacto comercial                       NO VALIDADO
```

---

# ARQUITECTURA VIGENTE

```text
VIDEO / COLLECTOR + GPS OPCIONAL
→ RAW / NORMALIZED DATA
→ FEATURE ENGINE
→ ANALYTICS
→ EXPERT SYSTEM / DS-ML
→ PRODUCT SERVICE / ACCESS
→ DASHBOARD
   ↓              ↓
COACH COPILOT     PDF
```

Regla global:

> Una capa superior no inventa métricas, scores, rankings o recomendaciones que no existan en una capa inferior validada.

Coach Copilot actual:

```text
QUESTION
→ DETERMINISTIC HIGH-CONFIDENCE ROUTER
→ si la consulta es clara: READ-ONLY TOOL directamente
→ si es ambigua: QWEN 3.5 4B local o OPENAI BYOK opcional
→ PYTHON / DUCKDB / ANALYTICS / EXPERT SYSTEM
→ STRUCTURED EVIDENCE
→ respuesta factual determinista o síntesis externa limitada
→ POLICY / NUMERIC GUARDS
→ COACH
```

Ni Qwen ni OpenAI tienen acceso directo a DuckDB. Match Rating, Performance Index, rankings, features y decisiones críticas se calculan fuera del LLM.

---

# MÓDULOS CERRADOS

```text
DATA-01/02/03/04                    CERRADO / VALIDADO
COLLECTOR-01                        CERRADO / V1.1 / FINAL GATE PASS
GPS NORMALIZATION                   CERRADO / VALIDADO
GPS SYNTHETIC DEMO                  CERRADO / VALIDADO
GPS PHYSICAL SUMMARY                CERRADO / REAL > SYNTHETIC
FEATURE-01/02/03                    CERRADO / VALIDADO
ANALYTICS-01                        CERRADO / VALIDADO
EXPERT-01..07 N1000-N13000          CERRADO / VALIDADO
MATCH RATING V5                     CERRADO / CONGELADO
PERFORMANCE INDEX                   v0.2 EXPERIMENTAL / OPERATIVO
DASHBOARD TEAM / PLAYER / MATCH     QA PASS
DASHBOARD GPS                       QA PASS
ATTENTION CENTRE                    CERRADO / v0.3
ACCESS CONTROL                      CONTRACT PASS / AUTH REAL PENDIENTE
COACH COPILOT LOCAL                 CERRADO / 22/22 REAL SMOKE PASS
COACH COPILOT OPENAI BYOK           IMPLEMENTADO / CONTRACT + CI PASS
REPORTS V6                          CERRADO / PASS
```

---

# COLLECTOR V1.1 — VARIABLES APROBADAS

Taxonomía congelada:

```text
collector/event_catalog.json
catalog_version=0.3.0
```

Variables observables aprobadas:
- identificación: jugador, dorsal, titular/suplente, minutos;
- contexto: partido, equipo, rival, fecha, formación, rol/posición, lado y cambios;
- pase normal/largo/centro × éxito/fallo;
- pase clave y asistencia;
- regate y pérdida;
- remate: gol / a puerta / fuera / bloqueado;
- defensa: entrada, intercepción, bloqueo y despeje;
- falta cometida/recibida con localización;
- tarjeta amarilla/roja;
- penal ganado/concedido con resultado;
- portero: parada y gol encajado;
- córner a favor/en contra + resultado ABP.

No recoger manualmente xG, PPDA, posesión avanzada, pressing, heatmaps, fatiga ni métricas derivables.

---

# DATA / FEATURES / ANALYTICS

Caso profesional de desarrollo:

```text
matches=38
players context=36
played appearances=590
```

```text
FEATURE-01 = 28 features / 23380 rows / 6324 non-null / PASS
FEATURE-02 = 28 × 7 temporal operators / 163660 rows / strict-past PASS
FEATURE-03 = 117735 rows / 43060 non-null / 590/835 con rol observado / PASS
ANALYTICS-01 = 46760 rows / SELF_ROLE_PRIOR + PEER_ROLE_PRIOR / strict-past PASS
```

Current-player exclusion y equal-player weighting: PASS.

---

# MATCH RATING / PERFORMANCE INDEX

Match Rating activo y congelado:

```text
match_rating_v0.5-candidate
coverage=590/590
mean=6.388
median=6.257
q10=5.757
q90=7.216
min=3.206
max=9.554
```

No modificar sin nueva evidencia + experimento + validación.

Performance Index:

```text
performance_score_v0.2-experimental
```

Capa histórica/posicional complementaria. No sustituye al Match Rating.

---

# EXPERT SYSTEM

```text
N1000   disponibilidad / actividad
N2000   perfil estructural
N3000   forma / evolución
N4000   amenaza ofensiva
N5000   creación / progresión
N6000   contribución defensiva
N7000   finalización
N8000   contexto equipo
N9000   componente físico
N10000  rol / contexto
N11000  consistencia / tendencia
N12000  player-fit evidence
N13000  recommendation gate
```

Contrato:

```text
entrada → condición → resultado → confianza → justificación
```

Estado:

```text
engine_version=expert_0.7.0
decision_rows=154475
N13000_rows=2505
NO_EVIDENCE=89
POLICY_UNVALIDATED=501
ROLE_UNKNOWN=245
```

N13000 no recomienda sin policy validada. N9000 no usa GPS sintético como evidencia física observada.

---

# GPS

```text
provider file / synthetic demo
→ gps_imports
→ gps_player_map
→ gps_observations
→ player_match_gps_summary
→ dashboard / reports
```

```text
gps_physical_summary_v0.1-descriptive
gps_synthetic_demo_v1.2.0
imports=38
mappings=590
observations=38197
summaries=590
REAL_OVER_SYNTHETIC=PASS
```

No existen thresholds canónicos de HSR, sprint, workload, fatiga, readiness o lesión.

---

# COACH COPILOT — RUNTIME FINAL

## Arquitectura local

Runtime principal de producto:

```text
pregunta
→ router determinista de alta confianza
→ tools read-only
→ Python/DuckDB
→ respuesta factual determinista
```

Solo cuando la intención no se puede resolver con suficiente confianza:

```text
pregunta ambigua
→ qwen3.5:4b como router semántico local
→ tools read-only
→ Python/DuckDB
→ evidencia estructurada
→ respuesta factual determinista
```

Qwen no calcula métricas críticas ni sintetiza rankings numéricos por su cuenta.

Métricas queryables actuales:
- goals;
- assists;
- shots;
- passes_total;
- passes_completed;
- tackles_total;
- tackles_won;
- interceptions;
- turnovers;
- dispossessed;
- minutes;
- appearances;
- total_distance_m;
- peak_speed_m_s;
- max_acceleration_m_s2;
- min_acceleration_m_s2;
- latest_match_rating;
- avg_last5;
- trend_delta_5v5.

Operaciones soportadas:
- retrieve / rank / compare / trend / aggregate / evidence;
- sum / mean / max / min / latest donde corresponda;
- ventanas `últimos N partidos`;
- follow-ups ordinales y de evidencia.

Guardrails explícitos:
- fatiga/cansancio;
- readiness;
- riesgo de lesión;
- XI/titularidad;
- recomendación táctica no validada;
- `mejor jugador`, `más completo`, `más determinante` sin definición analítica aprobada.

## Validación local real — 04/10/2026

DuckDB profesional + `qwen3.5:4b`:

```text
SMOKE CONTRACT: PASS (22/22)
average_elapsed=1.4s
consultas deterministas típicas=0.1–0.8s
follow-ups encadenados=0.1–0.2s
pregunta fuera de dominio vía fallback Qwen=25.3s
```

Casos cubiertos: rating, rating medio L5, distancia media, top remates, asistencias, evolución, perfil natural, GPS, comparación, partido, estado de equipo, calidad, fatiga, lesión, titularidad, criterio no validado, fuera de dominio y cadena de follow-ups con evidencia.

El smoke reproducible está en:

```text
llm/smoke_test_coach_agent.py
```

## Integración OpenAI opcional — BYOK

Implementada como segunda opción dentro de la misma página del Asistente IA:

```text
Local · Qwen
OpenAI API · clave propia
```

Arquitectura:

```text
pregunta clara
→ router determinista local
→ tool FPS
→ DuckDB
→ respuesta
→ 0 llamadas OpenAI

pregunta ambigua
→ OpenAI semantic router
→ tools FPS limitadas y revalidadas localmente
→ DuckDB / analytics / expert
→ evidencia estructurada
→ síntesis OpenAI con numeric grounding guard
```

Reglas:
- la API key pertenece al usuario;
- la UI no la persiste en DuckDB ni en archivos del proyecto;
- OpenAI no recibe acceso directo a DuckDB;
- tool calls externas se revalidan contra el contrato local;
- tools desconocidas se descartan;
- límites deportivos y guardrails son los mismos que en modo local.

Estado de validación:

```text
implementación                       PASS
unit / contract tests                PASS
synthetic demo CI                    PASS
llamada real con API key             NO VALIDADA AÚN
```

No implementar ahora conexión inversa ChatGPT → FPS / MCP. Queda como extensión futura.

---

# HISTÓRICO DE MODELOS / EXPERIMENTOS LLM

```text
qwen3:1.7b
- rápido
- insuficiente en selección semántica compleja y algunos guardrails
- descartado como runtime final

qwen3.5:4b
- buen routing semántico
- demasiado lento cuando se usa en todas las consultas (~55-61s observado)
- aprobado como fallback semántico, no como paso obligatorio

gemma3:4b
- tool calling Ollama HTTP 400
- descartado

granite4.2:3b
- benchmark contractual inicial 9/9
- avg ~34.7s
- fallos espontáneos posteriores en rating/GPS/follow-ups
- descartado como runtime final; se conserva como benchmark histórico
```

Decisión final: no validar frases aisladas; validar el espacio de consultas y usar composición `entidad + operación + métrica + agregación + filtros + ventana + follow-up`.

---

# PRODUCTO / UI

Modos:
- Equipo;
- Jugador;
- Partido;
- Físico/GPS;
- Calidad y alertas;
- Asistente IA.

Demo presentation:

```text
team → Equipo Demo
players → Jugador 01...
opponents → Rival 01...
```

Access roles:
- SUPERADMIN;
- CLUB_ADMIN;
- STAFF.

Autenticación email/password/session: no implementada.

UI presentation audit: cerrado. Tras los cambios del Coach Copilot debe hacerse una última revisión visual y recaptura de las pantallas finales.

---

# REPORTS V6

```text
report_metrics=report_descriptive_v0.2
schema=0.7.0
Team=4 páginas
Player=3 páginas
Match=3 páginas
REPORTS ELITE TECHNICAL GATE V6=PASS
```

---

# QA / REPRODUCIBILIDAD / CI

```text
Fase 1 — Data/Core          PASS
Fase 2 — Analytics/Expert   PASS
Fase 3A — Product           PASS
Fase 3B — Delivery          PASS
GLOBAL END-TO-END QA        PASS
```

Demo sintética pública:

```text
demo_version=synthetic_public_demo_v0.1.0
matches=12
players=18
player_match=216
played=192
FEATURE-01=6048
FEATURE-02=42336
FEATURE-03=30456
analytics_rows=12096
expert_rows=39960
N13000=648
ratings=192
performance_index=192
gps=192
professional_source_rows=0
app_read_layer=PASS
report_payloads=PASS
redistribution_status=REDISTRIBUTABLE_SYNTHETIC_DEMO
```

CI activo:

```text
.github/workflows/tests.yml
push + pull_request + workflow_dispatch
Python 3.13
pytest
synthetic demo rebuild + validation
```

Runs recientes de referencia:

```text
37162911509 = SUCCESS — smoke test direct execution import fix
37163349049 = SUCCESS — optional OpenAI Coach Copilot mode
37163417219 = SUCCESS — OpenAI BYOK Assistant UI + contracts
37163457928 = SUCCESS — external OpenAI tool-surface contract tests
```

---

# ARCHIVOS IMPORTANTES

Core de producto:
- `app/streamlit_app.py`;
- `app/pages/5_Assistent_IA.py`;
- `app/data_access.py`;
- `app/gps_physical_access.py`;
- `collector/data_collector_futbol.html`;
- `collector/event_catalog.json`.

Coach Copilot:
- `llm/coach_agent_fast.py` — entrada pública local + normalización/guards;
- `llm/coach_agent_general.py` — query grammar, router determinista, tools y respuestas;
- `llm/coach_agent_external.py` — OpenAI BYOK opcional;
- `llm/smoke_test_coach_agent.py` — smoke real reproducible;
- `tests/test_coach_agent_fast.py`;
- `tests/test_coach_agent_external.py`.

Documentación académica:
- `docs/TFM_MANUSCRIPT_DRAFT.md`;
- `docs/TFM_METHODOLOGY_DRAFT.md`;
- `docs/TFM_RESULTS_DRAFT.md`;
- `docs/TFM_DISCUSSION_CONCLUSIONS_DRAFT.md`;
- `docs/TFM_EVIDENCE_MATRIX.md`;
- `docs/TFM_TABLES_RESULTS.md`;
- `docs/TFM_ANNEXES_DRAFT.md`;
- `docs/TFM_SCREENSHOT_CHECKLIST.md`;
- `docs/TFM_DEFENSE_OUTLINE.md`;
- `docs/TFM_SUBMISSION_CHECKLIST.md`.

---

# DECISIONES APROBADAS

- MVP funcional antes de aumentar complejidad;
- Collector V1.1 congelado;
- raw / features / analytics / decision / LLM separados;
- strict-past obligatorio;
- Match Rating V5 congelado;
- Performance Index separado y experimental;
- experto jerárquico y auditable;
- ML solo con target defendible y contra baseline simple;
- GPS opcional, real > synthetic;
- synthetic GPS no es evidencia física observada;
- no inferir rol sin evidencia;
- LLM downstream y read-only;
- query-space composicional antes que una lista creciente de frases;
- router determinista para consultas claras;
- `qwen3.5:4b` solo como fallback semántico local;
- respuesta factual crítica calculada fuera del LLM;
- OpenAI BYOK opcional dentro de FPS, sin convertirlo en dependencia obligatoria;
- pregunta no soportada no cae en un resumen genérico del equipo;
- PDF downstream de analytics;
- demo pública sintética separada del dataset profesional;
- CI automático obligatorio;
- hipótesis limitada a viabilidad técnica/auditable;
- UI final muestra lenguaje de producto, no tokens internos.

---

# DECISIONES DESCARTADAS / APLAZADAS

- recrear proveedores profesionales;
- recoger métricas avanzadas manuales sin coste/beneficio claro;
- LLM como motor analítico;
- XI ideal o rol óptimo sin policy validada;
- fatiga/lesión/readiness sin datos y validación;
- inferir posición de suplentes sin evidencia;
- publicar dataset profesional sin derechos;
- autenticación SaaS completa en MVP;
- añadir ML solo por complejidad;
- inventar validación con usuarios;
- qwen3:1.7b como runtime conversacional final;
- qwen3.5:4b como paso obligatorio en cada consulta;
- gemma3:4b como runtime de tool calling con Ollama actual;
- Granite 4.2 3B como runtime final tras fallos espontáneos;
- embeddings / nuevo semantic-router antes de la entrega;
- conexión externa ChatGPT → FPS / MCP en el MVP.

---

# PROBLEMAS ABIERTOS

Prioridad de entrega:
- última revisión visual de `app/pages/5_Assistent_IA.py` tras añadir selector Local/OpenAI;
- capturas canónicas finales;
- sincronizar README y manuscrito con la arquitectura final del Coach Copilot;
- revisar checklist de entrega;
- maquetación/presentación final según plantilla disponible.

Limitaciones conocidas:
- fallback Qwen local puede tardar ~20–30s en CPU para lenguaje realmente ambiguo;
- modo OpenAI requiere API key y conexión externa;
- modo OpenAI no tiene todavía una prueba live con una API key real;
- autenticación de producción no implementada;
- dataset profesional no redistribuible mientras no se resuelva licencia;
- no existe validación externa con entrenadores ni ground truth para recomendaciones N13000.

---

# SIGUIENTE PASO EXACTO

1. `git pull --ff-only`.
2. Arrancar la app con la DuckDB profesional y revisar visualmente el Asistente IA en modo `Local · Qwen`.
3. Probar en la UI: rating, distancia, evolución, GPS, comparación y un guardrail; confirmar trazas legibles.
4. Verificar que aparece `OpenAI API · clave propia`; no es necesario gastar API para cerrar el MVP si no se dispone de una key de prueba.
5. Capturar la pantalla final del Coach Copilot y completar las 10 capturas de `docs/TFM_SCREENSHOT_CHECKLIST.md`.
6. Sincronizar manuscrito/resultados/arquitectura con este estado final.
7. Ejecutar checklist de entrega y congelar versión.
