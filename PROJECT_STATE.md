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

## Arquitectura de producto

```text
COLLECTOR + GPS opcional
→ DATABASE
→ FEATURE ENGINE
→ ANALYTICS
→ EXPERT SYSTEM / ML
→ WEB DASHBOARD
→ ASSISTANT IA
→ PDF / informes
```

La web es el producto principal. PDF/PPT son salidas estáticas complementarias.

## Rendimiento

```text
MATCH RATING
= nota inmediata jugador-partido
= disponible desde partido 1
= no requiere historial

PERFORMANCE INDEX
= capa histórica/posicional
= evolución, forma, consistencia y comparación por rol
= no es la nota del partido
```

Versiones vigentes:

```text
match_rating_v0.1-experimental
performance_score_v0.2-experimental
gps_physical_summary_v0.1-descriptive
attention_flags_v0.1-auditable
```

## Gates validados

```text
MATCH RATING CONTRACT: PASS
590/590 apariciones con minutos valoradas
38 partidos
16 ratings ya en el primer partido

MATCH MODE CONTRACT: PASS
first_match_rated_players=16
post_match_observation_players=16
pdf_bytes=5500

LLM MATCH RATING CONTEXT: PASS
team_snapshot_players=28
first_match_rating_rows=16

GPS PHYSICAL SUMMARY CONTRACT: PASS
real_gps_observations=0
real_summary_rows=0
GPS opcional

ATTENTION FLAGS CONTRACT: PASS
ROLE_CONTEXT_UNAVAILABLE=172
INSUFFICIENT_RATING_EVIDENCE=7
GPS_QUALITY_FLAGS_PRESENT=0
```

## Producto actual

### Home
`app/streamlit_app.py` es la home operativa del staff con equipo, último partido, ratings, evolución, Centre d'Atenció, estado GPS y accesos rápidos.

### Jugador
Match Rating, confidence, perfil, Performance Index, dimensiones, evolución, técnico, motor experto, partidos y PDF.

### Equip
Match Rating operativo, plantilla, evolución, Performance Index complementario, historial y PDF.

### Partit
Ratings, confidence, roles, minutos, dimensiones, observaciones deterministas y PDF desde partido 1.

### Físic / GPS
Capa descriptiva opcional sobre GPS canónico. Sin HSR/sprint/load/fatigue/readiness no validados.

### Alertes
Solo estados auditables de contexto/calidad. Sin diagnóstico de rendimiento, lesión o fatiga.

### Assistent IA
Consume analytics estructurados. No calcula ni altera ratings ni puede saltarse guardrails.

## Guardrails

- no copiar fórmulas propietarias;
- no convertir missing en zero sin semántica validada;
- no thresholds bueno/malo sin validación;
- no recomendación táctica derivada directamente del rating;
- suplentes sin rol táctico no reciben rol inventado;
- porteros usan camino separado;
- LLM downstream del motor;
- GPS opcional;
- no HSR/sprint/load/fatigue/readiness sin definición validada.

## Siguiente paso exacto

```powershell
cd C:\Users\sergi\Desktop\football-performance-system
git pull
$env:FPS_DB_PATH = "D:\Data\Sergi\Desktop\football-performance-system\data\football_performance.duckdb"
streamlit run app\streamlit_app.py
```

Check visual de la nueva home. Después: cerrar DASHBOARD-03 #89, revisar PDFs finales, pulir navegación/labels, preparar despliegue Streamlit y actualizar README final.
