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
DSAI-07 ROLE CLASSIFICATION BASELINE CERRADO / EXPERIMENTAL_SIGNAL / NO DEPLOY — ISSUE #45
DSAI-08 ROLE GRANULARITY AUDIT      CERRADO / LIMITED_SOURCE_POSITION_BASELINE — ISSUE #46
DSAI-09 SOURCE POSITION BASELINE    CERRADO / EXPERIMENTAL_SIGNAL_IMPROVED / NO DEPLOY — ISSUE #49
DSAI-10 PREMATCH POSITION BASELINE  CERRADO / PREMATCH_EXPERIMENTAL_SIGNAL / NO DEPLOY — ISSUE #50
DSAI-11 PREMATCH ROBUSTNESS         ACTIVO — ISSUE #51 / SCRIPT IMPLEMENTADO
FINAL-01                            BLOQUEADO HASTA REDISEÑO DE PRODUCTO
```

## DSAI-10 — resultado cerrado

```text
candidate_rows=418
evaluated_rows=362
evaluated_positions=6
safe_features=140
skipped_no_prematch_history=12
skipped_no_other_player_prior_position=44
logreg_accuracy=0.4834
logreg_balanced_accuracy=0.3121
logreg_macro_f1=0.3002
majority_accuracy=0.0967
majority_balanced_accuracy=0.0426
majority_macro_f1=0.0302
conclusion=PREMATCH_SOURCE_POSITION_BASELINE_COMPLETE_NO_DEPLOYMENT_DECISION
```

Decisión: `PREMATCH_EXPERIMENTAL_SIGNAL / NO_DEPLOY`.

DSAI-10 confirma que FEATURE-02 strict-past contiene señal pre-match sobre la `source_position` futura incluso cuando el jugador evaluado queda completamente excluido del entrenamiento. El rendimiento baja respecto a DSAI-09 al retirar la información del partido actual, pero sigue muy por encima del baseline mayoritario.

No se interpreta como player-fit ni como recomendación táctica. El baseline mayoritario es demasiado débil para determinar todavía el valor incremental real del ML.

## DSAI-11 — activo

Issue #51.

Script: `dsai/source_position_prematch_robustness.py`.

Objetivo: comparar DSAI-10 con baselines futbolísticos pre-match fuertes y ejecutar ablations de FEATURE-02.

Comparaciones:
- LogisticRegression con los 140 inputs pre-match seguros;
- `prior_mean_only`;
- `prev_only`;
- mayoría del train;
- última `source_position` observada del jugador;
- `source_position` modal histórica del jugador, con desempate por la más reciente.

Validación:
- ML entrenado solo con fechas estrictamente anteriores;
- jugador de test excluido completamente del train ML;
- baselines del jugador calculados solo con titularidades estrictamente anteriores;
- sin FEATURE-01 actual, sin `delta_*` y sin FEATURE-03;
- análisis separado de permanencia de posición vs cambio de posición;
- head-to-head ML vs última posición.

La fase no define threshold de despliegue, player-fit, ranking ni recomendación.

## Líneas todavía bloqueadas

- `role_player_fit`: sin target independiente defendible;
- `expert_vs_ml`: sin shared target independiente;
- calibración N13000: sin ground truth de recomendación.

## Siguiente paso exacto

```powershell
cd C:\Users\sergi\Desktop\football-performance-system
git pull
python dsai\source_position_prematch_robustness.py
```

No instalar nada.
