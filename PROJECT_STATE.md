# PROJECT_STATE

Última actualización: 01/10/2026

Memoria técnica operativa del proyecto. Si contradice un chat antiguo, prevalece este archivo. Antes de trabajar, comprobar siempre el código actual de `main` y commits posteriores a esta actualización.

## Estado actual

```text
DATA-01/02/03/04                    CERRADO / VALIDADO
COLLECTOR-01 MVP                    CERRADO FUNCIONALMENTE / UX+ES+MÓVIL PENDIENTE
GPS-01                              CERRADO / VALIDADO ESTRUCTURALMENTE
FEATURE-01/02/03                    CERRADO / VALIDADO
EXPERT-01..07 N1000-N13000          BASELINE CERRADO / VALIDADO
LLM-01                              PROTOTYPE v0.1 / CONTRATOS PASS
LLM-02 LOCAL COACH COPILOT          CERRADO MVP / CASTELLANO / LIMITACIÓN MENOR DOCUMENTADA
REPORTS-01                          PROTOTYPE v0.1 / CONTRATO PASS
REPORTS-02 PROFESSIONAL PDF         ACTIVO — GATE VISUAL PENDIENTE
DASHBOARD-01                        CONTRACT PASS
DASHBOARD PROFESSIONAL REDESIGN     IMPLEMENTADO / CHECK VISUAL LOCAL PENDIENTE
PRODUCT-SPIRAL-01                   PREPARADO — UI/PDF SAFE AUTO-IMPROVEMENT + REGRESSION QA
ARCHITECTURE-01                     CERRADO
ANALYTICS-01                        CERRADO / VALIDADO
DECISION POLICY / N13000            GATE APROBADO
PERF-18 MATCH RATING DATA SCIENCE   CERRADO / VALIDADO — V5 ACTIVA
SCORE-INTEGRATION-01                v0.2 VALIDADA / CONTRACT PASS
DASHBOARD-02 PLAYER VIEW            CERRADO / VALIDADO VISUALMENTE
DASHBOARD-03 TEAM MODE              ACTIVO / MATCH RATING V5 INTEGRADO
MATCH MODE                          CONTRACT PASS / OPERATIVO DESDE PARTIDO 1
DASHBOARD-04 PHYSICAL/GPS           CERRADO / VALIDADO
ALERTS-01 ATTENTION CENTRE          CERRADO / VALIDADO — v0.3
UI COMPATIBILITY                    PASS
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

## Rendimiento vigente

```text
MATCH RATING
= nota inmediata jugador-partido
= disponible desde partido 1
= no requiere historial
= versión activa match_rating_v0.5-candidate

PERFORMANCE INDEX
= capa histórica/posicional
= evolución, forma, consistencia y comparación por rol
= performance_score_v0.2-experimental
= no es la nota del partido
```

Match Rating V5 permanece congelado como baseline. No modificar fórmula, pesos o arquitectura sin nueva evidencia, experimentación explícita y validación.

## Gates validados principales

```text
MATCH RATING CONTRACT: PASS
590/590 apariciones valoradas
38/38 partidos
nulls=0
duplicates=0
out_of_range=0

ATTENTION FLAGS CONTRACT: PASS
MATCH MODE CONTRACT: PASS
DASHBOARD-01 DATA CONTRACT: PASS
LLM MATCH RATING CONTEXT: PASS
REPORTS-01 PDF CONTRACT: PASS
N13000 recommendation gate safety: PASS
```

## LLM-02 — Local Coach Copilot — CERRADO MVP

### Arquitectura final

```text
DuckDB local
→ analytics / expert system materializados
→ tools Python read-only
→ router determinista
→ compact evidence V5/V6
→ Ollama qwen3:1.7b
→ semantic guard determinista
→ Coach Copilot
→ entrenador
```

El modelo no tiene acceso directo a DuckDB y no calcula Match Rating, Performance Index, features críticas ni decisiones expertas.

La revisión humana del primer gate automático detectó que un 136/136 técnico podía ocultar respuestas semánticamente malas. A raíz de ello se añadieron:

- normalización explícita de campos V5/V6;
- semantic guard determinista;
- respuestas seguras para Team / Player / Compare / Match / GPS / Quality;
- separación explícita Match Rating / Performance Index / motor experto;
- explicación de Match Rating únicamente mediante dimensiones materializadas;
- grounding por procedencia de evidencia, no solo por coincidencia textual;
- revisión humana más amplia.

### Decisión de idioma

Para cerrar el MVP sin seguir gastando tiempo en i18n, el Coach Copilot oficial queda **solo en castellano**.

Catalán no forma parte del contrato de aceptación de LLM-02. Puede recuperarse como extensión futura si aporta valor.

### Gate final ES — 01/10/2026

Configuración:

```text
model=qwen3:1.7b
profile=balanced
router ES=17/17 = 100%
```

Challenge sets:

```text
seed 20260930: 17/17 = 100.0%
seed 20261001: 15/17 = 88.2%
seed 20261002: 17/17 = 100.0%
seed 20261003: 17/17 = 100.0%
```

Agregado:

```text
66/68 = 97.1% end-to-end
runtime errors = 0
safety failures = 0
numeric grounding = PASS
Spanish language = PASS
subject contract = PASS
average latency <= 12 s = PASS
```

El gate automático estricto imprimió `FAIL` por:

```text
sentence_limit_100 = FAIL
all_supported_categories_at_least_90 = FAIL
```

La segunda condición es derivada de los mismos dos casos challenge fallidos. No se detectaron fallos de seguridad, runtime, grounding, idioma ni sujeto.

### Criterio de cierre

LLM-02 se acepta como **MVP cerrado con limitación menor documentada** porque:

- supera ampliamente el umbral global del 90%;
- routing ES es 100%;
- no hay errores de seguridad;
- no hay errores de runtime;
- no hay claims numéricos no grounded detectados;
- el contrato de castellano pasa;
- la limitación restante es de longitud/formato en 2/68 casos challenge, no de lógica crítica.

No seguir iterando LLM-02 salvo que aparezca un error funcional grave durante el uso real.

### Limitaciones explícitas del Copilot MVP

No soporta como capacidad validada:

- ranking condicionado por rol (`role_ranking`);
- similitud entre jugadores (`player_similarity`);
- predicción futura (`future_prediction`);
- decisión de titularidad / XI ideal;
- recomendaciones tácticas automáticas;
- fatiga, readiness o riesgo de lesión sin capa analítica validada.

Estas preguntas deben devolver una limitación segura o evidencia descriptiva, no inventar una respuesta.

## Producto actual

### Home / Command Center

Coach Command Center con último partido, brief operativo, forma, tendencias, cambios 5-vs-5, ratings destacados, calidad de datos y accesos principales.

Pendiente: gate visual local.

### Jugador

Match Rating V5, confidence, perfil, Performance Index, dimensiones, evolución, técnico, motor experto, partidos y PDF.

### Equipo

Match Rating V5, forma, matriz de plantilla, tendencias, participación, Performance Index complementario, historial y PDF.

### Partido

Ratings V5, confidence, roles, minutos, distribución, dimensiones, observaciones deterministas y PDF desde partido 1.

### Físico / GPS

Capa descriptiva opcional sobre GPS canónico. La base local aún no contiene observaciones GPS reales suficientes para una demo completa. No usar HSR/sprint/load/fatigue/readiness sin definición validada.

### Alertas

Solo estados auditables de contexto/calidad. Sin diagnóstico de lesión, fatiga o readiness.

## REPORTS-02 — professional PDFs

Estado técnico:

- schema 0.3.0;
- Team / Player / Match payloads válidos;
- identidad visual y jerarquía implementadas;
- Match Rating destacado;
- sin cálculos críticos en PDF;
- validación de contrato PASS.

Pendiente:

1. inspección visual de tres PDFs;
2. clipping/overlap/legibilidad;
3. corregir solo si el gate visual detecta problemas.

## Collector

Variables funcionales cerradas.

Pendiente:

1. simplificar UX;
2. castellano completo;
3. mobile-first/responsive;
4. reducir fricción de captura;
5. mantener semántica y compatibilidad con esquema actual.

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

## Decisiones descartadas / no prioritarias

- seguir optimizando indefinidamente qwen3:1.7b: descartado para el MVP; coste marginal no justificado;
- mantener CA+ES en LLM-02: descartado para el MVP; castellano único reduce complejidad y tiempo;
- confiar solo en pass rate automático sin revisión humana: descartado tras detectar falsos positivos semánticos;
- usar LLM como calculadora o motor crítico: descartado por arquitectura y auditabilidad.

## Problemas abiertos

- gate visual Home / Team / Player / Match;
- gate visual de tres PDFs;
- UX/ES/móvil del collector;
- demo GPS con datos reales o ejemplo claramente etiquetado;
- Performance Index histórico y capacidades futuras no necesarias para el MVP;
- QA global final y documentación TFM;
- derechos/licencia antes de cualquier publicación pública.

## Siguiente paso exacto

**LLM-02 queda congelado. No seguir trabajando en el agente.**

Orden inmediato:

1. gate visual local de Home / Team / Player / Match;
2. corregir únicamente problemas visuales o de UX detectados;
3. gate visual de los tres PDFs y cierre REPORTS-02;
4. Collector UX / castellano / móvil;
5. demo GPS;
6. QA global del producto;
7. documentación final del TFM.
