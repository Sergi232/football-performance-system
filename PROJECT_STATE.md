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
DSAI-01A..11                        CERRADO / RESULTADOS DOCUMENTADOS
PERF-01..12                         CERRADO / AUDITORÍAS + NULL/ZERO VALIDADO
PERF-13 SCORE POLICY + ROLE-AWARE   CERRADO / CANDIDATO 3PLUS + ROLE_AWARE
PERF-14 POSITION-SPECIFIC SCORE     ACTIVO — ISSUE #87 / SCRIPT IMPLEMENTADO
FINAL-01                            BLOQUEADO HASTA GATE PERF-14
```

## Objetivo principal confirmado

El objetivo analítico central es **adjudicar un score de rendimiento jugador-partido** que sea auditable, role-aware y utilizable por el sistema experto, dashboard y asistente IA.

## PERF-11 — NULL vs zero

Validado:

```text
shots_total NULL -> 0 cuando el evento observado no ocurrió
goals NULL       -> 0 cuando el evento observado no ocurrió
red_cards NULL   -> 0 cuando el evento observado no ocurrió
yellow_cards     -> NO reinterpretar como 0 (5 contradicciones)
```

## PERF-12 — impacto de la semántica validada

```text
outfield_rows=552
full_five_before=3
full_five_after=100
finishing: 37 -> 552
discipline: 87 -> 552
attacking_threat: 196 -> 196
creation_progression: 413 -> 413
defensive_contribution: 262 -> 262

2 dimensiones = 67
3 dimensiones = 199
4 dimensiones = 186
5 dimensiones = 100
```

Conclusión: exigir 5/5 descarta demasiados jugador-partido.

## PERF-13 — cerrado

Scripts:

- `dsai/performance_score_policy_experiment.py`
- `dsai/performance_score_policy_experiment_v2.py` — compatibilidad pandas 3.x.

Resultado:

```text
GLOBAL
COMPLETE_5D     100/552 = 18.12%
AVAILABLE_4PLUS 286/552 = 51.81%
AVAILABLE_3PLUS 485/552 = 87.86%
AVAILABLE_2PLUS 552/552 = 100.00%

ROLE_AWARE
COMPLETE_5D     100/552 = 18.12%
AVAILABLE_4PLUS 286/552 = 51.81%
AVAILABLE_3PLUS 485/552 = 87.86%
AVAILABLE_2PLUS 552/552 = 100.00%
```

Gate metodológico:

**Candidato seleccionado para continuar: `AVAILABLE_3PLUS + ROLE_AWARE`.**

Motivos:

- 87.9% de cobertura;
- `2PLUS` se considera demasiado permisivo como baseline de producto;
- `4PLUS/5D` pierden demasiados casos;
- GLOBAL vs ROLE_AWARE en 3PLUS: Spearman `0.9419`, mean absolute delta `2.29`;
- la adaptación posicional cambia el score sin destruir el orden general.

Sensibilidad 3PLUS ROLE_AWARE:

```text
attacking_threat        mean_abs_delta 2.28 | Spearman 0.910
creation_progression    mean_abs_delta 5.37 | Spearman 0.748
defensive_contribution  mean_abs_delta 3.43 | Spearman 0.864
finishing               mean_abs_delta 3.94 | Spearman 0.944
discipline              mean_abs_delta 3.39 | Spearman 0.982
```

Conclusión: una media igual de dimensiones no debe congelarse como score final. `creation_progression` domina demasiado el ranking agregado y justifica pasar a ponderación específica por posición.

## PERF-14 — activo

Issue: **#87 — position-specific performance score + confidence**

Archivos:

- `dsai/performance_position_weight_priors.json`
- `dsai/performance_position_score_experiment.py`

Grupos tácticos experimentales:

```text
CB
FB_WB
DM_CM
AM_W
ST
OTHER_OUTFIELD  # fallback diagnóstico, no candidato de producto
```

### Arquitectura PERF-14

```text
primary_role / source_position
-> position_group
-> percentiles de features dentro del position_group
-> dimensiones PERF existentes
-> mínimo 3 dimensiones + dimensión nuclear
-> pesos posicionales experimentales
-> performance_score_position_experimental
-> score_evidence_confidence
-> sensitivity gate
```

La normalización ahora es realmente específica por grupo táctico: un CB se compara contra CB, un ST contra ST, etc. Si una feature no se puede estimar dentro del grupo, se mantiene el fallback global ya validado en PERF-13.

### Priors posicionales

No son pesos finales ni se presentan como verdad científica. Se codifican como niveles ordinales de relevancia `1..5`, transparentes y auditables, y se normalizan en runtime.

Ejemplo conceptual:

- CB: prioridad defensiva;
- FB/WB: defensa + progresión;
- DM/CM: creación/progresión + defensa;
- AM/W: creación + amenaza ofensiva + finalización;
- ST: finalización + amenaza ofensiva.

Los missing no se imputan. Los pesos disponibles se renormalizan únicamente cuando la fila cumple la política de elegibilidad.

### Confidence

`score_evidence_confidence` NO es una probabilidad de acierto.

Es:

```text
peso posicional previsto realmente observado / peso posicional total previsto * 100
```

Permite distinguir un score sustentado por casi toda la evidencia relevante de uno calculado con evidencia parcial.

### Gate PERF-14

El script calcula:

- cobertura total y por posición;
- auditoría del mapping de `primary_role`;
- distribución del score;
- comparación con ROLE_AWARE 3PLUS sin pesos;
- leave-one-dimension-out por posición;
- perturbación +/-1 de cada nivel ordinal de peso;
- confidence de evidencia.

No se aprobarán los priors si el ranking es excesivamente sensible.

## Guardrails vigentes

- no copiar fórmula propietaria Sofascore/FotMob;
- no convertir missing en 0 fuera de la semántica PERF-11;
- no aprobar threshold bueno/malo sin validación;
- no introducir ranking/recomendación de producto todavía;
- porteros mantienen camino separado;
- LLM no calcula ni altera el score;
- DuckDB y FEATURE-01 no se mutan en estos experimentos.

## Siguiente paso exacto

```powershell
cd C:\Users\sergi\Desktop\football-performance-system
git pull
python dsai\performance_position_score_experiment.py
```

No instalar nada.

Outputs esperados:

```text
dsai/output/performance_position_score_experiment.json
dsai/output/performance_position_score_experiment.csv
dsai/output/performance_position_score_experiment.md
```

Después de esta ejecución se decide en un único gate:

1. si el mapping posicional es correcto;
2. si la cobertura sigue siendo suficiente;
3. si los priors son estables;
4. congelar o ajustar `performance_score_v0.1-experimental`;
5. pasar inmediatamente a integración con motor experto/dashboard.
