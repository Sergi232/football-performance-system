# PROJECT_STATE

Última actualización: 04/10/2026

Fuente de verdad operativa del proyecto junto con el código actual de `main`. Si contradice un chat antiguo, prevalece este archivo.

---

# 1. ESTADO EJECUTIVO

```text
PRODUCTO WEB FUNCIONAL                 CERRADO / VALIDADO
GLOBAL END-TO-END QA                   PASS
REPRODUCIBILIDAD                       PASS
CI AUTOMÁTICO                          PASS
DEMO PÚBLICA SINTÉTICA                 PASS / REDISTRIBUIBLE
TEAM / PLAYER / MATCH / GPS            QA PASS
EXPERT SYSTEM N1000-N13000             CERRADO / VALIDADO
MATCH RATING V5                        CONGELADO
PERFORMANCE INDEX                      v0.2 EXPERIMENTAL
REPORTS V6                             PASS
COACH COPILOT QUERY-SPACE CONTRACT     PASS EN CI
COACH COPILOT LOCAL REAL               PASS 28/28 · avg 0.4s
COACH COPILOT OPENAI BYOK              IMPLEMENTADO / CONTRACT PASS / LIVE API NO VALIDADA
ANONIMIZACIÓN DEMO ASSISTANT           CONTRACT PASS
CAPTURAS FINALES                       PASS · 10/10 DEMO SINTÉTICA
PUBLIC DEPLOYMENT                      NO HACER CON DATASET REAL POR LICENCIA
```

No añadir nueva funcionalidad deportiva salvo defecto real. Coach Copilot queda congelado para entrega; el cierre documental continúa sujeto a plantilla universitaria y presentación final.

---

# 2. HIPÓTESIS DEL TFM

> **Un equipo de fútbol amateur o semiprofesional puede disponer de un sistema integral y auditable de soporte a la decisión a partir de datos de vídeo y GPS opcional, capaz de transformarlos en información sobre rendimiento, evolución, rol y comportamiento físico de los jugadores y del equipo.**

Estado del contraste:

```text
viabilidad técnica / arquitectónica     FAVORABLEMENTE CONTRASTADA
mejora causal de decisiones             NO DEMOSTRADA
mejora causal del rendimiento           NO DEMOSTRADA
fatiga / readiness / lesión             NO IMPLEMENTADO / NO VALIDADO
impacto comercial                       NO VALIDADO
```

---

# 3. ARQUITECTURA ACTUAL

```text
VIDEO / DATA COLLECTOR + GPS OPCIONAL
→ RAW / NORMALIZED DATA
→ FEATURE ENGINE
→ ANALYTICS
→ EXPERT SYSTEM / DS-ML
→ PRODUCT SERVICE / ACCESS LAYER
→ WEB DASHBOARD
   ↓                         ↓
COACH COPILOT               PDF
```

Regla global:

> Una capa superior no puede inventar métricas, scores, rankings, thresholds o recomendaciones que no existan o no estén autorizados por una capa inferior validada.

Arquitectura Coach Copilot:

```text
PREGUNTA
→ PREFLIGHT / GUARDRAILS
→ ROUTER DETERMINISTA DE ALTA CONFIANZA
→ si es resoluble: TOOL READ-ONLY
→ si sigue siendo ambigua y está dentro de dominio:
     Qwen 3.5 4B local
     o OpenAI BYOK opcional
→ PYTHON / DUCKDB / ANALYTICS / EXPERT SYSTEM
→ EVIDENCIA ESTRUCTURADA
→ RESPUESTA
→ COACH
```

Qwen/OpenAI no tienen acceso directo a DuckDB ni calculan Match Rating, Performance Index, rankings o decisiones críticas.

---

# 4. VARIABLES APROBADAS DEL DATA COLLECTOR

Taxonomía congelada:

```text
collector/event_catalog.json
catalog_version=0.3.0
collector/data_collector_futbol.html
```

Variables observables aprobadas:
- identificación: jugador, dorsal, titular/suplente, minutos;
- contexto: partido, equipo, rival, fecha, formación, rol/posición, lado y cambios de rol;
- pase normal/largo/centro × éxito/fallo;
- pase clave y asistencia;
- regate y pérdida;
- remate: gol / a puerta / fuera / bloqueado;
- defensa: entrada, intercepción, bloqueo y despeje;
- falta cometida/recibida con localización;
- tarjetas y penaltis;
- córners/ABP y resultado de secuencia;
- portero: parada y gol encajado.

No recoger manualmente xG, PPDA, posesión avanzada, pressing, heatmaps, fatiga ni métricas que se puedan derivar automáticamente.

---

# 5. DATA / FEATURES / ANALYTICS

Unidad analítica principal: `player_match`.

Caso profesional de desarrollo:

```text
matches=38
players context=36
played appearances=590
```

Estado:

```text
FEATURE-01  28 features base / 23380 rows / PASS
FEATURE-02  28 × 7 operadores temporales / strict-past PASS
FEATURE-03  role-conditioned / strict-past + same-role PASS
ANALYTICS-01 SELF_ROLE_PRIOR + PEER_ROLE_PRIOR / PASS
```

Principios cerrados:
- current-player exclusion en peers;
- equal-player weighting;
- no same-date/future leakage;
- no inferir rol cuando falta evidencia.

---

# 6. MATCH RATING / PERFORMANCE INDEX

Match Rating activo:

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

Está congelado. No modificar sin nueva evidencia + experimento explícito + validación.

Performance Index:

```text
performance_score_v0.2-experimental
```

Es complementario y experimental; no sustituye al Match Rating.

---

# 7. EXPERT SYSTEM

```text
N1000   disponibilidad / actividad
N2000   perfil estructural
N3000   forma / evolución
N4000   amenaza ofensiva
N5000   creación / progresión
N6000   contribución defensiva
N7000   finalización
N8000   contexto equipo
N9000   componente físico opcional
N10000  rol / contexto
N11000  consistencia / tendencia
N12000  player-fit evidence
N13000  recommendation gate
```

Contrato por nodo:

```text
entrada → condición → resultado → confianza → justificación
```

`expert_0.7.0` está cerrado. N13000 no emite recomendación táctica sin policy validada. N9000 no considera GPS sintético como evidencia física real.

---

# 8. GPS

```text
archivo proveedor / demo sintética
→ gps_imports
→ gps_player_map
→ gps_observations
→ player_match_gps_summary
→ dashboard / reports
```

Estado profesional de desarrollo:

```text
imports=38
mappings=590
observations=38197
summaries=590
REAL_OVER_SYNTHETIC=PASS
```

No hay thresholds canónicos de HSR, sprint, workload, fatiga, readiness o riesgo de lesión.

---

# 9. COACH COPILOT — CONTRATO FINAL

Contrato canónico:

```text
llm/COACH_COPILOT_CONTRACT.md
```

La consulta se modela como composición de:

```text
ENTIDAD
+ OPERACIÓN
+ MÉTRICA(S)
+ AGREGACIÓN
+ ROL/POSICIÓN
+ FILTROS
+ VENTANA TEMPORAL
+ CONTEXTO CONVERSACIONAL
```

No se valida una lista de frases aisladas. Se valida el espacio de consultas.

Métricas queryables actuales:

```text
goals
assists
shots
passes_total
passes_completed
tackles_total
tackles_won
interceptions
turnovers
dispossessed
minutes
appearances
total_distance_m
peak_speed_m_s
max_acceleration_m_s2
min_acceleration_m_s2
latest_match_rating
avg_last5
trend_delta_5v5
```

Operaciones soportadas:
- retrieve;
- rank;
- compare players;
- compare role/position;
- trend;
- aggregate;
- explain evidence;
- data quality;
- follow-ups ordinales, temporales y de evidencia.

Agregaciones soportadas cuando corresponda:

```text
sum / mean / max / min / latest
```

Roles/posiciones cubiertos:

```text
GK  portero / guardameta
CB  central
FB  lateral / carrilero
DM  pivote / mediocentro defensivo
CM  mediocentro / centrocampista / interior
AM  mediapunta
W   extremo
ST  delantero / delantero centro / punta / atacante
```

Comparación por posición:
- si se pregunta `quién ha rendido mejor` dentro de un rol, el criterio explícito es **Match Rating medio en la muestra de ese rol**;
- las demás métricas son evidencia descriptiva;
- no se crea un score nuevo.

Prioridad de entidades:

```text
jugador concreto > palabra que coincide con una posición
```

Esto evita que nombres como `Portero Demo` o `Central Demo A` se interpreten como grupos posicionales.

Guardrails:
- fatiga/cansancio/readiness;
- riesgo de lesión;
- XI/titularidad;
- táctica/recomendación no validada;
- `mejor jugador`, `más completo`, `más determinante` sin criterio analítico aprobado;
- causalidad no soportada;
- métricas inexistentes.

Preflight final:
- entrada basura como `sss` → aclaración inmediata, 0 LLM;
- meta-consulta como `no puedes hacer nada` / `qué puedes hacer` → capacidades, 0 LLM;
- fuera de dominio obvio como teoría de juegos → rechazo inmediato, 0 LLM;
- Qwen/OpenAI quedan reservados para ambigüedad **dentro del dominio**.

Follow-ups soportados:

```text
¿Y el segundo?
¿Y el tercero?
¿Y en los últimos N partidos?
¿Qué evidencias tienes?
Sí, compáralos
Muéstrame las métricas
```

---

# 10. ANONIMIZACIÓN DEL ASSISTANT

En demo pública la capa de presentación usa exactamente las identidades de la plataforma:

```text
Equipo Demo
Jugador 01, Jugador 02, ...
Rival 01, Rival 02, ...
```

Boundary:

```text
alias visible
→ app/assistant_identity.py
→ identidad interna canónica
→ tools / DuckDB
→ respuesta interna
→ app/assistant_identity.py
→ alias visible
```

Si queda una identidad interna conocida antes de renderizar, la UI bloquea la respuesta en lugar de exponerla.

Contract tests cubren round-trip de jugador/rival y ausencia de fugas en comparaciones por rol.

---

# 11. VALIDACIÓN COACH COPILOT

## CI reproducible

Workflow:

```text
.github/workflows/tests.yml
→ pytest -q
→ build + validate synthetic public demo
→ python -m llm.validate_coach_contract --db data/football_performance_synthetic_demo.duckdb
```

Últimos gates verificados:

```text
37166566145  SUCCESS  query-space + roles + identity precedence
37167083614  SUCCESS  unit tests + synthetic demo + query-space + preflight
37167157174  SUCCESS  último main code gate tras ampliar smoke real
```

El validador CI cubre rankings, métricas, todas las posiciones, ventanas, follow-ups, guardrails, ruido/fuera de dominio y aliases demo sin usar LLM.

## Validación local real final — 04/10/2026

DuckDB profesional + `qwen3.5:4b` configurado:

```text
SMOKE CONTRACT: PASS (28/28)
average_elapsed=0.4s
```

Cobertura real del smoke final:
- rating y rating medio L5;
- distancia media, remates y asistencias;
- evolución, perfil natural y GPS de jugador;
- comparación entre jugadores;
- detalle de partido, estado de equipo y calidad de datos;
- guardrails de fatiga, lesión, titularidad y criterio no validado;
- comparación por posición;
- fuera de dominio, ruido y meta-consulta sin LLM;
- follow-ups ordinales, temporales y de evidencia;
- follow-up de comparación por posición.

Todos los casos del smoke final se resolvieron con `rounds=0`; no fue necesario activar fallback semántico para este contrato. El Coach Copilot local queda **congelado para entrega** salvo defecto real reproducible.

Gate reproducible:

```powershell
python llm\smoke_test_coach_agent.py
```

---

# 12. OPENAI BYOK

La página del Assistant permite:

```text
Local · Qwen
OpenAI API · clave propia
```

Reglas:
- la clave pertenece al usuario;
- no se guarda en DuckDB ni en archivos del proyecto;
- consultas claras se resuelven localmente y no consumen API;
- comparaciones por posición también son deterministas y provider-independent;
- preflight/guardrails se ejecutan antes de OpenAI;
- OpenAI solo puede seleccionar tools read-only permitidas;
- cada tool call se revalida localmente;
- tools desconocidas se descartan;
- OpenAI no tiene acceso directo a DuckDB.

Estado:

```text
implementation                 PASS
unit / contract tests          PASS
CI                             PASS
real OpenAI API call           NOT VALIDATED
```

La conexión inversa `ChatGPT → FPS` / MCP queda como extensión futura y no forma parte del MVP.

---

# 13. EXPERIMENTOS Y DECISIONES DESCARTADAS

LLM:

```text
qwen3:1.7b       rápido pero insuficiente semánticamente → descartado
qwen3.5:4b       aprobado como fallback, no como paso obligatorio
Gemma3:4b        tool calling HTTP 400 → descartado
Granite4.2:3b    benchmark inicial 9/9 pero fallos espontáneos + latencia → descartado como runtime final
```

DS/ML:
- change detection: experimental / no deploy;
- player similarity: exploratorio / no deploy;
- role/source-position classification: context-only / no deploy;
- no forzar ML cuando baseline/regla simple es más defendible;
- role-player-fit y Expert-vs-ML quedan bloqueados sin ground truth independiente suficiente.

Decisión de producto aprobada:

> FPS no depende de un LLM concreto. El conocimiento está en data + analytics + expert system + tools; Qwen/OpenAI son capas de interpretación.

---

# 14. ARCHIVOS IMPORTANTES

Producto:
- `app/streamlit_app.py`;
- `app/pages/2_Jugador.py`;
- `app/pages/3_Equip.py`;
- `app/pages/4_Partit.py`;
- `app/pages/5_Assistent_IA.py`;
- `app/data_access.py`;
- `app/presentation.py`;
- `app/assistant_identity.py`.

Coach Copilot:
- `llm/COACH_COPILOT_CONTRACT.md` — contrato canónico;
- `llm/coach_agent_fast.py` — entrada pública local, preflight y guards;
- `llm/coach_agent_general.py` — query grammar, router, tools y respuestas;
- `llm/coach_role_analysis.py` — comparaciones por posición;
- `llm/coach_agent_external.py` — OpenAI BYOK;
- `llm/validate_coach_contract.py` — gate automático CI;
- `llm/smoke_test_coach_agent.py` — gate real local.

Collector / GPS / engine:
- `collector/data_collector_futbol.html`;
- `collector/event_catalog.json`;
- `features/`;
- `analytics/`;
- `decision_tree/`;
- `gps/`.

Entrega:
- `README.md`;
- `docs/TFM_MANUSCRIPT_DRAFT.md` — manuscrito canónico;
- `docs/TFM_EVIDENCE_MATRIX.md`;
- `docs/TFM_METHODOLOGY_DRAFT.md`;
- `docs/TFM_RESULTS_DRAFT.md`;
- `docs/TFM_DISCUSSION_CONCLUSIONS_DRAFT.md`;
- `docs/TFM_SCREENSHOT_CHECKLIST.md`;
- `docs/TFM_SUBMISSION_CHECKLIST.md`.

---

# 15. PROBLEMAS ABIERTOS / LIMITACIONES

- OpenAI BYOK tiene contract tests pero no una llamada real con API key;
- no hay autenticación productiva completa;
- no hay validación causal con entrenadores/clubes;
- no publicar automáticamente el dataset profesional;
- no implementar MCP/ChatGPT→FPS antes de la entrega.

---

# 16. SIGUIENTE PASO EXACTO

```text
1. adaptar la memoria a la plantilla/rúbrica universitaria disponible
2. revisar bibliografía, numeración y referencias cruzadas conforme a esa plantilla
3. preparar y ensayar la defensa con el material estático disponible
4. congelar main para entrega
```

No volver al patrón `usuario prueba frases al azar → se añade una regla`. Los defectos del espacio soportado deben detectarse mediante contrato + tests paramétricos + CI.
