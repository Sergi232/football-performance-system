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

## DSAI-02 — change detection / evolution — ACTIVO

Primer experimento prioritario.

Objetivo: evaluar sensibilidad a cambios sobre secuencias jugador-rol-feature usando exclusivamente referencias strict-past de FEATURE-03.

Ejecución:

```powershell
python dsai\change_detection_experiment.py
```

No requiere dependencias nuevas.

Método experimental inicial:

```text
score = abs(current - same_role_prior_mean) / same_role_prior_std
```

Para validar sensibilidad sin disponer de change-points etiquetados, el script crea observaciones sintéticas situadas a `0.5 / 1.0 / 1.5 / 2.0` desviaciones estándar de la media strict-past. La referencia histórica no se modifica, por lo que no se introduce información futura.

Se reportan:
- cobertura evaluable;
- sensibilidad por tamaño de cambio;
- ROC-AUC entre observaciones originales e inyecciones sintéticas;
- sensibilidad según longitud del historial;
- cobertura por feature y rol;
- limitaciones.

No se selecciona ningún threshold operativo y no se crea alerta de producto, score futbolístico, ranking ni recomendación.

Outputs locales:

```text
dsai/output/change_detection_experiment.json
dsai/output/change_detection_experiment.md
```

## DSAI-03 — player similarity / profiles — SIGUIENTE

Se construirá después de validar DSAI-02. Será exploratorio, condicionado a rol y con validación de estabilidad; la similitud no se interpretará como calidad ni recomendación.

## Observed-role classification — HOLD

Existe un label observado independiente, pero el feasibility audit detecta 23 etiquetas y `Substitute` concentra 172 filas. Antes de entrenar un clasificador se debe auditar la semántica del target y evitar agrupar roles por intuición.

## Líneas bloqueadas

`role_player_fit`, `expert_vs_ml` y calibración final de N13000 no se activan sin ground truth independiente defendible. N12000/N13000 no pueden utilizarse como target ML y después presentarse como validación independiente.

## Regla metodológica

La fase DSAI puede producir experimentos negativos o `NO DEPLOY`. El criterio académico es que hipótesis, datos, baselines, validación, leakage, métricas, error y limitaciones queden documentados de forma reproducible.