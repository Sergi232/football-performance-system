# PROJECT_STATE

Última actualización: 30/09/2026

Memoria técnica operativa del proyecto. Si contradice un chat antiguo, prevalece este archivo. Antes de trabajar, comprobar siempre el código actual de `main` y commits posteriores a esta actualización.

## Estado actual

```text
DATA-01/02/03/04                    CERRADO / VALIDADO
COLLECTOR-01 MVP                    CERRADO FUNCIONALMENTE / UX+ES+MÓVIL PENDIENTE
GPS-01                              CERRADO / VALIDADO ESTRUCTURALMENTE
FEATURE-01/02/03                    CERRADO / VALIDADO
EXPERT-01..07 N1000-N13000          BASELINE CERRADO / VALIDADO
LLM-01                              PROTOTYPE v0.1 / CONTRATOS PASS
LLM-02 LOCAL COACH COPILOT          IMPLEMENTADO / QA FINAL ACTIVO
LLM-QA-SPLIT-01                     IMPLEMENTADO — ROUTER/TOOLS vs SYNTHESIS SEPARADOS
LLM-QA-GROUNDING-01                 IMPLEMENTADO / EJECUCIÓN LOCAL PENDIENTE
LLM-GUARDRAIL-I18N-01               FIX APLICADO / VALIDACIÓN LOCAL PENDIENTE
REPORTS-01                          PROTOTYPE v0.1 / CONTRATO PASS
REPORTS-02 PROFESSIONAL PDF         ACTIVO — ISSUE #94 / GATE VISUAL PENDIENTE
DASHBOARD-01                        CONTRACT PASS
DASHBOARD PROFESSIONAL REDESIGN     IMPLEMENTADO / CHECK VISUAL LOCAL PENDIENTE
PRODUCT-SPIRAL-01                   PREPARADO — UI/PDF SAFE AUTO-IMPROVEMENT + REGRESSION QA
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
UI COMPATIBILITY                    PASS 26/09/2026
DOCUMENTATION-SYNC-01               CERRADO 30/09/2026
FINAL-01                            ACTIVO / PRODUCTO FINAL
PUBLIC DEPLOYMENT                   NO HACER — decisión explícita actual
```

## Fuente de verdad

Orden de precedencia:

```text
código actual de main + commits recientes
→ PROJECT_STATE.md
→ docs/DECISIONS.md
→ docs/ARCHITECTURE.md
→ documentación específica del módulo
→ README.md / docs/WORKFLOW.md
→ conversaciones antiguas
```

El 30/09/2026 se corrigió documentation drift en:

- `README.md`;
- `docs/WORKFLOW.md`;
- `docs/DECISIONS.md`.

Decisiones formalmente alineadas:

- `DG-UX-01`: insight-first, audit-detail second;
- `DG-LLM-01`: local-first mediante Ollama con provider opcional desacoplado;
- `DG-REP-01`: informes profesionales específicos Team / Player / Match;
- `D-010`: Match Rating V5 congelado como baseline activo;
- `D-011`: separación explícita Match Rating vs Performance Index.

`DG-PUB-01` continúa pendiente de derechos/licencia del dataset.

## Arquitectura de producto

```text
COLLECTOR / IMPORT + GPS opcional
→ RAW / NORMALIZED DATA
→ FEATURE ENGINE
→ ANALYTICS
→ EXPERT SYSTEM / ML
→ PRODUCT SERVICE / ACCESS LAYER
→ WEB DASHBOARD
   ↓              ↓
ASSISTANT IA      PDF
```

La web es el producto principal. Los PDF son salidas estáticas complementarias.

Regla: una capa superior no puede inventar cálculos, métricas, scores, clasificaciones o recomendaciones que no existan en una capa inferior validada.

Arquitectura LLM local:

```text
DuckDB local
→ analytics / expert system materializados
→ tools Python read-only
→ router v2 determinista
→ Ollama localhost
→ Coach Copilot
→ entrenador
```

El modelo local no recibe acceso directo a DuckDB y no calcula ratings, features críticas ni decisiones expertas. OpenAI no es necesario para el producto local.

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
- Reproducción del benchmark Opta Points sobre PannaData: Pearson ~0.9984, Spearman ~0.9980, MAE ~0.0134.

### Outfield

- rating por CB / FB / DM / CM / AM / W / ST;
- referencia profesional estrictamente anterior al primer partido local;
- anchors principales: gol +1.00, asistencia +0.60, penalti recibido +0.40, amarilla -0.20, roja -0.50;
- hipótesis FPS: penalti concedido -0.40;
- ajuste contextual secundario: -0.10 por gol encajado mientras el jugador consta en campo;
- construct gate: PASS;
- V4.1 on-pitch contract: PASS.

Precisión temporal on-pitch: 156 filas exactas y 434 con fallback de minuto/duración, 171 derivadas de conflictos resueltos.

### Goalkeeper

```text
selected_weights = 90% shot-stopping / 10% distribution
TEST MAE vs Opta Points = 0.3536
TEST Spearman = 0.9221
monotonicity_gate = PASS
local_weight_sensitivity_gate = PASS
GK_FINAL_GATE = PASS
```

Selección de pesos en VALID; TEST quedó intacto.

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

Distribución:

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

Derrota 0-3 del 20/12/2025: media 6.143, mediana 5.996. El antiguo comportamiento ~7.4 queda corregido sin castigo global por resultado.

Match Rating V5 queda congelado como baseline vigente. No modificar fórmula, pesos o arquitectura sin nueva evidencia, experimentación explícita y validación.

## Gates validados tras V5

```text
MATCH RATING CONTRACT: PASS
590/590 apariciones valoradas
38 partidos
38 porteros
172 role-unavailable fallback explícitos
0 neutral-insufficient rows
16 ratings en el primer partido

ATTENTION FLAGS CONTRACT: PASS
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
LLM explica analytics materializados y no recalcula rating

REPORTS-01 PDF CONTRACT: PASS
team/player/match payloads válidos
recommendation/report guardrails=PASS
PDFs generados correctamente
```

## Producto actual

### Home / Command Center

Coach Command Center con último partido, brief operativo, forma, tendencias, cambios 5-vs-5, ratings destacados, calidad de datos y accesos principales. Gate visual local pendiente.

### Jugador

Match Rating V5, confidence, perfil, Performance Index, dimensiones, evolución, técnico, motor experto, partidos y PDF. Gate visual local pendiente.

### Equipo

Match Rating V5, forma, matriz de plantilla, tendencias, participación, Performance Index complementario, historial y PDF. Gate visual local pendiente.

### Partido

Ratings V5, confidence, roles, minutos, distribución, dimensiones, observaciones deterministas y PDF desde partido 1. Gate visual local pendiente.

### Físico / GPS

Capa descriptiva opcional sobre GPS canónico. Sin HSR/sprint/load/fatigue/readiness no validados. La base local no contiene observaciones GPS reales; falta ejemplo local claramente etiquetado para demo.

### Alertas

Solo estados auditables de contexto/calidad. Sin diagnóstico de lesión, fatiga o readiness.

## LLM-02 — Local Coach Copilot

Implementado:

- `llm/coach_agent.py`: tools read-only sobre analytics materializados;
- `llm/coach_agent_hybrid.py`: router local + compact evidence + Ollama synthesis;
- `llm/coach_agent_fast.py`: entry point de baja latencia usado por el producto;
- `llm/coach_agent_router_v2.py`: routing bilingüe ES/CA;
- preguntas abiertas y multi-tool;
- resolución de jugador/rival y follow-ups;
- memoria conversacional en Streamlit;
- guardrails de rating, métricas, lesión/fatiga/readiness y recomendaciones tácticas;
- `qwen3:1.7b` usado en QA anterior por latencia;
- Auto-QA previo: 216 casos / 210 PASS = 97,22%, principalmente router/tool QA.

### QA: hallazgo metodológico 30/09/2026

El runner adaptativo ya registraba por caso:

```text
router_pass
synthesis_attempted
synthesis_pass
classification
```

pero su `overall_pass_rate` mezclaba `ROUTER_PASS` y `FULL_PASS`. Por tanto, el 97% global previo no debe interpretarse como 97% de calidad final de respuesta.

Además, el criterio histórico `synthesis_pass` solo valida ejecución/contrato:

- sin error;
- respuesta no vacía;
- tools esperadas presentes;
- ausencia del fallback conocido.

No valida por sí mismo corrección semántica completa.

### LLM-QA-SPLIT-01

Nuevo:

`llm/summarize_adaptive_qa.py`

Separa:

- Router/Tools pass rate;
- Synthesis execution success;
- synthesis coverage;
- end-to-end sobre casos sintetizados;
- resultados por categoría;
- resultados por perfil de síntesis.

Incluye advertencia explícita de que synthesis execution != semantic quality.

### LLM-GUARDRAIL-I18N-01

Bug detectado: `router_v2` reconocía preguntas prohibidas en español pero devolvía el mensaje de guardrail en catalán.

Fix aplicado en `llm/coach_agent_router_v2.py`:

- guardrail castellano para pregunta castellana;
- guardrail catalán para pregunta catalana.

`llm/validate_local_agent.py` también se ha alineado con el runtime real:

```text
coach_agent_fast
→ instala router_v2
→ hybrid runtime
```

y ahora prueba guardrail ES + CA.

Validación local pendiente porque GitHub no dispone de la DuckDB/Ollama del PC.

### LLM-QA-GROUNDING-01

Nuevo:

`llm/run_synthesis_grounding_qa.py`

Benchmark sin LLM juez externo. Captura la compact evidence real y evalúa de forma determinista:

- routing/tools;
- runtime/fallback;
- grounding de claims numéricos contra pregunta/evidencia;
- patrones de recomendaciones prohibidas;
- idioma cuando es detectable;
- límite de seis frases;
- guardrails ES/CA.

No afirma evaluar completamente:

- utilidad para entrenador;
- matiz;
- corrección semántica total;
- causalidad más allá de checks explícitos.

La revisión humana sigue siendo necesaria.

### Pendiente para cerrar LLM-02

1. ejecutar localmente `validate_local_agent.py`;
2. ejecutar `run_synthesis_grounding_qa.py` sobre `qwen3:1.7b`;
3. si `qwen3:4b` está instalado o se decide instalar, ejecutar el mismo set compartido sobre ambos modelos;
4. revisar fallos por componente, no solo pass rate global;
5. corregir solo fallos reproducibles;
6. repetir benchmark;
7. hacer una pequeña revisión humana de respuestas representativas;
8. cerrar LLM-02 únicamente si router/tools + grounding/safety + síntesis revisada son suficientes.

## REPORTS-02 — professional PDFs

Issue #94.

Estado técnico:

- `reports/data_builder.py` schema 0.3.0;
- payload equipo: snapshot/historial Match Rating V5;
- payload jugador: Performance Index actual e historial;
- payload partido: observaciones deterministas;
- `reports/pdf_engine.py`: identidad visual, KPIs, tablas y jerarquía;
- Match Rating destacado en jugador/partido;
- sin cálculos críticos en PDF;
- `python reports\validate_reports.py` = PASS.

Pendiente:

1. inspección visual de tres PDFs;
2. clipping/overlap/legibilidad;
3. corregir solo si el gate visual detecta problemas.

## PRODUCT-SPIRAL-01

Mejora y stress de web + PDF sin tocar analytics críticos.

Archivos:

- `product/run_product_spiral.py`;
- `product/run_product_spiral_safe.py`;
- `product/run_product_spiral_optimizer.py`;
- `product/README.md`.

Allowlist:

```text
app/ui_theme.py
app/coach_ui.py
reports/pdf_engine.py
```

Protegido: `analytics/`, `data/`, `features/`, `decision_tree/`, `models/`, `llm/`, `gps/`.

No modifica DB, Match Rating, Performance Index, thresholds ni decisiones expertas. No hace push/merge automático. Puede operar con DB real o DB-free. Gate visual humano obligatorio.

## Collector

Variables funcionales cerradas. Pendiente:

1. simplificar UX;
2. castellano completo;
3. mobile-first/responsive;
4. reducir fricción de captura;
5. mantener semántica y compatibilidad con esquema actual.

## UI compatibility

```text
app/validate_ui_compatibility.py
```

Última ejecución documentada 26/09/2026:

```text
STREAMLIT UI COMPATIBILITY: PASS
deprecated_use_container_width=0
known_invalid_navigation_icons=0
```

Falta revisión visual tras el rediseño profesional.

## Guardrails globales

- no copiar fórmulas propietarias;
- no convertir missing en zero sin semántica validada;
- no thresholds bueno/malo sin validación;
- no recomendación táctica derivada directamente del Match Rating;
- no inventar roles;
- porteros usan camino separado;
- LLM downstream del motor;
- LLM local no tiene acceso directo a DuckDB;
- GPS opcional;
- no HSR/sprint/load/fatigue/readiness sin definición validada;
- PDF/dashboard consumen analytics materializados;
- Product Spiral no toca lógica crítica;
- no desplegar/publicar públicamente mientras siga bloqueado.

## Siguiente paso exacto

La prioridad sigue siendo **cerrar LLM-02 / Coach Copilot QA**.

En el PC que contiene DuckDB + Ollama:

```powershell
git pull
$env:FPS_DB_PATH = "RUTA_A_TU_football_performance.duckdb"
python llm\validate_local_agent.py
python llm\run_synthesis_grounding_qa.py --models qwen3:1.7b --cases 28
```

Si `qwen3:4b` está instalado y se quiere hacer comparación controlada:

```powershell
python llm\run_synthesis_grounding_qa.py --models qwen3:1.7b,qwen3:4b --cases 28
```

Para separar correctamente las métricas de una ejecución adaptativa previa o nueva:

```powershell
python llm\summarize_adaptive_qa.py
```

Después:

1. analizar los JSON/CSV resultantes por componente;
2. corregir fallos reproducibles del Copilot;
3. repetir QA;
4. cerrar LLM-02;
5. revisar Product Spiral;
6. gate visual Home / Team / Player / Match;
7. gate visual de tres PDFs y cierre REPORTS-02;
8. Collector UX/ES/móvil;
9. demo GPS;
10. Performance Index histórico;
11. QA global y documentación final TFM.
