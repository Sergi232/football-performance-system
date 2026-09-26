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
PERF-04 DIRECTION VALIDATION        ACTIVO — ISSUE #56 / SCRIPT IMPLEMENTADO
FINAL-01                            BLOQUEADO HASTA REDISEÑO DE PRODUCTO
```

## Objetivo principal confirmado

El objetivo analítico central es **adjudicar un score de rendimiento jugador-partido**.

```text
PLAYER-MATCH DATA
→ DIMENSIONES DE RENDIMIENTO
→ VALIDACIÓN DE DIRECCIONES
→ VALIDACIÓN DE PESOS / AGREGACIÓN
→ SCORE GLOBAL VALIDADO
→ EVOLUCIÓN / CONSISTENCIA
→ CONTEXTO DE ROL
→ CONCLUSIONES / RECOMENDACIONES
```

Rol/posición se usa como contexto de comparación/normalización. No existe todavía una fórmula de score aprobada.

## DSAI-11 — cerrado

La persistencia simple de última posición observada (89,44% accuracy) supera ampliamente el ML pre-match (49,29%). La clasificación de posición queda cerrada como `CONTEXT_ONLY`.

## PERF-01 — cerrado

Resultado final: `EXPERT_WEIGHT_VALIDATION_REQUIRED`.

No existe un anchor holístico individual independiente en la fuente auditada. El score se construirá como constructo validado; no como copia/predicción de un rating de proveedor.

## PERF-02 — cerrado

Resultado final: `DIMENSION_MAPPING_AND_DIRECTION_VALIDATION_REQUIRED`.

```text
approved_features=28
mapped_unique_features=23
unmapped_approved_features=5
duplicate_mapped_features=1
```

Detectó 5 features sin mapping explícito y la duplicación de `shots_total_per90`.

## PERF-03 — cerrado

Resultado:

```text
approved_features=28
mapping_entries=28
mapped_unique_features=28
dimensions=6
missing=0
unknown=0
duplicate_primary=0
goalkeeping_scope_ok=True
shots_primary_once=True
shots_secondary_finishing_context=True
dimension_counts=attacking_threat:5,creation_progression:9,defensive_contribution:7,discipline:2,finishing:3,goalkeeping:2
conclusion=DIMENSION_MAPPING_COMPLETE_DIRECTION_VALIDATION_REQUIRED
```

Decisión:
- 28/28 features tienen exactamente una `primary_dimension`;
- no hay features desconocidas ni duplicación primaria;
- `goalkeeping` es role-specific;
- `shots_total_per90` solo puede contarse una vez y conserva finalización como contexto secundario.

Ficheros:
```text
dsai/performance_dimension_map.json
dsai/performance_dimension_mapping_audit.py
```

## PERF-04 — activo

Issue #56.

Objetivo: validar la dirección de cada feature antes de construir prototipos de dimensiones o pesos.

Estados permitidos:
- `POSITIVE_SUPPORTED`
- `NEGATIVE_SUPPORTED`
- `CONTEXT_DEPENDENT`
- `PENDING_EVIDENCE`

La evidencia se registra en:
```text
dsai/performance_direction_evidence.json
dsai/performance_direction_audit.py
```

Principios:
- semántica directa de evento puede justificar una dirección cuando el outcome es inequívoco;
- literatura académica se usa como evidencia convergente, no como ground truth individual cuando el estudio es team-level;
- métricas de volumen no se convierten automáticamente en mejor/peor;
- métricas de portero y oportunidad siguen siendo contextuales/role-specific;
- ninguna dirección autoriza todavía pesos o score.

Literatura inicial documentada:
- Kempe et al. 2018 — DOI 10.2174/1875399X01811010003;
- Wang et al. 2022 — DOI 10.1371/journal.pone.0265540 / PMID 35298562;
- World Cup match-statistics study — PMID 23487020;
- Bayrakdaroğlu et al. 2026 — PMID 42216227;
- Bar-Eli et al. 2006 — PMID 17115523.

## Incidencias de issues

Issue #55 fue un artefacto accidental del conector y quedó cerrado inmediatamente como `not_planned`. No contiene trabajo del proyecto.

## Líneas todavía bloqueadas

- score global final: hasta validar direcciones y pesos;
- `role_player_fit`: sin target independiente defendible;
- `expert_vs_ml`: sin shared target independiente;
- calibración N13000: sin ground truth de recomendación.

## Siguiente paso exacto

```powershell
cd C:\Users\sergi\Desktop\football-performance-system
git pull
python dsai\performance_direction_audit.py
```

No instalar nada.
