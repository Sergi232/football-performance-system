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
PERF-01..13                         CERRADO / SCORE POLICY VALIDADA
PERF-14 POSITION-SPECIFIC SCORE     CERRADO COMO BASELINE EXPERIMENTAL — ISSUE #87
SCORE-INTEGRATION-01                ACTIVO / MATERIALIZACIÓN + DASHBOARD IMPLEMENTADOS
FINAL-01                            DESBLOQUEADO TRAS VALIDAR SCORE-INTEGRATION-01
```

## Objetivo principal confirmado

El objetivo analítico central es **adjudicar un score de rendimiento jugador-partido** que sea auditable, role-aware y utilizable por el sistema analítico, dashboard y asistente IA.

## Score congelado como baseline experimental

Versión de producto:

```text
performance_score_v0.1-experimental
```

Arquitectura:

```text
raw data
-> FEATURE-01
-> semántica NULL/0 validada PERF-11
-> percentiles dentro del grupo posicional
-> dimensiones PERF
-> AVAILABLE_3PLUS
-> pesos posicionales experimentales
-> performance_score 0-100
-> score_evidence_confidence
```

Grupos posicionales:

```text
CB
FB_WB
DM_CM
AM_W
ST
```

Porteros mantienen un camino separado.

## PERF-14 — gate cerrado

Resultado final v2:

```text
outfield_rows                  = 552
observable_mapped_role_rows    = 380
eligible_rows_observable_roles = 304
coverage_rate_observable_roles = 0.8000
source_role_unavailable_rows   = 172
total_outfield_coverage_rate   = 0.5507
spearman_vs_unweighted_3plus   = 0.8964
```

Cobertura por grupo:

```text
CB      53/86 = 61.63%
FB_WB   42/68 = 61.76%
DM_CM   89/95 = 93.68%
AM_W    58/65 = 89.23%
ST      62/66 = 93.94%
```

Los 172 `Substitute` no se consideran un fallo del score: DATA-02/DSAI-05 estableció que la fuente no ofrece un rol táctico fiable para esas apariciones. No se imputa posición desde historia, modal role ni otro partido.

Mapping corregido:

```text
Defender | Left/Centre              -> CB
Defender | Centre/Right             -> CB
Midfielder | Left/Centre            -> DM_CM
Midfielder | Centre/Right           -> DM_CM
Defensive Midfielder | Left/Centre  -> DM_CM
Midfielder | Left/Right             -> AM_W
Wing Back | Left/Right              -> FB_WB
Striker                              -> ST
```

Sensibilidad de priors: el peor Spearman ante perturbaciones +/-1 de los pesos queda aproximadamente entre 0.986 y 0.989 en los cinco grupos candidatos. Se considera suficientemente estable para un baseline experimental.

### Decisión

`performance_score_v0.1-experimental` queda congelado como **baseline experimental de producto**, no como verdad científica definitiva.

Los priors siguen siendo revisables cuando haya más datos o validación externa. No se abren más auditorías PERF antes de integrar el MVP.

## SCORE-INTEGRATION-01 — activo

Implementado en GitHub:

```text
analytics/build_performance_score.py
app/performance_score_access.py
app/pages/1_Performance_Score.py
app/validate_performance_score.py
```

### Materialización

`analytics/build_performance_score.py` reutiliza PERF-14 v2 y escribe en DuckDB:

```text
player_match_performance_score
```

La tabla contiene, por jugador-partido:

- posición/rol observado;
- grupo posicional;
- cinco dimensiones;
- `performance_score`;
- `score_evidence_confidence`;
- estado de elegibilidad;
- método y versión;
- versión del experimento fuente.

El dashboard NO recalcula el score.

### Dashboard

Nueva página Streamlit:

```text
Performance Score
```

Muestra:

- score 0-100;
- confidence de evidencia;
- grupo posicional;
- dimensiones disponibles;
- cinco dimensiones;
- evolución temporal;
- historial jugador-partido;
- explicación explícita cuando no existe rol táctico observable.

## Guardrails vigentes

- no copiar fórmulas propietarias Sofascore/FotMob;
- no convertir missing en 0 fuera de PERF-11;
- no threshold bueno/malo sin validación;
- no etiqueta automática de calidad;
- no recomendación táctica derivada directamente del score;
- suplentes sin rol táctico observable no se imputan;
- porteros mantienen camino separado;
- el LLM no calcula ni altera el score;
- el dashboard consume resultados materializados, no recalcula lógica crítica.

## Siguiente paso exacto

```powershell
cd C:\Users\sergi\Desktop\football-performance-system
git pull
python analytics\build_performance_score.py
python app\validate_performance_score.py
streamlit run app\streamlit_app.py
```

Resultado esperado del validador:

```text
PERFORMANCE SCORE DASHBOARD CONTRACT: PASS
rows=552
observable_role_rows=380
eligible_scores=304
coverage_observable_roles=0.8000
source_role_unavailable_rows=172
```

Después de este PASS:

1. cerrar issue #87;
2. marcar SCORE-INTEGRATION-01 como cerrado;
3. integrar el score en contexto LLM/informes;
4. continuar con evolución temporal, alertas y uso del score dentro del producto sin modificar su fórmula base.
