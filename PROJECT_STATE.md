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
PERF-05 SIGNED CORE FEASIBILITY     ACTIVO — ISSUE #57 / SCRIPT IMPLEMENTADO
FINAL-01                            BLOQUEADO HASTA REDISEÑO DE PRODUCTO
```

## Objetivo principal confirmado

El objetivo analítico central es **adjudicar un score de rendimiento jugador-partido**.

```text
PLAYER-MATCH DATA
→ DIMENSIONES DE RENDIMIENTO
→ VALIDACIÓN DE DIRECCIONES
→ AUDITORÍA DEL NÚCLEO PUNTUABLE
→ VALIDACIÓN DE PESOS / AGREGACIÓN
→ SCORE GLOBAL VALIDADO
→ EVOLUCIÓN / CONSISTENCIA
→ CONTEXTO DE ROL
→ CONCLUSIONES / RECOMENDACIONES
```

Rol/posición se usa como contexto de comparación/normalización. No existe todavía una fórmula de score aprobada.

## PERF-03 — cerrado

Resultado: `DIMENSION_MAPPING_COMPLETE_DIRECTION_VALIDATION_REQUIRED`.

28/28 features tienen exactamente una `primary_dimension`, sin features desconocidas ni duplicación primaria. `goalkeeping` es role-specific y `shots_total_per90` solo puede contarse una vez.

## PERF-04 — cerrado

Resultado ejecutado:

```text
approved_features=28
direction_entries=28
covered_unique_features=28
positive_supported=6
negative_supported=5
context_dependent=17
pending_evidence=0
missing=0
unknown=0
duplicates=0
invalid_statuses=0
mapping_missing=0
conclusion=DIRECTION_CLASSIFICATION_COMPLETE_CONTEXTUAL_METRICS_RETAINED
```

Decisión:
- 11 features tienen dirección respaldada (6 positiva, 5 negativa);
- 17 se mantienen `CONTEXT_DEPENDENT` y no se fuerzan dentro de un score;
- ninguna feature queda sin evidencia administrativa (`PENDING_EVIDENCE=0`), pero contextual no significa puntuable;
- ningún peso, threshold o score queda aprobado.

Registro:
```text
dsai/performance_direction_evidence.json
dsai/performance_direction_audit.py
```

## PERF-05 — activo

Issue #57.

Objetivo: auditar si las features con dirección respaldada forman un núcleo puntuable suficiente por dimensión antes de construir cualquier agregado.

Se comprobará:
- cobertura real de las 11 features `POSITIVE_SUPPORTED`/`NEGATIVE_SUPPORTED` en los 590 player-match jugados;
- qué dimensiones disponen de al menos una feature firmada;
- qué dimensiones dependen exclusivamente de métricas contextuales;
- separación explícita de `goalkeeping`;
- cobertura de filas por dimensión sin crear medias, z-scores, pesos o rankings.

Regla estructural importante:
- si `goalkeeping` no tiene ninguna feature con dirección defendible, no se forzará dentro del mismo score de jugadores de campo;
- el resultado decidirá si procede un núcleo outfield separado y qué validación adicional necesita portería.

## Incidencias de issues

Issue #55 fue un artefacto accidental del conector y quedó cerrado inmediatamente como `not_planned`. No contiene trabajo del proyecto.

## Líneas todavía bloqueadas

- score global final: hasta validar núcleo puntuable y pesos;
- `role_player_fit`: sin target independiente defendible;
- `expert_vs_ml`: sin shared target independiente;
- calibración N13000: sin ground truth de recomendación.

## Siguiente paso exacto

```powershell
cd C:\Users\sergi\Desktop\football-performance-system
git pull
python dsai\performance_signed_core_audit.py
```

No instalar nada.
