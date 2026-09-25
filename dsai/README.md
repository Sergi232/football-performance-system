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

Script:

```powershell
python dsai\change_detection_experiment.py
```

Resultado: `EXPERIMENTALLY_USEFUL / NO_DEPLOY`.

La sensibilidad sintética aumenta para cambios de 1.5–2.0 desviaciones estándar, pero no existe ground truth natural de change-points. No se selecciona threshold operativo ni se genera alerta de producto.

## DSAI-03 — player similarity / profiles — CERRADO

Script:

```powershell
python dsai\player_similarity_experiment.py
```

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

Decisión: `EXPLORATORY_RESULT / NO_DEPLOY`.

La cobertura permite estudiar perfiles, pero la estabilidad temporal es baja: solo 22 perfiles son elegibles para la prueba temporal, el nearest-neighbour se conserva en 22.7% de los casos y la correlación de distancias entre mitades es 0.214. Por tanto, “jugadores similares” no se expone todavía como funcionalidad del producto.

La similitud no se interpreta como calidad, player-fit ni recomendación.

## DSAI-04 — role-label audit — ACTIVO

Antes de entrenar un clasificador supervisado de rol se audita el target `primary_role`.

Ejecución:

```powershell
python dsai\role_label_audit.py
```

El audit reporta:
- distribución exacta de labels;
- jugadores por label;
- titularidad y minutos por label;
- diagnóstico específico de `Substitute`;
- coexistencia de `Substitute` con roles tácticos del mismo jugador en otros partidos;
- transiciones cronológicas entre labels;
- sparsity del target;
- si el target raw puede usarse tal cual o requiere depuración basada en fuente.

No se agrupan etiquetas por intuición y no se entrena ningún modelo en esta fase.

## Observed-role classification — HOLD

Existe un label observado independiente, pero el feasibility audit detecta 23 etiquetas y `Substitute` concentra 172 filas. La importación de lineups documenta que `Substitute` es un estado de banquillo y no un rol táctico específico. La clasificación supervisada queda bloqueada hasta cerrar DSAI-04.

## Líneas bloqueadas

`role_player_fit`, `expert_vs_ml` y calibración final de N13000 no se activan sin ground truth independiente defendible. N12000/N13000 no pueden utilizarse como target ML y después presentarse como validación independiente.

## Regla metodológica

La fase DSAI puede producir experimentos negativos o `NO_DEPLOY`. El criterio académico es que hipótesis, datos, baselines, validación, leakage, métricas, error y limitaciones queden documentados de forma reproducible.