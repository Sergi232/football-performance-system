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
DSAI-08 ROLE GRANULARITY AUDIT      CERRADO / LIMITED_SOURCE_POSITION_BASELINE — ISSUE #46
DSAI-09 SOURCE POSITION BASELINE    CERRADO / EXPERIMENTAL_SIGNAL_IMPROVED / NO_DEPLOY — ISSUE #49
DSAI-10 PREMATCH POSITION BASELINE  ACTIVO — ISSUE #50 / SCRIPT IMPLEMENTADO
FINAL-01                            BLOQUEADO HASTA REDISEÑO DE PRODUCTO
```

## DSAI-09 — resultado cerrado

```text
candidate_rows=418
evaluated_rows=363
evaluated_positions=6
skipped_no_other_player_prior_position=55
logreg_accuracy=0.5537
logreg_balanced_accuracy=0.3482
logreg_macro_f1=0.3614
majority_accuracy=0.0964
majority_balanced_accuracy=0.0423
majority_macro_f1=0.0302
conclusion=LIMITED_SOURCE_POSITION_BASELINE_COMPLETE_NO_DEPLOYMENT_DECISION
```

Decisión: `EXPERIMENTAL_SIGNAL_IMPROVED / NO_DEPLOY`.

La granularidad de fuente de 7 posiciones mejora de forma sustancial respecto a los 22 roles detallados de DSAI-07. Bajo validación temporal strict-past e independiente de identidad, LogisticRegression obtiene 55,37% de accuracy y macro-F1 0,3614 frente a 9,64% y 0,0302 del baseline mayoritario.

La conclusión sigue siendo experimental: solo se evalúan 6 posiciones, una posición depende de un único jugador y FEATURE-01 usa estadísticas del mismo partido, por lo que DSAI-09 demuestra asociación post-partido entre comportamiento y posición observada, no capacidad predictiva pre-partido ni player-fit.

## DSAI-10 — activo

Issue #50.

Script: `dsai/source_position_prematch_baseline.py`.

Objetivo: probar si el mismo target `source_position` puede predecirse usando exclusivamente información disponible antes del partido.

Predictores permitidos: FEATURE-02 strict-past con operadores:
- `history_n`;
- `prev`;
- `prior_mean`;
- `prior_std`;
- `prior_slope`.

Se excluyen explícitamente `delta_prev` y `delta_prior_mean` porque incorporan el valor del partido actual y no son pre-match. FEATURE-03 también queda excluido por estar condicionado al rol.

Diseño:
- target de titular observado en el partido actual;
- solo features históricas strict-past del jugador;
- train con fechas estrictamente anteriores al test;
- jugador de test completamente excluido del train;
- posición objetivo previamente observada en otro jugador;
- fila de test con al menos una observación histórica real;
- imputación y escalado ajustados únicamente dentro de train;
- LogisticRegression vs baseline de clase mayoritaria;
- sin threshold de despliegue, player-fit, ranking o recomendación.

## Líneas todavía bloqueadas

- `role_player_fit`: sin target independiente defendible;
- `expert_vs_ml`: sin shared target independiente;
- calibración N13000: sin ground truth de recomendación.

## Siguiente paso exacto

```powershell
cd C:\Users\sergi\Desktop\football-performance-system
git pull
python dsai\source_position_prematch_baseline.py
```

No instalar nada.
