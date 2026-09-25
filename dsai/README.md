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

```text
profiles=64
players=24
roles=22
features=28
profiles_with_neighbour=61
temporal_eligible=22
same_neighbour=5
retention_rate=0.22727272727272727
pair_distance_corr=0.2143880082112036
```

Decisión: `EXPLORATORY_RESULT / NO_DEPLOY` por baja estabilidad temporal.

## DSAI-04 — role-label audit — CERRADO

Resultado: `REFORMULATE_LABELS` porque `Substitute` mezclaba estado de participación y rol táctico.

## DSAI-05 — role target reconstruction — CERRADO

Resultado local:

```text
rows=835
played=590
starters=418
substitute_appearances=172
unused_bench=245
clean_target_rows=418
labels=22
players=24
single_player_labels=3
withheld_substitute_appearances=172
invalid_starter_rows=0
substitute_labels_remaining=0
```

El target limpio conserva únicamente roles tácticos directamente observados en titulares. No se infiere el rol de los suplentes ni se agrupan clases.

## DSAI-06 — supervised role feasibility — ACTIVO

Ejecutar:

```powershell
python dsai\role_supervised_feasibility.py
```

Antes de entrenar un classificador se auditan:
- cobertura real de FEATURE-01 en las 418 filas limpias;
- diversidad de jugadores por clase;
- posibilidad de evaluación temporal strict-past;
- posibilidad de evaluación independent de identidad usando observaciones previas del mismo label en otros jugadores;
- clases que solo existen en un jugador.

No se entrena ningún modelo. FEATURE-03 queda excluido de este experimento porque está condicionado al rol y sería circular para predecir ese mismo target. `player_id`, nombres, el propio rol y outputs del sistema experto tampoco pueden actuar como predictores.

La salida será `GO_BASELINE_EXPERIMENT`, `LIMITED_EXPERIMENT_ONLY` o `NO_GO_SUPERVISED`, sin introducir un mínimo de muestra arbitrario.

## Líneas bloqueadas

`role_player_fit`, `expert_vs_ml` y calibración final de N13000 siguen bloqueados sin ground truth independiente defendible.

## Regla metodológica

La fase DSAI puede producir experimentos negativos o `NO_DEPLOY`. El criterio académico es que hipótesis, datos, baselines, validación, leakage, métricas, error y limitaciones queden documentados de forma reproducible.
