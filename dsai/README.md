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

Decisiones:

```text
player_similarity_profiles        GO_EXPLORATORY
change_detection_evolution        GO_EXPERIMENT
observed_role_classification      CANDIDATE_SUPERVISED
role_player_fit                   REFORMULATE_TARGET
expert_vs_ml                      BLOCKED_SHARED_TARGET
n13000_recommendation_calibration BLOCKED_GROUND_TRUTH
```

El plan experimental congelado está en `docs/DSAI_EXPERIMENT_PLAN.md`.

## DSAI-02 — change detection / evolution — CERRADO

Resultado: `EXPERIMENTALLY_USEFUL / NO_DEPLOY`.

## DSAI-03 — player similarity / profiles — CERRADO

Resultado local:

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

## DSAI-04 — role-label audit — ACTIVO

Antes de entrenar un clasificador supervisado de rol se audita `primary_role`.

Ejecutar:

```powershell
python dsai\role_label_audit.py
```

El audit reporta distribución, jugadores, titularidad, minutos, diagnóstico de `Substitute`, coexistencia con roles tácticos, transiciones cronológicas y sparsity. No entrena modelos ni agrupa roles por intuición.

## Líneas bloqueadas

`role_player_fit`, `expert_vs_ml` y calibración final de N13000 siguen bloqueados sin ground truth independiente defendible. N12000/N13000 no pueden utilizarse como target ML y después presentarse como validación independiente.

## Regla metodológica

La fase DSAI puede producir experimentos negativos o `NO_DEPLOY`. El criterio académico es que hipótesis, datos, baselines, validación, leakage, métricas, error y limitaciones queden documentados de forma reproducible.