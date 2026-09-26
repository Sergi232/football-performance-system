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
PERF-01 PERFORMANCE SCORE AUDIT     ACTIVO — ISSUE #52 / SCRIPT IMPLEMENTADO
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

La regla simple y estrictamente pre-match de última posición observada (89,44% accuracy) supera ampliamente al ML (49,29%). No se justifica seguir optimizando esta línea. Se conserva la evidencia académica ya generada y la posición pasa a ser contexto para rendimiento.

## PERF-01 — activo

Issue #52.

Script:

```powershell
python dsai\performance_score_audit.py
```

Objetivo: auditar qué necesitamos para construir un score de rendimiento defendible antes de calcularlo.

Se audita:
- cobertura real de FEATURE-01 en player-match con minutos;
- cobertura por dimensiones N4000-N7000;
- disponibilidad de contexto táctico observado;
- posibles anchors externos de validación en `opta_player_stats.parquet` (`rating`, `score`, `grade`, etc.);
- variables cuya dirección/peso todavía no está validada.

Reglas:
- no crear score todavía;
- no asumir que más volumen = mejor;
- no usar ratings externos como input del producto; solo podrían servir como anchor de validación;
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
