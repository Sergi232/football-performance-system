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
logreg_accuracy=0.5537
logreg_balanced_accuracy=0.3482
logreg_macro_f1=0.3614
majority_accuracy=0.0964
majority_balanced_accuracy=0.0423
majority_macro_f1=0.0302
```

Decisión: `EXPERIMENTAL_SIGNAL_IMPROVED / NO_DEPLOY`.

FEATURE-01 del mismo partido contiene señal clara sobre la posición observada, pero el experimento sigue siendo post-partido.

## DSAI-10 — pre-match source-position baseline — CERRADO

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
```

Decisión: `PREMATCH_EXPERIMENTAL_SIGNAL / NO_DEPLOY`.

El modelo conserva señal usando exclusivamente FEATURE-02 strict-past (`history_n`, `prev`, `prior_mean`, `prior_std`, `prior_slope`). `delta_prev`, `delta_prior_mean`, FEATURE-01 actual y FEATURE-03 quedan excluidos.

La validación mantiene train estrictamente anterior y exclusión completa del jugador evaluado. El resultado todavía no demuestra player-fit ni justifica producto porque el baseline de clase mayoritaria es demasiado débil.

## DSAI-11 — pre-match robustness and football baselines — ACTIVO

Script:

```powershell
python dsai\source_position_prematch_robustness.py
```

Objetivo: comprobar si DSAI-10 aporta valor incremental respecto a baselines futbolísticos simples y fuertes disponibles antes del partido.

Comparaciones:
- modelo completo con los 140 FEATURE-02 pre-match seguros;
- ablation `prior_mean_only`;
- ablation `prev_only`;
- mayoría del train;
- última `source_position` observada del jugador;
- posición modal histórica del jugador, con desempate por la más reciente.

También se analiza:
- partidos donde el jugador mantiene posición;
- partidos donde cambia de posición;
- head-to-head del ML frente al baseline de última posición.

Todos los baselines de jugador usan únicamente titularidades estrictamente anteriores. No se usa información del partido actual.

## Líneas bloqueadas

`role_player_fit`, `expert_vs_ml` y calibración final de N13000 siguen bloqueados sin ground truth independiente defendible.

## Regla metodológica

La fase DSAI puede producir experimentos negativos o `NO_DEPLOY`. El criterio académico es que hipótesis, datos, baselines, validación temporal, leakage, métricas, error y limitaciones queden documentados de forma reproducible.
