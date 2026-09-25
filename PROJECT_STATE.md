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

El TFM es de Data Science e IA. El producto web es el vehículo final, pero el núcleo académico debe quedar demostrado en:
- data engineering;
- feature engineering leakage-safe;
- analytics estadístico;
- sistema experto auditable;
- experimentación DS/ML;
- validación y explicabilidad;
- IA generativa como capa final, no como motor de cálculo.

## 5. Baseline de datos

Caso de desarrollo: Deportivo Alavés 2025/26.

```text
matches=38
players=36
player_match=835
```

FEATURE-01 `0.1.0`: 28 features.
FEATURE-02 `0.2.0`: temporal strict-past.
FEATURE-03 `0.3.0`: temporal same-role strict-past.

Roles observados: 590/835 player-match con rol; 23 raw labels.

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

Contrato objetivo futuro:
- recomendación;
- confianza/calibración;
- evidencia;
- justificación;
- limitaciones;
- alternativa.

Aún no se autoriza ninguna recomendación porque no hay criterios/thresholds/calibración validados. N13000 mantiene `RECOMMENDATION_NOT_ISSUED_*`.

## 8. DSAI-01A — FEASIBILITY AUDIT CERRADO

Resultado:
```text
player_similarity_profiles        GO_EXPLORATORY
change_detection_evolution        GO_EXPERIMENT
observed_role_classification      CANDIDATE_SUPERVISED
role_player_fit                   REFORMULATE_TARGET
expert_vs_ml                      BLOCKED_SHARED_TARGET
n13000_recommendation_calibration BLOCKED_GROUND_TRUTH
```

Más datos:
```text
player-role sequences=87
repeated=67
median_matches=5
max_matches=38
FEATURE-01 non-null=6324/23380
GPS observations=0
```

## 9. DSAI-02 — CHANGE DETECTION CERRADO EXPERIMENTAL

Script: `dsai/change_detection_experiment.py`.

Cobertura:
```text
evaluable_rows=3647
players=25
roles=18
features=25
```

Validación sintética:
```text
0.5 std  AUC=0.2365  median uplift=-0.4645
1.0 std  AUC=0.5341  median uplift= 0.0355
1.5 std  AUC=0.7211  median uplift= 0.5355
2.0 std  AUC=0.8024  median uplift= 1.0355
```

Decisión: `EXPERIMENTALLY_USEFUL / NO_DEPLOY`.

Motivo: muestra sensibilidad estadística para cambios suficientemente grandes, pero no existe ground truth real de change-points para calibrar alertas operativas.

## 10. DSAI-03 — PLAYER SIMILARITY CERRADO EXPLORATORIO

Issue #32.

Script:
```text
dsai/player_similarity_experiment.py
```

Unidad:
```text
player_id + exact observed primary_role
```

Ejecución local:
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

Interpretación:
- cobertura descriptiva razonable para un experimento exploratorio;
- solo 22 perfiles permiten validación temporal;
- nearest-neighbour retention = 22.7%;
- correlación de distancias entre mitades = 0.214;
- la estabilidad temporal es insuficiente para desplegar ahora una funcionalidad de “jugadores similares”.

Decisión: `EXPLORATORY_RESULT / NO_DEPLOY`.

Se conserva como resultado académico negativo/limitado y como base para repetir con más partidos, temporadas/equipos y una taxonomía de roles validada. Similarity no equivale a calidad, fit ni recomendación.

## 11. DSAI-04 — ROLE-LABEL AUDIT ACTIVO

Objetivo: decidir si `primary_role` puede utilizarse de forma defendible como target supervisado antes de entrenar ningún clasificador.

Motivo:
- hay 23 raw labels;
- `Substitute` concentra 172 filas en el feasibility audit;
- la importación de lineups documenta que `position='Substitute'` es un estado de banquillo y no un rol táctico específico;
- no se agruparán etiquetas por intuición.

Audit requerido:
- distribución exacta por label, jugadores, titularidad y minutos;
- diagnóstico específico de `Substitute`;
- coexistencia del mismo jugador con roles tácticos en otros partidos;
- transiciones temporales de labels;
- clases con muy pocos jugadores/observaciones;
- conclusión metodológica sobre si el target raw es entrenable tal cual, requiere depuración basada en fuente o debe descartarse.

Script:
```text
dsai/role_label_audit.py
```

## 12. Líneas bloqueadas

- role/player fit: sin target independiente;
- Expert vs ML: sin shared target independiente;
- N13000 calibration: sin ground truth;
- GPS ML: 0 observaciones en dataset actual;
- role classification: bloqueada hasta cerrar DSAI-04.

## 13. Producto actual

Dashboard, Reports y Assistant funcionan técnicamente, pero continúan como prototipo v0.1.

Pendientes después del núcleo DS/IA:
- Product UX insight-first;
- Reports-02 profesionales;
- arquitectura final LLM local/cloud/híbrida;
- Product Service Layer común;
- publicación final y TFM.

## 14. Decision gates pendientes

- `DG-UX-01`;
- `DG-LLM-01`;
- `DG-REP-01`;
- `DG-PUB-01`.

## 15. Siguiente paso exacto

No instalar nada:

```powershell
cd C:\Users\sergi\Desktop\football-performance-system
git pull
python dsai\role_label_audit.py
```

Después A5 decide si una tarea supervisada de clasificación de rol es metodológicamente defendible y con qué target exacto, o si se documenta como no viable con este dataset.