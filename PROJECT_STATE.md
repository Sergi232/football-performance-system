# PROJECT_STATE

Última actualización: 26/09/2026

Memoria técnica operativa del proyecto. Si contradice un chat antiguo, prevalece este archivo.

## 1. Estado actual

```text
DATA-01/02/03/04                    CERRADO / VALIDADO
COLLECTOR-01 MVP                    CERRADO FUNCIONALMENTE
GPS-01                              CERRADO / VALIDADO
FEATURE-01/02/03                    CERRADO / VALIDADO
EXPERT-01..07 N1000-N13000          BASELINE CERRADO / VALIDADO
LLM-01/02                           PROTOTYPE v0.1 / CONTRATOS PASS
REPORTS-01                          PROTOTYPE v0.1 / CONTRATO PASS
PUBLICATION-01                      CERRADO / VALIDADO TÉCNICAMENTE
DASHBOARD-01                        PROTOTYPE v0.1 / CONTRACT PASS
ARCHITECTURE-01                     CERRADO — ISSUE #25
ANALYTICS-01                        CERRADO / VALIDADO — ISSUE #26
DECISION POLICY / N13000            GATE APROBADO — ISSUE #27 CERRADO
DSAI-01A FEASIBILITY AUDIT          CERRADO — ISSUE #28
DSAI-02 CHANGE DETECTION            CERRADO EXPERIMENTAL / NO DEPLOY — ISSUE #29
DSAI-03 PLAYER SIMILARITY           CERRADO EXPLORATORIO / NO DEPLOY — ISSUE #32
DSAI-04 ROLE-LABEL AUDIT            ACTIVO
FINAL-01                            BLOQUEADO HASTA REDISEÑO DE PRODUCTO
```

## 2. Forma de trabajo

Flujo architecture-first + gated. GitHub es la fuente de verdad.

Documentos principales:
1. `PROJECT_STATE.md`;
2. `docs/ARCHITECTURE.md`;
3. `docs/DECISIONS.md`;
4. `docs/WORKFLOW.md`;
5. `docs/DATA_SCIENCE_AI_STRATEGY.md`;
6. `docs/DSAI_EXPERIMENT_PLAN.md`;
7. `README.md`.

## 3. Arquitectura vigente

```text
CAPTURE / IMPORT
→ RAW + NORMALIZED DATA
→ FEATURE ENGINE
→ ANALYTICS ENGINE
→ DECISION ENGINE
→ DS / ML EXPERIMENTAL CORE
→ PRODUCT SERVICE LAYER
→ WEB / REPORTS / AI ASSISTANT
→ QA / PUBLICATION
```

Una capa superior no puede inventar métricas, rankings, evaluaciones o recomendaciones que no existan en una capa inferior validada.

## 4. Prioridad académica

El TFM es de Data Science e IA. El producto web es el vehículo final, pero el núcleo académico debe quedar demostrado en data engineering, feature engineering leakage-safe, analytics estadístico, sistema experto auditable, experimentación DS/ML, validación/explicabilidad e IA generativa como capa final.

## 5. Baseline de datos

Caso de desarrollo: Deportivo Alavés 2025/26.

```text
matches=38
players=36
player_match=835
FEATURE-01=28 features
FEATURE-02=temporal strict-past
FEATURE-03=temporal same-role strict-past
observed roles=590/835 player-match
raw role labels=23
```

## 6. ANALYTICS-01 — CERRADO

DG-AN-01 = C:
- `SELF_ROLE_PRIOR`;
- `PEER_ROLE_PRIOR`;
- siempre separados.

Validación:
```text
analytics rows=46760
SELF_ROLE_PRIOR=23380
PEER_ROLE_PRIOR=23380
strict-past peer checks=PASS
FEATURE-03 provenance=PASS
no score/ranking/recommendation=PASS
```

## 7. N13000 policy

DG-N13-01 = C.

Contrato objetivo futuro: recomendación + confianza/calibración + evidencia + justificación + limitaciones + alternativa. Aún no se autoriza ninguna recomendación porque no hay criterios/thresholds/calibración validados.

## 8. DSAI-01A — FEASIBILITY AUDIT CERRADO

```text
player_similarity_profiles        GO_EXPLORATORY
change_detection_evolution        GO_EXPERIMENT
observed_role_classification      CANDIDATE_SUPERVISED
role_player_fit                   REFORMULATE_TARGET
expert_vs_ml                      BLOCKED_SHARED_TARGET
n13000_recommendation_calibration BLOCKED_GROUND_TRUTH
```

## 9. DSAI-02 — CHANGE DETECTION CERRADO EXPERIMENTAL

Cobertura:
```text
evaluable_rows=3647
players=25
roles=18
features=25
```

Validación sintética:
```text
0.5 std  AUC=0.2365
1.0 std  AUC=0.5341
1.5 std  AUC=0.7211
2.0 std  AUC=0.8024
```

Decisión: `EXPERIMENTALLY_USEFUL / NO_DEPLOY` por ausencia de ground truth real de change-points.

## 10. DSAI-03 — PLAYER SIMILARITY CERRADO EXPLORATORIO

Issue #32. Script: `dsai/player_similarity_experiment.py`.

Resultado local:
```text
profiles=64
players=24
roles=22
features=28
profiles_with_neighbour=61
temporal_eligible=22
same_neighbour=5
retention_rate=0.22727272727272727
pair_distance_corr=0.2143880082112036
```

Decisión: `EXPLORATORY_RESULT / NO_DEPLOY`.

La estabilidad temporal es insuficiente para exponer ahora “jugadores similares” como funcionalidad de producto. El resultado se conserva como evidencia académica negativa/limitada y como baseline para repetir con más datos y una taxonomía de roles validada.

## 11. DSAI-04 — ROLE-LABEL AUDIT ACTIVO

Objetivo: decidir si `primary_role` puede utilizarse de forma defendible como target supervisado antes de entrenar ningún clasificador.

Motivo:
- 23 raw labels;
- `Substitute` concentra 172 filas;
- la importación de lineups documenta que `position='Substitute'` es un estado de banquillo y no un rol táctico específico;
- no se agruparán etiquetas por intuición.

Audit requerido:
- distribución por label, jugadores, titularidad y minutos;
- diagnóstico de `Substitute`;
- coexistencia del mismo jugador con roles tácticos;
- transiciones temporales de labels;
- sparsity del target;
- conclusión metodológica sobre target raw.

Script: `dsai/role_label_audit.py`.

## 12. Líneas bloqueadas

- role/player fit: sin target independiente;
- Expert vs ML: sin shared target independiente;
- N13000 calibration: sin ground truth;
- GPS ML: 0 observaciones;
- role classification: bloqueada hasta cerrar DSAI-04.

## 13. Producto actual

Dashboard, Reports y Assistant continúan como prototipo v0.1. Después del núcleo DS/IA: Product UX insight-first → Reports-02 → arquitectura LLM final → Product Service Layer → publicación/TFM.

## 14. Decision gates pendientes

- `DG-UX-01`;
- `DG-LLM-01`;
- `DG-REP-01`;
- `DG-PUB-01`.

## 15. Siguiente paso exacto

```powershell
cd C:\Users\sergi\Desktop\football-performance-system
git pull
python dsai\role_label_audit.py
```

Después A5 decide si la clasificación supervisada de rol es metodológicamente defendible y con qué target exacto, o si se documenta como no viable con este dataset.