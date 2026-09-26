# PROJECT_STATE

Última actualización: 26/09/2026

Memoria técnica operativa del proyecto. Si contradice un chat antiguo, prevalece este archivo.

## Estado actual

```text
DATA-01/02/03/04                    CERRADO / VALIDADO
COLLECTOR-01 MVP                    CERRADO FUNCIONALMENTE / UX+ES+MÓVIL PENDIENTE
GPS-01                              CERRADO / VALIDADO ESTRUCTURALMENTE
FEATURE-01/02/03                    CERRADO / VALIDADO
EXPERT-01..07 N1000-N13000          BASELINE CERRADO / VALIDADO
LLM-01/02                           PROTOTYPE v0.1 / CONTRATOS PASS
REPORTS-01                          PROTOTYPE v0.1 / CONTRATO PASS
REPORTS-02 PROFESSIONAL PDF         ACTIVO — ISSUE #94 / GATE VISUAL PENDIENTE
DASHBOARD-01                        PROTOTYPE v0.1 / CONTRACT PASS
ARCHITECTURE-01                     CERRADO — ISSUE #25
ANALYTICS-01                        CERRADO / VALIDADO — ISSUE #26
DECISION POLICY / N13000            GATE APROBADO — ISSUE #27 CERRADO
DSAI-01A..11                        CERRADO / RESULTADOS DOCUMENTADOS
PERF-01..14                         CERRADO / BASELINE v0.1 DOCUMENTADA
PERF-15 COVERAGE REPAIR             CERRADO / VALIDADO — ISSUE #90
PERF-16 MATCH RATING                CERRADO / VALIDADO — ISSUE #91
PERF-18 MATCH RATING DATA SCIENCE   CERRADO / VALIDADO — V5 ACTIVA
SCORE-INTEGRATION-01                v0.2 VALIDADA / CONTRACT PASS
DASHBOARD-02 PLAYER VIEW            CERRADO — ISSUE #88 / VALIDADO VISUALMENTE
DASHBOARD-03 TEAM MODE              ACTIVO — ISSUE #89 / MATCH RATING V5 INTEGRADO
MATCH MODE                          CONTRACT PASS / OPERATIVO DESDE PARTIDO 1
LLM MATCH RATING CONTEXT            CONTRACT PASS / V5
DASHBOARD-04 PHYSICAL/GPS           CERRADO / VALIDADO — ISSUE #92
ALERTS-01 ATTENTION CENTRE          CERRADO / VALIDADO — v0.3
FINAL DASHBOARD HOME                IMPLEMENTADA / PENDIENTE CHECK VISUAL
UI COMPATIBILITY                    GATE ESTÁTICO AÑADIDO / LIMPIEZA DEPRECATIONS EN CURSO
FINAL-01                            DESBLOQUEADO
PUBLIC DEPLOYMENT                   NO HACER — decisión explícita actual
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
= activo en V5

PERFORMANCE INDEX
= capa histórica/posicional
= evolución, forma, consistencia y comparación por rol
= no es la nota del partido
```

Versiones vigentes:

```text
match_rating_v0.5-candidate              ACTIVA
performance_score_v0.2-experimental
gps_physical_summary_v0.1-descriptive
attention_flags_v0.3-auditable
report_schema_version=0.3.0
```

## PERF-18 — Match Rating V5

Objetivo: sustituir el rating manual/heurístico visible por un sistema multidimensional, posicional, auditable y validado con datos profesionales, manteniendo variables compatibles con el Collector amateur.

Arquitectura final:

```text
OUTFIELD con rol fiable
→ referencia profesional pre-temporada local
→ dimensiones estructurales por posición
→ anchors decisivos explícitos
→ V4.1 outfield

GOALKEEPER
→ modelo separado
→ shot-stopping con save rate shrinkage
→ distribución específica de portero
→ pesos finales 90% / 10%

ROL NO DISPONIBLE
→ fallback histórico V2 explícito
→ nunca se inventa una posición

TODO
→ Match Rating V5 unificado
```

### Benchmark externo

- Opta Player Rating: solo inspiración metodológica pública; fórmula propietaria no reproducida.
- Opta Points: benchmark transparente externo; fórmula pública reconstruida para validación, no tratada como ground truth.
- El Collector reproduce el benchmark Opta Points con fidelidad muy alta sobre PannaData: Pearson ~0.9984, Spearman ~0.9980, MAE ~0.0134.

### Outfield

- rating posicional por CB / FB / DM / CM / AM / W / ST;
- normalización y referencia profesional estrictamente anterior al primer partido local;
- anchors públicos principales: gol +1.00, asistencia +0.60, penalti recibido +0.40, amarilla -0.20, roja -0.50;
- hipótesis FPS explícita: penalti concedido -0.40;
- ajuste contextual secundario: -0.10 por gol encajado mientras el jugador consta en campo;
- construct gate final: PASS;
- V4.1 on-pitch contract: PASS.

El contexto on-pitch se conserva como ajuste pequeño y auditable, no como causalidad individual. La precisión temporal es desigual: 156 filas exactas y 434 con fallback de minuto/duración, de las cuales 171 provienen de conflictos resueltos.

### Goalkeeper

Modelo totalmente separado de los jugadores de campo.

Gate final:

```text
selected_weights = 90% shot-stopping / 10% distribution
TEST MAE vs Opta Points = 0.3536
TEST Spearman = 0.9221
monotonicity_gate = PASS
local_weight_sensitivity_gate = PASS
GK_FINAL_GATE = PASS
```

La selección de pesos se hizo en VALID sobre una rejilla predefinida 50/50..90/10; TEST quedó intacto. No se dejó que PCA decidiera el mérito final.

### V5 unificada

```text
590/590 apariciones con minutos
38/38 partidos
380 OUTFIELD_PERF18_ANCHORED
38 GOALKEEPER_PERF18_SHOT90_DIST10
172 OUTFIELD_ROLE_UNAVAILABLE_FALLBACK_V2
nulls=0
duplicates=0
out_of_range=0
FINAL_CANDIDATE_CONTRACT=PASS
```

Distribución V5:

```text
mean=6.388
median=6.257
q10=5.757
q90=7.216
min=3.206
max=9.554
```

Por resultado:

```text
DRAW median=6.263
LOSS median=6.136
WIN  median=6.332
```

Caso que motivó la revisión: derrota 0-3 del 20/12/2025 queda en media 6.143 y mediana 5.996; el antiguo comportamiento ~7.4 queda corregido sin imponer un castigo global por resultado.

## Gates validados tras activación V5

```text
MATCH RATING CONTRACT: PASS
match_rating_version=match_rating_v0.5-candidate
590/590 apariciones valoradas
38 partidos
38 porteros
172 role-unavailable fallback explícitos
0 neutral-insufficient rows
16 ratings en el primer partido

ATTENTION FLAGS CONTRACT: PASS
attention_version=attention_flags_v0.3-auditable
ROLE_CONTEXT_UNAVAILABLE=172
INSUFFICIENT_RATING_EVIDENCE=0
GPS_QUALITY_FLAGS_PRESENT=0

MATCH MODE CONTRACT: PASS
first_match_rated_players=16
post_match_observation_players=16
PDF generado

DASHBOARD-01 DATA CONTRACT: PASS
team=Deportivo Alavés
matches=38
players=36
FEATURE-01 metrics=28
expert engine=expert_0.7.0
N13000 recommendation gate safety=PASS

LLM MATCH RATING CONTEXT: PASS
team_snapshot_players=28
first_match_rating_rows=16
LLM explica analytics materializados y no recalcula el rating

REPORTS-01 PDF CONTRACT: PASS
team/player/match payloads válidos
recommendation/report guardrails=PASS
PDFs generados correctamente
```

## Producto actual

### Home
`app/streamlit_app.py` es la home operativa del staff con equipo, último partido, ratings V5, evolución, Centre d'Atenció, estado GPS y accesos rápidos.

### Jugador
Match Rating V5, confidence, perfil, Performance Index, dimensiones, evolución, técnico, motor experto, partidos y PDF.

### Equipo
Match Rating V5 operativo, plantilla, evolución, Performance Index complementario, historial y PDF.

### Partido
Ratings V5, confidence, roles, minutos, dimensiones, observaciones deterministas y PDF desde partido 1.

### Físico / GPS
Capa descriptiva opcional sobre GPS canónico. Sin HSR/sprint/load/fatigue/readiness no validados. La base local aún no contiene observaciones GPS reales; falta ejemplo local claramente etiquetado si se quiere demostrar km/velocidad en UI.

### Alertas
Solo estados auditables de contexto/calidad. Sin diagnóstico de rendimiento, lesión o fatiga.

### Asistente IA
Consume analytics estructurados. No calcula ni altera ratings ni puede saltarse guardrails.

## REPORTS-02 — professional PDFs

Issue #94.

Estado técnico:

- `reports/data_builder.py` schema 0.3.0;
- payload de equipo incorpora snapshot/historial de Match Rating V5;
- payload de jugador incorpora Performance Index actual e historial;
- payload de partido incorpora observaciones deterministas postpartido;
- `reports/pdf_engine.py` mantiene identidad visual, KPIs, tablas y jerarquía de secciones;
- Match Rating destacado en jugador/partido;
- ningún cálculo crítico se mueve a la capa PDF;
- `python reports\validate_reports.py` = PASS.

Pendiente para cerrar REPORTS-02:

1. inspección visual de los tres PDFs generados;
2. comprobar clipping/overlap/legibilidad;
3. corregir diseño solo si la revisión visual detecta problemas.

## Collector

Variables funcionales cerradas. Pendiente de producto:

1. simplificar/mejorar UX;
2. traducción completa al castellano;
3. diseño mobile-first/responsive;
4. mantener la misma semántica de variables, sin ampliar el scope sin justificación.

## UI compatibility

Gate disponible:

```text
app/validate_ui_compatibility.py
```

Detecta `use_container_width` residual y el icono inválido conocido. Falta completar revisión visual de la home/páginas y deprecations residuales.

## Guardrails

- no copiar fórmulas propietarias;
- no convertir missing en zero sin semántica validada;
- no thresholds bueno/malo sin validación;
- no recomendación táctica derivada directamente del rating;
- suplentes sin rol táctico no reciben rol inventado;
- porteros usan camino separado;
- LLM downstream del motor;
- GPS opcional;
- no HSR/sprint/load/fatigue/readiness sin definición validada;
- PDF y dashboard consumen analytics materializados, no recalculan resultados críticos;
- no desplegar ni publicar públicamente mientras se mantenga la instrucción actual del usuario.

## Siguiente paso exacto

PERF-18 queda cerrado. El siguiente bloque es producto/UX, no seguir ajustando el rating sin nueva evidencia.

Orden inmediato:

1. ejecutar `python app\validate_ui_compatibility.py`;
2. revisar visualmente Home / Team / Player / Match con V5 activa;
3. revisar visualmente los tres PDFs ya generados y cerrar REPORTS-02 si no hay clipping/overlap;
4. mejorar Collector: castellano + móvil + simplificación UX;
5. mejorar diseño del dashboard;
6. añadir un ejemplo GPS local claramente etiquetado para demostrar km/velocidad, sin mezclarlo con datos reales;
7. continuar mejora del Performance Index histórico y perfiles;
8. preparar documentación final del TFM, sin despliegue público.
