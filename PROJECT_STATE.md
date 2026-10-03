# PROJECT_STATE

Última actualización: 03/10/2026

Memoria técnica operativa del proyecto. Si contradice un chat antiguo, prevalecen el código actual de `main` y este archivo.

---

# 1. Estado actual

```text
DATA-01/02/03/04                    CERRADO / VALIDADO
COLLECTOR-01                        CERRADO / V1.1 OFICIAL / FINAL GATE PASS
GPS-01 NORMALIZATION                CERRADO / VALIDADO ESTRUCTURALMENTE
GPS-DEMO SYNTHETIC                  CERRADO / VALIDADO
GPS PHYSICAL SUMMARY                CERRADO / VALIDADO / REAL > SYNTHETIC
FEATURE-01/02/03                    CERRADO / VALIDADO
ANALYTICS-01                        CERRADO / VALIDADO
EXPERT-01..07 N1000-N13000          BASELINE CERRADO / VALIDADO
PERF-18 MATCH RATING                CERRADO / V5 ACTIVA / CONGELADA
PERFORMANCE INDEX                   v0.2 EXPERIMENTAL / OPERATIVO
DASHBOARD TEAM / PLAYER / MATCH     OPERATIVO / QA PASS
DASHBOARD PHYSICAL / GPS            CERRADO / VALIDADO
ALERTS-01 ATTENTION CENTRE          CERRADO / VALIDADO v0.3
UI-PRESENTATION-ES-DEMO             CONTRACT PASS
ACCESS-CONTROL-01                   CONTRACT PASS / AUTH REAL PENDIENTE
LLM-01                              CONTRATOS PASS
LLM-02 LOCAL COACH COPILOT          CERRADO MVP / CASTELLANO / SMOKE 4/4 PASS
REPORTS-03 ELITE REPORTS            CERRADO / V6 / GATE PASS
PUBLIC DEMO ANONYMIZED              PASS / NO REDISTRIBUIBLE
PUBLIC DEMO SYNTHETIC               CERRADO / PASS / REDISTRIBUIBLE
REPRODUCIBILITY                     CERRADO / PASS
CI AUTOMÁTICO                       ACTIVO / PASS
GLOBAL END-TO-END QA                CERRADO / PASS
TFM MARCO TEÓRICO                   BORRADOR ACADÉMICO CREADO
TFM METODOLOGÍA                     BORRADOR ACADÉMICO CREADO
TFM RESULTADOS                      BORRADOR ACADÉMICO CREADO
TFM DISCUSIÓN / CONCLUSIONES        BORRADOR ACADÉMICO CREADO
TFM EVIDENCE MATRIX                 CREADA
TFM TABLAS RESULTADOS               CREADAS
TFM FIGURAS ARQUITECTURA            5 SVG CREADOS
TFM SCREENSHOT CHECKLIST            CREADA / CAPTURAS REALES PENDIENTES
TFM DEFENSE OUTLINE                 CREADO
FINAL-01                            PRODUCTO FUNCIONAL / CIERRE ACADÉMICO
PUBLIC DEPLOYMENT                   NO HACER — derechos dataset real no resueltos
```

---

# 2. Hipótesis principal

> **Un equipo de fútbol amateur o semiprofesional puede disponer de un sistema integral y auditable de soporte a la decisión a partir de datos de vídeo y GPS opcional, capaz de transformarlos en información sobre rendimiento, evolución, rol y comportamiento físico de los jugadores y del equipo.**

Estado del contraste:

```text
viabilidad técnica / arquitectónica    FAVORABLEMENTE CONTRASTADA
mejora causal decisiones entrenador    NO DEMOSTRADA
mejora rendimiento deportivo           NO DEMOSTRADA
fatiga / readiness / lesión            NO DEMOSTRADO / NO IMPLEMENTADO
impacto comercial                      NO VALIDADO
```

---

# 3. Arquitectura vigente

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

> Una capa superior no puede inventar métricas, scores, rankings o recomendaciones que no existan en una capa inferior validada.

Arquitectura LLM:

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

El LLM no calcula Match Rating, Performance Index, features críticas ni decisiones expertas.

---

# 4. Variables aprobadas — Collector V1.1

Unidad principal: jugador-partido.

Identificación/contexto:
- jugador;
- dorsal editable;
- titular/suplente;
- minutos;
- partido/equipo/rival/fecha;
- formación;
- rol/posición/lado/cambios de rol.

Eventos:
- pase normal/largo/centro × éxito/fallo;
- pase clave;
- asistencia;
- regate éxito/fallo;
- pérdida;
- remate: gol/a puerta/fuera/bloqueado;
- entrada;
- intercepción;
- bloqueo;
- despeje;
- falta cometida/recibida con x/y;
- tarjeta amarilla/roja;
- segunda amarilla como roja con flag;
- penal ganado/concedido con resultado;
- parada;
- gol encajado;
- córner a favor/en contra con resultado de ABP.

Taxonomía congelada:

```text
collector/event_catalog.json
catalog_version=0.3.0
```

No recoger manualmente:
- xG;
- posesión avanzada;
- PPDA;
- pressing;
- heatmaps;
- fatiga;
- métricas derivables automáticamente.

---

# 5. Data / Feature / Analytics

DuckDB con separación explícita:

```text
master
→ raw observations
→ raw aggregates
→ derived features
→ analytics evidence
→ decision results
```

Caso profesional de desarrollo:

```text
matches=38
players context=36
played appearances=590
```

FEATURE-01:
- 28 features base;
- 23.380 filas;
- 6.324 non-null;
- PASS.

FEATURE-02:
- 28 × 7 operadores temporales;
- 163.660 filas;
- strict-past;
- PASS.

FEATURE-03:
- 117.735 filas;
- 43.060 non-null;
- 590/835 player-match con rol observado;
- no inventa rol faltante;
- PASS.

ANALYTICS-01:
- 46.760 filas;
- `SELF_ROLE_PRIOR` + `PEER_ROLE_PRIOR`;
- strict-past;
- current-player excluido del peer pool;
- equal-player weighting;
- PASS.

---

# 6. Match Rating / Performance Index

Match Rating:

```text
version=match_rating_v0.5-candidate
coverage=590/590
matches=38
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

V5 permanece congelada. No modificar fórmula/pesos sin nueva evidencia y validación.

Performance Index:

```text
performance_score_v0.2-experimental
```

Es capa histórica/posicional complementaria; no sustituye Match Rating.

---

# 7. Expert System

Familias:

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

Contrato de nodo:

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

N13000 no emite recomendación táctica sin policy validada.

N9000 solo acepta GPS observado no sintético como evidencia física.

Estado actual:

```text
observed non-synthetic GPS player-match for expert=0
Synthetic demo GPS excluded from expert evidence=PASS
```

---

# 8. GPS

Flujo canónico:

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

Demo integración:

```text
generator_version=gps_synthetic_demo_v1.2.0
imports=38
mappings=590
observations=38197
summaries/latest=590
REAL_OVER_SYNTHETIC=PASS
```

No existen thresholds canónicos de HSR, sprint, workload, fatiga, readiness o riesgo de lesión.

GPS no modifica Match Rating ni Performance Index.

---

# 9. Dashboard / producto

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

Access control estructural:
- SUPERADMIN;
- CLUB_ADMIN;
- STAFF.

Autenticación real email/password/session: no implementada.

---

# 10. LLM-02 Coach Copilot

MVP oficial: castellano.

Perfil local validado:

```text
model=qwen3:1.7b
scope=SPANISH_ONLY_MVP
thinking=False
FPS_AGENT_NUM_CTX=1536
FPS_AGENT_TIMEOUT=18
keep_alive=30m
```

Regla operativa:
- warm-up y runtime deben usar mismo `num_ctx`;
- `512 → 1536` provocaba reload y timeout de primera síntesis;
- `llm/validate_local_agent.py` corregido;
- reiniciar Ollama si `/api/tags` queda bloqueado es incidencia operativa, no regresión automática del producto.

Gate final:

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
- player similarity como función final;
- predicción futura;
- XI ideal;
- recomendaciones tácticas automáticas;
- fatiga/readiness/lesión.

---

# 11. Reports V6

```text
report_metrics=report_descriptive_v0.2
schema=0.7.0
Team=4 páginas
Player=3 páginas
Match=3 páginas
REPORTS ELITE TECHNICAL GATE V6=PASS
```

Los PDF consumen analytics materializados y no recalculan lógica crítica.

---

# 12. QA global

```text
Fase 1 — Data/Core          PASS
Fase 2 — Analytics/Expert   PASS
Fase 3A — Product           PASS
Fase 3B — Delivery          PASS
GLOBAL END-TO-END QA        PASS
```

Cadena cubierta:

```text
Collector
→ DuckDB
→ Features
→ Analytics
→ Match Rating
→ GPS
→ Expert
→ Dashboard
→ Access Control
→ Demo Presentation
→ Coach Copilot
→ PDF
→ Publication
```

---

# 13. Reproducibilidad + CI

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

Match Rating y Performance Index de esta demo son fixtures sintéticos de compatibilidad, no revalidación científica.

CI:

```text
.github/workflows/tests.yml
triggers=push + pull_request + workflow_dispatch
Python=3.13
pytest=enabled
synthetic demo rebuild=enabled
```

Run de referencia confirmado:

```text
37081464123 → SUCCESS
```

---

# 14. Memoria académica — estado real

Documentos canónicos:

- `docs/TFM_MANUSCRIPT_ASSEMBLY.md` — estructura final de la memoria;
- `docs/TFM_MEMORIA_BASE.md` — narrativa inicial;
- `docs/TFM_MARCO_TEORICO_REFERENCIAS.md` — marco teórico + bibliografía;
- `docs/TFM_METHODOLOGY_DRAFT.md` — metodología integrada;
- `docs/TFM_RESULTS_DRAFT.md` — resultados basados en gates;
- `docs/TFM_DISCUSSION_CONCLUSIONS_DRAFT.md` — discusión, limitaciones y conclusiones;
- `docs/TFM_EVIDENCE_MATRIX.md` — control de claims;
- `docs/TFM_TABLES_RESULTS.md` — tablas canónicas;
- `docs/TFM_FIGURES_TABLES_PLAN.md` — plan visual;
- `docs/TFM_SCREENSHOT_CHECKLIST.md` — capturas reales pendientes;
- `docs/TFM_DEFENSE_OUTLINE.md` — guion base de defensa.

Figuras reproducibles creadas:

- `docs/figures/tfm_architecture_overview.svg`;
- `docs/figures/tfm_llm_grounding.svg`;
- `docs/figures/tfm_strict_past.svg`;
- `docs/figures/tfm_expert_system.svg`;
- `docs/figures/tfm_data_model.svg`;
- `docs/figures/README.md` contiene pies y reglas de uso.

Estado:

```text
Introducción / hipótesis       BASE DISPONIBLE
Marco teórico                  BORRADOR COMPLETO
Metodología                    BORRADOR COMPLETO
Arquitectura                   DOCUMENTADA + FIGURAS
Resultados                     BORRADOR COMPLETO
Discusión                      BORRADOR COMPLETO
Limitaciones                   BORRADOR COMPLETO
Conclusiones                   BORRADOR COMPLETO
Bibliografía                   BASE CURADA
Tablas de resultados           CREADAS
Figuras técnicas               5 SVG CREADOS
Capturas producto              PENDIENTES
Anexos                         ESTRUCTURA DEFINIDA
Plantilla universitaria        PENDIENTE
Maquetación final              PENDIENTE
Defensa                        GUION BASE CREADO
```

---

# 15. Experimentos / decisiones aprobadas

- Collector V1.1 congelado sobre `event_catalog v0.3.0`;
- Match Rating V5 congelado;
- Performance Index separado del Match Rating;
- sistema experto jerárquico preferido frente a un único DecisionTreeClassifier;
- ML solo si supera baseline simple con target defendible;
- línea ML de posición cerrada como context-only;
- LLM downstream y read-only;
- MVP LLM oficial en castellano;
- control de acceso separado de autenticación;
- GPS real > synthetic;
- GPS synthetic no cuenta como evidencia física observada;
- no inferir rol específico sin evidencia;
- PDF downstream de analytics;
- demo pública sintética separada del caso profesional;
- CI automático obligatorio;
- hipótesis principal limitada a viabilidad técnica/auditable.

---

# 16. Decisiones descartadas / aplazadas

- recrear Opta/StatsBomb/tracking profesional;
- recoger manualmente métricas avanzadas derivables;
- LLM bilingüe para MVP;
- optimización indefinida de qwen3:1.7b;
- confiar solo en pass rate automático;
- XI ideal / recomendación táctica sin policy validada;
- fatiga / lesión / readiness sin datos y validación;
- inferir rol de suplentes sin evidencia;
- publicar dataset profesional sin derechos;
- login SaaS completo en el MVP;
- PDF como captura literal de la web;
- inventar validación con entrenadores/usuarios;
- añadir ML solo por complejidad académica.

---

# 17. Problemas abiertos

- adaptar memoria a plantilla/rúbrica oficial cuando esté disponible;
- realizar capturas reales del producto en modo demo;
- ensamblar texto académico final en un único manuscrito;
- revisar formato bibliográfico exigido;
- producir anexos finales y referencias cruzadas;
- preparar defensa final y plan B de demo;
- opcional: validación con entrenadores/analistas reales;
- opcional: estudio interobservador del Collector;
- opcional: GPS real;
- autenticación completa solo si evoluciona a producto comercial;
- resolver licencia antes de cualquier redistribución del dataset profesional.

---

# 18. Siguiente paso exacto

1. producir las capturas reales definidas en `docs/TFM_SCREENSHOT_CHECKLIST.md`;
2. insertar tablas y figuras ya creadas en el manuscrito académico único;
3. ensamblar Introducción → Marco teórico → Metodología → Arquitectura → Resultados → Discusión → Limitaciones → Conclusiones;
4. adaptar estructura, extensión y referencias a la plantilla/rúbrica oficial cuando se disponga de ella;
5. cerrar anexos;
6. preparar presentación/defensa utilizando `docs/TFM_DEFENSE_OUTLINE.md`;
7. no añadir nuevas funcionalidades deportivas salvo defecto real o nueva evidencia.