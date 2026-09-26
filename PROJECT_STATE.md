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
PERF-15 COVERAGE REPAIR             CERRADO / VALIDADO — ISSUE #90
PERF-16 MATCH RATING                ACTIVO — ISSUE #91 / PENDIENTE GATE LOCAL
SCORE-INTEGRATION-01                v0.2 VALIDADA / CONTRACT PASS
DASHBOARD-02 PLAYER VIEW            CERRADO — ISSUE #88 / VALIDADO VISUALMENTE
DASHBOARD-03 TEAM MODE              ACTIVO — ISSUE #89
MATCH MODE                          IMPLEMENTADO / PENDIENTE VALIDACIÓN LOCAL
FINAL-01                            DESBLOQUEADO
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

## Distinción de producto aprobada

A partir de PERF-16 se separan dos conceptos:

```text
MATCH RATING
= nota inmediata de un jugador en un partido
= debe existir desde el partido 1
= no requiere historial previo

PERFORMANCE INDEX
= capa histórica/posicional
= sirve para evolución, forma, consistencia, tendencia y comparación por rol
= no es la nota del partido
```

La interfaz debe mostrar primero el Match Rating cuando se habla de un partido o del último rendimiento.

## PERF-15 — cerrado / validado

Baseline histórica vigente:

```text
performance_score_v0.2-experimental
source experiment: performance_position_score_experiment_0.3.0
```

Resultado local:

```text
observable_role_rows=380
eligible_before=304
eligible_after=379
recovered=75
coverage_observable_roles=0.9974
source_role_unavailable_rows=172
high_participation_without_score=0
fallback_creation_progression=128
fallback_defensive_contribution=205
```

Contrato dashboard PASS. PERF-15 corrige el problema de dimensiones vacías sin inventar acciones.

## PERF-16 — Match Rating

Issue #91.

Versión candidata:

```text
match_rating_v0.1-experimental
```

Archivos:

```text
analytics/build_match_rating.py
app/match_rating_access.py
app/validate_match_rating.py
app/pages/2_Jugador.py
app/pages/4_Partit.py
reports/data_builder.py
reports/pdf_engine.py
```

### Contrato funcional

Cada `player_match` con `minutes_played > 0` debe producir una fila de Match Rating.

El rating debe estar disponible desde el primer partido; la evolución histórica es una capa posterior.

### Jugadores de campo

```text
PERF-15 dimensions disponibles
-> pesos posicionales si rol observable
-> pesos iguales si la fuente solo dice Substitute
-> rating_100
-> rating_10
```

Un suplente sin rol táctico fiable NO recibe un rol inventado. Para el informe del partido puede recibir rating con `GENERIC_ROLE_UNAVAILABLE`, explícitamente separado de evidencia táctica.

Si una aparición no dispone de ninguna dimensión utilizable:

```text
rating_100 = 50 midpoint
confidence = 0
status = NEUTRAL_INSUFFICIENT_OUTFIELD_EVIDENCE
```

Esto es una presentación neutral para garantizar continuidad operativa, no una afirmación de rendimiento. No se inventan acciones.

### Porter

Camino separado:

- si `saves` y `goals_conceded` están observados y hubo tiros a puerta enfrentados, señal = `save_rate`;
- si no hubo oportunidades o la evidencia está incompleta, midpoint explícito con confidence reducida;
- nunca se mezcla el porter con las dimensiones de jugadores de campo.

### Escala

Interna:

```text
match_rating_100: 0-100
```

Presentación:

```text
match_rating_10 = 4.0 + 0.06 * match_rating_100
```

Por tanto:

```text
0   -> 4.0
50  -> 7.0
100 -> 10.0
```

La transformación es lineal y solo visual; preserva completamente el orden. No copia ninguna fórmula propietaria.

### Dashboard

`Jugador` muestra ahora como KPI principal:

```text
Match Rating /10
Confianza
Perfil del partit
Performance Index complementari
```

La evolución principal es Match Rating. El Performance Index queda como capa histórica secundaria.

Nueva página:

```text
Partit
```

Permite seleccionar un partido y consultar:

- jugadores utilizados;
- rating /10;
- confianza;
- rol/perfil;
- minutos/titularidad;
- dimensiones del partido;
- detalle por jugador;
- PDF del partido.

### Informes

`reports/data_builder.py` y `reports/pdf_engine.py` incorporan Match Rating en:

- informe de jugador;
- informe de partido.

Esto permite generar un informe presentable desde el primer partido siempre que el pipeline del partido haya sido procesado.

## Guardrails vigentes

- no copiar fórmulas propietarias Sofascore/FotMob;
- no convertir missing en 0 salvo semántica validada;
- no threshold bueno/malo sin validación;
- no recomendación táctica derivada directamente del rating;
- Match Rating y Performance Index son capas distintas;
- suplentes sin rol táctico no reciben rol inventado;
- porteros mantienen camino separado;
- cualquier midpoint por evidencia insuficiente debe quedar identificado y con confidence reducida;
- el LLM no calcula ni altera ratings;
- dashboard/PDF consumen resultados materializados.

## Gate PERF-16 pendiente

Ejecutar:

```powershell
cd C:\Users\sergi\Desktop\football-performance-system
git pull
$env:FPS_DB_PATH = "D:\Data\Sergi\Desktop\football-performance-system\data\football_performance.duckdb"
python analytics\build_match_rating.py --db $env:FPS_DB_PATH
python app\validate_match_rating.py
streamlit run app\streamlit_app.py
```

El gate debe confirmar:

1. una fila de rating por cada jugador-partido con minutos;
2. 100% de ratings no nulos;
3. ratings presentes ya en el primer partido;
4. porteros incluidos;
5. número de casos genéricos por rol no observable;
6. número de ratings neutrales por evidencia insuficiente.

Después del PASS: cerrar PERF-16 y continuar Team Mode + insights automáticos del partido + integración LLM.
