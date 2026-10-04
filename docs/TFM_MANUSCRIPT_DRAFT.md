# Football Performance System

## Diseño e implementación de un sistema auditable de análisis del rendimiento futbolístico para equipos amateur y semiprofesionales mediante vídeo, GPS opcional, analítica de datos, sistema experto e inteligencia artificial

**Estado:** borrador integrado de memoria.  
**Idioma:** castellano.  
**Fecha de referencia técnica:** 04/10/2026.  
**Fuente de verdad técnica:** código actual de `main` + `PROJECT_STATE.md`.

> Este documento es el manuscrito académico integrado de trabajo. Debe adaptarse a la plantilla, extensión y norma bibliográfica oficial de la universidad cuando estén disponibles.

---

# Resumen

Este Trabajo Final de Máster presenta el diseño, implementación y validación técnica de un sistema integral de análisis de rendimiento orientado a equipos de fútbol amateur y semiprofesionales sin departamento propio de análisis. El objetivo no es reproducir plataformas profesionales de tracking o proveedores comerciales de eventos, sino demostrar que un conjunto reducido de datos observables de vídeo y GPS opcional puede transformarse en información estructurada, auditable y consultable por un cuerpo técnico.

La solución se organiza mediante una arquitectura por capas que separa datos brutos, variables derivadas, evidencia analítica, lógica de decisión y generación de lenguaje natural. El flujo parte de un Data Collector HTML y de una capa opcional de normalización GPS, almacena la información en DuckDB, construye features deterministas con control temporal `strict-past`, genera evidencia analítica, aplica un sistema experto jerárquico N1000-N13000, presenta los resultados mediante una aplicación Streamlit e incorpora un Coach Copilot grounded. El asistente resuelve consultas claras mediante preflight, routing determinista y herramientas de solo lectura, y reserva un modelo local Qwen para lenguaje ambiguo dentro del dominio; adicionalmente existe un modo OpenAI opcional con clave propia del usuario. Los informes PDF consumen resultados estructurados ya calculados y no recalculan lógica crítica.

El prototipo se ha validado mediante contratos de datos, tests unitarios, validadores por capa, pruebas end-to-end y un pipeline de integración continua. El sistema principal supera el QA global y dispone de una demo pública sintética reproducible que puede generarse desde un entorno limpio sin depender de la base profesional utilizada durante el desarrollo. El Coach Copilot cerró su smoke real final sobre la DuckDB profesional con 28/28 casos correctos y 0,4 s de latencia media en esa batería concreta; todos esos casos siguieron la ruta determinista o de preflight sin activar el fallback semántico. Los resultados permiten contrastar favorablemente la hipótesis en su dimensión técnica y arquitectónica. No se demuestra, sin embargo, un efecto causal sobre las decisiones de entrenadores, el rendimiento deportivo, la fatiga o la prevención de lesiones.

**Palabras clave:** football analytics; performance analysis; expert systems; data engineering; GPS; large language models; reproducibility.

---

# 1. Introducción

El análisis del rendimiento en fútbol ha evolucionado desde enfoques notacionales relativamente simples hasta ecosistemas profesionales que combinan vídeo, eventos, tracking, GPS, modelos estadísticos y herramientas de scouting. En clubes profesionales, gran parte de esta infraestructura puede obtenerse a través de proveedores especializados. En fútbol amateur o semiprofesional, en cambio, el coste económico, tecnológico y operativo limita el acceso a sistemas equivalentes.

Muchos equipos de menor presupuesto sí disponen de vídeo de los partidos y, en algunos casos, dispositivos GPS. El problema no es únicamente capturar datos, sino convertirlos en una estructura histórica coherente, derivar variables de forma consistente, contextualizar el rendimiento por jugador y rol, y presentar resultados que el cuerpo técnico pueda interpretar sin depender de un analista especializado.

Este TFM aborda ese problema como una cuestión de accesibilidad analítica. La propuesta no intenta reproducir Opta, StatsBomb o sistemas profesionales de tracking. Se centra en diseñar un producto que funcione con variables observables y realistas para un partido de 90 minutos y que mantenga trazabilidad desde el dato hasta la explicación final.

La literatura de performance analysis señala que el rendimiento futbolístico es multidimensional y contextual. Mackenzie y Cushion (2013), Sarmento et al. (2014) y Sarmento et al. (2022) destacan la importancia de interpretar los indicadores teniendo en cuenta el contexto y evitando reducir el rendimiento a una única variable. Esta idea se traduce en una arquitectura que separa datos brutos, features, evidencia analítica y decisión.

El producto final es una aplicación web con Team Mode, Player Mode y Match Mode, complementada por una capa física GPS, un sistema experto, un asistente IA grounded y exportación PDF.

---

# 2. Estado del arte y marco teórico

## 2.1 Performance analysis en fútbol

El análisis de partidos combina dimensiones técnicas, tácticas, físicas y contextuales. Sarmento et al. (2014) revisaron la literatura de match analysis y destacaron la necesidad de definiciones operacionales claras, categorías estandarizadas y consideración de variables situacionales. Mackenzie y Cushion (2013) remarcan que la utilidad de los indicadores depende no solo de su disponibilidad, sino también de la validez de las inferencias derivadas.

La umbrella review de Sarmento et al. (2022) refuerza una perspectiva multidimensional del rendimiento en deportes colectivos. Para este trabajo, estas evidencias justifican una arquitectura que combina varias capas de información y evita asumir que una única métrica resume el rendimiento completo.

## 2.2 Metodología observacional y análisis notacional

James (2006) describe el papel del análisis notacional en fútbol y subraya problemas metodológicos relacionados con la definición de indicadores y el análisis longitudinal. Ortega-Toro et al. (2019) muestran que un instrumento observacional debe definir explícitamente categorías y comprobar su fiabilidad.

El Collector de este TFM adopta el principio de registrar hechos observables mediante categorías operacionales explícitas. No obstante, la validación técnica del Collector no equivale a una validación científica interobservador; esta última queda como trabajo futuro.

## 2.3 Contexto, rol y evolución

Los indicadores técnicos deben interpretarse en contexto. Posición, rol, estado del partido y calidad del rival pueden modificar su significado. En un sistema longitudinal, además, es necesario controlar qué información estaba disponible realmente en cada momento.

Por este motivo, el sistema separa el historial del propio jugador en su rol (`SELF_ROLE_PRIOR`) de la comparación con peers del mismo rol (`PEER_ROLE_PRIOR`) y mantiene separadas una valoración inmediata de partido y una capa histórica experimental.

## 2.4 GPS y carga externa

Los sistemas GPS permiten cuantificar componentes de carga externa, pero la validez de sus medidas depende del dispositivo, frecuencia de muestreo y tipo de movimiento. Scott, Scott y Kelly (2016) señalan que la distancia total puede presentar una fiabilidad razonable, mientras que velocidades altas, movimientos cortos y cambios de dirección generan mayores dificultades.

Miguel et al. (2021) muestran una elevada heterogeneidad en las métricas utilizadas para monitorización de carga en fútbol. Hader et al. (2019) advierten que las variables de carga externa no deben convertirse automáticamente en inferencias de fatiga.

Estas limitaciones justifican que el GPS se utilice en este TFM como una capa descriptiva y opcional, sin derivar automáticamente readiness, riesgo de lesión o fatiga.

## 2.5 Data leakage

Kaufman et al. (2012) definen data leakage como la incorporación de información que no estaría legítimamente disponible en el momento de realizar una predicción o decisión. En datos deportivos longitudinales, este problema puede aparecer si una feature histórica utiliza partidos futuros o agregaciones de toda la temporada.

El sistema implementa una política `strict-past`: para una fila en fecha `t`, solo se utilizan observaciones con fecha estrictamente anterior.

## 2.6 Sistemas expertos e interpretabilidad

Liu, Gegov y Cocea (2016) describen los sistemas basados en reglas como una forma de sistema experto construida mediante condiciones explícitas. Rudin (2019) defiende modelos intrínsecamente interpretables cuando la trazabilidad es importante.

El sistema experto del proyecto sigue este principio mediante una jerarquía N1000-N13000. Cada nodo conserva entrada, condición, resultado, confianza y justificación.

## 2.7 LLM, grounding y herramientas

Los modelos de lenguaje pueden producir respuestas plausibles pero incorrectas. Huang et al. (2025) revisan el problema de hallucination y factualidad. Lewis et al. (2020) muestran el valor de combinar generación con memoria externa, mientras que Schick et al. (2023) muestran la utilidad de conectar modelos de lenguaje a herramientas especializadas.

El Coach Copilot adopta el mismo principio general: el LLM no accede directamente a la base ni calcula métricas críticas, sino que consulta resultados estructurados mediante herramientas de solo lectura. Además, el sistema prioriza routing determinista para consultas claras, reduciendo tanto la latencia como la superficie de error del modelo generativo.

## 2.8 Reproducibilidad computacional

Sandve et al. (2013) proponen registrar cómo se producen los resultados, conservar versiones y automatizar procesos. El proyecto implementa estos principios mediante Git, tests, validators, CI y una demo sintética generable desde cero.

---

# 3. Hipótesis y objetivos

## 3.1 Hipótesis principal

> **Un equipo de fútbol amateur o semiprofesional puede disponer de un sistema integral y auditable de soporte a la decisión a partir de datos de vídeo y GPS opcional, capaz de transformarlos en información sobre rendimiento, evolución, rol y comportamiento físico de los jugadores y del equipo.**

La hipótesis se interpreta como una hipótesis de viabilidad técnica y arquitectónica. No se formula como prueba causal de mejora deportiva.

## 3.2 Objetivo general

Diseñar, implementar y validar un sistema reproducible que transforme datos simples de vídeo y GPS opcional en información estructurada para el análisis de equipo, jugador y partido.

## 3.3 Objetivos específicos

- diseñar un Data Collector adecuado al contexto amateur;
- definir un modelo de datos con unidad jugador-partido;
- normalizar GPS de diferentes proveedores;
- construir un Feature Engine determinista y sin leakage temporal;
- separar Analytics de la lógica de decisión;
- implementar un sistema experto jerárquico y auditable;
- desarrollar un Match Rating inmediato y una capa histórica complementaria;
- construir una aplicación Streamlit Team/Player/Match;
- integrar un asistente grounded que no recalcule métricas críticas;
- permitir opcionalmente un proveedor LLM externo mediante clave del propio usuario sin darle acceso directo a DuckDB;
- generar informes PDF a partir de resultados estructurados;
- validar el sistema por capas y end-to-end;
- garantizar una demo reproducible sin redistribuir datos profesionales.

## 3.4 Preguntas de investigación y alcance de la evaluación

Las preguntas se formulan para evaluar la contribución de Ciencia de Datos e IA del prototipo, no para inferir eficacia deportiva causal.

| Pregunta | Evidencia evaluada | Alcance de la respuesta |
|---|---|---|
| **PI1.** ¿Puede una arquitectura basada en datos observables producir análisis reproducibles sin leakage temporal? | FEATURE-01/02/03, validadores strict-past, contracts de datos y demo sintética. | Viabilidad técnica y reproducibilidad del pipeline. |
| **PI2.** ¿Puede una capa de IA en lenguaje natural mantener grounding y trazabilidad sin calcular métricas críticas? | Contrato composicional, preflight, tools read-only, CI y smoke final del Coach. | Grounding técnico de las consultas soportadas; no satisfacción de usuarios ni cobertura universal del lenguaje. |
| **PI3.** ¿Puede el prototipo ofrecer un flujo integrado para equipo, jugador y partido con evidencia visible? | Collector, dashboard, PDF, capturas y QA end-to-end. | Integración funcional; no mejora causal de decisiones ni de resultados deportivos. |

La relación completa entre preguntas, evidencia y limitaciones se mantiene en `docs/TFM_EVIDENCE_MATRIX.md`. Los protocolos para evaluar fiabilidad interobservador y utilidad con staff se preparan en `docs/TFM_EVALUATION_PROTOCOLS.md`, pero no se presentan como resultados ejecutados.

---

# 4. Metodología

## 4.1 Enfoque de desarrollo

El desarrollo siguió una estrategia incremental orientada a producto. Cada capa se validó antes de utilizarla como dependencia de la siguiente.

```text
Collector / Import + GPS opcional
→ Raw / Normalized Data
→ Feature Engine
→ Analytics
→ Expert System / DS-ML
→ Product Service / Access
→ Dashboard
→ AI Assistant
→ PDF
```

La regla global fue impedir que una capa superior inventara resultados no soportados por una capa inferior.

## 4.2 Selección de variables y Collector

Las variables candidatas se filtraron por cinco criterios: observabilidad, consistencia de captura, información diferencial, utilidad posterior y coste de recogida.

La taxonomía final quedó congelada en `event_catalog v0.3.0` e incluye identificación, minutos, rol, pases, centros, regates, pérdidas, remates, defensa, faltas, tarjetas, penaltis, portero y córners/ABP.

No se recogen manualmente métricas avanzadas como xG, PPDA o fatiga.

## 4.3 Modelo de datos

DuckDB actúa como base analítica. `player_match` es la unidad principal.

El diseño separa:

```text
master data
→ raw observations
→ raw aggregates
→ features
→ analytics evidence
→ decision results
```

Esta separación facilita auditabilidad y evita almacenar interpretaciones como datos brutos.

## 4.4 Feature Engine

FEATURE-01 genera 28 features base deterministas. Los ratios y per-90 preservan valores faltantes cuando el denominador no es válido.

FEATURE-02 genera operadores temporales utilizando únicamente pasado estricto.

FEATURE-03 añade contexto temporal condicionado por rol observado y evita imputar un rol específico cuando no existe evidencia.

## 4.5 Analytics Engine

La capa analítica materializa dos contextos principales:

```text
SELF_ROLE_PRIOR
PEER_ROLE_PRIOR
```

El jugador actual se excluye del pool de peers y cada peer recibe el mismo peso. Analytics no emite recomendaciones.

## 4.6 Match Rating y Performance Index

El Match Rating V5 ofrece una valoración inmediata jugador-partido desde el primer partido. La versión activa es `match_rating_v0.5-candidate`.

El Performance Index `performance_score_v0.2-experimental` se mantiene como capa histórica y posicional complementaria.

## 4.7 Sistema experto

El sistema experto se organiza en 13 familias:

```text
N1000   disponibilidad / actividad
N2000   perfil estructural
N3000   forma / evolución
N4000   amenaza ofensiva
N5000   creación / progresión
N6000   contribución defensiva
N7000   finalización
N8000   contexto equipo
N9000   componente físico
N10000  rol / contexto
N11000  consistencia / tendencia
N12000  player-fit evidence
N13000  recommendation gate
```

N13000 puede abstenerse de recomendar cuando falta evidencia o cuando la policy no ha sido validada.

## 4.8 ML experimental

Las líneas de change detection, similitud y clasificación de posición se trataron como experimentos separados. Se priorizó un baseline simple frente a modelos más complejos cuando no existía una mejora defendible o un target independiente.

## 4.9 GPS

El GPS es opcional. Los ficheros de proveedor se normalizan a un esquema común mediante `gps_imports`, `gps_player_map` y `gps_observations`.

Posteriormente se materializa `gps_physical_summary_v0.1-descriptive`.

GPS real tiene prioridad sobre synthetic y el GPS sintético no cuenta como evidencia física observada en N9000.

## 4.10 Aplicación web

La aplicación Streamlit ofrece Team Mode, Player Mode, Match Mode, Físico/GPS, Attention Centre y Coach Copilot.

Existe control de acceso estructural SUPERADMIN/CLUB_ADMIN/STAFF, pero no autenticación completa.

## 4.11 Coach Copilot

La arquitectura final prioriza consultas deterministas y añade un preflight explícito antes del routing:

```text
QUESTION
→ PREFLIGHT / GUARDRAILS
→ DETERMINISTIC HIGH-CONFIDENCE ROUTER
→ READ-ONLY TOOLS
→ PYTHON / DUCKDB / ANALYTICS / EXPERT SYSTEM
→ STRUCTURED EVIDENCE
→ FACTUAL ANSWER
→ COACH
```

El espacio de consulta se modela como composición de `entidad + operación + métrica + agregación + rol + filtros + ventana + contexto conversacional`, en lugar de una lista de frases cerrada. El preflight resuelve localmente entradas basura, meta-consultas y preguntas claramente fuera de dominio.

Cuando la intención sigue siendo ambigua y permanece dentro del dominio, se activa un fallback semántico local:

```text
QUESTION AMBIGUA
→ QWEN3.5:4B LOCAL
→ TOOL SELECTION
→ LOCAL TOOL VALIDATION
→ READ-ONLY TOOLS
→ PYTHON / DUCKDB
→ STRUCTURED EVIDENCE
→ FACTUAL ANSWER
```

La aplicación incorpora además un modo opcional `OpenAI API · clave propia`. En este modo, las consultas claras siguen la ruta determinista y no consumen API. Solo el lenguaje ambiguo puede utilizar OpenAI para seleccionar herramientas y, cuando es necesario, sintetizar una respuesta a partir de evidencia JSON. Las llamadas de herramientas externas se revalidan localmente y ninguna capa LLM recibe acceso directo a DuckDB.

Las comparaciones por posición están soportadas de forma determinista. Si se pregunta quién ha rendido mejor dentro de una posición, el sistema declara como criterio de ordenación el Match Rating medio dentro de la muestra de ese rol y muestra el resto de métricas como evidencia descriptiva; no crea un score nuevo.

Los guardrails bloquean inferencias no validadas como fatiga, riesgo de lesión, XI ideal, recomendaciones tácticas o conceptos globales como «mejor jugador», «más completo» o «más determinante» cuando no existe una definición analítica aprobada.

## 4.12 Informes PDF

Los PDF Team/Player/Match consumen resultados materializados. No recalculan Match Rating, Performance Index ni decisiones expertas.

## 4.13 Validación

Cada capa dispone de tests y validators específicos. Posteriormente se ejecutó QA end-to-end dividido en Data/Core, Analytics/Expert, Product y Delivery.

El Coach Copilot se valida en dos niveles complementarios: un query-space contract reproducible en CI sobre la demo sintética y un smoke real sobre la DuckDB profesional. El smoke final contiene 28 casos que cubren rankings, perfiles, GPS, comparación entre jugadores, comparación por posición, partido, calidad, guardrails, ruido/fuera de dominio y follow-ups encadenados.

La validación técnica responde directamente a PI1, PI2 y PI3. Se distingue de forma explícita de la validación empírica con observadores o staff: esta última requeriría recogida de datos adicional y queda definida como protocolo, no como resultado del presente trabajo.

## 4.14 Reproducibilidad

La base profesional no se redistribuye. Se construyó una demo sintética desde cero y GitHub Actions ejecuta automáticamente tests, reconstrucción de la demo y validación del query-space del Coach Copilot en un entorno limpio.

---

# 5. Arquitectura e implementación

La arquitectura general se representa en `docs/figures/tfm_architecture_overview.svg`.

El modelo de datos simplificado se representa en `docs/figures/tfm_data_model.svg`.

El control temporal `strict-past` se representa en `docs/figures/tfm_strict_past.svg`.

La jerarquía del experto se representa en `docs/figures/tfm_expert_system.svg`.

La separación del Coach Copilot se representa en `docs/figures/tfm_llm_grounding.svg`.

Estas figuras muestran diseño e implementación; no constituyen por sí mismas evidencia de eficacia deportiva.

---

# 6. Resultados

## 6.1 Caso profesional de desarrollo

El caso utilizado para validar el producto contiene:

```text
38 partidos
36 jugadores en contexto producto
590 apariciones jugadas
```

La validación de base de datos cerró sin duplicados críticos, minutos inválidos u orphan events.

## 6.2 Feature Engine

FEATURE-01:

```text
28 features base
23.380 filas
6.324 valores no nulos
PASS
```

FEATURE-02:

```text
28 × 7 operadores temporales
163.660 filas
strict-past PASS
```

FEATURE-03:

```text
117.735 filas
43.060 valores no nulos
590/835 player-match con rol observado
PASS
```

## 6.3 Analytics

```text
46.760 filas
SELF_ROLE_PRIOR + PEER_ROLE_PRIOR
strict-past PASS
current-player exclusion PASS
equal-player weighting PASS
```

## 6.4 Sistema experto

```text
engine_version=expert_0.7.0
decision_rows=154.475
N13000_rows=2.505
```

Estados relevantes:

```text
NO_EVIDENCE=89
POLICY_UNVALIDATED=501
ROLE_UNKNOWN=245
```

El sistema conserva evidencia y puede abstenerse de emitir recomendaciones.

## 6.5 Match Rating V5

```text
coverage=590/590
matches=38
outfield PERF18_ANCHORED=380
goalkeeper route=38
generic role fallback=172
nulls=0
duplicates=0
out_of_range=0
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

Estos datos demuestran cobertura técnica, no validez universal externa.

## 6.6 GPS

La demo de integración produjo:

```text
generator_version=gps_synthetic_demo_v1.2.0
imports=38
mappings=590
observations=38.197
summaries/latest=590
REAL_OVER_SYNTHETIC=PASS
```

No existen observaciones GPS reales no sintéticas utilizadas por N9000 en el cierre actual del QA.

## 6.7 Producto

Los principales gates de producto cerraron en PASS:

```text
DASHBOARD-01 DATA CONTRACT
STREAMLIT UI COMPATIBILITY
DEMO PRESENTATION
ACCESS CONTROL
ATTENTION FLAGS
MATCH MODE
```

La demo pública mantiene identidades anónimas coherentes (`Equipo Demo`, `Jugador XX`, `Rival XX`) también en la capa conversacional del Assistant.

## 6.8 Coach Copilot

La arquitectura final se validó sobre la DuckDB profesional mediante `llm/smoke_test_coach_agent.py`.

Resultado real del smoke final:

```text
SMOKE CONTRACT: PASS (28/28)
average_elapsed=0.4s
final semantic rounds=0 en todos los casos
```

La batería cubre:
- Match Rating más reciente;
- Match Rating medio últimos cinco;
- distancia media por partido;
- top de remates;
- asistencias;
- evolución y perfil natural de jugador;
- GPS;
- comparación entre jugadores;
- comparación de delanteros;
- comparación de centrales con criterio explícito;
- detalle de partido;
- estado del equipo;
- calidad de datos;
- guardrails de fatiga, lesión y titularidad;
- criterios globales no validados;
- pregunta fuera de dominio;
- entrada basura y meta-consulta;
- follow-ups ordinales, ventana temporal, evidencia y comparación por posición.

Los 28 casos finales pudieron resolverse sin activar el fallback Qwen. La media de 0,4 s corresponde únicamente a esta batería en el PC de desarrollo; no constituye un SLA universal ni mide la latencia de consultas ambiguas que sí requieran inferencia semántica. El modelo `qwen3.5:4b` se conserva como fallback para ese caso residual.

El modo OpenAI con clave propia del usuario también dispone de tests contractuales y CI: la superficie de herramientas externas coincide con las tools FPS permitidas, los argumentos se revalidan localmente y una tool desconocida se descarta. No se ha realizado todavía una validación live con una API key real, por lo que no se reporta latencia ni calidad live de ese modo.

## 6.9 Informes PDF

```text
Team=4 páginas
Player=3 páginas
Match=3 páginas
REPORTS ELITE TECHNICAL GATE V6=PASS
```

## 6.10 QA end-to-end

```text
Fase 1 — Data/Core          PASS
Fase 2 — Analytics/Expert   PASS
Fase 3A — Product           PASS
Fase 3B — Delivery          PASS
GLOBAL END-TO-END QA        PASS
```

## 6.11 Demo pública sintética

```text
demo_version=synthetic_public_demo_v0.1.0
matches=12
players=18
player_match=216
played=192
FEATURE-01=6.048
FEATURE-02=42.336
FEATURE-03=30.456
analytics_rows=12.096
expert_rows=39.960
N13000=648
ratings=192
performance_index=192
gps=192
professional_source_rows=0
app_read_layer=PASS
report_payloads=PASS
redistribution_status=REDISTRIBUTABLE_SYNTHETIC_DEMO
```

## 6.12 Integración continua

GitHub Actions ejecuta automáticamente instalación, tests, reconstrucción de la demo sintética y validación del query-space del Coach Copilot.

Runs de referencia del cierre:

```text
37167083614 = SUCCESS — query-space + preflight contract
37167157174 = SUCCESS — code gate previo al smoke local final
37168110570 = SUCCESS — documentación/defensa sincronizada sobre la arquitectura final
```

El smoke 28/28 es un gate local adicional sobre la DuckDB profesional; el CI usa la demo sintética para garantizar regresión reproducible desde un entorno limpio.

---

# 7. Discusión

## 7.1 Viabilidad general

Los resultados muestran que es técnicamente viable integrar captura, almacenamiento, feature engineering, analítica, sistema experto, dashboard, LLM y reporting en un producto único orientado a un contexto sin infraestructura profesional.

El principal valor no es una métrica aislada, sino la trazabilidad entre dato, cálculo, evidencia y explicación.

## 7.2 Collector y coste de captura

Limitar el Collector a hechos observables reduce complejidad y aproxima el sistema al contexto objetivo. Esta decisión es coherente con la literatura observacional, aunque sigue pendiente una evaluación formal de fiabilidad interobservador.

## 7.3 Auditabilidad

La separación raw → features → analytics → decisión permite corregir una capa sin alterar el resto del sistema. Esta modularidad también facilita identificar si una conclusión procede de datos observados o de una inferencia posterior.

## 7.4 Leakage

La política `strict-past` reduce el riesgo de que tendencias históricas utilicen información futura. Este control mejora la validez temporal, aunque no demuestra por sí mismo que cada feature sea deportivamente relevante.

## 7.5 Match Rating

La cobertura completa resuelve una necesidad de producto, pero no debe confundirse con validación científica universal. V5 debe considerarse una herramienta interna congelada a la espera de validación externa.

## 7.6 Sistema experto

La capacidad de abstenerse es una propiedad importante. N13000 no fuerza recomendaciones cuando falta evidencia o policy. Esto limita funcionalidad inmediata, pero evita presentar inferencias no validadas como decisiones tácticas.

## 7.7 ML

El trabajo muestra que ML no debe incorporarse únicamente para aumentar complejidad académica. Su uso queda condicionado a disponer de targets independientes y a superar baselines simples de forma defendible.

## 7.8 GPS

El sistema demuestra integración GPS, no validación fisiológica. La decisión de no inferir fatiga o lesión a partir de una demo sintética es coherente con las limitaciones descritas por la literatura.

## 7.9 Coach Copilot

El asistente demuestra que una interfaz de lenguaje natural puede mantenerse downstream de un motor analítico sin trasladar cálculos críticos al LLM. La evolución del prototipo también mostró que depender de un modelo local para cada consulta penalizaba latencia y robustez. La arquitectura final resuelve primero el espacio de consultas mediante reglas composicionales —entidad, operación, métrica, agregación, rol, filtros, ventana y follow-up—, incorpora preflight determinista y reserva el LLM para interpretación semántica cuando es realmente necesario.

Este enfoque produjo 28/28 casos correctos en el smoke real final y una latencia media de 0,4 segundos en esa batería concreta. Todos los casos finales utilizaron `rounds=0`, de modo que el resultado cuantifica la ruta determinista/preflight y no la latencia del fallback Qwen. Las consultas ambiguas que sí requieran un modelo local pueden seguir siendo considerablemente más lentas en CPU.

La integración OpenAI BYOK amplía opcionalmente la interfaz sin cambiar la arquitectura de grounding: el proveedor externo no recibe acceso directo a DuckDB y las tool calls se revalidan localmente. Al no existir todavía prueba live con una clave real, esta extensión se presenta como implementación técnicamente integrada pero no como benchmark empírico de latencia o calidad externa.

## 7.10 Reproducibilidad

La demo sintética separa software reproducible de redistribución de datos profesionales. Esta distinción permite que el repositorio sea evaluable sin vulnerar derechos de terceros.

## 7.11 Contraste de la hipótesis

La hipótesis queda contrastada favorablemente en su dimensión técnica y arquitectónica porque existe un pipeline funcional, auditable, versionado y reproducible.

No queda demostrado un impacto causal sobre decisiones de entrenadores, resultados deportivos o prevención de lesiones.

En términos de preguntas de investigación, PI1 queda respaldada por los contratos de datos, los validadores strict-past y la reconstrucción de la demo; PI2 por el contrato composicional y el smoke/CI del Coach; y PI3 por el flujo integrado Collector–dashboard–PDF y sus gates end-to-end. Ninguna de estas respuestas sustituye un estudio de uso con staff ni una validación externa del Match Rating.

---

# 8. Limitaciones

Las principales limitaciones son:

1. ausencia de validación formal con entrenadores/analistas reales;
2. ausencia de estudio interobservador del Collector;
3. Match Rating sin ground truth universal independiente;
4. ausencia de GPS real no sintético en la evidencia N9000 utilizada para cerrar el QA;
5. N13000 sin policy validada de rol óptimo o XI ideal;
6. autenticación real no implementada;
7. derechos de redistribución del dataset profesional no resueltos;
8. demo sintética válida para integración, no para validación fisiológica o deportiva;
9. fallback Qwen potencialmente lento en consultas realmente ambiguas sobre CPU;
10. modo OpenAI BYOK con validación contractual y CI, pero sin benchmark live con una API key real.

---

# 9. Conclusiones

El TFM demuestra que es posible construir un sistema funcional, auditable y reproducible de análisis de rendimiento para fútbol amateur o semiprofesional a partir de vídeo, datos estructurados y GPS opcional.

Las principales contribuciones son:

- Collector orientado a hechos observables;
- modelo de datos jugador-partido;
- Feature Engine temporalmente seguro;
- Analytics independiente de decisión;
- sistema experto N1000-N13000;
- Match Rating inmediato;
- Performance Index separado y experimental;
- GPS descriptivo opcional;
- aplicación Team/Player/Match;
- Coach Copilot grounded con preflight, router determinista y fallback semántico local;
- comparaciones por posición con criterio explícito y sin score nuevo;
- integración OpenAI BYOK opcional sin acceso directo a DuckDB;
- informes PDF;
- QA end-to-end;
- demo pública sintética;
- CI automático.

La conclusión central es:

> **La propuesta es técnicamente viable, funcional y reproducible como arquitectura de soporte al análisis de rendimiento. Su impacto real sobre decisiones de entrenadores y rendimiento deportivo requiere validación adicional con usuarios, datos reales adicionales y ground truth independiente.**

---

# 10. Trabajo futuro

Las siguientes mejoras deben priorizar evidencia antes que complejidad:

1. estudio de fiabilidad interobservador del Collector;
2. validación con entrenadores/analistas;
3. incorporación y validación de GPS real;
4. validación externa del Match Rating;
5. policy validada para N13000;
6. comparación experto vs ML con ground truth independiente;
7. automatización parcial del Collector mediante visión artificial si reduce coste real de captura;
8. autenticación completa y despliegue solo cuando los derechos estén resueltos;
9. validación live y comparación de proveedores externos del asistente solo si aporta valor al producto;
10. posible exposición futura de las tools mediante un protocolo estándar, sin convertirla en dependencia del MVP.

---

# Referencias

Hader, K., Rumpf, M. C., Hertzog, M., Kilduff, L. P., Girard, O., & Silva, J. R. (2019). Monitoring the Athlete Match Response: Can External Load Variables Predict Post-match Acute and Residual Fatigue in Soccer? A Systematic Review with Meta-analysis. *Sports Medicine - Open, 5*, 48. https://doi.org/10.1186/s40798-019-0219-7

Huang, L., Yu, W., Ma, W., Zhong, W., Feng, Z., Wang, H., Chen, Q., Peng, W., Feng, X., Qin, B., & Liu, T. (2025). A Survey on Hallucination in Large Language Models: Principles, Taxonomy, Challenges, and Open Questions. *ACM Transactions on Information Systems, 43*(2), Article 42. https://doi.org/10.1145/3703155

James, N. (2006). Notational analysis in soccer: past, present and future. *International Journal of Performance Analysis in Sport, 6*(2), 67–81. https://doi.org/10.1080/24748668.2006.11868373

Kaufman, S., Rosset, S., Perlich, C., & Stitelman, O. (2012). Leakage in data mining: Formulation, detection, and avoidance. *ACM Transactions on Knowledge Discovery from Data, 6*(4), Article 15. https://doi.org/10.1145/2382577.2382579

Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., Küttler, H., Lewis, M., Yih, W.-t., Rocktäschel, T., Riedel, S., & Kiela, D. (2020). Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. *Advances in Neural Information Processing Systems, 33*.

Liu, H., Gegov, A., & Cocea, M. (2016). Rule-based systems: a granular computing perspective. *Granular Computing, 1*, 259–274. https://doi.org/10.1007/s41066-016-0021-6

Mackenzie, R., & Cushion, C. (2013). Performance analysis in football: A critical review and implications for future research. *Journal of Sports Sciences, 31*(6), 639–676. https://doi.org/10.1080/02640414.2012.746720

Miguel, M., Oliveira, R., Loureiro, N., García-Rubio, J., & Ibáñez, S. J. (2021). Load Measures in Training/Match Monitoring in Soccer: A Systematic Review. *International Journal of Environmental Research and Public Health, 18*(5), 2721. https://doi.org/10.3390/ijerph18052721

Ortega-Toro, E., García-Angulo, A., Giménez-Egido, J. M., García-Angulo, F. J., & Palao, J. M. (2019). Design, Validation, and Reliability of an Observation Instrument for Technical and Tactical Actions of the Offense Phase in Soccer. *Frontiers in Psychology, 10*, 22. https://doi.org/10.3389/fpsyg.2019.00022

Rudin, C. (2019). Stop explaining black box machine learning models for high stakes decisions and use interpretable models instead. *Nature Machine Intelligence, 1*, 206–215. https://doi.org/10.1038/s42256-019-0048-x

Sandve, G. K., Nekrutenko, A., Taylor, J., & Hovig, E. (2013). Ten Simple Rules for Reproducible Computational Research. *PLoS Computational Biology, 9*(10), e1003285. https://doi.org/10.1371/journal.pcbi.1003285

Sarmento, H., Marcelino, R., Anguera, M. T., Campaniço, J., Matos, N., & Leitão, J. C. (2014). Match analysis in football: a systematic review. *Journal of Sports Sciences, 32*(20), 1831–1843. https://doi.org/10.1080/02640414.2014.898852

Sarmento, H., Clemente, F. M., Afonso, J., Araújo, D., Fachada, M., Nobre, P., & Davids, K. (2022). Match Analysis in Team Ball Sports: An Umbrella Review of Systematic Reviews and Meta-Analyses. *Sports Medicine - Open, 8*, 66. https://doi.org/10.1186/s40798-022-00454-7

Schick, T., Dwivedi-Yu, J., Dessì, R., Raileanu, R., Lomeli, M., Hambro, E., Zettlemoyer, L., Cancedda, N., & Scialom, T. (2023). Toolformer: Language Models Can Teach Themselves to Use Tools. *Advances in Neural Information Processing Systems, 36*, 68539–68551.

Scott, M. T. U., Scott, T. J., & Kelly, V. G. (2016). The Validity and Reliability of Global Positioning Systems in Team Sport: A Brief Review. *Journal of Strength and Conditioning Research, 30*(5), 1470–1490. https://doi.org/10.1519/JSC.0000000000001221

---

# Material pendiente para versión final

- adaptar portada, índice y extensión a la plantilla oficial;
- convertir figuras SVG al formato exigido si es necesario;
- integrar en la maquetación las capturas reales ya disponibles en `docs/screenshots/`;
- seleccionar qué tablas quedan en cuerpo y cuáles pasan a anexos;
- revisar estilo bibliográfico final;
- añadir numeración cruzada de figuras/tablas;
- maquetar anexos;
- revisión lingüística final.
