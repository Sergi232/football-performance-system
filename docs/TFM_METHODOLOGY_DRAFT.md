# TFM — Borrador integrado de metodología

Fecha: 04/10/2026
Estado: borrador académico para integrar en la memoria final.
Idioma: castellano.

Este capítulo describe cómo se diseñó, implementó y validó el Football Performance System. La metodología se formula a partir del producto realmente construido y de los contratos técnicos registrados en el repositorio. No introduce funcionalidades ni resultados que no existan en `main`.

---

# 1. Enfoque metodológico general

El proyecto se desarrolló como un sistema de soporte al análisis orientado a fútbol amateur y semiprofesional, con una restricción central: las variables de entrada debían ser razonablemente obtenibles a partir de vídeo sin requerir una infraestructura profesional de tracking. El GPS se trató como fuente opcional de variables descriptivas, no como evidencia fisiológica si no procedía de una observación real.

El desarrollo siguió un enfoque incremental por capas:

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

La regla metodológica principal fue que una capa superior no podía inventar métricas, scores, rankings o recomendaciones que no estuvieran respaldados por una capa inferior validada.

El trabajo se dividió en cuatro tipos de actividad:

1. definición y captura de datos;
2. transformación analítica;
3. construcción de reglas/modelos;
4. validación funcional y reproducibilidad.

---

# 2. Definición de variables y Data Collector

El puente first-party se valida mediante el contrato `Collector HTML → JSON → importer → DuckDB`. JSON V1.1 es el formato oficial porque conserva metadatos, plantilla, minutos, rol/lado, stints y eventos; CSV queda como export auxiliar. El importer valida catálogo y estructura y no calcula features ni métricas avanzadas.

La selección de variables se realizó aplicando cinco filtros:

1. que la acción fuese observable en vídeo;
2. que pudiera registrarse con consistencia razonable durante o después de un partido de 90 minutos;
3. que aportara información diferente de otras variables ya incluidas;
4. que fuera utilizada por algún componente posterior del sistema;
5. que justificara su coste de recogida.

La literatura de análisis observacional en fútbol respalda la necesidad de utilizar categorías operacionales claras y estandarizadas, pero el TFM no asume por ello una fiabilidad interobservador ya demostrada para el instrumento propio. Esa validación queda fuera del alcance actual.

La taxonomía final quedó congelada en:

```text
collector/event_catalog.json
catalog_version = 0.3.0
```

El Collector V1.1 registra, entre otros elementos:

- partido, equipo, rival, fecha y formación;
- jugador, dorsal, titular/suplente y minutos;
- rol, lado y cambios de rol;
- pases normal/largo/centro con éxito o fallo;
- pase clave y asistencia;
- regates y pérdidas;
- remates y outcomes;
- acciones defensivas;
- faltas y tarjetas;
- penaltis;
- córners y secuencias de balón parado;
- acciones de portero.

No se recogen manualmente xG, posesión avanzada, PPDA, fatiga, pressing, heatmaps o métricas complejas que puedan derivarse posteriormente o cuya codificación manual sea poco realista.

---

# 3. Modelo de datos

El sistema utiliza DuckDB y adopta `player_match` como unidad analítica principal.

La separación lógica distingue:

```text
master data
→ raw observations
→ raw aggregates
→ derived features
→ analytics evidence
→ decision results
```

Entidades principales:

```text
teams
players
matches
team_match
player_match
player_role_stints
match_events
player_match_raw_stats
player_match_features
gps_imports
gps_player_map
gps_observations
player_match_gps_summary
decision_results
```

Esta separación evita confundir observaciones con interpretaciones y permite rastrear una conclusión hasta su origen.

---

# 4. Feature Engine

El Feature Engine se diseñó en tres etapas.

## 4.1 FEATURE-01 — variables base

A partir de estadísticas raw se generan 28 features deterministas.

Principios:

- ratios acotados cuando corresponde;
- métricas per-90 no negativas;
- preservación de `NULL` cuando el denominador o la evidencia no son válidos;
- ausencia de scores o juicios evaluativos en esta capa.

## 4.2 FEATURE-02 — operadores temporales

Las variables temporales se construyen con una regla estricta de pasado:

```text
para una observación en fecha t
solo pueden usarse observaciones con fecha < t
```

Los partidos de la misma fecha tampoco se informan mutuamente.

El objetivo es evitar leakage temporal y aproximar la información disponible antes del partido para las features, comparativas y tendencias históricas. No convierte las valoraciones jugador-partido calculadas tras el encuentro en predicciones prepartido.

## 4.3 FEATURE-03 — contexto de rol

El sistema añade contexto condicionado por el rol observado del jugador.

Cuando el rol no está disponible, no se imputa una posición específica de forma automática.

---

# 5. Analytics Engine

La capa de Analytics se separó deliberadamente de la decisión final.

Se materializan dos contextos principales:

```text
SELF_ROLE_PRIOR
PEER_ROLE_PRIOR
```

`SELF_ROLE_PRIOR` describe el historial previo del propio jugador en el rol observado.

`PEER_ROLE_PRIOR` compara con compañeros del mismo rol utilizando únicamente información pasada. El jugador actual se excluye del pool de peers y cada peer recibe el mismo peso.

Esta capa produce evidencia descriptiva, no recomendaciones.

---

# 6. Match Rating y Performance Index

Se mantuvieron dos conceptos separados.

## 6.1 Match Rating

El Match Rating es una valoración inmediata jugador-partido disponible desde el primer partido.

Versión activa:

```text
match_rating_v0.5-candidate
```

La arquitectura utiliza rutas específicas según rol cuando existe evidencia suficiente y un fallback explícito cuando no existe rol fiable. El portero dispone de una ruta propia.

La fórmula V5 se congeló como especificación técnica de producto tras validar cobertura, rango y rutas de cálculo. Cualquier modificación requiere nueva evidencia, experimento explícito y validación; su congelación no equivale a validación externa del constructo.

## 6.2 Performance Index

El Performance Index es una capa histórica/posicional complementaria:

```text
performance_score_v0.2-experimental
```

Se mantiene separado del Match Rating para no mezclar una valoración inmediata con una capa histórica aún experimental.

---

# 7. Motor experto de evaluación y evidencia con gate de recomendación

En lugar de utilizar un único `DecisionTreeClassifier`, se implementó un sistema experto jerárquico y modular.

Familias:

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

Cada nodo conserva el contrato:

```text
entrada
→ condición
→ resultado
→ confianza
→ justificación
```

La finalidad es garantizar trazabilidad y permitir que una conclusión pueda auditarse.

N1000–N12000 generan y estructuran evidencia auditable. N13000 actúa como gate final: decide si habría base suficiente para recomendar, pero no emite una recomendación táctica si no existe una policy validada o falta evidencia. En el caso evaluado, la salida final es siempre una abstención.

---

# 8. Machine Learning experimental

El ML se trató como una capa posterior al sistema experto, no como punto de partida.

Se realizaron líneas experimentales relacionadas con:

- change detection;
- similitud entre jugadores;
- clasificación de rol/posición.

La política fue comparar modelos con baselines simples y no desplegar modelos complejos cuando no existiera un target independiente o cuando una regla simple igualara o superara el rendimiento del modelo.

La línea de clasificación de posición quedó como `context-only` y no se utiliza como motor de recomendación final.

---

# 9. GPS opcional

El GPS se diseñó como fuente complementaria.

La capa de normalización convierte ficheros de proveedor en un esquema común:

```text
gps_imports
→ gps_player_map
→ gps_observations
```

Campos canónicos de observación:

```text
source_player_key
timestamp_ms
x
y
distance_m
speed_m_s
acceleration_m_s2
source_row_number
quality_flags
```

Posteriormente se construye un resumen descriptivo jugador-partido:

```text
gps_physical_summary_v0.1-descriptive
```

Reglas metodológicas:

- GPS real observado tiene prioridad sobre GPS sintético;
- GPS sintético se etiqueta explícitamente;
- GPS sintético no alimenta N9000 como evidencia física observada;
- no se definen umbrales universales de HSR, sprint, workload, fatiga, readiness o riesgo de lesión sin validación específica.

---

# 10. Aplicación y capa de producto

La aplicación principal se implementó en Streamlit.

Modos funcionales:

- Team Mode;
- Player Mode;
- Match Mode;
- Físico / GPS;
- Attention Centre;
- Coach Copilot.

El producto incorpora una capa de control de acceso estructural con roles `SUPERADMIN`, `CLUB_ADMIN` y `STAFF`.

La autenticación real por email/contraseña/sesiones no forma parte del MVP actual.

---

# 11. Coach Copilot

El asistente se diseñó como capa downstream de la analítica y no como motor de cálculo.

## 11.1 Query-space contract, preflight y routing determinista

La arquitectura final parte de un espacio de consultas finito y composicional:

```text
entidad + operación + métrica + agregación + rol + filtros + ventana + contexto conversacional
```

Antes del routing se aplica un preflight local. Su función es resolver o rechazar sin LLM entradas como ruido, meta-consultas o preguntas claramente fuera del dominio.

Cuando la consulta es de alta confianza, se resuelve sin LLM:

```text
QUESTION
→ PREFLIGHT / GUARDRAILS
→ DETERMINISTIC HIGH-CONFIDENCE ROUTER
→ READ-ONLY TOOLS
→ PYTHON / DUCKDB / ANALYTICS / EXPERT SYSTEM
→ STRUCTURED EVIDENCE
→ FACTUAL ANSWER
```

Las métricas queryables se definen explícitamente en código y las agregaciones posibles se restringen a operaciones válidas como `sum`, `mean`, `max`, `min` o `latest` según el caso.

Las comparaciones por posición forman parte del contrato. Si se pregunta quién ha rendido mejor dentro de un rol, el sistema utiliza de forma explícita el Match Rating medio de la muestra como criterio de ordenación y presenta métricas adicionales como evidencia; no genera un score nuevo.

## 11.2 Fallback semántico local

Si la consulta no puede mapearse de forma determinista con suficiente confianza y sigue dentro del dominio, se utiliza:

```text
qwen3.5:4b
```

Su función es interpretar el lenguaje y seleccionar una tool válida. El cálculo sigue ejecutándose en Python/DuckDB.

Arquitectura:

```text
QUESTION AMBIGUA
→ QWEN LOCAL
→ TOOL SELECTION
→ LOCAL VALIDATION OF CALL
→ READ-ONLY TOOL
→ PYTHON / DUCKDB
→ STRUCTURED EVIDENCE
→ FACTUAL ANSWER
```

El LLM no puede:

- crear métricas nuevas;
- recalcular Match Rating;
- modificar pesos del experto;
- emitir recomendaciones tácticas no validadas;
- sustituir al motor analítico.

Guardrails explícitos bloquean fatiga/readiness, riesgo de lesión, XI/titularidad y criterios globales no definidos como `mejor jugador`, `más completo` o `más determinante`.

## 11.3 Follow-ups

El historial conversacional conserva la última consulta sustantiva como anchor. Esto permite resolver follow-ups como:

```text
¿Quién corre más distancia por partido?
→ ¿Y el segundo?
→ ¿Y en los últimos 5 partidos?
→ ¿Qué evidencias tienes?
```

sin perder la métrica y la operación originales. El mismo principio se aplica a follow-ups de comparación por posición.

## 11.4 Proveedor OpenAI opcional

La misma capa permite seleccionar opcionalmente:

```text
OpenAI API · clave propia
```

Las consultas claras siguen la ruta determinista y, por tanto, no requieren llamada API. Para lenguaje ambiguo, OpenAI puede seleccionar únicamente tools FPS bounded/read-only.

Cada tool call externa:

1. se transforma a la estructura local;
2. se revalida contra el contrato de tools permitido;
3. se ejecuta localmente sobre Python/DuckDB;
4. produce evidencia estructurada;
5. puede ser sintetizada por el modelo externo con numeric grounding guard.

La API key pertenece al usuario y la UI no la persiste en DuckDB ni en archivos del proyecto.

La integración OpenAI se considera implementada y validada contractualmente, pero no se presenta como benchmark live porque no se ha realizado una prueba real con API key.

## 11.5 Anonimización en demo

La capa conversacional comparte el mismo contrato de identidad que el resto de la demo pública:

```text
Equipo Demo
Jugador XX
Rival XX
```

Los aliases visibles se traducen a identidades internas únicamente antes de llamar a las tools y se vuelven a anonimizar antes de renderizar. Una identidad interna conocida detectada en la respuesta final de demo provoca el bloqueo de esa respuesta.

---

# 12. Informes PDF

Los informes son una capa de presentación estática.

Versiones activas:

```text
Team   = 4 páginas
Player = 3 páginas
Match  = 3 páginas
```

Los PDF consumen resultados materializados y no recalculan lógica crítica.

---

# 13. Estrategia de validación

La validación se realizó por capas y posteriormente de extremo a extremo. Se organiza en seis bloques: **pipeline y trazabilidad**, **Match Rating**, **motor experto**, **validación funcional**, **robustez y abstención**, y **privacidad y reproducibilidad**. La primera verifica la cadena de datos hasta las superficies visibles; la segunda combina cobertura, sensibilidad, rutas por rol observado y estabilidad descriptiva; la tercera inspecciona evidencia, reglas y abstención; la cuarta contrasta preguntas representativas con materializaciones de referencia; la quinta fuerza condiciones incompletas; y la sexta separa la fuente privada de una demo anónima y reproducible.

Esta organización evita convertir una colección dispersa de `PASS` en una afirmación científica única. Los resultados se informan agrupados por bloque y los logs completos permanecen en anexos.

## 13.1 Contratos y validators

Cada módulo relevante dispone de tests, contratos o validadores específicos para comprobar propiedades como:

- integridad de datos;
- ausencia de duplicados;
- cobertura;
- preservación de taxonomía;
- comportamiento temporal strict-past;
- seguridad de gates;
- precedencia real/synthetic en GPS;
- ausencia de recomendaciones no validadas;
- compatibilidad entre capas.

Para el Coach Copilot se aplican dos gates complementarios:

```text
CI reproducible
→ llm/validate_coach_contract.py
→ demo sintética
→ query-space + posiciones + guardrails + follow-ups + preflight + aliases

smoke real local
→ llm/smoke_test_coach_agent.py
→ DuckDB profesional
→ 28 casos finales
```

El smoke real final obtuvo:

```text
SMOKE CONTRACT: PASS (28/28)
average_elapsed=0.4s
semantic rounds=0 en los 28 casos
```

Esta media describe la batería concreta ejecutada en el PC de desarrollo; no constituye un SLA universal ni mide la latencia del fallback Qwen.

## 13.2 QA global

La secuencia se cerró en cuatro bloques:

```text
Fase 1 — Data/Core
Fase 2 — Analytics/Expert
Fase 3A — Product
Fase 3B — Delivery
```

El criterio de cierre no fue la ausencia total de limitaciones, sino que las limitaciones conocidas quedaran explícitas y no produjeran claims no soportados.

---

# 14. Reproducibilidad

El caso profesional utilizado durante el desarrollo no se redistribuye automáticamente por cuestiones de derechos/licencia.

Para separar reproducibilidad de redistribución se creó una demo sintética generada desde cero:

```text
publication/build_synthetic_demo.py
publication/validate_synthetic_demo.py
```

La demo sintética ejecuta el pipeline técnico con datos no profesionales y permite comprobar integración del producto sin copiar filas, nombres o IDs del dataset de desarrollo.

La reproducibilidad se complementa con GitHub Actions.

Workflow:

```text
push / pull_request
→ entorno Ubuntu limpio
→ Python 3.13
→ instalación de dependencias
→ pytest
→ construcción de demo sintética
→ validator end-to-end
→ Coach Copilot query-space contract
```

---

# 15. Separación entre evidencia técnica y validez deportiva

Una decisión metodológica transversal fue distinguir:

```text
VALIDACIÓN TÉCNICA
¿el sistema implementa correctamente su contrato?

VALIDACIÓN DEPORTIVA/CAUSAL
¿la salida mejora decisiones o rendimiento real?
```

El TFM demuestra principalmente la primera dimensión.

No se considera demostrado:

- mejora causal en decisiones de entrenador;
- mejora en victorias, puntos o rendimiento deportivo;
- validez fisiológica del GPS sintético;
- detección de fatiga/readiness/lesión;
- superioridad universal del Match Rating;
- recomendación táctica óptima por N13000;
- calidad, coste o latencia live del modo OpenAI BYOK sin prueba real.

Esta separación delimita el alcance de la hipótesis y evita sobreinterpretar el prototipo.

## 15.1 Preguntas de investigación y trazabilidad de la evaluación

La evaluación técnica se organiza en torno a una pregunta principal sobre la transformación de datos observables en información útil sobre rendimiento y evolución, y dos subpreguntas sobre el sistema experto y la capa conversacional. La matriz `docs/TFM_EVIDENCE_MATRIX.md` relaciona cada una con sus evidencias y limita la inferencia permitida. El control temporal, la separación raw/features/analytics/decision, el grounding y los guardrails son garantías metodológicas usadas para sostener la calidad de la evaluación, no preguntas de investigación independientes.

La fiabilidad interobservador del Collector y la utilidad con staff requieren datos que no se recogieron durante el cierre técnico. Sus diseños de evaluación se documentan en `docs/TFM_EVALUATION_PROTOCOLS.md`; son protocolos futuros, no evidencia empírica del presente TFM.

---

# 16. Síntesis metodológica

La metodología completa puede resumirse así:

```text
variables observables y realistas
→ almacenamiento raw separado
→ features deterministas
→ control temporal strict-past
→ analytics descriptivo
→ sistema experto auditable
→ ML solo cuando existe ground truth defendible
→ GPS opcional y conservador
→ preflight + query-space contract + routing determinista
→ LLM solo como interpretación downstream cuando hace falta
→ proveedor externo opcional bajo el mismo contrato de tools
→ validación por contratos
→ QA end-to-end
→ demo sintética reproducible
→ CI automático
```

El objetivo no fue maximizar complejidad algorítmica, sino construir un sistema funcional, trazable, reproducible y metodológicamente defendible.
