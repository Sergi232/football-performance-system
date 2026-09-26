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
PERF-12 VALIDATED ZERO IMPACT       ACTIVO — ISSUE #78 / SCRIPT IMPLEMENTADO
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
→ COBERTURA / OBSERVABILIDAD
→ SEMÁNTICA NULL VS ZERO
→ IMPACTO DE SEMÁNTICA VALIDADA
→ POLÍTICA DE SCORE
→ SENSIBILIDAD / ABLATIONS
→ ESTABILIDAD TEMPORAL / CONTEXTO
→ SCORE GLOBAL VALIDADO
→ EVOLUCIÓN / CONSISTENCIA
→ CONCLUSIONES / RECOMENDACIONES
```

Rol/posición se usa como contexto de comparación/normalización, no como objetivo principal ni como componente directo del score.

## PERF-11 — cerrado

Resultado ejecutado:

```text
player_match_rows=835
played_rows=590
audited_metrics=4
validated_candidates=3
blocked=1
shots_total: raw_null=559 null_event_zero=559 null_event_positive=0 nonnull_mismatch=0 all_mismatch_after_null0=0 status=EVENT_VALIDATED_NULL_AS_ZERO_CANDIDATE
goals: raw_null=798 null_event_zero=798 null_event_positive=0 nonnull_mismatch=0 all_mismatch_after_null0=0 status=EVENT_VALIDATED_NULL_AS_ZERO_CANDIDATE
yellow_cards: raw_null=749 null_event_zero=744 null_event_positive=5 nonnull_mismatch=0 all_mismatch_after_null0=5 status=NULL_AS_ZERO_NOT_VALIDATED
red_cards: raw_null=830 null_event_zero=830 null_event_positive=0 nonnull_mismatch=0 all_mismatch_after_null0=0 status=EVENT_VALIDATED_NULL_AS_ZERO_CANDIDATE
validated_null_as_zero_candidates=goals,red_cards,shots_total
conclusion=EVENT_VALIDATED_NULL_AS_ZERO_CANDIDATES_FOUND
```

Decisión:
- `shots_total`, `goals` y `red_cards` tienen evidencia atómica completa para interpretar raw `NULL` como **zero observado** en una futura versión de features;
- `yellow_cards` queda bloqueada: existen 5 filas raw NULL con evento amarillo positivo;
- no se modifica raw data ni FEATURE-01 todavía;
- no se autoriza ningún `fillna(0)` global.

Impacto esperado a auditar:
- `goals_per90`: puede pasar de missing a 0 observado en partidos sin gol;
- `goal_per_shot_rate`: puede pasar a 0 cuando hay tiros y ningún gol; si `shots_total=0`, la ratio sigue indefinida;
- `red_cards_per90`: puede pasar de missing a 0 observado cuando no hay expulsión;
- `shots_total_per90` también puede adquirir 0 observado, pero sigue siendo `CONTEXT_DEPENDENT` y no entra por sí sola en el signed core.

## PERF-12 — activo

Issue #78.

Script:
```text
dsai/performance_validated_zero_impact.py
```

Objetivo: aplicar **solo en memoria** la semántica validada de PERF-11 y medir cuánto cambia la cobertura del signed core y de las 5 dimensiones outfield.

Compara:
- cobertura FEATURE-01 original;
- cobertura con `shots_total`, `goals` y `red_cards` reinterpretados como zero observado únicamente cuando raw es NULL;
- cobertura de `goals_per90`, `goal_per_shot_rate`, `red_cards_per90`;
- distribución 0..5 dimensions antes/después;
- full-five coverage antes/después;
- dimensión cuello de botella antes/después.

Reglas:
- no escribe en DuckDB;
- no modifica FEATURE-01 ni `features/catalog.json`;
- `yellow_cards` permanece sin reinterpretar;
- denominador `shots_total=0` mantiene `goal_per_shot_rate=NULL`;
- ningún peso, threshold, ranking o recomendación.

## Guardrails del score

- ningún threshold de bueno/malo;
- ningún ranking/recomendación de producto;
- ningún peso aprobado;
- ningún `fillna(0)` global;
- solo se admite zero observado con evidencia independiente;
- ratios con denominador 0 siguen indefinidas;
- no usar PCA/correlación/varianza como definición de calidad;
- score outfield y score de portero no se comparan directamente;
- rol/posición = contexto, no target;
- el LLM no recalcula el score.

## Incidencias de repositorio

Los issues #62, #64, #65, #66, #67, #68, #69, #71, #72, #73, #74, #75 y #76 fueron artefactos accidentales del conector y quedaron cerrados como `not_planned`. El #63 fue una planificación prematura y también quedó cerrado. Ninguno contiene trabajo del proyecto.

Los ficheros auxiliares redundantes `docs/PERF_05_*` siguen pendientes de limpieza; no son fuente de verdad.

## Líneas todavía bloqueadas

- score global validado: hasta resolver cobertura tras semántica validada + política de score + sensibilidad/ablations + estabilidad;
- `role_player_fit`: sin target independiente defendible;
- `expert_vs_ml`: sin shared target independiente;
- calibración N13000: sin ground truth de recomendación.

## Siguiente paso exacto

```powershell
cd C:\Users\sergi\Desktop\football-performance-system
git pull
python dsai\performance_validated_zero_impact.py
```

No instalar nada.
