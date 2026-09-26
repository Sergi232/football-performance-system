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
PERF-06 GOALKEEPER EFFICIENCY       ACTIVO — ISSUE #58 / SCRIPT IMPLEMENTADO
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

## PERF-04 — cerrado

Resultado:
```text
positive_supported=6
negative_supported=5
context_dependent=17
pending_evidence=0
conclusion=DIRECTION_CLASSIFICATION_COMPLETE_CONTEXTUAL_METRICS_RETAINED
```

Decisión: 11 features tienen dirección respaldada; las 17 restantes siguen contextuales y no se fuerzan en el score.

## PERF-05 — cerrado

Resultado ejecutado:
```text
played_rows=590
players=28
matches=38
approved_features=28
signed_features=11
contextual_features=17
dimensions=6
dimensions_without_signed_core=1
outfield_without_signed_core=0
goalkeeping_signed_core_present=False
dimensions_without_signed=goalkeeping
conclusion=OUTFIELD_SIGNED_CORE_AVAILABLE_GOALKEEPER_SEPARATE_VALIDATION_REQUIRED
```

Decisión:
- todas las dimensiones outfield tienen al menos una feature con dirección respaldada;
- `goalkeeping` sigue sin núcleo firmado;
- no se fuerza portería dentro del núcleo outfield;
- no se ha creado ningún score, peso, normalización o threshold.

## PERF-06 — activo

Issue #58.

Script:
```text
dsai/goalkeeper_efficiency_feasibility.py
```

Objetivo: comprobar si puede derivarse de los raw aprobados una métrica de eficiencia específica de portero:
```text
shots_on_target_faced = saves + goals_conceded
save_rate = saves / (saves + goals_conceded)
```

Reglas:
- ambos inputs deben existir;
- denominador > 0;
- missing permanece missing;
- no se inventa xGOT/PSxG ni calidad de tiro;
- `save_rate` no entra en FEATURE-01 hasta que la auditoría pase;
- no se crea score de portero, pesos o thresholds en PERF-06.

Conclusiones posibles:
- `GOALKEEPER_SAVE_RATE_DERIVABLE_CONTEXT_VALIDATION_REQUIRED`;
- `GOALKEEPER_EFFICIENCY_INSUFFICIENT_RAW_EVIDENCE`;
- `GOALKEEPER_EFFICIENCY_INSUFFICIENT_DENOMINATOR_EVIDENCE`;
- `GOALKEEPER_EFFICIENCY_DATA_INCONSISTENCY_REQUIRES_FIX`;
- `GOALKEEPER_EFFICIENCY_BLOCKED_MISSING_RAW_COLUMNS`.

## Incidencias de repositorio

Issue #55 fue un artefacto accidental del conector y quedó cerrado inmediatamente como `not_planned`.

Durante la preparación de PERF-05 se generaron varios ficheros auxiliares redundantes bajo `docs/PERF_05_*`; no son fuente de verdad. Se limpiarán sin afectar metodología ni resultados. La fuente de verdad sigue siendo este archivo, `docs/PERFORMANCE_SCORE_METHOD.md` y los scripts/auditorías de `dsai/`.

## Líneas todavía bloqueadas

- score global final: hasta validar portero y agregación/pesos;
- `role_player_fit`: sin target independiente defendible;
- `expert_vs_ml`: sin shared target independiente;
- calibración N13000: sin ground truth de recomendación.

## Siguiente paso exacto

```powershell
cd C:\Users\sergi\Desktop\football-performance-system
git pull
python dsai\goalkeeper_efficiency_feasibility.py
```

No instalar nada.
