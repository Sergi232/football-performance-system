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
DSAI-09 SOURCE POSITION BASELINE    ACTIVO — ISSUE #49 / SCRIPT IMPLEMENTADO
FINAL-01                            BLOQUEADO HASTA REDISEÑO DE PRODUCTO
```

## DSAI-08 — resultado cerrado

```text
rows=418
detailed_labels=22
source_positions=7
players=24
matches=38
strict_past_position_seen=402/418
identity_independent_strict_past=363/418
single_player_positions=1
positions_without_any_strict_past=0
positions_without_other_player_strict_past=1
parsing_anomalies=0
conclusion=LIMITED_SOURCE_POSITION_BASELINE
```

La taxonomía `source_position` se recupera de forma determinista desde DATA-02, separando `position` de `position_side`; no es una agrupación intuitiva. La estructura mejora de 22 a 7 clases y aumenta la cobertura de validación independiente de identidad de 302 a 363 filas, aunque una posición sigue dependiendo de un único jugador.

## DSAI-09 — activo

Issue #49.

Script: `dsai/source_position_classification_baseline.py`.

Objetivo: repetir el baseline supervisado bajo la granularidad de fuente `source_position` con exactamente el mismo diseño leakage-safe:
- target de titulares directamente observado;
- `source_position` derivado determinísticamente del label DATA-02;
- únicamente FEATURE-01 como predictores;
- train con fechas estrictamente anteriores al test;
- jugador evaluado excluido completamente del train;
- solo se evalúa una fila si su `source_position` ya existía previamente en otro jugador;
- imputación y escalado ajustados solo dentro del train;
- comparación LogisticRegression vs baseline de clase mayoritaria;
- sin threshold de despliegue, player-fit, ranking o recomendación.

## Líneas todavía bloqueadas

- `role_player_fit`: sin target independiente defendible;
- `expert_vs_ml`: sin shared target independiente;
- calibración N13000: sin ground truth de recomendación.

## Siguiente paso exacto

```powershell
cd C:\Users\sergi\Desktop\football-performance-system
git pull
python dsai\source_position_classification_baseline.py
```

No instalar nada.
