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
PERF-02 DIMENSION EVIDENCE AUDIT    ACTIVO — ISSUE #53 / v0.1.1 PENDIENTE DE REEJECUCIÓN
FINAL-01                            BLOQUEADO HASTA REDISEÑO DE PRODUCTO
```

## Objetivo principal confirmado

El objetivo analítico central es **adjudicar un score de rendimiento jugador-partido**.

```text
PLAYER-MATCH DATA
→ DIMENSIONES DE RENDIMIENTO
→ SCORE GLOBAL VALIDADO
→ EVOLUCIÓN / CONSISTENCIA
→ CONTEXTO DE ROL
→ CONCLUSIONES / RECOMENDACIONES
```

Rol/posición se usa como contexto de comparación/normalización. No existe todavía una fórmula de score aprobada.

## DSAI-11 — cerrado

La persistencia simple de última posición observada (89,44% accuracy) supera ampliamente el ML pre-match (49,29%). La clasificación de posición queda cerrada como `CONTEXT_ONLY`.

## PERF-01 — cerrado

Resultado v0.2:

```text
played_rows=590
players=28
matches=38
features=28
feature_values=6324/16520
role_context=418/590
domain_nodes=24
external_anchor_candidates=0
rejected_lexical_matches=3
rejected_anchor_columns=home_score,away_score,bigChanceScored
conclusion=EXPERT_WEIGHT_VALIDATION_REQUIRED
```

Decisión:
- no existe un anchor holístico individual independiente en la fuente auditada;
- no se puede entrenar un score supervisado defendible usando un rating extern;
- la ruta pasa a validar **dimensions, direccions i posteriorment pesos**;
- no crear un score global abans d’aquesta validació.

## PERF-02 — activo

Issue #53.

Script:

```powershell
python dsai\performance_dimension_audit.py
```

Objetivo: convertir el catálogo actual en una auditoría completa de las dimensiones de rendimiento antes de asignar signo o peso.

Se audita:
- cobertura y variabilidad por métrica;
- cobertura por familia N4000-N7000;
- redundancias de una misma feature en más de un nodo;
- features FEATURE-01 no representadas en N4000-N7000;
- disponibilidad de contexto de rol;
- métricas de `output`, `efficiency`, `cost`, `volume` y `context` sin convertir esos roles semánticos en signos automáticos;
- cobertura específica de portero y disciplina, que no puede quedar oculta por el score general.

Primera ejecución: error técnico de serialización en `clean()` porque `pd.isna()` recibió valores array-like (`families`, `node_labels`, `metric_roles`). No afecta a la lógica de la auditoría.

Corrección `performance_dimension_audit_0.1.1`:
- listas, tuplas, sets y diccionarios se limpian recursivamente;
- arrays se convierten con `tolist()`;
- `pd.isna()` solo se aplica a escalares.

Reglas:
- no crear score;
- no asignar signo positivo/negativo automáticamente;
- no inventar pesos;
- no usar correlación o PCA como sinónimo de calidad;
- no ocultar features aprobadas que todavía no estén mapeadas a una dimensión.

## Líneas todavía bloqueadas

- score global final: hasta validar dimensiones, direcciones y pesos;
- `role_player_fit`: sin target independiente defendible;
- `expert_vs_ml`: sin shared target independiente;
- calibración N13000: sin ground truth de recomendación.

## Siguiente paso exacto

```powershell
cd C:\Users\sergi\Desktop\football-performance-system
git pull
python dsai\performance_dimension_audit.py
```

No instalar nada.
