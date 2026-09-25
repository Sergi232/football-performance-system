# DSAI — Data Science / AI experimental core

Esta carpeta contiene la fase experimental de Data Science / IA del TFM.

## DSAI-01A — feasibility audit — CERRADO

El audit local confirmó:

```text
matches=38
players=36
player_match=835
observed-role rows=590
raw role labels=23
labeled_players=28
player-role sequences=87
repeated sequences=67
median matches=5
max matches=38
FEATURE-01 names=28
FEATURE-01 non-null=6324/23380
analytics rows=46760
GPS observations=0
```

## DSAI-02 — change detection / evolution — CERRADO

Resultado: `EXPERIMENTALLY_USEFUL / NO_DEPLOY`.

## DSAI-03 — player similarity / profiles — CERRADO

Resultado: `EXPLORATORY_RESULT / NO_DEPLOY` por baja estabilidad temporal.

## DSAI-04 — role-label audit — CERRADO

Resultado: `REFORMULATE_LABELS` porque `Substitute` mezclaba estado de participación y rol táctico.

## DSAI-05 — role target reconstruction — CERRADO

Target limpio: 418 filas, 22 labels, 24 jugadores. `Substitute` queda fuera del target táctico y no se infiere el rol de suplentes.

## DSAI-06 — supervised role feasibility — CERRADO

Resultado: `LIMITED_EXPERIMENT_ONLY`. Hay 302/418 filas con soporte strict-past del mismo label en otro jugador, pero 3 labels no tienen validación independiente de identidad.

## DSAI-07 — detailed-role baseline — CERRADO

```text
candidate_rows=418
evaluated_rows=302
evaluated_labels=19
logreg_accuracy=0.1325
logreg_balanced_accuracy=0.0823
logreg_macro_f1=0.0722
majority_accuracy=0.0033
majority_balanced_accuracy=0.0016
majority_macro_f1=0.0005
```

Decisión: `EXPERIMENTAL_SIGNAL / NO_DEPLOY`. FEATURE-01 aporta señal, pero las 22 clases detalladas están demasiado fragmentadas.

## DSAI-08 — source-position granularity audit — CERRADO

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

`source_position` se obtiene únicamente invirtiendo la representación validada de DATA-02 `position | position_side`. No es una agrupación creada a posteriori para mejorar métricas.

## DSAI-09 — source-position classification baseline — ACTIVO

Ejecutar:

```powershell
python dsai\source_position_classification_baseline.py
```

Diseño:
- target de titulares directamente observado;
- target `source_position` derivado determinísticamente de DATA-02;
- únicamente FEATURE-01;
- train estrictamente anterior a cada fila de test;
- jugador evaluado excluido completamente del train;
- fila evaluable solo si la posición objetivo ya existía en otro jugador en strict-past;
- imputación mediana y escalado fit solo sobre train;
- LogisticRegression vs baseline de clase mayoritaria;
- accuracy, balanced accuracy y macro-F1;
- sin threshold de despliegue, player-fit, ranking o recomendación.

## Líneas bloqueadas

`role_player_fit`, `expert_vs_ml` y calibración final de N13000 siguen bloqueados sin ground truth independiente defendible.

## Regla metodológica

La fase DSAI puede producir experimentos negativos o `NO_DEPLOY`. El criterio académico es que hipótesis, datos, baselines, validación temporal, leakage, métricas, error y limitaciones queden documentados de forma reproducible.
