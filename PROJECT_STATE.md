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
PERF-07 GK SAVE_RATE CONTEXT         CERRADO / FEATURE ADMISSION READY — ISSUE #59
PERF-08 AGGREGATION FEASIBILITY      ACTIVO — ISSUE #60
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
→ SENSIBILIDAD / ESTABILIDAD
→ SCORE GLOBAL VALIDADO
→ EVOLUCIÓN / CONSISTENCIA
→ CONTEXTO DE ROL
→ CONCLUSIONES / RECOMENDACIONES
```

Rol/posición se usa como contexto de comparación/normalización, no como objetivo principal.

## PERF-07 — cerrado

Resultado v0.1.1:

```text
played_rows=590
candidate_rows=31
players=1
matches=31
direct_gk_candidates=31
validated_context_rows=31
direct_conflicts=0
unknown_mixed=0
unknown_no_gk_evidence=0
positive_save_rows=34
positive_save_current_non_gk=0
current_positions=Goalkeeper:31
conclusion=SAVE_RATE_GOALKEEPER_CONTEXT_VALIDATED_FEATURE_ADMISSION_READY
```

Decisión:
- las 31 filas derivables de `save_rate` son directamente `Goalkeeper`;
- no existe contaminación por `saves > 0` en roles no-portero;
- `goals_conceded` en jugadores de campo se conserva como contexto informativo y no bloquea;
- `save_rate = saves / (saves + goals_conceded)` queda admitida como feature **role-specific de portero** para la línea de performance score;
- no se inventa xGOT/PSxG ni ajuste por calidad del tiro.

`save_rate` se registra fuera de FEATURE-01 por ahora para no romper el contrato actual del feature engine. Su integración formal se hará junto al score engine cuando la política de normalización quede cerrada.

## PERF-08 — activo

Issue #60.

Objetivo: comprobar si el núcleo signado puede normalizarse y agregarse de forma transparente antes de crear el primer score experimental.

Entrada:
- 11 FEATURE-01 con dirección respaldada;
- `save_rate` role-specific para portero;
- mapping primario de dimensiones;
- rol/posición únicamente como contexto.

Auditará:
- cobertura, dispersión, valores únicos y zero-inflation de cada feature signada;
- viabilidad de normalización global robusta/rank-based sin imponer todavía una fórmula;
- cobertura de cada dimensión con evidencia disponible;
- soporte de contexto por `source_position` sin exigir posición como target;
- separación estructural outfield / goalkeeper.

No crea todavía:
- score;
- pesos aprobados;
- thresholds;
- rankings;
- recomendaciones.

## Política de agregación que se evaluará

La ruta preferente para el primer experimento, si PERF-08 pasa, será un **baseline nulo y auditable**:
1. transformar cada feature respetando su signo;
2. normalizar con método robusto/rank-based validado por la distribución;
3. agregar primero feature → dimensión;
4. agregar después dimensión → global para evitar que una dimensión domine solo por tener más variables;
5. tratar pesos iguales únicamente como baseline experimental, nunca como peso final aprobado;
6. ejecutar sensibilidad/ablations antes de cualquier uso de producto.

## Líneas todavía bloqueadas

- score global final: hasta PERF-08 + baseline experimental + sensibilidad;
- `role_player_fit`: sin target independiente defendible;
- `expert_vs_ml`: sin shared target independiente;
- calibración N13000: sin ground truth de recomendación.

## Siguiente paso exacto

```powershell
cd C:\Users\sergi\Desktop\football-performance-system
git pull
python dsai\performance_aggregation_feasibility.py
```

No instalar nada.
