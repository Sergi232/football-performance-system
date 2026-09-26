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
PERF-16 MATCH RATING                BACKEND PASS — ISSUE #91 / UI+PDF FINAL GATE PENDIENTE
SCORE-INTEGRATION-01                v0.2 VALIDADA / CONTRACT PASS
DASHBOARD-02 PLAYER VIEW            CERRADO — ISSUE #88 / VALIDADO VISUALMENTE
DASHBOARD-03 TEAM MODE              ACTIVO — ISSUE #89 / MATCH RATING INTEGRADO
MATCH MODE                          IMPLEMENTADO / INSIGHTS + PDF / GATE LOCAL PENDIENTE
LLM MATCH RATING CONTEXT            IMPLEMENTADO / GATE LOCAL PENDIENTE
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

## PERF-15 — cerrado / validado

Baseline histórica vigente:

```text
performance_score_v0.2-experimental
source experiment: performance_position_score_experiment_0.3.0
```

Resultado local validado:

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

PERF-15 corrige dimensiones vacías sin inventar acciones.

## PERF-16 — Match Rating

Issue #91.

Versión:

```text
match_rating_v0.1-experimental
```

Materialización:

```text
analytics/build_match_rating.py
player_match_rating
```

Contrato funcional:

- una fila por cada `player_match` con `minutes_played > 0`;
- rating disponible desde el primer partido;
- no depende del historial para calcular la nota del partido;
- jugadores de campo con rol observable usan contexto posicional;
- suplentes sin rol táctico fiable usan `GENERIC_ROLE_UNAVAILABLE`, sin inventar posición;
- porteros usan camino GK separado;
- evidencia insuficiente conserva rating neutral explícito + confidence baja/0;
- ningún LLM calcula ni altera el rating.

Escala interna:

```text
match_rating_100 = 0..100
```

Presentación:

```text
match_rating_10 = 4.0 + 0.06 * match_rating_100
0 -> 4.0
50 -> 7.0
100 -> 10.0
```

La transformación /10 es experimental y solo de presentación; no copia una fórmula propietaria.

### Gate local ya validado

```text
PERF-16 MATCH RATING MATERIALIZATION: COMPLETE
played_rows=590
rated_rows=590
rating_coverage=1.0
outfield_rows=552
goalkeeper_rows=38
generic_role_unavailable_rows=172
neutral_insufficient_evidence_rows=7
first_match_capable=True
history_required_for_match_rating=False

MATCH RATING CONTRACT: PASS
played_rows=590
rated_rows=590
rating_coverage=1.0000
matches=38
goalkeeper_rows=38
generic_role_rows=172
neutral_insufficient_evidence_rows=7
first_match_rated_rows=16
```

Conclusión: el backend cumple el requisito de producto de generar ratings desde el partido 1.

## Dashboard — Player Mode

Vista `Jugador` validada visualmente.

KPIs principales actuales:

```text
Match Rating /10
Confianza
Perfil del partido
Performance Index complementario
```

Incluye además:

- dimensiones del último partido;
- evolución del Match Rating;
- datos técnicos;
- motor experto;
- historial de partidos;
- PDF.

## Match Mode

Archivo:

```text
app/pages/4_Partit.py
```

Incluye:

- selección de partido;
- resultado y formación;
- jugadores utilizados;
- Match Rating /10;
- confidence;
- rol/perfil;
- minutos y titularidad;
- dimensiones player-match;
- detalle por jugador;
- observaciones postpartido deterministas;
- PDF del partido.

Observaciones actuales, siempre derivadas de datos observados:

- goleadores;
- asistentes;
- máximo de remates observados;
- máximo de pases completados;
- máximo de entradas ganadas;
- máximo de intercepciones;
- número de ratings genéricos por rol no observable;
- casos con confidence < 50%.

No son recomendaciones tácticas ni conclusiones de un LLM.

Validador nuevo:

```text
app/validate_match_mode.py
```

Debe confirmar que el primer partido tiene ratings, observaciones y PDF generable.

## Team Mode

Issue #89.

`Equip` ahora usa Match Rating como capa operativa principal:

- rating mediana del último partido;
- jugadores valorados;
- confidence mediana;
- último Match Rating por jugador;
- plantilla con rating actual y media últimos 5;
- evolución temporal de la mediana de rating por partido;
- delta descriptivo 5 vs 5;
- Performance Index en pestaña separada;
- historial de partidos;
- PDF.

El Performance Index ya no se presenta como nota del partido.

## Informes PDF

`reports/data_builder.py` y `reports/pdf_engine.py` incorporan Match Rating en:

- informe de jugador;
- informe de partido.

El objetivo operativo es que tras procesar el partido 1 ya exista un informe postpartido presentable.

## Asistente IA

Arquitectura obligatoria mantenida:

```text
DATA -> ANALYTICS -> DECISION ENGINE -> LLM -> COACH
```

Archivos actualizados:

```text
llm/context_builder.py
llm/assistant_service.py
app/pages/5_Assistent_IA.py
llm/validate_match_rating_context.py
```

El context builder expone ahora:

### Team
- Match Rating snapshot;
- historial de Match Rating;
- datos de equipo.

### Player
- último Match Rating;
- historial de ratings;
- Performance Index complementario;
- features;
- motor experto.

### Match
- ratings materializados;
- lineup;
- observaciones postpartido deterministas.

El asistente puede explicar una nota ya calculada, pero no recalcularla, alterar pesos ni crear una recomendación táctica.

Nueva página:

```text
Assistent IA
```

Funciona en modo determinista sin API key. Si existe proveedor LLM configurado, se mantiene downstream del contexto estructurado y los guardrails.

## Guardrails vigentes

- no copiar fórmulas propietarias Sofascore/FotMob;
- no convertir missing en 0 salvo semántica validada;
- no threshold bueno/malo sin validación;
- no recomendación táctica derivada directamente del rating;
- Match Rating y Performance Index son capas distintas;
- suplentes sin rol táctico no reciben rol inventado;
- porteros mantienen camino separado;
- cualquier midpoint por evidencia insuficiente queda identificado y con confidence reducida;
- el LLM no calcula ni altera ratings;
- dashboard/PDF consumen resultados materializados;
- observaciones postpartido son descriptivas y auditables.

## Siguiente paso exacto

Ejecutar únicamente los nuevos gates:

```powershell
cd C:\Users\sergi\Desktop\football-performance-system
git pull
$env:FPS_DB_PATH = "D:\Data\Sergi\Desktop\football-performance-system\data\football_performance.duckdb"

python app\validate_match_mode.py
python llm\validate_match_rating_context.py
streamlit run app\streamlit_app.py
```

Comprobar visualmente:

1. `Partit` -> primer partido -> ratings + Observacions + PDF;
2. `Equip` -> Resum / Plantilla / Evolució;
3. `Assistent IA` -> contexto Jugador -> `Per què té aquest Match Rating?`;
4. `Assistent IA` -> contexto Partit -> `Resumeix què ha passat en aquest partit.`

Si ambos validators dan PASS y las tres vistas cargan correctamente:

1. cerrar PERF-16 #91;
2. cerrar DASHBOARD-03 #89;
3. pasar a GPS/físico + alertas validadas + pulido final/publicación.
