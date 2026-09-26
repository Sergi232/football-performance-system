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
DSAI-07 ROLE CLASSIFICATION BASELINE CERRADO / EXPERIMENTAL_SIGNAL / NO DEPLOY — ISSUE #45
DSAI-08 ROLE GRANULARITY AUDIT      CERRADO / LIMITED_SOURCE_POSITION_BASELINE — ISSUE #46
DSAI-09 SOURCE POSITION BASELINE    CERRADO / EXPERIMENTAL_SIGNAL_IMPROVED / NO DEPLOY — ISSUE #49
DSAI-10 PREMATCH POSITION BASELINE  CERRADO / PREMATCH_EXPERIMENTAL_SIGNAL / NO DEPLOY — ISSUE #50
DSAI-11 PREMATCH ROBUSTNESS         CERRADO / POSITION CONTEXT ONLY — ISSUE #51
PERF-01 PERFORMANCE SCORE AUDIT     CERRADO / EXPERT_WEIGHT_VALIDATION_REQUIRED — ISSUE #52
PERF-02 DIMENSION EVIDENCE AUDIT    CERRADO / MAPPING+DIRECTION REQUIRED — ISSUE #53
PERF-03 DIMENSION MAPPING AUDIT     CERRADO / MAPPING COMPLETE — ISSUE #54
PERF-04 DIRECTION VALIDATION        CERRADO / CONTEXTUAL METRICS RETAINED — ISSUE #56
PERF-05 SIGNED CORE FEASIBILITY     CERRADO / OUTFIELD CORE AVAILABLE — ISSUE #57
PERF-06 GOALKEEPER EFFICIENCY       CERRADO / SAVE_RATE DERIVABLE — ISSUE #58
PERF-07 GK SAVE_RATE CONTEXT        CERRADO / FEATURE ADMISSION READY — ISSUE #59
PERF-08 AGGREGATION FEASIBILITY     CERRADO / BASELINE FEASIBLE WITH 1 DEGENERATE — ISSUE #60
PERF-09 EXPERIMENTAL SCORE          ACTIVO — ISSUE #61 / SCRIPT IMPLEMENTADO
FINAL-01                            BLOQUEADO HASTA REDISEÑO DE PRODUCTO
```

## Objetivo principal confirmado

El objetivo analítico central es **adjudicar un score de rendimiento jugador-partido**.

```text
PLAYER-MATCH DATA
→ DIMENSIONES DE RENDIMIENTO
→ DIRECCIONES VALIDADAS
→ NÚCLEO PUNTUABLE
→ NORMALIZACIÓN / AGREGACIÓN
→ SCORE EXPERIMENTAL
→ SENSIBILIDAD / ABLATIONS
→ ESTABILIDAD TEMPORAL / CONTEXTO
→ SCORE GLOBAL VALIDADO
→ EVOLUCIÓN / CONSISTENCIA
→ CONCLUSIONES / RECOMENDACIONES
```

Rol/posición se usa como contexto de comparación/normalización, no como objetivo principal ni como componente directo del score.

## PERF-08 — cerrado

Resultado v0.1.1:

```text
played_rows=590
outfield_rows=552
known_role_rows=418
direct_gk_rows=38
signed_features=11
outfield_dimensions=5
rank_feasible=10
robust_z_feasible=10
degenerate=1
robust_z_limited=0
dimensions_without_evidence=0
degenerate_features=penalties_conceded_per90
goalkeeper_save_rate_rows=31
goalkeeper_rank_feasible=True
conclusion=AGGREGATION_BASELINE_BLOCKED_DEGENERATE_SIGNED_FEATURES
```

Decisión metodológica final:
- el bloqueo proviene únicamente de `penalties_conceded_per90`, que no presenta variación suficiente en esta muestra;
- la feature **no se elimina ni cambia de dirección**;
- queda excluida solo del primer baseline experimental porque una variable degenerada no puede aportar información ordinal;
- debe poder reentrar en futuros datasets cuando exista variación;
- las otras 10 features signadas son rank-normalizables;
- las 5 dimensiones outfield conservan evidencia;
- `save_rate` es normalizable en la ruta separada de portero.

Resultado operativo:
`EXPERIMENTAL_BASELINE_FEASIBLE_WITH_DEGENERATE_FEATURE_EXCLUDED`.

## PERF-09 — activo

Issue #61.

Script:
```text
dsai/performance_score_experimental.py
```

Objetivo: crear el primer score jugador-partido **EXPERIMENTAL / NO_DEPLOY**.

Política baseline nulo:
1. usar únicamente features con dirección respaldada y variación observable;
2. aplicar normalización empírica rank/percentile 0–100;
3. invertir ordinalmente las features `NEGATIVE_SUPPORTED` para que un valor normalizado más alto represente mejor resultado;
4. agregar con pesos iguales entre features disponibles dentro de cada dimensión;
5. agregar las cinco dimensiones outfield con peso igual;
6. emitir score global outfield solo cuando las cinco dimensiones tengan evidencia;
7. conservar missing como missing;
8. excluir `penalties_conceded_per90` solo mientras sea degenerada;
9. mantener portería separada con percentile de `save_rate`;
10. excluir de la ruta outfield cualquier fila de `Goalkeeper` y cualquier fila con rol desconocido pero `saves > 0`, sin imputar una posición.

Los pesos iguales son exclusivamente un **baseline nulo experimental**. No quedan aprobados para producto.

Salidas previstas:
```text
dsai/output/performance_score_experimental.json
dsai/output/performance_score_experimental.md
dsai/output/performance_score_experimental.csv
```

PERF-09 debe terminar en una de dos conclusiones:
- `EXPERIMENTAL_SCORE_BASELINE_CREATED_SENSITIVITY_REQUIRED`;
- `EXPERIMENTAL_SCORE_BLOCKED_NO_COMPLETE_DIMENSION_ROWS`.

Si se crea el baseline, el siguiente paso será sensibilidad/ablations antes de cualquier decisión de despliegue.

## Guardrails del score

- ningún threshold de bueno/malo;
- ningún ranking/recomendación de producto;
- ningún peso aprobado;
- no convertir missing a cero;
- no usar PCA/correlación/varianza como definición de calidad;
- score outfield y score de portero no se comparan directamente;
- rol/posición = contexto, no target;
- el LLM no recalcula el score.

## Incidencias de repositorio

Los issues #62, #64, #65, #66, #67, #68 y #69 fueron artefactos accidentales del conector y quedaron cerrados como `not_planned`. El #63 fue una planificación prematura y también quedó cerrado. Ninguno contiene trabajo del proyecto.

Los ficheros auxiliares redundantes `docs/PERF_05_*` siguen pendientes de limpieza; no son fuente de verdad.

## Líneas todavía bloqueadas

- score global validado: hasta PERF-09 + sensibilidad/ablations + estabilidad;
- `role_player_fit`: sin target independiente defendible;
- `expert_vs_ml`: sin shared target independiente;
- calibración N13000: sin ground truth de recomendación.

## Siguiente paso exacto

```powershell
cd C:\Users\sergi\Desktop\football-performance-system
git pull
python dsai\performance_score_experimental.py
```

No instalar nada.
