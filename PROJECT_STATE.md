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
PERF-10 COVERAGE / OBSERVABILITY    ACTIVO — ISSUE #70 / SCRIPT IMPLEMENTADO
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
→ SENSIBILIDAD / ABLATIONS
→ ESTABILIDAD TEMPORAL / CONTEXTO
→ SCORE GLOBAL VALIDADO
→ EVOLUCIÓN / CONSISTENCIA
→ CONCLUSIONES / RECOMENDACIONES
```

Rol/posición se usa como contexto de comparación/normalización, no como objetivo principal ni como componente directo del score.

## PERF-09 — cerrado

Resultado ejecutado:

```text
played_rows=590
outfield_eligible_rows=552
direct_gk_rows=38
unknown_gk_evidence_excluded=0
signed_candidates=11
used_features=10
excluded_degenerate=1
dimensions=5
complete_outfield_score_rows=3
goalkeeper_score_rows=31
excluded_features=penalties_conceded_per90
outfield_score=min:37.1014 p25:40.2510 median:43.4006 p75:48.7546 max:54.1085
goalkeeper_score=min:3.2258 p25:24.1935 median:51.6129 p75:77.4194 max:96.7742
conclusion=EXPERIMENTAL_SCORE_BASELINE_CREATED_SENSITIVITY_REQUIRED
```

Decisión:
- el primer score experimental existe y funciona técnicamente;
- sigue `EXPERIMENTAL / NO_DEPLOY`;
- `penalties_conceded_per90` queda excluida solo por degeneración en esta muestra;
- portería sigue separada mediante `save_rate`;
- **solo 3/552 filas outfield tienen las cinco dimensiones disponibles**;
- por esa cobertura, no se pasa todavía a sensibilidad de pesos: primero hay que entender el cuello de botella.

No se relaja el requisito de 5 dimensiones de forma arbitraria y missing no se convierte en cero.

## PERF-10 — activo

Issue #70.

Script:
```text
dsai/performance_score_coverage_audit.py
```

Objetivo: explicar la baja cobertura completa del score antes de cambiar política de agregación.

Audita:
- cobertura por feature signada;
- cobertura por dimensión;
- distribución de filas con 0..5 dimensiones disponibles;
- patrones de dimensiones ausentes;
- leave-one-dimension-out para identificar cuellos de botella;
- para per90: raw NULL vs raw zero vs raw >0;
- para ratios: inputs missing vs denominador zero vs denominador positivo;
- contexto descriptivo por `source_position`.

Reglas:
- no crea un score nuevo;
- no aprueba un mínimo de dimensiones;
- no imputa missing como cero;
- una ratio con denominador 0 se trata como indefinida, no como mal rendimiento;
- rol/posición = diagnóstico contextual;
- no se tocan pesos ni rankings.

Conclusiones posibles:
- `FULL_DIMENSION_COVERAGE_COMPLETE_SENSITIVITY_READY`;
- `FULL_DIMENSION_COVERAGE_INCOMPLETE_POLICY_REDESIGN_REQUIRED`.

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

Los issues #62, #64, #65, #66, #67, #68, #69, #71, #72, #73, #74, #75 y #76 fueron artefactos accidentales del conector y quedaron cerrados como `not_planned`. El #63 fue una planificación prematura y también quedó cerrado. Ninguno contiene trabajo del proyecto.

Los ficheros auxiliares redundantes `docs/PERF_05_*` siguen pendientes de limpieza; no son fuente de verdad.

## Líneas todavía bloqueadas

- score global validado: hasta resolver cobertura + sensibilidad/ablations + estabilidad;
- `role_player_fit`: sin target independiente defendible;
- `expert_vs_ml`: sin shared target independiente;
- calibración N13000: sin ground truth de recomendación.

## Siguiente paso exacto

```powershell
cd C:\Users\sergi\Desktop\football-performance-system
git pull
python dsai\performance_score_coverage_audit.py
```

No instalar nada.
