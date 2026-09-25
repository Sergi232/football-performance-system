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

Target limpio:

```text
418 filas
22 labels
24 jugadores
3 labels de un único jugador
```

`Substitute` queda fuera del target táctico y no se infiere el rol de suplentes.

## DSAI-06 — supervised role feasibility — CERRADO

Resultado:

```text
target_rows=418
labels=22
players=24
matches=38
feature_values=5081/11704
features_per_row=min:1 median:12 max:20
strict_past_label_seen=396/418
identity_independent_strict_past=302/418
single_player_labels=3
labels_without_other_player_strict_past=3
conclusion=LIMITED_EXPERIMENT_ONLY
```

La línea de role classification puede avanzar únicamente como experimento limitado. No se considera todavía apta para producto.

## DSAI-07 — role classification baseline — ACTIVO

Script:

```powershell
python dsai\role_classification_baseline.py
```

Diseño:
- target limpio de titulares;
- únicamente FEATURE-01;
- entrenamiento estrictamente anterior a la fecha de cada test;
- exclusión completa del jugador evaluado del train;
- solo se evalúan casos cuyo label ya existía previamente en otro jugador;
- no se fusionan clases;
- imputación de mediana fit únicamente sobre train;
- regresión logística multinomial como primer baseline ML;
- comparación con baseline de clase mayoritaria;
- accuracy, balanced accuracy y macro-F1;
- resultados y predicciones reproducibles en JSON/Markdown/CSV.

Es un experimento post-partido para estudiar si el comportamiento estadístico contiene señal sobre el rol observado. No predice alineaciones futuras ni emite recomendaciones.

## Líneas bloqueadas

`role_player_fit`, `expert_vs_ml` y calibración final de N13000 siguen bloqueados sin ground truth independiente defendible.

## Regla metodológica

La fase DSAI puede producir experimentos negativos o `NO_DEPLOY`. El criterio académico es que hipótesis, datos, baselines, validación, leakage, métricas, error y limitaciones queden documentados de forma reproducible.
