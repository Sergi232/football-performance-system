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
PERF-03 DIMENSION MAPPING AUDIT     ACTIVO — ISSUE #54 / SCRIPT IMPLEMENTADO
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

Resultado v0.1.1:

```text
played_rows=590
players=28
matches=38
approved_features=28
domain_nodes=24
mapped_unique_features=23
unmapped_approved_features=5
duplicate_mapped_features=1
unmapped_features=dribble_success_rate,goals_conceded_per90,red_cards_per90,saves_per90,yellow_cards_per90
duplicate_features=shots_total_per90
role_context=418/590
conclusion=DIMENSION_MAPPING_AND_DIRECTION_VALIDATION_REQUIRED
```

Decisión:
- cobertura suficiente para continuar;
- 5 features aprobadas necesitan mapping explícito;
- `shots_total_per90` no puede contarse dos veces en un futuro score;
- portero y disciplina requieren dimensión/tratamiento explícito;
- ningún signo o peso queda aprobado.

## PERF-03 — activo

Issue #54.

Ficheros:
```text
dsai/performance_dimension_map.json
dsai/performance_dimension_mapping_audit.py
```

Objetivo: cerrar el mapping estructural de las 28 FEATURE-01 antes de validar direcciones.

Dimensiones estructurales candidatas:
- `attacking_threat`
- `creation_progression`
- `defensive_contribution`
- `finishing`
- `discipline`
- `goalkeeping` (role-specific)

Reglas:
- cada feature tiene exactamente una `primary_dimension`;
- `shots_total_per90` queda con una sola dimensión primaria y puede mantenerse como contexto secundario de finalización sin doble conteo;
- el mapping no asigna dirección positiva/negativa;
- no crea pesos, score, thresholds, rankings ni recomendaciones;
- N4000-N7000 siguen siendo evidencia experta separada de la futura fórmula del performance score.

Conclusión esperada si pasa:
`DIMENSION_MAPPING_COMPLETE_DIRECTION_VALIDATION_REQUIRED`.

## Incidencias de issues

Issue #55 fue un artefacto accidental del conector y quedó cerrado inmediatamente como `not_planned`. No contiene trabajo del proyecto.

## Líneas todavía bloqueadas

- score global final: hasta validar mapping, direcciones y pesos;
- `role_player_fit`: sin target independiente defendible;
- `expert_vs_ml`: sin shared target independiente;
- calibración N13000: sin ground truth de recomendación.

## Siguiente paso exacto

```powershell
cd C:\Users\sergi\Desktop\football-performance-system
git pull
python dsai\performance_dimension_mapping_audit.py
```

No instalar nada.
