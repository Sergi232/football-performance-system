# PROJECT_STATE

Última actualización: 03/10/2026

Fuente de verdad operativa del proyecto junto con el código actual de `main`. Si contradice un chat antiguo, prevalece este archivo.

---

# ESTADO EJECUTIVO

```text
PRODUCTO FUNCIONAL                    CERRADO / VALIDADO
GLOBAL END-TO-END QA                  PASS
REPRODUCIBILIDAD                      PASS
CI AUTOMÁTICO                         ACTIVO / PASS
DEMO PÚBLICA SINTÉTICA                PASS / REDISTRIBUIBLE
UI FINAL PRESENTATION AUDIT           CERRADO / CORREGIDO / CI PASS
LLM-02 COACH COPILOT                  REABIERTO — GRANITE RUNTIME / LOCAL E2E PENDIENTE
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
CAPTURAS REALES PRODUCTO              EN CURSO — ESPERAR CIERRE LLM-02
PLANTILLA / RÚBRICA UNIVERSIDAD       PENDIENTE EXTERNO
PUBLIC DEPLOYMENT                     NO HACER — licencia dataset real no resuelta
```

No añadir nueva funcionalidad deportiva salvo defecto real o nueva evidencia.

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

LLM:

```text
QUESTION
→ OLLAMA LOCAL / TOOL SELECTION
→ READ-ONLY TOOLS
→ DATA / ANALYTICS / DECISION ENGINE
→ STRUCTURED EVIDENCE
→ OLLAMA LOCAL / SYNTHESIS
→ NUMERIC / POLICY GUARD
→ COACH
```

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
LLM-01                              PASS
LLM-02 COACH COPILOT                REABIERTO — GRANITE / LOCAL E2E PENDIENTE
REPORTS V6                          CERRADO / PASS
```

---

# COLLECTOR V1.1

Taxonomía congelada:

```text
collector/event_catalog.json
catalog_version=0.3.0
```

Variables aprobadas:
- jugador, dorsal, titular/suplente, minutos;
- partido, equipo, rival, fecha, formación;
- rol/posición, lado y cambios;
- pase normal/largo/centro × éxito/fallo;
- pase clave y asistencia;
- regate y pérdida;
- remate: gol/a puerta/fuera/bloqueado;
- entrada, intercepción, bloqueo, despeje;
- falta cometida/recibida con x/y;
- tarjeta amarilla/roja;
- penal ganado/concedido con resultado;
- parada y gol encajado;
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

Match Rating activo:

```text
match_rating_v0.5-candidate
coverage=590/590
outfield PERF18_ANCHORED=380
goalkeeper route=38
generic role fallback=172
nulls=0
duplicates=0
out_of_range=0
mean=6.388
median=6.257
q10=5.757
q90=7.216
min=3.206
max=9.554
```

V5 congelada. No modificar sin nueva evidencia + experimento + validación.

Performance Index:

```text
performance_score_v0.2-experimental
```

Capa histórica/posicional complementaria.

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

Final:

```text
engine_version=expert_0.7.0
decision_rows=154475
N13000_rows=2505
NO_EVIDENCE=89
POLICY_UNVALIDATED=501
ROLE_UNKNOWN=245
```

N13000 no recomienda sin policy validada.

N9000 solo acepta GPS observado no sintético:

```text
observed non-synthetic GPS player-match=0
synthetic GPS excluded from expert evidence=PASS
```

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

# PRODUCTO

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

## UI FINAL PRESENTATION AUDIT — CERRADO 03/10/2026

La revisión visual real de Team/Match/Player/GPS/Alerts detectó inconsistencias que los gates estructurales no cubrían. Se corrigieron sin cambiar analytics ni arquitectura:

- badges técnicos públicos (`match_rating_v0.5-candidate`, `performance_score_v0.2-experimental`, GPS/Attention versions) → labels de producto amigables;
- `TEAM MODE`, `PLAYER MODE`, `MATCH MODE`, `COACH COPILOT`, `ATTENTION CENTRE · DATA QUALITY` → castellano de presentación;
- `Coach Brief` → `Resumen técnico`;
- `GOALKEEPER_SEPARATE_PRO_REFERENCE_SHOT90_DIST10` y paths internos → texto de entrenador;
- `Shot-stopping` → `Paradas`;
- advertencia ambigua `rating V2` → `modelo de respaldo de Match Rating V5`;
- tablas Match Mode con columnas raw → columnas de producto;
- `H/A` bajo cabecera `L/V` en Player/GPS → `L/V` real;
- Attention Centre: catalán residual y códigos `CONTEXT_LIMITATION`, `ROLE_CONTEXT_UNAVAILABLE`, source layers → labels castellanos legibles;
- Assistant trace: nombres internos de tools → nombres de consultas legibles;
- sugerencia de similitud/rol ambiguo del Assistant → pregunta soportada de evolución;
- Performance Index: `baseline`, `N fallback` y fallback de evidencia raw → terminología final.

Cambios principales:
- `app/coach_ui.py` sanitización central de labels;
- `app/pages/1_Performance_Index.py`;
- `app/pages/2_Jugador.py`;
- `app/pages/4_Partit.py`;
- `app/pages/5_Assistent_IA.py`;
- `app/pages/6_Fisic_GPS.py`;
- `app/pages/7_Alertes.py`;
- `analytics/build_attention_flags.py`;
- `app/validate_demo_presentation.py`;
- `tests/test_ui_presentation_contract.py`.

Validación GitHub Actions:

```text
run=37085564464
unit + contract tests=PASS
synthetic public demo rebuild + validation=PASS
conclusion=SUCCESS
```

La revisión visual debe repetirse tras `git pull`; no reutilizar las capturas anteriores como figuras finales.

---

# COACH COPILOT

## Decisión anterior — SUPERADA COMO RUNTIME FINAL

El perfil previo `qwen3:1.7b + router por patrones + semantic guard determinista` alcanzó sus gates definidos, pero una prueba visual con preguntas espontáneas reveló baja cobertura conversacional. El 97,1% era válido sobre el Golden Set existente, no sobre lenguaje libre de entrenador.

Benchmark local comparativo 03/10/2026:

```text
qwen3:1.7b
- rápido (~3-12 s warm)
- FALLA selección semántica compleja de tools
- FALLA guardrail espontáneo de cansancio

qwen3.5:4b
- 5/5 tool-selection benchmark PASS
- guardrail PASS
- ~55-61 s por selección de tool en el PC objetivo → demasiado lento como runtime principal

gemma3:4b
- tool calling Ollama: HTTP 400 → descartado para esta arquitectura

granite4.2:3b
- goals / assists tool selection PASS
- player / GPS selecciona tool correcta pero devuelve alias corto `07`
- match-detail no seleccionado en benchmark inicial
- ~8-11 s warm en la mayoría de casos
- candidato elegido por equilibrio calidad / latencia
```

## Runtime candidato actual

```text
model=granite4.2:3b
scope=SPANISH_ONLY_MVP
thinking=False
FPS_AGENT_NUM_CTX=1536
FPS_AGENT_TIMEOUT=75
keep_alive=30m
```

Arquitectura implementada:

```text
question
→ Granite tool selection
→ bounded read-only tools
→ Python/DuckDB + analytics/expert outputs
→ compact structured evidence
→ Granite synthesis
→ numeric/policy guard
→ coach
```

Cambios:
- `llm/coach_agent_granite.py` nuevo runtime;
- `llm/coach_agent_fast.py` mantiene API y delega a Granite;
- `query_team_stats` añade rankings descriptivos de goles, asistencias, remates, minutos y apariciones;
- normalización de argumentos `07 → Jugador 07` y `09 → Rival 09 / match_id`;
- ninguna pregunta desconocida cae por defecto en `get_team_snapshot`;
- guardrails explícitos para fatiga/cansancio, lesión, XI ideal y recomendación táctica;
- el LLM redacta la respuesta normal; el guard solo controla grounding numérico y policy;
- `tests/test_coach_agent_granite.py` cubre modelo, aliases, guardrails, tools y grounding;
- `llm/validate_local_agent.py` contiene el gate end-to-end real de 9 casos.

CI estructural del nuevo runtime:

```text
run=37150798394
unit + contract tests=PASS
synthetic public demo rebuild + validation=PASS
conclusion=SUCCESS
```

Estado:

```text
código / contratos / CI              PASS
selección de modelo                  GRANITE 4.2 3B CANDIDATO
local end-to-end con DuckDB real     PENDIENTE
cierre LLM-02                        PENDIENTE DEL GATE LOCAL
```

No validados y por tanto no permitidos:
- ranking por rol como recomendación;
- similarity final;
- predicción futura;
- XI ideal;
- recomendación táctica automática;
- fatiga/readiness/lesión.

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

Runs de referencia:

```text
37081464123 = SUCCESS — reproducibilidad inicial
37085564464 = SUCCESS — UI final presentation audit
37150798394 = SUCCESS — Granite runtime contracts / synthetic demo
```

---

# MEMORIA ACADÉMICA — FUENTES CANÓNICAS

Manuscrito único:
- `docs/TFM_MANUSCRIPT_DRAFT.md`.

Soporte:
- `docs/TFM_MANUSCRIPT_ASSEMBLY.md`;
- `docs/TFM_MEMORIA_BASE.md`;
- `docs/TFM_MARCO_TEORICO_REFERENCIAS.md`;
- `docs/TFM_METHODOLOGY_DRAFT.md`;
- `docs/TFM_RESULTS_DRAFT.md`;
- `docs/TFM_DISCUSSION_CONCLUSIONS_DRAFT.md`;
- `docs/TFM_EVIDENCE_MATRIX.md`;
- `docs/TFM_TABLES_RESULTS.md`;
- `docs/TFM_ANNEXES_DRAFT.md`;
- `docs/TFM_SCREENSHOT_CHECKLIST.md`;
- `docs/TFM_DEFENSE_OUTLINE.md`;
- `docs/TFM_SUBMISSION_CHECKLIST.md`.

Figuras reproducibles:
- `docs/figures/tfm_architecture_overview.svg`;
- `docs/figures/tfm_llm_grounding.svg`;
- `docs/figures/tfm_strict_past.svg`;
- `docs/figures/tfm_expert_system.svg`;
- `docs/figures/tfm_data_model.svg`.

Estado:

```text
manuscrito integrado              CREADO
marco teórico / bibliografía      CREADOS
metodología / resultados          CREADOS
discusión / conclusiones          CREADAS
tablas / figuras / anexos         CREADOS
guion defensa                     CREADO
capturas reales                   EN CURSO — ESPERAR CIERRE LLM-02
plantilla universitaria           PENDIENTE
maquetación final                 PENDIENTE
presentación final                PENDIENTE
```

---

# DECISIONES APROBADAS

- MVP funcional antes de aumentar complejidad;
- Collector V1.1 congelado;
- raw / features / analytics / decision / LLM separados;
- strict-past obligatorio;
- Match Rating V5 congelado;
- Performance Index separado;
- experto jerárquico y auditable;
- ML solo con target defendible y contra baseline simple;
- GPS opcional, real > synthetic;
- synthetic GPS no es evidencia física observada;
- no inferir rol sin evidencia;
- LLM downstream y read-only;
- MVP LLM castellano;
- selección de tool guiada por modelo, no por un listado creciente de `if` semánticos;
- guardrails de policy pueden ser deterministas;
- pregunta no soportada no cae en un resumen genérico del equipo;
- PDF downstream de analytics;
- demo pública sintética separada del dataset profesional;
- CI automático obligatorio;
- hipótesis limitada a viabilidad técnica/auditable;
- UI final debe mostrar lenguaje de producto, no tokens internos; trazabilidad técnica queda en expanders/metodología.

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
- gemma3:4b como runtime de tool calling con Ollama actual.

---

# PROBLEMAS ABIERTOS

Prioridad inmediata:
- ejecutar `llm/validate_local_agent.py` con Granite + DuckDB real;
- corregir solo fallos observados del gate local;
- cerrar LLM-02 si el gate real pasa;
- después recapturar Asistente IA y el resto de capturas definitivas.

Externos / pendientes:
- plantilla/rúbrica universitaria;
- formato bibliográfico definitivo;
- maquetación final;
- presentación/defensa final;
- licencia antes de redistribuir dataset profesional.

Mejoras opcionales, no inventar:
- estudio interobservador;
- validación con entrenadores/analistas;
- GPS real;
- validación externa Match Rating;
- ground truth N13000;
- Expert vs ML independiente.

---

# SIGUIENTE PASO EXACTO

**No añadir más funciones antes del gate local del nuevo agente.**

1. `git pull --ff-only`;
2. ejecutar `python llm\validate_local_agent.py` con `FPS_DB_PATH` apuntando a la DuckDB profesional y `granite4.2:3b`;
3. si falla, corregir únicamente los casos observados;
4. si pasa, cerrar LLM-02 y revisar visualmente el Asistente IA;
5. producir exactamente las 10 capturas canónicas de `docs/TFM_SCREENSHOT_CHECKLIST.md`: Collector, Team, Player, Match, GPS, Attention, Coach Copilot y los tres PDF;
6. seleccionar cuerpo/anexos y continuar maquetación final.
