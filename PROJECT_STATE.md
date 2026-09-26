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
PERF-09 EXPERIMENTAL SCORE          CERRADO / BASELINE CREATED, COVERAGE BOTTLENECK — ISSUE #61
PERF-10 COVERAGE / OBSERVABILITY    CERRADO / POLICY REDESIGN REQUIRED — ISSUE #70
PERF-11 NULL VS ZERO SEMANTICS      CERRADO / 3 VALIDATED CANDIDATES — ISSUE #77
PERF-12 VALIDATED ZERO IMPACT       CERRADO / COVERAGE 5D 3→100
PERF-13 SCORE POLICY + ROLE-AWARE   ACTIVO — ISSUE #78 / SCRIPT IMPLEMENTADO
FINAL-01                            BLOQUEADO HASTA DECISIÓN PERF-13
```

## Objetivo principal confirmado

El objetivo analítico central es **adjudicar un score de rendimiento jugador-partido**.

## PERF-11 — resultado

```text
shots_total -> EVENT_VALIDATED_NULL_AS_ZERO_CANDIDATE
goals -> EVENT_VALIDATED_NULL_AS_ZERO_CANDIDATE
yellow_cards -> NULL_AS_ZERO_NOT_VALIDATED (5 contradicciones)
red_cards -> EVENT_VALIDATED_NULL_AS_ZERO_CANDIDATE
```

## PERF-12 — resultado

Se aplicó solo en memoria la semántica validada de PERF-11.

```text
outfield_rows=552
full_five_before=3
full_five_after=100
gain=97
finishing: 37 -> 552
discipline: 87 -> 552
attacking_threat: 196 -> 196
creation_progression: 413 -> 413
defensive_contribution: 262 -> 262
dimension_count_after:
  2 dimensiones = 67
  3 dimensiones = 199
  4 dimensiones = 186
  5 dimensiones = 100
residual_bottleneck=attacking_threat
```

Conclusión: la semántica NULL→0 validada mejora mucho la cobertura, pero exigir 5/5 dimensiones sigue descartando demasiados jugador-partido.

## PERF-13 — activo

Script:

`dsai/performance_score_policy_experiment.py`

Compara, sin modificar DB ni FEATURE-01:

1. `COMPLETE_5D`
2. `AVAILABLE_4PLUS`
3. `AVAILABLE_3PLUS`
4. `AVAILABLE_2PLUS`

Cada política se evalúa con dos variantes:

- `GLOBAL`: percentiles sobre toda la población outfield.
- `ROLE_AWARE`: percentiles dentro de `source_position` cuando la muestra permite estimarlos; fallback global si no.

La posición se usa como contexto de comparación, no como target ni como peso directo. Esto permite probar un score realmente comparable por posición antes de introducir pesos específicos por rol que todavía no están validados.

El experimento calcula:

- cobertura;
- distribución del score;
- cobertura y sesgo descriptivo por posición;
- sensibilidad leave-one-dimension-out;
- correlación de rangos entre políticas;
- comparación GLOBAL vs ROLE_AWARE;
- evidencia disponible por jugador-partido.

Guardrails:

- solo se reinterpretan como 0 `shots_total`, `goals` y `red_cards` según PERF-11;
- `yellow_cards` missing no se convierte a 0;
- `goal_per_shot_rate` sigue undefined si no hay remates;
- no hay pesos definitivos por posición;
- no hay threshold bueno/malo;
- no hay ranking/recomendación de producto;
- porter separado;
- LLM no calcula ni altera el score.

## Siguiente paso exacto

```powershell
cd C:\Users\sergi\Desktop\football-performance-system
git pull
python dsai\performance_score_policy_experiment.py
```

No instalar nada.

Al terminar deben generarse:

```text
dsai/output/performance_score_policy_experiment.json
dsai/output/performance_score_policy_experiment.csv
dsai/output/performance_score_policy_experiment.md
```

La decisión siguiente será escoger la política candidata de `performance_score_v0.1-experimental` según cobertura + estabilidad + comparabilidad por posición. Después, y solo después, se evaluarán pesos específicos por posición/rol.
