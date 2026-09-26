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
PERF-07 GK SAVE_RATE CONTEXT         ACTIVO — ISSUE #59 / SCRIPT IMPLEMENTADO
FINAL-01                            BLOQUEADO HASTA REDISEÑO DE PRODUCTO
```

## Objetivo principal confirmado

El objetivo analítico central es **adjudicar un score de rendimiento jugador-partido**.

```text
PLAYER-MATCH DATA
→ DIMENSIONES DE RENDIMIENTO
→ VALIDACIÓN DE DIRECCIONES
→ AUDITORÍA DEL NÚCLEO PUNTUABLE
→ VALIDACIÓN ESPECÍFICA DE PORTERO
→ VALIDACIÓN DE PESOS / AGREGACIÓN
→ SCORE GLOBAL VALIDADO
→ EVOLUCIÓN / CONSISTENCIA
→ CONTEXTO DE ROL
→ CONCLUSIONES / RECOMENDACIONES
```

Rol/posición se usa como contexto de comparación/normalización. No existe todavía una fórmula de score aprobada.

## PERF-06 — cerrado

Resultado ejecutado:
```text
candidate_rows=397
players=26
matches=36
rows_with_both_inputs=31
positive_denominator=31
save_rate_rows=31
anomalies=0
save_rate=min:0.2500 median:0.6250 max:0.8333
conclusion=GOALKEEPER_SAVE_RATE_DERIVABLE_CONTEXT_VALIDATION_REQUIRED
```

Decisión:
- `save_rate = saves / (saves + goals_conceded)` es matemáticamente derivable;
- 31 player-match tienen denominador válido;
- no hay valores fuera de 0..1;
- todavía no entra en FEATURE-01 hasta validar que esas filas son realmente de portero.

## PERF-07 — activo

Issue #59.

Script:
```text
dsai/goalkeeper_save_rate_context_audit.py
```

Objetivo: validar contexto y procedencia de las 31 filas derivables antes de admitir `save_rate` como feature role-specific.

Audita:
- `primary_role` / `source_position` actual;
- contradicciones explícitas de rol no-portero;
- filas con rol actual desconocido y evidencia source-backed de portero del mismo jugador en otros partidos;
- posibles eventos positivos de portero asignados a roles actuales no-portero.

Reglas:
- el historial de rol se usa solo para auditoría semántica, nunca como predictor o imputación de rendimiento;
- no se inventa xGOT/PSxG;
- no se crea score, peso, threshold, ranking o recomendación;
- no se modifica FEATURE-01 en PERF-07.

Si el contexto queda validado, el siguiente paso será admitir `save_rate` como feature de portero con dirección positiva contextualizada y pasar a validación de agregación/pesos.

## Incidencias de repositorio

Issue #55 fue un artefacto accidental del conector y quedó cerrado inmediatamente como `not_planned`.

Durante la preparación de PERF-05 se generaron varios ficheros auxiliares redundantes bajo `docs/PERF_05_*`; no son fuente de verdad y se limpiarán sin afectar resultados.

## Líneas todavía bloqueadas

- score global final: hasta validar portero y agregación/pesos;
- `role_player_fit`: sin target independiente defendible;
- `expert_vs_ml`: sin shared target independiente;
- calibración N13000: sin ground truth de recomendación.

## Siguiente paso exacto

```powershell
cd C:\Users\sergi\Desktop\football-performance-system
git pull
python dsai\goalkeeper_save_rate_context_audit.py
```

No instalar nada.
