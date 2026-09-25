# DSAI — Data Science / AI experimental core

Esta carpeta contiene la fase experimental de Data Science / IA del TFM.

## DSAI-01A — feasibility audit — CERRADO

Base validada: 38 partidos, 36 jugadores, 835 player-match, 28 FEATURE-01.

## DSAI-02 — change detection / evolution — CERRADO

Resultado: `EXPERIMENTALLY_USEFUL / NO_DEPLOY`.

## DSAI-03 — player similarity / profiles — CERRADO

Resultado: `EXPLORATORY_RESULT / NO_DEPLOY` por baja estabilidad temporal.

## DSAI-04 — role-label audit — CERRADO

Resultado: `REFORMULATE_LABELS`; `Substitute` mezclaba participación y rol táctico.

## DSAI-05 — role target reconstruction — CERRADO

Target limpio: 418 filas, 22 labels, 24 jugadores. El rol de suplentes no se infiere.

## DSAI-06 — supervised role feasibility — CERRADO

Resultado: `LIMITED_EXPERIMENT_ONLY`. 302/418 filas tienen soporte strict-past del mismo label en otro jugador; 3 labels no permiten validación independiente de identidad.

## DSAI-07 — role classification baseline — CERRADO

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

Decisión: `EXPERIMENTAL_SIGNAL / NO_DEPLOY`. FEATURE-01 contiene señal respecto al baseline, pero el rendimiento absoluto y la fragmentación de 22 clases no justifican producto.

## DSAI-08 — role granularity audit — ACTIVO

```powershell
python dsai\role_granularity_audit.py
```

DATA-02 almacena el rol observado como `position | position_side`. DSAI-08 recupera el componente `position` de manera determinista y audita si esa granularidad de fuente permite una validación más defendible. No es una agrupación intuitiva y no se entrena ningún modelo en esta fase.

Salida: `GO_SOURCE_POSITION_BASELINE`, `LIMITED_SOURCE_POSITION_BASELINE` o `NO_GO_SOURCE_POSITION`.

## Líneas bloqueadas

`role_player_fit`, `expert_vs_ml` y calibración final de N13000 siguen bloqueados sin ground truth independiente defendible.

## Regla metodológica

La fase DSAI puede producir experimentos negativos o `NO_DEPLOY`. El criterio académico es que hipótesis, datos, baselines, validación, leakage, métricas, error y limitaciones queden documentados de forma reproducible.
