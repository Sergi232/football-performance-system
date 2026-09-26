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
PERF-07 GK SAVE_RATE CONTEXT         ACTIVO / RERUN v0.1.1 — ISSUE #59
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

Resultado:
```text
candidate_rows=397
rows_with_both_inputs=31
positive_denominator=31
save_rate_rows=31
anomalies=0
save_rate=min:0.2500 median:0.6250 max:0.8333
conclusion=GOALKEEPER_SAVE_RATE_DERIVABLE_CONTEXT_VALIDATION_REQUIRED
```

`save_rate = saves / (saves + goals_conceded)` es matemáticamente derivable, pero solo puede admitirse como feature específica de portero después de validar semántica y rol.

## PERF-07 — activo / rerun requerido

Issue #59.

Resultado v0.1.0:
```text
candidate_rows=31
players=1
matches=31
validated_context_rows=31
direct_conflicts=0
unknown_mixed=0
unknown_no_gk_evidence=0
current_positions=Goalkeeper:31
positive_gk_event_rows=397
positive_event_current_non_gk=299
conclusion=SAVE_RATE_CONTEXT_CONTAMINATION_REQUIRES_FIX
```

Revisión metodológica:
- las 31 filas derivables son directamente `Goalkeeper` y no tienen conflicto de rol;
- el criterio v0.1.0 marcó falsamente contaminación al tratar `goals_conceded > 0` en jugadores de campo como un evento específico de portero;
- `goals_conceded` puede aparecer como contexto de jugador/equipo y no bloquea por sí solo la feature;
- la contaminación real se comprobará con `saves > 0` asignado a un rol actual no-portero.

Corrección implementada en:
```text
dsai/goalkeeper_save_rate_context_audit.py
version=goalkeeper_save_rate_context_audit_0.1.1
```

Criterio de admisión:
- `save_rate` solo será admisible en filas cuya `source_position` actual sea `Goalkeeper`;
- historial de posición = auditoría de procedencia únicamente, nunca imputación o predictor;
- no se inventa xGOT/PSxG;
- no se crea todavía ningún score, peso o threshold.

## Líneas todavía bloqueadas

- score global final: hasta cerrar PERF-07 y validar agregación/pesos;
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
