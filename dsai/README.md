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
FEATURE-01 names=28
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

Resultado: `LIMITED_EXPERIMENT_ONLY`.

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

Decisión: `EXPERIMENTAL_SIGNAL / NO_DEPLOY`.

## DSAI-08 — source-position granularity audit — CERRADO

```text
rows=418
detailed_labels=22
source_positions=7
identity_independent_strict_past=363/418
single_player_positions=1
parsing_anomalies=0
conclusion=LIMITED_SOURCE_POSITION_BASELINE
```

`source_position` se obtiene únicamente invirtiendo la representación validada de DATA-02 `position | position_side`.

## DSAI-09 — source-position current-match baseline — CERRADO

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
```

Decisión: `EXPERIMENTAL_SIGNAL_IMPROVED / NO_DEPLOY`.

La granularidad de 7 posiciones mejora sustancialmente el baseline de 22 roles. Sin embargo, FEATURE-01 contiene estadísticas del partido actual, por lo que este experimento mide asociación post-partido entre comportamiento y posición observada; no es una predicción pre-partido.

## DSAI-10 — pre-match source-position baseline — ACTIVO

Script:

```powershell
python dsai\source_position_prematch_baseline.py
```

Predictores: únicamente FEATURE-02 strict-past con `history_n`, `prev`, `prior_mean`, `prior_std` y `prior_slope`.

Quedan excluidos:
- `delta_prev` y `delta_prior_mean`, porque incorporan el valor del partido actual;
- FEATURE-03, porque está condicionado al rol;
- identidad del jugador, nombres, rol observado y outputs N12000/N13000.

Validación:
- train estrictamente anterior a cada test;
- jugador evaluado excluido del train;
- posición real previamente observada en otro jugador;
- al menos una observación histórica real disponible para la fila de test;
- imputación y escalado fit solo sobre train;
- LogisticRegression vs baseline de clase mayoritaria.

DSAI-10 es el primer test de esta línea cuyo input es completamente pre-match. Sigue sin producir player-fit, ranking o recomendación.

## Líneas bloqueadas

`role_player_fit`, `expert_vs_ml` y calibración final de N13000 siguen bloqueados sin ground truth independiente defendible.

## Regla metodológica

La fase DSAI puede producir experimentos negativos o `NO_DEPLOY`. El criterio académico es que hipótesis, datos, baselines, validación temporal, leakage, métricas, error y limitaciones queden documentados de forma reproducible.
