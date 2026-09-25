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
DSAI-07 ROLE CLASSIFICATION BASELINE ACTIVO — ISSUE #45 / SCRIPT IMPLEMENTADO
FINAL-01                            BLOQUEADO HASTA REDISEÑO DE PRODUCTO
```

## DSAI-06 — resultado cerrado

```text
target_rows=418
labels=22
players=24
matches=38
features=28
feature_values=5081/11704
features_per_row=min:1 median:12 max:20
strict_past_label_seen=396/418
identity_independent_strict_past=302/418
single_player_labels=3
labels_without_any_strict_past_test=0
labels_without_other_player_strict_past=3
conclusion=LIMITED_EXPERIMENT_ONLY
```

Decisión: existe suficiente estructura para un experimento supervisado limitado, pero no para considerar el classificador un modelo de producto. Tres clases no pueden validarse de forma independiente de identidad.

## DSAI-07 — activo

Objetivo: ejecutar el primer baseline ML supervisado real del TFM bajo un diseño más estricto que DSAI-06:
- target táctico limpio de titulares;
- únicamente FEATURE-01 como predictores;
- test jugador-partido evaluado solo con entrenamiento de fechas estrictamente anteriores;
- el jugador evaluado queda excluido completamente del entrenamiento de ese test;
- el label objetivo debe existir previamente en otros jugadores;
- no se fusionan ni eliminan clases para mejorar resultados;
- imputación mediana solo dentro del train de cada evaluación;
- comparación contra baseline de clase mayoritaria del train;
- métricas: accuracy, balanced accuracy y macro-F1;
- sin threshold de despliegue, ranking, fit o recomendación.

Interpretación: es un experimento post-partido de relación entre comportamiento observable y rol observado, no un predictor pre-partido ni una recomendación táctica.

Nueva dependencia de proyecto: `scikit-learn>=1.6`.

## Líneas todavía bloqueadas

- `role_player_fit`: sin target independiente defendible;
- `expert_vs_ml`: sin shared target independiente;
- calibración N13000: sin ground truth de recomendación.

## Siguiente paso exacto

```powershell
cd C:\Users\sergi\Desktop\football-performance-system
git pull
python dsai\role_classification_baseline.py
```

Si aparece `ModuleNotFoundError: sklearn`, instalar una sola vez:

```powershell
python -m pip install "scikit-learn>=1.6"
```
