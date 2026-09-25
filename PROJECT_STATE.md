# PROJECT_STATE

Última actualización: 26/09/2026

Memoria técnica operativa del proyecto. Si contradice un chat antiguo, prevalece este archivo.

## Estado actual

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

## Flujo vigente

```text
DATA
→ FEATURE ENGINE
→ ANALYTICS
→ EXPERT SYSTEM
→ DSAI EXPERIMENTS
→ PRODUCT SERVICE LAYER
→ WEB / REPORTS / AI ASSISTANT
→ QA / PUBLICATION
```

GitHub es la fuente de verdad. Una capa superior no puede inventar métricas, rankings, scores o recomendaciones.

## Baseline

Caso de desarrollo: Deportivo Alavés 2025/26.

```text
matches=38
players=36
player_match=835
FEATURE-01=28 features
FEATURE-02=temporal strict-past
FEATURE-03=temporal same-role strict-past
observed-role rows=590
raw role labels=23
analytics rows=46760
GPS observations=0
```

## ANALYTICS-01

DG-AN-01 = C:
- SELF_ROLE_PRIOR;
- PEER_ROLE_PRIOR;
- siempre separados.

PASS final:
```text
SELF_ROLE_PRIOR=23380
PEER_ROLE_PRIOR=23380
strict-past peer checks=PASS
no score/ranking/recommendation=PASS
```

## N13000

DG-N13-01 = C. Contrato objetivo futuro:
- recomendación;
- confianza/calibración;
- evidencia;
- justificación;
- limitaciones;
- alternativa.

Todavía no emite recomendaciones porque no existe calibración/ground truth validado.

## DSAI-01A — feasibility audit

```text
player_similarity_profiles        GO_EXPLORATORY
change_detection_evolution        GO_EXPERIMENT
observed_role_classification      CANDIDATE_SUPERVISED
role_player_fit                   REFORMULATE_TARGET
expert_vs_ml                      BLOCKED_SHARED_TARGET
n13000_recommendation_calibration BLOCKED_GROUND_TRUTH
```

## DSAI-02 — change detection

Resultado:
```text
evaluable_rows=3647
players=25
roles=18
features=25
AUC 0.5σ=0.2365
AUC 1.0σ=0.5341
AUC 1.5σ=0.7211
AUC 2.0σ=0.8024
```

Decisión: `EXPERIMENTALLY_USEFUL / NO_DEPLOY` por ausencia de ground truth real de change-points.

## DSAI-03 — player similarity

Script: `dsai/player_similarity_experiment.py`.

Resultado:
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

La estabilidad temporal es demasiado baja para exponer “jugadores similares” como funcionalidad del producto. El experimento se conserva como resultado académico y baseline para futuros datos más amplios.

## DSAI-04 — role-label audit ACTIVO

Objetivo: decidir si `primary_role` puede utilizarse como target supervisado defendible.

Problema identificado:
- 23 raw labels;
- `Substitute` concentra 172 filas;
- la importación de lineups documenta que `Substitute` es estado de banquillo, no rol táctico;
- no se permite agrupar labels por intuición.

El audit debe revisar:
- distribución exacta por label;
- jugadores por label;
- titularidad y minutos;
- diagnóstico de `Substitute`;
- coexistencia del mismo jugador con roles tácticos;
- transiciones temporales;
- sparsity;
- conclusión sobre si el target raw puede usarse, debe depurarse por fuente o descartarse.

Script: `dsai/role_label_audit.py`.

## Líneas bloqueadas

- role/player fit: sin target independiente;
- Expert vs ML: sin shared target independiente;
- N13000 calibration: sin ground truth;
- GPS ML: sin observaciones;
- role classification: bloqueada hasta cerrar DSAI-04.

## Producto

Dashboard, Reports y Assistant siguen como prototipo v0.1. Después del núcleo DS/IA: Product UX insight-first → Reports-02 → arquitectura LLM final → Product Service Layer → publicación/TFM.

## Siguiente paso exacto

```powershell
cd C:\Users\sergi\Desktop\football-performance-system
git pull
python dsai\role_label_audit.py
```

No instalar nada.