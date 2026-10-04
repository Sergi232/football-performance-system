# Arquitectura v1 — Football Performance System

Estado: **ARCHITECTURE-01 / CERRADO**  
Fecha de sincronización: 04/10/2026

Este documento define la arquitectura vigente del producto. `PROJECT_STATE.md` y el código actual de `main` prevalecen si existe cualquier discrepancia histórica.

## 1. Objetivo del producto

Producto web para equipos amateur o semiprofesionales sin departamento de análisis que transforma datos realistas de vídeo y GPS opcional en información útil, auditable y explicable para el cuerpo técnico.

La web es el producto principal. El LLM y los PDF son capas downstream de interacción/presentación y no motores de cálculo crítico.

## 2. Arquitectura vigente

```text
COLLECTOR / IMPORT + GPS OPCIONAL
        ↓
RAW / NORMALIZED DATA
        ↓
FEATURE ENGINE
        ↓
ANALYTICS ENGINE
        ↓
DECISION ENGINE
        ↓
PRODUCT SERVICE / ACCESS LAYER
        ↓
WEB DASHBOARD
   ↓              ↓
AI ASSISTANT      PDF
```

Regla central: **una capa superior no puede inventar cálculos, métricas, scores, rankings, clasificaciones o recomendaciones que no existan en una capa inferior validada**.

## 3. Capas y estado

### L0 — Governance / Architecture

Responsable de contratos, decisiones, gates, estado del proyecto, documentación y prevención de duplicidades.

Fuente de verdad:

```text
código actual de main + commits recientes
→ PROJECT_STATE.md
→ docs/DECISIONS.md
→ docs/ARCHITECTURE.md
→ documentación específica del módulo
→ README.md / docs/WORKFLOW.md
→ conversaciones antiguas
```

### L1 — Capture / Import

Incluye:
- Data Collector V1.1 oficial;
- imports de datos externos;
- GPS opcional multi-proveedor.

Estado: **cerrado/validado en el MVP actual**.

Responsabilidad: recoger hechos observables, trazables y realistas para fútbol amateur. No calcula conclusiones.

### L2 — Data Layer

Unidad analítica principal: `player_match`.

Responsabilidad:
- identidades;
- partidos;
- minutos;
- rol observado;
- acciones de vídeo;
- estadísticas raw;
- GPS normalizado;
- contexto de equipo;
- trazabilidad/procedencia.

Estado: **cerrado/validado**.

Debe preservar ausencia y ambigüedad. No rellena datos mediante supuestos silenciosos.

### L3 — Feature Engine

Responsabilidad:
- ratios;
- per90;
- históricos strict-past;
- tendencia matemática;
- variabilidad;
- features condicionadas a rol.

Estado: **FEATURE-01/02/03 cerrados y validados**.

No decide si un valor es bueno/malo ni recomienda.

### L4 — Analytics Engine

Responsabilidad: convertir features en evidencia analítica estructurada.

Incluye:
- evolución;
- cambio;
- consistencia;
- comparación self-history;
- comparación peer-role cuando existe rol observado;
- contexto;
- tamaño de muestra;
- evidencia y provenance.

Estado: **ANALYTICS-01 cerrado y validado**.

Self-role y peer-role permanecen separados. No se introducen thresholds deportivos arbitrarios.

### L5 — Decision Engine

Sistema experto jerárquico N1000–N13000.

Cada resultado conserva:

```text
input → condition → result → confidence → justification
```

Estado: **expert_0.7.0 cerrado/validado**.

N13000 actúa como gate y no emite recomendación táctica sin policy validada.

GPS sintético no constituye evidencia física observada para N9000.

### L6 — DS / ML Layer

ML es complementario y posterior al baseline determinista/experto.

Experimentos realizados:
- change detection: señal experimental, no deploy;
- player similarity: exploratorio, estabilidad insuficiente, no deploy;
- clasificación de posición/rol: experimento cerrado como `context-only`; el baseline simple de última posición superó al ML.

Estado: **baseline experimental cerrado; no hay modelo ML adicional desplegado en el producto**.

No se fuerza un modelo cuando no existe target o ground truth defendible.

### L7 — Performance layers

Dos capas distintas:

```text
MATCH RATING
= evaluación inmediata jugador-partido
= match_rating_v0.5-candidate
= disponible desde partido 1

PERFORMANCE INDEX
= capa histórica/posicional complementaria
= performance_score_v0.2-experimental
```

Match Rating V5 está congelado como baseline vigente. El Performance Index sigue siendo experimental y no sustituye al Match Rating.

### L8 — Product Service / Access Layer

Responsabilidad:
- consultas TEAM / PLAYER / MATCH;
- payloads estructurados;
- provenance;
- acceso a Match Rating, Performance Index, expert, GPS y alertas;
- autorización por equipo;
- evitar que web, PDF y LLM reimplementen lógica analítica.

Estado: **operativo y validado contractualmente**.

Autorización estructural:
- SUPERADMIN;
- CLUB_ADMIN;
- STAFF.

Autenticación real email/contraseña/sesiones no forma parte del MVP cerrado.

### L9 — Web Product

Modos actuales:
- TEAM MODE — principal;
- PLAYER MODE — complementario;
- MATCH MODE;
- FÍSICO / GPS;
- CALIDAD / ALERTAS;
- ASISTENTE IA;
- RIVAL MODE — futuro.

Principio:

```text
insight-first, audit-detail second
```

Estado: **dashboard profesional operativo; contratos de datos, presentación demo, compatibilidad, access control, alertas y Match Mode en PASS**.

### L10 — AI Assistant

Arquitectura final del runtime local:

```text
pregunta natural
→ preflight / guardrails
→ router determinista de alta confianza
→ tools Python read-only
→ DuckDB + analytics / expert system materializados
→ evidencia estructurada
→ respuesta factual determinista
→ Coach Copilot
```

Solo cuando la intención sigue siendo ambigua y permanece dentro del dominio:

```text
pregunta ambigua
→ qwen3.5:4b como router semántico local
→ tool validada
→ Python / DuckDB
→ evidencia estructurada
→ respuesta factual
```

Versión oficial MVP: **castellano**.

El LLM no accede directamente a DuckDB, no recalcula Match Rating/Performance Index y no puede crear métricas críticas ni saltarse los guardrails o N13000.

La gramática de consulta se compone de:

```text
entidad + operación + métrica + agregación + rol + filtros + ventana + follow-up
```

Las consultas claras no necesitan LLM. Ruido, meta-consultas y fuera de dominio obvio se resuelven también mediante preflight local sin invocar un modelo.

Validación local real final con DuckDB profesional:

```text
SMOKE CONTRACT: PASS (28/28)
average_elapsed=0.4s
all final smoke cases: rounds=0
```

El smoke final cubre rankings, ventanas temporales, perfiles, GPS, comparación entre jugadores, comparación por posición, partidos, calidad de datos, guardrails, ruido/fuera de dominio y follow-ups encadenados.

El fallback Qwen queda reservado para lenguaje ambiguo dentro del dominio y puede tener una latencia significativamente mayor en CPU; por eso no forma parte de la ruta obligatoria de una consulta clara.

Guardrails explícitos:
- fatiga/cansancio;
- readiness;
- riesgo de lesión;
- XI/titularidad;
- recomendación táctica no validada;
- `mejor jugador`, `más completo` o `más determinante` sin criterio analítico aprobado.

Comparación por posición:
- el sistema puede comparar grupos posicionales de forma determinista;
- si se pregunta quién ha rendido mejor dentro de una posición, el criterio explícito de ordenación es Match Rating medio en esa muestra;
- las métricas adicionales son evidencia descriptiva;
- no se crea un score nuevo.

#### Proveedor externo opcional

La misma página ofrece un segundo modo:

```text
OpenAI API · clave propia
```

Arquitectura:

```text
pregunta clara
→ mismo router determinista local
→ tool FPS
→ DuckDB
→ respuesta
→ 0 llamadas API

pregunta ambigua
→ OpenAI semantic router
→ tools bounded/read-only revalidadas localmente
→ DuckDB / analytics / expert
→ evidencia estructurada
→ síntesis externa limitada + numeric grounding guard
```

La API key pertenece al usuario y la UI no la persiste en DuckDB ni en archivos del proyecto. La implementación y contratos pasan CI; no existe todavía benchmark live con una API key real.

La conexión inversa `ChatGPT → FPS` mediante MCP no forma parte del MVP actual.

### L11 — Reporting

Informes Team / Player / Match V6.

Flujo:

```text
analytics materializados
→ reports/report_metrics.py
→ reports/data_builder.py
→ reports/pdf_engine_elite_v6.py
→ PDF
```

Estado: **REPORTS V6 cerrado / gate técnico + revisión visual PASS**.

Los PDF no recalculan Match Rating, Performance Index ni decisiones expertas.

### L12 — QA / Publication

Responsabilidad:
- tests y regresión;
- leakage checks;
- privacidad;
- anonimización;
- demo;
- instalación reproducible;
- GitHub;
- documentación TFM.

Estado: **Global end-to-end QA cerrado en PASS**.

La demo sintética es redistribuible y reproducible. La redistribución pública del dataset profesional sigue bloqueada por derechos/licencia.

## 4. Cadena validada end-to-end

```text
Collector
→ DuckDB
→ Features
→ Analytics
→ Match Rating
→ GPS
→ Expert N1000-N13000
→ Dashboard
→ Access control
→ Demo presentation
→ Coach Copilot
→ PDF
→ Public synthetic demo
```

Resultado vigente:

```text
GLOBAL END-TO-END QA: PASS
```

## 5. Reglas de estabilidad

No reabrir una capa cerrada por preferencia estética o por un test aislado sin interpretar primero su contrato y el estado documentado.

Una capa solo se reabre si existe:
1. incidencia funcional real;
2. nueva evidencia que invalida una decisión;
3. cambio de scope explícito;
4. Decision Gate de impacto estructural.

## 6. Decision Gates

Los gates estructurales relevantes ya resueltos o documentados incluyen:
- `DG-AN-01` — comparaciones analíticas;
- `DG-N13-01` — recommendation gate;
- `DG-UX-01` — jerarquía TEAM / PLAYER / MATCH;
- `DG-LLM-01` — arquitectura grounded del Assistant;
- `DG-REP-01` — informes técnicos;
- `DG-PUB-01` — redistribución de datos, todavía bloqueada para el dataset profesional por licencia.

Sergi no valida decisiones técnicas ordinarias o reversibles. Solo se abre gate si afecta significado deportivo, arquitectura, metodología, métrica principal, política de recomendación, UX principal, privacidad/publicación o scope del TFM.

## 7. Prioridad actual

El núcleo funcional está cerrado. La prioridad es:

```text
REVISIÓN VISUAL FINAL
→ CAPTURAS CANÓNICAS
→ SINCRONIZACIÓN DOCUMENTAL FINAL
→ MAQUETACIÓN MEMORIA
→ DEFENSA / DEMO
```

No se añaden módulos nuevos salvo que aparezca una necesidad real del cierre académico o una incidencia funcional demostrada.
