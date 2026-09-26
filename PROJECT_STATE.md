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
PERF-01..14                         CERRADO / BASELINE v0.1 DOCUMENTADA
PERF-15 COVERAGE REPAIR             ACTIVO — ISSUE #90 / v0.2 IMPLEMENTADA PENDIENTE GATE LOCAL
SCORE-INTEGRATION-01                v0.1 CERRADO; v0.2 PENDIENTE VALIDACIÓN LOCAL
DASHBOARD-02 PLAYER VIEW            CERRADO — ISSUE #88 / VALIDADO VISUALMENTE
DASHBOARD-03 TEAM MODE              PAUSADO — ISSUE #89 HASTA CERRAR PERF-15
FINAL-01                            DESBLOQUEADO TRAS PERF-15
```

## Objetivo principal

Producto web funcional para cuerpo técnico de fútbol amateur/semiprofesional:

```text
COLLECTOR + GPS opcional
-> DATABASE
-> FEATURE ENGINE
-> ANALYTICS
-> EXPERT SYSTEM / ML
-> WEB DASHBOARD
-> ASSISTANT IA
-> PDF / informes
```

El dashboard web es el producto principal. PDF/PPT son salidas estáticas complementarias.

## Variables y datos vigentes

Las variables raw aprobadas/importadas siguen separadas de features y score. Entre las usadas por la corrección PERF-15 ya existen en `player_match_raw_stats`:

```text
passes_total / passes_completed
long_balls_total / long_balls_completed
crosses_total / crosses_completed
dribbles_total / dribbles_won
assists
penalties_won
tackles_total / tackles_won
interceptions
blocked_passes
clearances
shots_total / goals
red_cards
```

No se han inventado variables nuevas.

## PERF-11 — semántica NULL/0 validada

Validado previamente:

```text
shots_total NULL -> 0 cuando el evento observado no ocurrió
goals NULL       -> 0 cuando el evento observado no ocurrió
red_cards NULL   -> 0 cuando el evento observado no ocurrió
yellow_cards     -> NO reinterpretar como 0
```

PERF-15 añade únicamente una identidad matemática segura para pares éxito/intento:

```text
si attempts observado = 0 y success es NULL -> success = 0
```

Ejemplos: `tackles_total=0 => tackles_won=0`, `dribbles_total=0 => dribbles_won=0`.

Todos los demás NULL permanecen NULL.

## PERF-13 / PERF-14 — baseline anterior

Política seleccionada:

```text
AVAILABLE_3PLUS + ROLE_AWARE
```

PERF-14 v2:

```text
outfield_rows                  = 552
observable_mapped_role_rows    = 380
eligible_rows_observable_roles = 304
coverage_rate_observable_roles = 0.8000
source_role_unavailable_rows   = 172
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

Los 172 `Substitute` siguen sin imputarse: la fuente no ofrece rol táctico fiable para esas apariciones.

## Problema detectado en v0.1

La baseline `performance_score_v0.1-experimental` construía dimensiones únicamente con features cuya dirección estaba explícitamente validada.

Eso podía provocar:

```text
no hay feature signada
=> dimensión NULL
=> score no elegible
```

incluso cuando existían acciones futbolísticas positivas observadas. Casos de jugadores con muchas apariciones/titularidades podían quedar sin score o con dimensiones vacías.

Decisión: **v0.1 no se considera suficiente como baseline final de producto.** Se conserva como historial experimental, pero queda supersedida por la candidata v0.2 si supera el gate local.

## PERF-15 — coverage repair

Issue #90.

Versión candidata:

```text
performance_score_v0.2-experimental
source experiment: performance_position_score_experiment_0.3.0
```

Archivos:

```text
dsai/performance_position_score_experiment_v3.py
analytics/build_performance_score.py
app/performance_score_access.py
app/validate_performance_score.py
```

### Principio

Las dimensiones signadas de PERF-14 siguen siendo la evidencia principal.

Solo si una dimensión está vacía, PERF-15 puede utilizar `CONTRIBUTION_FALLBACK` basado en acciones exitosas/positivas ya observadas.

Fallbacks actuales:

```text
attacking_threat
- dribbles_won_per90
- penalties_won_per90

creation_progression
- passes_completed_per90
- long_balls_completed_per90
- crosses_completed_per90
- assists_per90

defensive_contribution
- tackles_won_per90
- interceptions_per90
- blocked_passes_per90
- clearances_per90
```

No se usan intentos contextuales como si "más siempre fuera mejor". El fallback representa contribución observada y queda etiquetado explícitamente.

### Normalización

```text
successful actions raw
-> per90
-> percentil dentro del position_group
-> global fallback solo si la distribución del grupo no es estimable
-> rellenar únicamente dimensión previamente NULL
```

### Elegibilidad

Se mantiene:

```text
>=3 dimensiones + dimensión core del grupo posicional
```

No se imputa rol de suplentes.

### Provenance

Cada dimensión materializada puede quedar marcada como:

```text
DIRECT_SIGNED
CONTRIBUTION_FALLBACK
MISSING
```

La tabla `player_match_performance_score` añade:

```text
fallback_dimension_count
attacking_threat_evidence
creation_progression_evidence
defensive_contribution_evidence
finishing_evidence
discipline_evidence
```

## Gate PERF-15

La validación local debe cumplir:

1. cobertura de rol observable >= 0.80;
2. eligible rows no puede bajar de 304;
3. reportar filas recuperadas;
4. reportar número de scores que usan fallback;
5. mantener 172 filas con rol de fuente no observable;
6. ningún jugador de campo con >=10 titularidades puede quedar con 0 scores elegibles.

El punto 6 es un gate de calidad de cobertura, no un threshold de rendimiento.

## Dashboard

DASHBOARD-02 está cerrado y validado visualmente. La vista de jugador tiene aspecto profesional y separa score, motor experto y datos técnicos.

Corrección ya aplicada: porteros muestran que el camino GK está separado; no se les atribuye erróneamente el motivo de suplente sin rol.

DASHBOARD-03 Team Mode queda temporalmente pausado hasta validar PERF-15. No tiene sentido seguir construyendo UX sobre una cobertura de score defectuosa.

## Guardrails vigentes

- no copiar fórmulas propietarias Sofascore/FotMob;
- no convertir missing en 0 salvo semántica validada o identidad éxito<=intentos con intentos=0;
- no threshold bueno/malo sin validación;
- no etiqueta automática de calidad;
- no recomendación táctica derivada directamente del score;
- no ranking universal entre posiciones;
- suplentes sin rol táctico observable no se imputan;
- porteros mantienen camino separado;
- el LLM no calcula ni altera el score;
- el dashboard consume resultados materializados;
- score y expert system son capas diferentes;
- los fallbacks quedan auditables y no ocultan su procedencia.

## Siguiente paso exacto

```powershell
cd C:\Users\sergi\Desktop\football-performance-system
git pull

$env:FPS_DB_PATH = "D:\Data\Sergi\Desktop\football-performance-system\data\football_performance.duckdb"

python dsai\performance_position_score_experiment_v3.py --db $env:FPS_DB_PATH
python analytics\build_performance_score.py --db $env:FPS_DB_PATH
python app\validate_performance_score.py
```

Revisar especialmente:

```text
eligible_before
eligible_after
recovered
coverage_observable_roles
high_participation_without_score
fallback_attacking_threat
fallback_creation_progression
fallback_defensive_contribution
```

Si el validador da `PASS`, cerrar PERF-15, congelar `performance_score_v0.2-experimental` y reanudar inmediatamente DASHBOARD-03.
