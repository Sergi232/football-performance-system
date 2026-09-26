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
PERF-11 NULL VS ZERO SEMANTICS      ACTIVO — ISSUE #77 / SCRIPT IMPLEMENTADO
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
→ POLÍTICA DE SCORE
→ SENSIBILIDAD / ABLATIONS
→ ESTABILIDAD TEMPORAL / CONTEXTO
→ SCORE GLOBAL VALIDADO
→ EVOLUCIÓN / CONSISTENCIA
→ CONCLUSIONES / RECOMENDACIONES
```

Rol/posición se usa como contexto de comparación/normalización, no como objetivo principal ni como componente directo del score.

## PERF-10 — cerrado

Resultado:

```text
outfield_rows=552
signed_candidates=11
used_features=10
degenerate=1
dimensions=5
full_five_rows=3
full_five_coverage=0.005434782608695652
dimension_count_distribution=0:59,1:168,2:185,3:106,4:31,5:3
bottleneck_dimensions=finishing
leave_one_out=attacking_threat:3,creation_progression:3,defensive_contribution:3,finishing:25,discipline:12
conclusion=FULL_DIMENSION_COVERAGE_INCOMPLETE_POLICY_REDESIGN_REQUIRED
```

Decisión:
- exigir las cinco dimensiones simultáneas no es viable con la semántica actual;
- `finishing` es el cuello de botella principal, pero no el único;
- eliminar una sola dimensión tampoco resuelve el problema;
- no se aprueba ningún mínimo arbitrario de 3/5 o 4/5;
- no se convierte missing a cero.

## Hallazgo metodológico previo a rediseñar el score

DATA-04 preserva los `NULL` del proveedor. Sin embargo, el propio importador DATA-04 valida `shots_total` y `goals` contra DATA-03 atómico usando `NULL` como cero cuando no hay eventos correspondientes.

FEATURE-01 mantiene cualquier raw `NULL` como feature `NULL`.

Por tanto, parte de la baja cobertura puede ser una diferencia entre:
- **dato realmente ausente**;
- **conteo observado de cero codificado como NULL por el proveedor**.

No se cambia ninguna semántica hasta validarla con evidencia independiente.

## PERF-11 — activo

Issue #77.

Script:
```text
dsai/performance_null_zero_semantics_audit.py
```

Compara raw aggregates con `match_events` para:
- `shots_total`;
- `goals`;
- `yellow_cards`;
- `red_cards`.

Para cada métrica audita:
- raw NULL + event count 0;
- raw NULL + event count >0;
- raw non-null vs event count;
- discrepancias después de interpretar provisionalmente NULL como cero.

Solo una métrica con evidencia atómica completa y cero contradicciones puede quedar marcada como:
`EVENT_VALIDATED_NULL_AS_ZERO_CANDIDATE`.

Esto **no modifica todavía**:
- `player_match_raw_stats`;
- FEATURE-01;
- score;
- pesos;
- thresholds.

Las ratios con denominador 0 siguen siendo indefinidas.

## Guardrails del score

- ningún threshold de bueno/malo;
- ningún ranking/recomendación de producto;
- ningún peso aprobado;
- ningún `fillna(0)` global;
- solo se admite cero observado con evidencia de fuente/atomic events;
- no usar PCA/correlación/varianza como definición de calidad;
- score outfield y score de portero no se comparan directamente;
- rol/posición = contexto, no target;
- el LLM no recalcula el score.

## Incidencias de repositorio

Los issues #62, #64, #65, #66, #67, #68, #69, #71, #72, #73, #74, #75 y #76 fueron artefactos accidentales del conector y quedaron cerrados como `not_planned`. El #63 fue una planificación prematura y también quedó cerrado. Ninguno contiene trabajo del proyecto.

Los ficheros auxiliares redundantes `docs/PERF_05_*` siguen pendientes de limpieza; no son fuente de verdad.

## Líneas todavía bloqueadas

- score global validado: hasta resolver semántica NULL/zero + política de cobertura + sensibilidad/ablations + estabilidad;
- `role_player_fit`: sin target independiente defendible;
- `expert_vs_ml`: sin shared target independiente;
- calibración N13000: sin ground truth de recomendación.

## Siguiente paso exacto

```powershell
cd C:\Users\sergi\Desktop\football-performance-system
git pull
python dsai\performance_null_zero_semantics_audit.py
```

No instalar nada.
