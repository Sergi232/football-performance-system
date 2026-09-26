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
PERF-16 MATCH RATING                CERRADO / VALIDADO — ISSUE #91
SCORE-INTEGRATION-01                v0.2 VALIDADA / CONTRACT PASS
DASHBOARD-02 PLAYER VIEW            CERRADO — ISSUE #88 / VALIDADO VISUALMENTE
DASHBOARD-03 TEAM MODE              ACTIVO — ISSUE #89 / MATCH RATING INTEGRADO
MATCH MODE                          CONTRACT PASS / OPERATIVO DESDE PARTIDO 1
LLM MATCH RATING CONTEXT            CONTRACT PASS
DASHBOARD-04 PHYSICAL/GPS           CERRADO / VALIDADO — ISSUE #92
ALERTS-01 ATTENTION CENTRE          CERRADO / VALIDADO — ISSUE #93
FINAL DASHBOARD HOME                IMPLEMENTADA / PENDIENTE CHECK VISUAL
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

## Arquitectura de rendimiento vigente

```text
MATCH RATING
= nota inmediata de un jugador en un partido
= existe desde el partido 1
= no requiere historial previo

PERFORMANCE INDEX
= capa histórica/posicional complementaria
= evolución, forma, consistencia, tendencia y comparación por rol
= NO es la nota del partido
```

La interfaz muestra Match Rating como resultado operativo principal de un partido.

## PERF-15 — Performance Index vigente

Versión:

```text
performance_score_v0.2-experimental
source experiment: performance_position_score_experiment_0.3.0
```

Resultado validado:

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

PERF-15 corrige dimensiones vacías sin inventar acciones. Los fallbacks quedan auditables.

## PERF-16 — Match Rating cerrado

Issue #91 cerrado.

Versión:

```text
match_rating_v0.1-experimental
```

Contrato validado localmente:

```text
played_rows=590
rated_rows=590
rating_coverage=1.0000
matches=38
goalkeeper_rows=38
generic_role_rows=172
neutral_insufficient_evidence_rows=7
first_match_rated_rows=16
```

Principios:

- cada `player_match` con minutos recibe rating;
- funciona desde el primer partido;
- rol observable -> contexto posicional;
- `Substitute` sin rol táctico -> contexto genérico explícito, sin imputar posición;
- porteros -> camino GK separado;
- evidencia insuficiente -> midpoint neutral explícito + confidence reducida;
- ningún LLM calcula ni altera el rating.

Escala de presentación experimental:

```text
rating_10 = 4.0 + 0.06 * rating_100
0 -> 4.0
50 -> 7.0
100 -> 10.0
```

No copia fórmulas propietarias.

## Player Mode

Vista `Jugador` validada visualmente.

KPIs principales:

```text
Match Rating /10
Confianza
Perfil del partido
Performance Index complementario
```

Incluye dimensiones del partido, evolución, datos técnicos, motor experto, historial y PDF.

## Match Mode

Archivo principal:

```text
app/pages/4_Partit.py
```

Incluye ratings, confidence, rol/perfil, minutos, dimensiones, detalle por jugador, observaciones deterministas y PDF.

Gate validado:

```text
MATCH MODE CONTRACT: PASS
first_match_rated_players=16
post_match_observation_players=16
pdf_bytes=5500
```

Conclusión: el flujo postpartido es operativo desde el primer partido.

## Team Mode

Issue #89 activo.

`Equip` usa Match Rating como capa operativa principal:

- rating mediana del último partido;
- jugadores valorados;
- confidence mediana;
- último Match Rating por jugador;
- plantilla con rating actual y media últimos 5;
- evolución temporal de la mediana por partido;
- delta descriptivo 5 vs 5;
- Performance Index en pestaña separada;
- historial y PDF.

## Asistente IA

Arquitectura obligatoria mantenida:

```text
DATA -> ANALYTICS -> DECISION ENGINE -> LLM -> COACH
```

Contextos disponibles:

### Team
- Match Rating snapshot;
- historial de Match Rating;
- datos de equipo.

### Player
- último Match Rating;
- historial de ratings;
- Performance Index;
- features;
- motor experto.

### Match
- ratings materializados;
- lineup;
- observaciones postpartido deterministas.

Gate validado:

```text
LLM MATCH RATING CONTEXT: PASS
team_snapshot_players=28
player_latest_rating=8.285714285714285
first_match_rating_rows=16
```

El asistente explica analytics materializados; no recalcula ratings.

## GPS / físico

GPS es opcional. Capa validada:

```text
player_match_gps_summary
summary_version = gps_physical_summary_v0.1-descriptive
```

Gate local validado:

```text
GPS PHYSICAL SUMMARY CONTRACT: PASS
synthetic_total_distance_m=11.0
synthetic_peak_speed_m_s=6.0
synthetic_max_acceleration_m_s2=1.0
synthetic_min_acceleration_m_s2=-2.0
real_gps_observations=0
real_summary_rows=0
```

Estado actual: no hay GPS real importado y esto es un estado válido del producto.

No se han creado HSR, zonas de sprint, workload, fatiga, readiness ni physical score.

## ALERTS-01 — cerrado / validado

Versión:

```text
attention_flags_v0.1-auditable
```

Gate local:

```text
ATTENTION FLAGS CONTRACT: PASS
rows=179
ROLE_CONTEXT_UNAVAILABLE=172
INSUFFICIENT_RATING_EVIDENCE=7
GPS_QUALITY_FLAGS_PRESENT=0
```

Los flags son de atención/traçabilidad, no diagnósticos de rendimiento.

## Home principal profesional

`app/streamlit_app.py` es ahora la home operativa del staff.

Incluye selector de equipo, hero TEAM MODE, KPIs de contexto, mediana descriptiva del Match Rating del último partido, último partido con ratings, Centre d'Atenció auditable, estado GPS, evolución de la mediana y accesos rápidos a todas las vistas del producto.

La home no recalcula métricas ni crea recomendaciones.

## Guardrails vigentes

- no copiar fórmulas propietarias Sofascore/FotMob;
- no convertir missing en 0 salvo semántica validada;
- no threshold bueno/malo sin validación;
- no recomendación táctica derivada directamente de ratings;
- Match Rating y Performance Index son capas distintas;
- suplentes sin rol táctico no reciben rol inventado;
- porteros mantienen camino separado;
- midpoint por evidencia insuficiente queda identificado y con confidence reducida;
- LLM no calcula ni altera ratings;
- dashboard/PDF consumen resultados materializados;
- GPS es opcional;
- no introducir HSR/sprint/load/fatigue sin validación;
- Attention Centre solo expone estados auditables existentes.

## Siguiente paso exacto

Reiniciar la app y comprobar visualmente la nueva home:

```powershell
cd C:\Users\sergi\Desktop\football-performance-system
git pull
$env:FPS_DB_PATH = "D:\Data\Sergi\Desktop\football-performance-system\data\football_performance.duckdb"
streamlit run app\streamlit_app.py
```

Después del check visual: cerrar DASHBOARD-03 #89 si Team Mode se considera final para MVP, revisar PDF finales, pulir navegación responsive, preparar publicación Streamlit/demo final y actualizar README con el flujo final.
