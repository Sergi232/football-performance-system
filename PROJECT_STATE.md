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
ALERTS-01 ATTENTION CENTRE          ACTIVO — ISSUE #93
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

## PERF-15 — Performance Index

Versión vigente:

```text
performance_score_v0.2-experimental
source experiment: performance_position_score_experiment_0.3.0
```

Validación:

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

## PERF-16 — Match Rating cerrado

Versión:

```text
match_rating_v0.1-experimental
```

Gate validado:

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
- porteros usan camino separado;
- suplentes sin rol táctico fiable no reciben posición inventada;
- evidencia insuficiente queda marcada y con confidence reducida;
- ningún LLM calcula o altera ratings.

## Dashboard actual

### Jugador

- Match Rating /10 como resultado principal del último partido;
- confidence;
- perfil del partido;
- Performance Index complementario;
- dimensiones;
- evolución temporal;
- técnico;
- motor experto;
- historial;
- PDF.

### Partit

- ratings de todos los participantes;
- confidence;
- rol/perfil;
- minutos y titularidad;
- dimensiones;
- observaciones postpartido deterministas;
- PDF.

Gate:

```text
MATCH MODE CONTRACT: PASS
first_match_rated_players=16
post_match_observation_players=16
pdf_bytes=5500
```

### Equip

- Match Rating como capa operativa principal;
- snapshot de plantilla;
- medias recientes;
- evolución;
- delta descriptivo 5 vs 5;
- Performance Index separado;
- historial y PDF.

### Assistent IA

Arquitectura mantenida:

```text
DATA -> ANALYTICS -> DECISION ENGINE -> LLM -> COACH
```

Gate:

```text
LLM MATCH RATING CONTEXT: PASS
team_snapshot_players=28
player_latest_rating=8.285714285714285
first_match_rating_rows=16
```

El asistente explica resultados materializados; no recalcula ratings.

## DASHBOARD-04 — Physical/GPS cerrado

Issue #92 cerrado.

Versión:

```text
gps_physical_summary_v0.1-descriptive
```

Capa materializada:

```text
player_match_gps_summary
```

Agregados descriptivos aprobados:

```text
total_distance_m
peak_speed_m_s
max_acceleration_m_s2
min_acceleration_m_s2
observation_duration_s
sample_count
coverage % por canal
```

Gate local validado:

```text
GPS PHYSICAL SUMMARY MATERIALIZATION: COMPLETE
summary_rows=0
latest_rows=0
matches=0
players=0
imports=0

GPS PHYSICAL SUMMARY CONTRACT: PASS
synthetic_total_distance_m=11.0
synthetic_peak_speed_m_s=6.0
synthetic_max_acceleration_m_s2=1.0
synthetic_min_acceleration_m_s2=-2.0
real_gps_observations=0
real_summary_rows=0
```

Conclusión: GPS sigue siendo opcional y la capa física funciona correctamente aunque no exista un archivo GPS real importado.

No se han definido HSR, sprint zones, workload, fatigue, readiness ni physical score.

## ALERTS-01 — Attention Centre activo

Issue #93.

Versión candidata:

```text
attention_flags_v0.1-auditable
```

Archivos:

```text
analytics/build_attention_flags.py
app/attention_access.py
app/pages/7_Alertes.py
app/validate_attention_flags.py
docs/ATTENTION_FLAGS_CONTRACT.md
```

La palabra alerta en esta fase significa elemento que requiere revisión por limitación explícita de datos, contexto o evidencia.

Códigos aprobados inicialmente:

```text
ROLE_CONTEXT_UNAVAILABLE
INSUFFICIENT_RATING_EVIDENCE
GPS_QUALITY_FLAGS_PRESENT
```

No son alertas de rendimiento.

No se permite todavía:

```text
fatigue
readiness
injury risk
bad/good performance alert
HSR/sprint thresholds
tactical recommendation
```

## Guardrails vigentes

- no copiar fórmulas propietarias Sofascore/FotMob;
- no convertir missing en 0 salvo semántica validada;
- no threshold bueno/malo sin validación;
- no recomendación táctica derivada directamente de ratings;
- Match Rating y Performance Index son capas distintas;
- suplentes sin rol táctico no reciben rol inventado;
- porteros mantienen camino separado;
- LLM no calcula ni altera ratings;
- dashboard/PDF consumen resultados materializados;
- GPS es opcional;
- no introducir HSR/sprint/load/fatigue/readiness sin validación;
- las alertas actuales solo reflejan estados auditables ya existentes en las capas fuente.

## Siguiente paso exacto

Validar ALERTS-01:

```powershell
cd C:\Users\sergi\Desktop\football-performance-system
git pull
$env:FPS_DB_PATH = "D:\Data\Sergi\Desktop\football-performance-system\data\football_performance.duckdb"

python analytics\build_attention_flags.py --db $env:FPS_DB_PATH
python app\validate_attention_flags.py
streamlit run app\streamlit_app.py
```

Comprobar `Alertes`.

Después del PASS:

1. cerrar ALERTS-01 #93;
2. integrar un resumen de attention flags en Team Mode;
3. pulir navegación global y home;
4. integrar GPS/attention context en PDF y LLM sin inventar interpretaciones;
5. preparar publicación final y README final.
