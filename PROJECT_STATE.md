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
DSAI-04 ROLE-LABEL AUDIT            CERRADO / REFORMULATE_LABELS — ISSUE #34
DSAI-05 ROLE TARGET RECONSTRUCTION  CERRADO / VALIDADO — ISSUE #35
DSAI-06 SUPERVISED ROLE FEASIBILITY CERRADO / LIMITED_EXPERIMENT_ONLY — ISSUE #36
DSAI-07 ROLE CLASSIFICATION BASELINE CERRADO / EXPERIMENTAL_SIGNAL / NO_DEPLOY — ISSUE #45
DSAI-08 ROLE GRANULARITY AUDIT      ACTIVO — ISSUE #46 / SCRIPT IMPLEMENTADO
FINAL-01                            BLOQUEADO HASTA REDISEÑO DE PRODUCTO
```

## DSAI-07 — resultado cerrado

```text
candidate_rows=418
evaluated_rows=302
evaluated_labels=19
skipped_no_other_player_prior_label=116
logreg_accuracy=0.1325
logreg_balanced_accuracy=0.0823
logreg_macro_f1=0.0722
majority_accuracy=0.0033
majority_balanced_accuracy=0.0016
majority_macro_f1=0.0005
conclusion=LIMITED_BASELINE_EXPERIMENT_COMPLETE_NO_DEPLOYMENT_DECISION
```

Decisión: `EXPERIMENTAL_SIGNAL / NO_DEPLOY`.

La regresión logística supera claramente el baseline de clase mayoritaria bajo validación temporal e independiente de identidad, pero el rendimiento absoluto sigue siendo bajo. Las 22 clases detalladas están demasiado fragmentadas para producto.

Los warnings de scikit-learn reflejan conjuntos temporales pequeños y muchas clases; no invalidan la ejecución, pero son evidencia adicional de fragmentación.

## DSAI-08 — activo

Issue #46.

Script: `dsai/role_granularity_audit.py`.

Objetivo: auditar una granularidad de target recuperada directamente de la semántica de DATA-02. El importador construye el rol como `position | position_side`; DSAI-08 recupera únicamente `position` de forma determinista. No es una agrupación intuitiva.

Se audita:
- labels detallados vs posiciones fuente;
- filas, jugadores y partidos por posición;
- soporte strict-past;
- soporte strict-past en otro jugador;
- clases dependientes de un único jugador;
- anomalías de parsing.

Salida posible: `GO_SOURCE_POSITION_BASELINE`, `LIMITED_SOURCE_POSITION_BASELINE` o `NO_GO_SOURCE_POSITION`.

## Líneas todavía bloqueadas

- `role_player_fit`: sin target independiente defendible;
- `expert_vs_ml`: sin shared target independiente;
- calibración N13000: sin ground truth de recomendación.

## Siguiente paso exacto

```powershell
cd C:\Users\sergi\Desktop\football-performance-system
git pull
python dsai\role_granularity_audit.py
```

No instalar nada.
