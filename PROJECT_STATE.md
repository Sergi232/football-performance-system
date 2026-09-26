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
PERF-01 PERFORMANCE SCORE AUDIT     ACTIVO — ISSUE #52 / v0.2 PENDIENTE DE REEJECUCIÓN
FINAL-01                            BLOQUEADO HASTA REDISEÑO DE PRODUCTO
```

## Objetivo principal confirmado

El objetivo analítico central es **adjudicar un score de rendimiento jugador-partido**, no predecir posiciones.

Arquitectura objetivo:

```text
PLAYER-MATCH DATA
→ DIMENSIONES DE RENDIMIENTO
→ SCORE GLOBAL VALIDADO
→ EVOLUCIÓN / CONSISTENCIA
→ CONTEXTO DE ROL
→ CONCLUSIONES / RECOMENDACIONES
```

Rol/posición se usa como contexto de comparación/normalización cuando existe de forma observada y fiable. No vuelve a ser el target principal del DS/ML.

No existe todavía una fórmula de score aprobada. No se inventan pesos, signos, percentiles, escalas ni thresholds.

## DSAI-11 — resultado cerrado

```text
candidate_rows=418
evaluated_rows=353
evaluated_positions=6
rows_with_prior_position=341
model_all_safe_accuracy=0.4929
model_all_safe_balanced_accuracy=0.3176
model_all_safe_macro_f1=0.3054
model_prior_mean_only_accuracy=0.4646
model_prev_only_accuracy=0.5552
player_last_position_accuracy=0.8944
player_last_position_balanced_accuracy=0.6982
player_last_position_macro_f1=0.6934
player_modal_position_accuracy=0.8915
switches=36
stays=305
ml_switch_accuracy=0.3611
head_to_head_model_only=13
head_to_head_last_only=150
both_correct=155
both_wrong=23
```

Decisión: `POSITION_CLASSIFICATION_LINE_CLOSED / CONTEXT_ONLY`.

La persistencia simple de última posición observada (89,44% accuracy) supera ampliamente el ML pre-match (49,29%). No se justifica seguir optimizando la clasificación de posición. El trabajo DSAI-04..11 se conserva como evidencia académica de auditoría de target, leakage control, validación temporal, baselines y reformulación de labels. A partir de ahora, posición/rol queda como contexto de rendimiento.

## PERF-01 — activo

Issue #52.

La primera ejecución de PERF-01 devolvió:

```text
played_rows=590
players=28
matches=38
features=28
feature_values=6324/16520
role_context=418/590
domain_nodes=24
external_anchor_candidates=3
anchor_columns=home_score,away_score,bigChanceScored
conclusion=SUPERVISED_ANCHOR_CANDIDATE
```

Esta conclusión **no se acepta** porque los tres nombres son falsos positivos semánticos del escaneo lexical:
- `home_score` y `away_score` son contexto/resultado del partido, no una valoración individual independiente;
- `bigChanceScored` es una estadística componente de rendimiento, no un rating holístico externo.

Se ha corregido `dsai/performance_score_audit.py` a `performance_score_audit_0.2.0` para separar coincidencia lexical de anchor semánticamente válido. Un campo `score/index/rank` solo puede aceptarse si está explícitamente cualificado como constructo de jugador/rendimiento; `rating/grade` también debe pasar bloqueadores de contexto/componentes.

Objetivo de la reejecución:
- confirmar cobertura FEATURE-01 y dominios N4000-N7000;
- registrar falsos positivos rechazados;
- determinar si existe realmente un anchor holístico de jugador;
- si no existe, la ruta pasa a `EXPERT_WEIGHT_VALIDATION_REQUIRED`.

Reglas:
- no crear score todavía;
- no asumir que más volumen = mejor;
- no usar ratings externos como input del producto; solo como posible anchor de validación;
- GPS fuera del score base mientras no haya observaciones reales;
- escala final del score pendiente de validación.

## Líneas todavía bloqueadas

- `role_player_fit`: sin target independiente defendible;
- `expert_vs_ml`: sin shared target independiente;
- calibración N13000: sin ground truth de recomendación;
- score global final: bloqueado hasta validar constructo, direcciones y pesos/anchor.

## Siguiente paso exacto

```powershell
cd C:\Users\sergi\Desktop\football-performance-system
git pull
python dsai\performance_score_audit.py
```

No instalar nada.
