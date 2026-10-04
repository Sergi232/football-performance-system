# TFM — Borrador del capítulo de resultados

Fecha: 04/10/2026
Estado: borrador académico basado exclusivamente en evidencia técnica ya registrada.

Regla: este documento no introduce nuevas métricas ni interpreta como causal aquello que los validators solo demuestran técnicamente.

---

# 1. Estructura de la validación

La evaluación del prototipo se dividió en dos contextos distintos:

1. **caso profesional de desarrollo**, utilizado para construir y validar el producto completo con una temporada real anonimizable localmente;
2. **demo pública sintética**, generada desde cero para comprobar reproducibilidad sin redistribuir datos profesionales.

Esta separación es importante porque la demo sintética demuestra integración y reproducibilidad, pero no revalida científicamente los modelos calibrados sobre el caso profesional.

---

# 2. Data Collector

La integración completa del primer paso fue validada sobre una DuckDB aislada: una fixture JSON fiel al export V1.1 importó titular, suplente, minutos, rol, cambio de rol, pases, remate, acción defensiva, falta y córner; FEATURE-01/02/03 y Analytics completaron sin reinterpretar eventos. La capa de datos de la app leyó el equipo, partido y jugadores importados. Un único partido no aporta histórico suficiente para Match Rating o recomendación, por lo que no se fuerza esa salida.

El Data Collector V1.1 superó el gate funcional final manteniendo la taxonomía `event_catalog v0.3.0`.

Resultados del gate:

```text
COLLECTOR V1.1 FINAL GATE: PASS
structured_opponent=PASS
editable_shirt_number=PASS
starter_substitute_explicit=PASS
starter_minutes_consistency_guard=PASS
shots_on_target_goal_plus_on_target=PASS
spanish_visible_labels=PASS
responsive_metadata_access=PASS
mobile_touch_targets=PASS
dynamic_form_ids_names_labels=PASS
summary_interactive_element_guard=PASS
event_taxonomy_unchanged=PASS
official_entrypoint=PASS
collector contract tests=PASS
```

Interpretación:
- el Collector implementa técnicamente el contrato definido;
- mantiene las categorías aprobadas;
- registra contexto y eventos observables;
- no introduce métricas avanzadas manuales.

Limitación:
- no se ha realizado todavía un estudio científico propio de fiabilidad interobservador con varios analistas.

---

# 3. Datos y Feature Engine

## 3.1 Caso profesional de desarrollo

Contexto principal:

```text
partidos = 38
jugadores en contexto producto = 36
apariciones jugadas = 590
```

El denominador `player_match=835` corresponde a registros de plantilla/alineación. Incluye 590 apariciones jugadas y 245 suplentes no utilizados (`started=false`, minutos 0 y rol nulo). Match Rating utiliza el universo de 590 apariciones jugadas; el motor experto utiliza los 835 registros para representar también disponibilidad, falta de rol y abstención.

La validación de base de datos confirmó, entre otros contratos:

```text
demo_match_count=38
duplicate_source_match_ids=0
missing_opponents=0
invalid_minutes=0
orphan_match_events=0
duplicate_source_events=0
Validation status: PASS
```

## 3.2 FEATURE-01

```text
feature definitions = 28
feature rows = 23380
non-null values = 6324
coverage = 38 matches / 36 players
FEATURE-01: PASS
```

El stage genera ratios y métricas per-90 deterministas preservando `NULL` según contrato.

## 3.3 FEATURE-02

```text
base features = 28
temporal operators = 7
feature rows = 163660
FEATURE-02: PASS
```

El contrato temporal utiliza pasado estricto y excluye información futura y de la misma fecha.

## 3.4 FEATURE-03

```text
rows = 117735 / 117735
non-null = 43060
registros de plantilla/alineación con rol observado y minutos positivos = 590 / 835
distinct role labels = 23
strict-past contract = PASS
```

Cuando no existe rol observado, no se imputa uno artificialmente.

---

# 4. Analytics Engine

`ANALYTICS-01` materializó evidencia separada para historial propio y peers de rol:

```text
analytics rows = 46760
scopes = SELF_ROLE_PRIOR + PEER_ROLE_PRIOR
strict-past = PASS
current-player peer exclusion = PASS
equal-player weighting = PASS
```

La capa no produce por sí misma score, ranking ni recomendación.

---

# 5. Motor experto de evaluación y evidencia con gate de recomendación

La construcción incremental cerró siete stages y culminó en `expert_0.7.0`.

Resultado final:

```text
decision rows = 154475
N13000 rows = 2505
engine_version = expert_0.7.0
```

Distribución del gate final N13000:

```text
NO_EVIDENCE = 89
POLICY_UNVALIDATED = 501
ROLE_UNKNOWN = 245
```

Interpretación:
- el sistema conserva evidencia y estados auditables;
- N13000 se abstiene en todos los casos: 501 por policy no validada, 245 por rol desconocido y 89 por falta de evidencia; por tanto, no es un recomendador táctico final.

## 5.1 N9000 y GPS

Tras la corrección metodológica, N9000 solo acepta GPS observado no sintético como evidencia física.

```text
player-match rows with observed non-synthetic GPS = 0
Synthetic demo GPS is excluded from expert evidence = PASS
```

Por tanto, el caso actual no permite presentar conclusiones expertas basadas en GPS real.

---

# 6. Match Rating V5

Versión activa:

```text
match_rating_v0.5-candidate
```

Cobertura validada:

```text
played appearances = 590
rated appearances = 590
coverage = 1.000
matches = 38
outfield PERF18_ANCHORED = 380
goalkeeper route = 38
generic role fallback = 172
nulls = 0
duplicates = 0
out_of_range = 0
```

Distribución de referencia:

```text
mean = 6.388
median = 6.257
q10 = 5.757
q90 = 7.216
min = 3.206
max = 9.554
```

Interpretación permitida:
- V5 ofrece cobertura completa de las apariciones jugadas del caso de desarrollo;
- existe una ruta específica de portero y un fallback explícito cuando el rol no es fiable.

No demostrado:
- que el rating sea una medida universal y objetiva del rendimiento futbolístico fuera del contexto en el que ha sido diseñado y validado técnicamente.

---

# 7. GPS y capa física descriptiva

La demo GPS utilizada para probar la integración produjo:

```text
generator_version = gps_synthetic_demo_v1.2.0
imports = 38
mappings = 590
observations = 38197
latest summaries = 590
summary_version = gps_physical_summary_v0.1-descriptive
```

La precedencia `REAL_OVER_SYNTHETIC` fue validada.

El sistema no genera HSR, sprint zones, workload, fatiga, readiness o riesgo de lesión mediante umbrales no validados.

La correlación minutos-distancia observada en la demo sintética forma parte de la lógica de generación de los datos y no constituye evidencia científica deportiva.

---

# 8. Dashboard y producto

La capa de producto superó los contratos principales:

```text
DASHBOARD-01 DATA CONTRACT: PASS
STREAMLIT UI COMPATIBILITY: PASS
DEMO PRESENTATION: PASS
ACCESS CONTROL: PASS
ATTENTION FLAGS CONTRACT: PASS
MATCH MODE CONTRACT: PASS
```

La presentación demo enmascara identidad de equipo, jugadores y rivales sin modificar la lógica interna. El mismo contrato de identidad se aplica al Coach Copilot, de modo que las respuestas visibles en demo utilizan `Equipo Demo`, `Jugador XX` y `Rival XX`.

El control de acceso estructural distingue:
- SUPERADMIN;
- CLUB_ADMIN;
- STAFF.

Limitación:
- autenticación real con email/contraseña/sesiones no está implementada.

---

# 9. Coach Copilot

La arquitectura final prioriza preflight y routing determinista de alta confianza, reservando el LLM para lenguaje ambiguo dentro del dominio.

Validación real final sobre la DuckDB profesional:

```text
SMOKE CONTRACT: PASS (28/28)
average_elapsed = 0.4s
all final smoke cases = rounds 0
```

La batería final incluye:
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
- entrada basura;
- meta-consulta;
- follow-ups ordinales, ventana temporal y evidencia;
- follow-up de comparación por posición.

El resultado muestra que toda la batería final pudo resolverse sin invocar Qwen. `qwen3.5:4b` queda como fallback semántico únicamente cuando el router determinista no puede resolver con suficiente confianza una consulta que sigue dentro del dominio soportado. Por tanto, esta batería valida la ruta determinista/preflight y no estima calidad, cobertura lingüística ni latencia del fallback.

Los guardrails bloquean explícitamente:
- fatiga/cansancio;
- readiness;
- riesgo de lesión;
- XI/titularidad;
- recomendación táctica automática no validada;
- conceptos como «mejor jugador», «más completo» o «más determinante» sin una definición analítica aprobada.

La comparación por posición sí forma parte del alcance validado. Si se pregunta quién ha rendido mejor dentro de una posición, el sistema declara como criterio de ordenación el **Match Rating medio dentro de la muestra de ese rol** y muestra métricas adicionales como evidencia descriptiva; no crea un score nuevo.

## 9.1 Preflight y query-space contract

El contrato del Assistant dejó de basarse en una lista cerrada de frases y pasó a modelarse como composición de:

```text
entidad + operación + métrica + agregación + rol + filtros + ventana + contexto conversacional
```

El CI ejecuta un validador específico del espacio de consultas sobre la demo sintética. Este gate cubre rankings, posiciones, ventanas, follow-ups, guardrails, ruido, fuera de dominio y aliases demo.

Casos obvios como `sss`, `no puedes hacer nada` o una pregunta claramente ajena al fútbol se resuelven mediante preflight local sin llamar al LLM.

## 9.2 OpenAI BYOK opcional

La aplicación incorpora una segunda opción de fallback semántico:

```text
OpenAI API · clave propia
```

Las consultas claras siguen utilizando la ruta determinista local y no generan una llamada API. Para consultas ambiguas, OpenAI puede seleccionar únicamente tools FPS bounded/read-only; cada llamada se revalida mediante el contrato local antes de ejecutarse.

Validación disponible:

```text
external tool surface = PASS
local revalidation of arguments = PASS
unknown external tool dropped = PASS
missing API key guard = PASS
unit / contract tests = PASS
synthetic demo CI = PASS
```

No se ha ejecutado todavía un benchmark live con una API key real. Por tanto, no se reportan resultados de latencia, coste o calidad live para este modo.

No están validados:
- player similarity como función final de producto;
- predicción futura;
- XI ideal;
- recomendaciones tácticas automáticas;
- fatiga/readiness/lesión;
- un criterio global de `mejor jugador` sin definición analítica explícita.

---

# 10. Informes PDF

La versión V6 superó el gate técnico:

```text
schema = 0.7.0
report_metrics = report_descriptive_v0.2
team = 4 páginas
player = 3 páginas
match = 3 páginas
REPORTS ELITE TECHNICAL GATE V6: PASS
```

Los reports consumen resultados materializados y no recalculan Match Rating, Performance Index ni decisiones expertas.

---

# 11. QA global end-to-end

Las fases se cerraron de forma incremental:

```text
Fase 1 — Data/Core              PASS
Fase 2 — Analytics/Expert       PASS
Fase 3A — Product               PASS
Fase 3B — Delivery              PASS
```

Resultado:

```text
GLOBAL END-TO-END QA: PASS
```

Cadena cubierta:

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
→ Publication layer
```

## 11.1 Síntesis de validación técnico-funcional

La evidencia se agrupa para responder las preguntas de investigación, no como una enumeración de gates.

| Bloque | Método | Resultado |
|---|---|---|
| Pipeline y trazabilidad | Traza real `raw → feature → analytics → rating/experto → dashboard → Coach/PDF`. | PASS; una salida visible conserva su provenance. |
| Match Rating | Cobertura, sensibilidad controlada, rutas por rol observado y estabilidad descriptiva. | PASS; 590/590 apariciones jugadas, 38 GK, 380 posicionales y 172 fallbacks. |
| Motor experto | Cobertura N1000–N13000 y traza de decisión auditable. | PASS; 835 registros evaluados y abstención final controlada. |
| Funcional | Seis preguntas representativas contrastadas con tablas de referencia. | 6/6 PASS. |
| Robustez y abstención | Casos de datos incompletos y dos consultas sin policy/evidencia. | PASS; no se fuerza conclusión ni recomendación. |
| Privacidad y reproducibilidad | Privacy gate, demo sintética y CI limpio. | PASS. |

El detalle de preguntas, trazas y logs se mantiene en anexos. Las comparaciones por posición usan roles observados; las filas con 1–4 apariciones son muestras pequeñas y solo descriptivas.

---

# 12. Demo pública sintética

Para comprobar que el repositorio no depende de la DuckDB profesional se creó una base pública sintética desde cero.

Gate local:

```text
SYNTHETIC PUBLIC DEMO CONTRACT: PASS
demo_version = synthetic_public_demo_v0.1.0
matches = 12
players = 18
player_match = 216
played = 192
FEATURE-01 = 6048
FEATURE-02 = 42336
FEATURE-03 = 30456
analytics_rows = 12096
expert_rows = 39960
N13000 = 648
ratings = 192
performance_index = 192
gps = 192
app_read_layer = PASS
report_payloads = PASS
professional_source_rows = 0
redistribution_status = REDISTRIBUTABLE_SYNTHETIC_DEMO
```

Los Match Rating y Performance Index de esta demo son fixtures sintéticos de compatibilidad de producto y no una revalidación de sus calibraciones.

---

# 13. Integración continua

GitHub Actions ejecuta automáticamente:

```text
checkout limpio
→ Python 3.13
→ instalación requirements
→ pytest
→ construcción completa de demo sintética
→ validator end-to-end
→ Coach Copilot query-space contract
```

Runs recientes de referencia:

```text
37167083614 = SUCCESS — query-space + preflight contract
37167157174 = SUCCESS — final code gate before local 28-case smoke
```

El smoke real final 28/28 se ejecutó localmente sobre la DuckDB profesional, mientras que el CI garantiza la regresión reproducible del espacio de consultas sobre la demo sintética.

---

# 14. Contraste de la hipótesis

Hipótesis:

> Un equipo de fútbol amateur o semiprofesional puede disponer de un sistema integral y auditable de soporte al análisis a partir de datos de vídeo y GPS opcional, capaz de transformar hechos observables en información trazable sobre rendimiento, evolución y rol; cuando existe GPS observado, puede añadir variables físicas descriptivas.

Los resultados respaldan favorablemente la **viabilidad técnico-funcional y arquitectónica** de la hipótesis porque:

1. existe un pipeline funcional y trazable desde captura/importación hasta dashboard, asistente y PDF;
2. las capas están separadas y versionadas;
3. el sistema degrada explícitamente cuando falta evidencia;
4. existe control temporal contra leakage;
5. seis preguntas representativas recuperan resultados estructurados correctos en el espacio de consultas soportado y el LLM no es responsable del cálculo crítico;
6. la solución se reproduce desde un entorno limpio mediante datos sintéticos.

En relación con las preguntas de investigación, la pregunta principal queda respaldada por el flujo integrado desde Collector hasta dashboard, PDF y demo reproducible. La primera subpregunta queda respaldada por la evidencia auditable del sistema experto y sus estados de abstención; la segunda, por el contrato conversacional, las herramientas de solo lectura y la batería del Coach. Los controles temporales y de grounding sustentan la calidad metodológica de esas respuestas, sin convertirse en su objetivo. Estas evidencias no sustituyen una evaluación con staff, una evaluación empírica del fallback LLM ni validación externa del Match Rating.

La hipótesis no debe reinterpretarse como demostración de que el sistema:
- mejora causalmente las decisiones del entrenador;
- aumenta rendimiento, puntos o victorias;
- predice lesiones o fatiga;
- identifica automáticamente el rol táctico óptimo.

---

# 15. Resultado principal del TFM

El principal resultado no es una métrica aislada, sino un producto integrado y auditable:

```text
captura de datos realista
+ modelo de datos
+ feature engineering temporal
+ analytics
+ sistema experto
+ Match Rating
+ GPS opcional
+ dashboard
+ Coach Copilot grounded
+ proveedor externo BYOK opcional
+ PDF
+ QA
+ reproducibilidad
```

El valor académico del prototipo reside tanto en lo que implementa como en las inferencias que deliberadamente decide no realizar sin evidencia suficiente. Cada resultado `PASS` debe interpretarse como conformidad con un contrato técnico definido, no como una prueba estadística de eficacia deportiva.
# Validación Fase 2: instalación nueva desde Collector

La simulación incremental reproducible de Equipo Demo B importó 12 JSON V1.1 en una DuckDB vacía y persistente. Produjo 264 registros `player_match`, 168 Match Rating V5 (144 rutas posicionales V4.1, 12 rutas GK y 12 fallback V2 por rol no disponible) y 48.840 filas del motor N1000–N13000. Team, Player, Match, Coach grounded y los PDF Team/Player/Match se validaron sobre esa misma base. La ausencia intencionada de GPS se registró como `GPS_NOT_AVAILABLE / EXPECTED_ABSTENTION`.

La referencia profesional se usa únicamente para calibración offline. En runtime, V4 y GK consumen artefactos congelados; la equivalencia contra la ruta original fue PASS, con error absoluto máximo `7.478e-13`. Esta evidencia prueba reproducibilidad técnica y no constituye validación externa del rating ni utilidad percibida.

