# TFM — Football Performance System

## Borrador técnico base de la memoria

Estado: borrador académico de trabajo.
Idioma: castellano.
Fuente de verdad técnica: `PROJECT_STATE.md` + código actual de `main`.

> Este documento no sustituye la plantilla formal de la universidad. Su función es fijar una narrativa académica coherente con el producto realmente construido y evitar introducir afirmaciones que el repositorio no pueda demostrar.

---

## Título provisional

**Diseño e implementación de un sistema auditable de análisis del rendimiento futbolístico para equipos amateur y semiprofesionales mediante vídeo, GPS opcional, analítica de datos, sistema experto e inteligencia artificial**

## Resumen provisional

Este Trabajo Final de Máster desarrolla un sistema integral de análisis de rendimiento orientado a equipos de fútbol amateur y semiprofesionales que no disponen de un departamento de análisis propio. El objetivo no es reproducir plataformas profesionales de tracking o proveedores comerciales de eventos, sino demostrar que un conjunto reducido de datos observables de vídeo y GPS opcional puede transformarse en información estructurada, auditable y útil para el cuerpo técnico.

La solución implementa una arquitectura por capas que separa datos brutos, variables derivadas, analítica, sistema experto, presentación y generación de lenguaje. El flujo principal parte de un Data Collector HTML y de una capa opcional de normalización GPS, almacena la información en DuckDB, construye features deterministas y temporalmente seguras, genera evidencia analítica, aplica un sistema experto jerárquico N1000-N13000, presenta los resultados en una aplicación Streamlit e incorpora un asistente local mediante Ollama. Los informes PDF se generan exclusivamente a partir de resultados estructurados ya calculados.

La validación técnica del prototipo se ha realizado mediante contratos de datos, tests unitarios, validadores por capa, pruebas end-to-end y un pipeline de integración continua. El sistema principal supera el QA global y se ha construido además una demo pública sintética reproducible que puede generarse desde un entorno limpio sin depender de la base de datos profesional utilizada durante el desarrollo. El trabajo demuestra la viabilidad técnica y arquitectónica de la propuesta, pero no pretende demostrar un efecto causal sobre la calidad de las decisiones de un entrenador, el rendimiento deportivo ni la prevención de lesiones.

---

# 1. Introducción

## 1.1 Problema

Los clubes profesionales pueden recurrir a proveedores especializados de eventos, tracking, GPS, vídeo y scouting. En fútbol amateur y semiprofesional, sin embargo, el coste económico y operativo de estas soluciones limita su adopción. Muchos cuerpos técnicos disponen de vídeo del partido y, en algunos casos, GPS, pero no de una infraestructura que transforme esas fuentes en una base histórica consistente y en información directamente consultable.

El problema abordado por este TFM es, por tanto, de **accesibilidad analítica**: cómo diseñar un sistema suficientemente útil y riguroso para apoyar el análisis de rendimiento sin exigir una infraestructura de captura profesional ni introducir métricas cuya recogida manual sea inviable durante un partido de 90 minutos.

## 1.2 Enfoque adoptado

El proyecto prioriza un MVP funcional basado en cuatro principios:

1. recoger únicamente hechos observables y razonablemente registrables;
2. separar estrictamente raw data, features, analytics, decisiones y lenguaje natural;
3. evitar data leakage, inferencias no justificadas y recomendaciones sin política validada;
4. hacer que cada resultado relevante pueda rastrearse hasta datos y reglas auditables.

El producto principal es una aplicación web. Los PDF son salidas complementarias y el LLM actúa únicamente como capa de interacción y explicación.

---

# 2. Hipótesis y objetivos

## 2.1 Hipótesis principal

> **Un equipo de fútbol amateur o semiprofesional puede disponer de un sistema integral y auditable de soporte al análisis a partir de datos de vídeo y GPS opcional, capaz de transformar hechos observables en información trazable sobre rendimiento, evolución y rol; cuando existe GPS observado, puede añadir variables físicas descriptivas.**

La hipótesis se interpreta en este TFM como una hipótesis de **viabilidad técnica y arquitectónica**. No se formula como una prueba causal de mejora deportiva.

## 2.2 Objetivo general

Diseñar, implementar y validar un sistema reproducible que transforme datos simples de vídeo y GPS opcional en información estructurada para el análisis de equipo, jugador y partido.

## 2.3 Objetivos específicos

- diseñar un Data Collector adecuado al contexto amateur;
- definir un modelo de datos con unidad principal jugador-partido;
- normalizar GPS de múltiples proveedores en un esquema común;
- construir un Feature Engine determinista y sin leakage temporal;
- construir una capa de Analytics separada de la lógica de decisión;
- implementar un sistema experto jerárquico y auditable;
- desarrollar un Match Rating inmediato y una capa histórica complementaria;
- construir una aplicación Streamlit con Team, Player y Match Mode;
- incorporar un asistente IA local que no recalcule métricas críticas;
- generar informes PDF a partir de resultados estructurados;
- validar el sistema por capas y end-to-end;
- garantizar una vía de demostración reproducible sin redistribuir datos profesionales no autorizados.

---

# 3. Metodología de desarrollo

El proyecto sigue un enfoque incremental orientado a producto. Cada capa se cierra antes de utilizarla como dependencia de la siguiente.

La secuencia implementada es:

```text
Collector / Import + GPS opcional
→ Raw / Normalized Data
→ Feature Engine
→ Analytics
→ Expert System / DS-ML
→ Product Service / Access Layer
→ Dashboard
→ AI Assistant
→ PDF
```

La regla central del sistema es que **una capa superior no puede inventar cálculos, métricas, rankings o recomendaciones que no existan en una capa inferior validada**.

Las decisiones metodológicas relevantes son:

- variables manuales limitadas a acciones observables;
- preservación explícita de valores faltantes;
- separación entre evidencia descriptiva y juicio evaluativo;
- baselines temporales construidos exclusivamente con pasado estricto;
- modelos complejos solo si superan alternativas simples;
- ausencia de recomendaciones tácticas cuando no existe una policy validada;
- GPS sintético separado de evidencia física real;
- LLM downstream y sin acceso directo a la base de datos.

---

# 4. Data Collector y variables observables

El Data Collector oficial es una aplicación HTML diseñada para registrar hechos observables durante o después del partido. La taxonomía está congelada en `event_catalog v0.3.0`.

Las principales familias registradas son:

- identificación: jugador, dorsal, titular/suplente, minutos;
- contexto: partido, equipo, rival, fecha, formación, rol, lado y cambios de rol;
- pase: normal, largo y centro con éxito/fallo, pase clave y asistencia;
- progresión y 1v1: regate y pérdida;
- finalización: remate, a puerta, bloqueado y gol;
- defensa: entrada, intercepción, bloqueo y despeje;
- disciplina: faltas, tarjetas y penaltis;
- portero: paradas y goles encajados;
- balón parado: córner a favor/en contra y resultado posterior de la secuencia.

El Collector no calcula xG, posesión avanzada, PPDA, pressing, heatmaps ni otras métricas difíciles de capturar manualmente de forma consistente.

La validación final del Collector V1.1 cerró correctamente sus contratos funcionales, de taxonomía, labels y comportamiento responsive.

---

# 5. Modelo de datos

El sistema utiliza DuckDB y adopta `player_match` como unidad analítica principal.

Las entidades principales son:

```text
team
match
player
player_match
player_role_stints
match_events
player_match_raw_stats
gps_imports
gps_player_map
gps_observations
player_match_features
analytics_evidence
decision_results
```

Esta separación permite distinguir:

- información maestra;
- hechos observados;
- estadísticas raw agregadas;
- variables derivadas;
- evidencia analítica;
- decisiones expertas.

El diseño evita almacenar como raw aquello que en realidad es una interpretación o una métrica derivada.

---

# 6. Feature Engine

El Feature Engine transforma estadísticas raw en variables analíticas mediante lógica determinista.

## 6.1 FEATURE-01

Contiene 28 features base. Incluye ratios y normalizaciones per-90. Los `NULL` se preservan y un denominador no válido no se convierte automáticamente en cero.

## 6.2 FEATURE-02

Construye operadores temporales sobre las features base utilizando exclusivamente partidos con fecha estrictamente anterior al partido actual.

No existe información futura ni contaminación entre partidos de la misma fecha.

## 6.3 FEATURE-03

Añade contexto temporal condicionado por el rol observado del jugador. Cuando el rol no está disponible, el sistema no lo inventa.

Esta estructura permite analizar evolución y contexto histórico sin mezclar información futura con el presente.

---

# 7. Analytics Engine

La capa `ANALYTICS-01` produce evidencia descriptiva independiente de la decisión final.

Se separan dos contextos:

- `SELF_ROLE_PRIOR`: historial previo del propio jugador en su rol;
- `PEER_ROLE_PRIOR`: comparación con compañeros del mismo rol utilizando únicamente pasado estricto.

El jugador actual queda excluido del pool de peers y cada peer recibe el mismo peso. La capa analítica puede calcular diferencias, medias o tendencias, pero no emite por sí misma etiquetas de “bueno/malo”, rankings ni recomendaciones.

---

# 8. Sistema experto N1000-N13000

El sistema experto se organiza como una jerarquía modular:

```text
N1000   disponibilidad / actividad
N2000   perfil estructural
N3000   forma / evolución
N4000   amenaza ofensiva
N5000   creación / progresión
N6000   contribución defensiva
N7000   finalización
N8000   contexto del equipo
N9000   componente físico
N10000  rol y contexto
N11000  consistencia / tendencia
N12000  player-fit evidence
N13000  recommendation gate
```

Cada nodo conserva el patrón:

```text
entrada → condición → resultado → confianza → justificación
```

La finalidad del árbol no es replicar un `DecisionTreeClassifier`, sino ofrecer una arquitectura de reglas auditables que pueda crecer de forma modular.

N13000 constituye un gate de seguridad. Aunque exista evidencia de rol, no se emite una recomendación táctica si no se ha validado previamente una política de recomendación, sus pesos y sus umbrales.

---

# 9. Match Rating y Performance Index

## 9.1 Match Rating V5

El Match Rating es una valoración inmediata jugador-partido disponible desde el primer partido.

Versión activa:

```text
match_rating_v0.5-candidate
```

Baseline validado:

- 590/590 apariciones con rating;
- 38/38 partidos;
- 380 apariciones de campo con ruta `PERF18_ANCHORED`;
- 38 apariciones de portero con ruta específica;
- 172 apariciones con fallback explícito cuando no existe rol fiable;
- 0 valores nulos;
- 0 duplicados;
- 0 valores fuera de rango.

La fórmula V5 está congelada y no debe modificarse sin nueva evidencia y validación experimental.

## 9.2 Performance Index

Versión:

```text
performance_score_v0.2-experimental
```

Es una capa histórica y posicional complementaria destinada a evolución, forma, consistencia y contexto de rol. No sustituye al Match Rating y mantiene su carácter experimental.

---

# 10. GPS opcional

El sistema no exige GPS para funcionar.

La normalización canónica utiliza:

```text
gps_imports
gps_player_map
gps_observations
```

La capa física descriptiva genera `player_match_gps_summary` mediante `gps_physical_summary_v0.1-descriptive`.

La precedencia de fuentes es explícita:

```text
GPS real observado > GPS sintético
```

El GPS sintético se utiliza para probar integración, UI y contratos, pero se excluye de la evidencia física experta en N9000.

No se han definido umbrales canónicos de HSR, sprint, carga, fatiga, readiness o riesgo de lesión. Por ello, el sistema no realiza estas inferencias.

---

# 11. Aplicación web

La aplicación Streamlit es el producto principal.

## 11.1 Team Mode

Permite consultar estado del equipo, plantilla, forma, participación, Match Rating, Performance Index, evolución, tendencias descriptivas, evidencia experta y GPS opcional.

## 11.2 Player Mode

Permite consultar perfil individual, historial de Match Ratings, Performance Index, dimensiones, evolución, rol observado, evidencia experta, GPS y PDF.

## 11.3 Match Mode

Funciona desde el primer partido y presenta ratings, confianza, minutos, roles, observaciones deterministas, GPS y exportación PDF.

## 11.4 Attention Centre

Las alertas se limitan a estados auditables de calidad o contexto. No se generan alertas de fatiga, riesgo de lesión o rendimiento bueno/malo sin una regla validada.

---

# 12. Coach Copilot

El asistente local sigue la arquitectura:

```text
DATA
→ ANALYTICS
→ DECISION ENGINE
→ READ-ONLY TOOLS
→ ROUTER
→ OLLAMA
→ SEMANTIC GUARD
→ COACH
```

Modelo MVP:

```text
qwen3:1.7b
scope=SPANISH_ONLY_MVP
thinking=False
num_ctx=1536
timeout=18s
```

El LLM no accede directamente a DuckDB, no recalcula métricas críticas y no puede sustituir al motor analítico.

El gate de evaluación previo alcanzó 66/68 casos correctos (97,1%), sin errores de runtime ni fallos de seguridad. La limitación aceptada fueron dos casos que superaron el límite formal de frases.

El smoke test final local del contrato del agente terminó en `PASS (4/4)`.

---

# 13. Informes PDF

Los PDF son exportaciones estáticas y no el producto principal.

Versión activa:

```text
Team   4 páginas
Player 3 páginas
Match  3 páginas
```

Los informes consumen datos y analytics ya materializados. No recalculan Match Rating, Performance Index ni decisiones expertas.

---

# 14. Validación

La validación se diseñó por capas.

## 14.1 QA funcional y de datos

Se validaron Collector, esquema de datos, features, analytics, Match Rating, GPS, sistema experto, dashboard, access control, asistente y reports.

Resultado global:

```text
GLOBAL END-TO-END QA: PASS
```

## 14.2 Reproducibilidad pública

El dataset profesional de desarrollo no se redistribuye automáticamente. Para evitar que el producto dependa de una base privada, se creó una demo pública 100% sintética generada desde cero.

Gate validado:

```text
SYNTHETIC PUBLIC DEMO CONTRACT: PASS
professional_source_rows=0
redistribution_status=REDISTRIBUTABLE_SYNTHETIC_DEMO
app_read_layer=PASS
report_payloads=PASS
```

La demo contiene 12 partidos, 18 jugadores, 216 filas `player_match` y 192 apariciones jugadas.

Match Rating y Performance Index de esta demo son fixtures sintéticos de compatibilidad para probar el producto; no se presentan como revalidación científica de los modelos calibrados en el caso profesional.

## 14.3 Integración continua

GitHub Actions ejecuta automáticamente en cada `push` y `pull_request`:

1. instalación de dependencias;
2. tests unitarios y de contratos;
3. construcción completa de la demo pública sintética;
4. validación del contrato reproducible.

La ejecución validada tras configurar correctamente `PYTHONPATH` terminó en `SUCCESS`.

---

# 15. Resultados principales

El resultado principal del TFM es un producto end-to-end funcional y auditable.

Se ha demostrado técnicamente que:

- una taxonomía reducida puede alimentar una arquitectura analítica completa;
- el historial temporal puede construirse evitando leakage;
- la evidencia descriptiva y la decisión pueden permanecer separadas;
- un sistema experto jerárquico puede degradar explícitamente cuando faltan datos;
- GPS puede ser opcional y no bloquear el funcionamiento del producto;
- un LLM local puede utilizar outputs estructurados sin convertirse en el motor de cálculo;
- el sistema puede generar dashboard, consultas asistidas e informes desde una misma capa analítica;
- el repositorio puede reconstruir una demo funcional desde un entorno limpio sin utilizar datos profesionales privados.

---

# 16. Limitaciones

Las principales limitaciones son:

- el caso profesional empleado en desarrollo no puede considerarse automáticamente redistribuible;
- no existe validación causal de mejora de decisiones del entrenador;
- no se ha realizado validación con una muestra real de entrenadores o analistas;
- el GPS disponible para la demo es sintético y no valida comportamiento fisiológico;
- no existe ground truth suficiente para validar recomendaciones tácticas N13000;
- Performance Index mantiene estado experimental;
- no se validan ranking por rol, player similarity operativa, XI ideal, predicción futura, fatiga, readiness o lesión;
- el control de acceso está implementado a nivel estructural, pero no existe autenticación comercial completa.

Estas limitaciones se mantienen explícitas para evitar sobreinterpretar el alcance del prototipo.

---

# 17. Conclusiones

El proyecto confirma la viabilidad técnica de construir un sistema integral de análisis de rendimiento para contextos con recursos limitados sin depender de una infraestructura profesional de tracking.

La principal aportación no es una única métrica, sino una arquitectura completa y auditable que conecta recogida de datos, almacenamiento, feature engineering, análisis temporal, sistema experto, GPS opcional, visualización, asistente IA e informes.

La separación estricta entre cálculo analítico y generación de lenguaje permite incorporar IA generativa sin delegarle decisiones críticas. Del mismo modo, la existencia de gates y estados de evidencia evita transformar automáticamente falta de datos en recomendaciones no justificadas.

Por tanto, la hipótesis principal queda apoyada en su dimensión de viabilidad técnica y arquitectónica mediante un prototipo funcional, validado y reproducible. Queda fuera del alcance demostrar que su uso mejora causalmente las decisiones técnicas o el rendimiento deportivo.

---

# 18. Trabajo futuro

Las extensiones prioritarias, condicionadas a disponer de datos y validación suficientes, son:

- validación con entrenadores y analistas reales;
- incorporación de GPS real de distintos proveedores;
- política validada de recomendación para N13000;
- comparación Expert System vs ML en tareas con ground truth defendible;
- automatización parcial del Collector mediante visión por computador;
- autenticación real y despliegue multi-club;
- Rival Mode si se dispone de datos fiables del rival.

No se recomienda ampliar estas líneas antes de cerrar la memoria, defensa y evaluación académica del MVP actual.

---

# 19. Anexos previstos

- A. Taxonomía del Collector V1.1;
- B. Esquema de datos;
- C. Catálogo de features;
- D. Familias N1000-N13000;
- E. Contrato Match Rating V5;
- F. Contrato GPS;
- G. Arquitectura del Coach Copilot;
- H. Matriz de validaciones y gates;
- I. Instrucciones de reproducción de la demo sintética;
- J. Capturas del dashboard y ejemplos de informes PDF.
