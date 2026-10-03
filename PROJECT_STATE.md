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
CAPTURAS REALES PRODUCTO              PENDIENTES
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
DATA
→ ANALYTICS
→ DECISION ENGINE
→ READ-ONLY TOOLS
→ ROUTER
→ OLLAMA LOCAL
→ SEMANTIC GUARD
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
LLM-02 COACH COPILOT                CERRADO / ES / SMOKE 4/4 PASS
REPORTS V6                          CERRADO / PASS
```

---

# COLLECTOR V1.1

Taxonomía congelada:

```text
collector/event_catalog.json
catalog_version=0.3.0
```

Variables principales:
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

FEATURE-01:

```text
28 features
23380 rows
6324 non-null
PASS
```

FEATURE-02:

```text
28 × 7 temporal operators
163660 rows
strict-past PASS
```

FEATURE-03:

```text
117735 rows
43060 non-null
590/835 player-match con rol observado
PASS
```

ANALYTICS-01:

```text
46760 rows
SELF_ROLE_PRIOR + PEER_ROLE_PRIOR
strict-past PASS
current-player exclusion PASS
equal-player weighting PASS
```

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

N9000 solo acepta GPS observado no sintético.

```text
observed non-synthetic GPS player-match=0
synthetic GPS excluded from expert evidence=PASS
```

---

# GPS

Flujo:

```text
provider file / synthetic demo
→ gps_imports
→ gps_player_map
→ gps_observations
→ player_match_gps_summary
→ dashboard / reports
```

Resumen:

```text
gps_physical_summary_v0.1-descriptive
```

Demo técnica:

```text
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
- Team;
- Player;
- Match;
- Físico/GPS;
- Attention Centre;
- Coach Copilot.

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

---

# COACH COPILOT

Perfil validado:

```text
model=qwen3:1.7b
scope=SPANISH_ONLY_MVP
thinking=False
FPS_AGENT_NUM_CTX=1536
FPS_AGENT_TIMEOUT=18
keep_alive=30m
```

Warm-up y runtime deben usar mismo `num_ctx`.

Gate:

```text
router=17/17
aggregate=66/68=97.1%
runtime_errors=0
safety_failures=0
numeric_grounding=PASS
castellano=PASS
subject_contract=PASS
average_latency<=12s PASS
LOCAL AGENT CONTRACT=PASS 4/4
```

No validados:
- ranking por rol;
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

QA:

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

CI:

```text
.github/workflows/tests.yml
push + pull_request + workflow_dispatch
Python 3.13
pytest
synthetic demo rebuild + validation
```

Run limpio de referencia confirmado:

```text
37081464123 = SUCCESS
```

---

# MEMORIA ACADÉMICA — FUENTES CANÓNICAS

Manuscrito único:
- `docs/TFM_MANUSCRIPT_DRAFT.md`.

Documentos de soporte:
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

Índice/pies:
- `docs/figures/README.md`.

Estado académico:

```text
manuscrito integrado              CREADO
marco teórico                     CREADO
bibliografía base                 CREADA
metodología                       CREADA
resultados                        CREADOS
 discusión / limitaciones         CREADAS
conclusiones                      CREADAS
tablas                            CREADAS
figuras técnicas                  CREADAS
anexos                            CREADOS
checklist entrega                 CREADA
guion defensa                     CREADO
capturas reales                   PENDIENTES
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
- PDF downstream de analytics;
- demo pública sintética separada del dataset profesional;
- CI automático obligatorio;
- hipótesis limitada a viabilidad técnica/auditable.

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
- inventar validación con usuarios.

---

# PROBLEMAS ABIERTOS

Externos / pendientes:
- plantilla/rúbrica universitaria;
- capturas reales del producto local;
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

**No seguir redactando más texto genérico ni añadir funciones.**

1. ejecutar la app local en modo demo;
2. producir las 10 capturas reales definidas en `docs/TFM_SCREENSHOT_CHECKLIST.md`;
3. revisar visualmente esas capturas y seleccionar cuáles van al cuerpo/anexos;
4. adaptar `docs/TFM_MANUSCRIPT_DRAFT.md` a la plantilla oficial cuando esté disponible;
5. maquetar tablas/figuras/capturas;
6. cerrar anexos y bibliografía;
7. crear presentación final y ensayar defensa.
