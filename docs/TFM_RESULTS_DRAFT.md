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
player-match with observed role = 590 / 835
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

# 5. Sistema experto N1000-N13000

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
- no fuerza una recomendación cuando falta evidencia o cuando la política no ha sido validada.

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

La presentación demo enmascara identidad de equipo, jugadores y rivales sin modificar la lógica interna.

El control de acceso estructural distingue:
- SUPERADMIN;
- CLUB_ADMIN;
- STAFF.

Limitación:
- autenticación real con email/contraseña/sesiones no está implementada.

---

# 9. Coach Copilot

La arquitectura final prioriza un router determinista de alta confianza y reserva el LLM para lenguaje ambiguo.

Validación real sobre la DuckDB profesional:

```text
SMOKE CONTRACT: PASS (22/22)
average_elapsed = 1.4s
consultas deterministas típicas = 0.1–0.8s
follow-ups encadenados = 0.1–0.2s
fallback Qwen observado en pregunta fuera de dominio = 25.3s
```

La batería incluye:
- Match Rating más reciente;
- Match Rating medio últimos cinco;
- distancia media por partido;
- top de remates;
- asistencias;
- evolución y perfil natural de jugador;
- GPS;
- comparación;
- detalle de partido;
- estado del equipo;
- calidad de datos;
- guardrails de fatiga, lesión y titularidad;
- criterios globales no validados;
- pregunta fuera de dominio;
- follow-ups ordinales, ventana temporal y evidencia.

El resultado muestra que las consultas soportadas y claras ya no dependen de un LLM en cada turno. `qwen3.5:4b` queda como fallback semántico cuando el router determinista no puede resolver la intención con suficiente confianza.

Los guardrails bloquean explícitamente:
- fatiga/cansancio;
- readiness;
- riesgo de lesión;
- XI/titularidad;
- recomendación táctica automática no validada;
- conceptos como «mejor jugador», «más completo» o «más determinante» sin una definición analítica aprobada.

## 9.1 OpenAI BYOK opcional

La aplicación incorpora una segunda opción de motor de lenguaje:

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
- ranking por rol como recomendación;
- player similarity como función final;
- predicción futura;
- XI ideal;
- recomendaciones tácticas automáticas;
- fatiga/readiness/lesión.

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
```

Runs recientes de referencia:

```text
37162911509 = SUCCESS — direct execution smoke fix
37163349049 = SUCCESS — optional OpenAI Coach Copilot
37163417219 = SUCCESS — OpenAI BYOK UI + contracts
37163457928 = SUCCESS — external tool-surface contract tests
```

Esto demuestra reproducibilidad técnica desde un entorno limpio del repositorio.

---

# 14. Contraste de la hipótesis

Hipótesis:

> Un equipo de fútbol amateur o semiprofesional puede disponer de un sistema integral y auditable de soporte a la decisión a partir de datos de vídeo y GPS opcional, capaz de transformarlos en información sobre rendimiento, evolución, rol y comportamiento físico de los jugadores y del equipo.

Los resultados permiten defender favorablemente la **viabilidad técnica y arquitectónica** de la hipótesis porque:

1. existe un pipeline funcional desde captura/importación hasta dashboard, asistente y PDF;
2. las capas están separadas y versionadas;
3. el sistema degrada explícitamente cuando falta evidencia;
4. existe control temporal contra leakage;
5. el LLM no es responsable del cálculo crítico;
6. la solución se reproduce desde un entorno limpio mediante datos sintéticos.

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

El valor académico del prototipo reside tanto en lo que implementa como en las inferencias que deliberadamente decide no realizar sin evidencia suficiente.
