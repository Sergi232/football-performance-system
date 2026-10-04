# TFM — Borrador de anexos

Fecha: 04/10/2026
Estado: estructura y contenido base para anexos de la memoria.

Objetivo: conservar trazabilidad técnica sin sobrecargar el cuerpo principal. Los anexos deben contener detalle reproducible, no repetir la discusión académica.

---

# Anexo A — Taxonomía del Data Collector

Fuente canónica:

```text
collector/event_catalog.json
catalog_version=0.3.0
```

Familias principales:

## A.1 Identificación y contexto

- partido;
- equipo;
- rival;
- fecha;
- jugador;
- dorsal;
- titular/suplente;
- minuto de entrada/salida;
- minutos derivados;
- rol/posición;
- lado;
- formación;
- cambio de rol.

## A.2 Pase

```text
PASS NORMAL  SUCCESS / FAIL
PASS LONG    SUCCESS / FAIL
PASS CROSS   SUCCESS / FAIL
```

Qualifiers:
- key_pass;
- assist.

Regla: una asistencia implica pase completado y pase clave.

## A.3 1v1 y pérdidas

```text
DRIBBLE SUCCESS
DRIBBLE FAIL
LOSS OTHER
```

`DRIBBLE FAIL` deriva una pérdida.

## A.4 Finalización

```text
SHOT GOAL
SHOT ON_TARGET
SHOT OFF_TARGET
SHOT BLOCKED
```

`GOAL` y `ON_TARGET` cuentan en remates a puerta según contrato.

## A.5 Defensa

- tackle success/fail;
- interception;
- block;
- clearance.

## A.6 Disciplina

- foul committed;
- foul received;
- tarjeta amarilla;
- tarjeta roja;
- segunda amarilla como roja con flag.

## A.7 Penaltis

```text
PENALTY WON / CONCEDED
×
GOAL / MISSED
```

El evento de penalti no duplica automáticamente remate/gol.

## A.8 Portero

- save;
- goal_conceded.

## A.9 Balón parado

```text
CORNER FOR / AGAINST
```

Resultado opcional:
- direct_shot;
- shot_after_restart;
- goal;
- no_shot.

---

# Anexo B — Modelo de datos

Unidad principal:

```text
player_match
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

Principio:

```text
observación raw
≠
feature derivada
≠
evidencia analítica
≠
decisión
```

Figura asociada:
- `docs/figures/tfm_data_model.svg`.

---

# Anexo C — Feature Engine

## C.1 FEATURE-01

```text
feature definitions=28
feature rows=23380
non-null=6324
```

Reglas:
- ratios con denominadores válidos;
- per-90 no negativos;
- NULL preservado;
- sin scores ni thresholds de decisión.

## C.2 FEATURE-02

```text
28 base features × 7 operadores temporales
rows=163660
```

Contrato:

```text
fecha fuente < fecha observación actual
```

## C.3 FEATURE-03

```text
rows=117735
non-null=43060
observed-role player-match=590/835
role labels=23
```

No se inventa rol faltante.

Figura asociada:
- `docs/figures/tfm_strict_past.svg`.

---

# Anexo D — Motor experto de evaluación y evidencia con gate de recomendación

Jerarquía:

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

N1000–N12000 estructuran evidencia auditable. N13000 decide si existe base suficiente para recomendar; en el caso evaluado se abstiene en los 835 registros: 501 por policy no validada, 245 por rol desconocido y 89 por falta de evidencia. No se emite una recomendación táctica final.

Contrato de cada nodo:

```text
entrada
→ condición
→ resultado
→ confianza
→ justificación
```

Resultado final de referencia:

```text
engine_version=expert_0.7.0
decision_rows=154475
N13000_rows=2505
```

Estados del gate final:

```text
NO_EVIDENCE=89
POLICY_UNVALIDATED=501
ROLE_UNKNOWN=245
```

Regla N9000:
- solo GPS observado no sintético cuenta como evidencia física.

Figura asociada:
- `docs/figures/tfm_expert_system.svg`.

---

# Anexo E — Match Rating V5

Versión:

```text
match_rating_v0.5-candidate
```

Cobertura:

```text
played=590
rated=590
matches=38
outfield PERF18_ANCHORED=380
goalkeeper route=38
generic role fallback=172
```

Calidad:

```text
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

Nota metodológica: estas cifras documentan comportamiento técnico del rating en el caso de desarrollo; no constituyen validación universal externa.

---

# Anexo F — GPS

Esquema canónico de observación:

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

Flujo:

```text
provider file
→ gps_imports
→ gps_player_map
→ gps_observations
→ player_match_gps_summary
```

Demo integración:

```text
generator_version=gps_synthetic_demo_v1.2.0
imports=38
mappings=590
observations=38197
summaries=590
```

No inferir:
- fatiga;
- readiness;
- lesión;
- HSR/sprint universal.

---

# Anexo G — Coach Copilot

Arquitectura local final:

```text
QUESTION
→ PREFLIGHT / GUARDRAILS
→ DETERMINISTIC HIGH-CONFIDENCE ROUTER
→ READ-ONLY TOOLS
→ PYTHON / DUCKDB / ANALYTICS / EXPERT
→ STRUCTURED EVIDENCE
→ FACTUAL ANSWER
```

Fallback semántico solo cuando la intención sigue siendo ambigua dentro del dominio:

```text
QUESTION AMBIGUA
→ qwen3.5:4b
→ TOOL SELECTION
→ LOCAL TOOL VALIDATION
→ PYTHON / DUCKDB
→ STRUCTURED EVIDENCE
→ FACTUAL ANSWER
```

Contrato del espacio de consultas:

```text
entidad + operación + métrica + agregación + rol + filtros + ventana + follow-up
```

Validación real final sobre la DuckDB profesional:

```text
SMOKE CONTRACT: PASS (28/28)
average_elapsed=0.4s
semantic rounds=0 en los 28 casos finales
```

El gate cubre rankings, ventanas, perfiles, GPS, comparación entre jugadores, comparación por posición, partidos, calidad, guardrails, ruido/fuera de dominio y follow-ups ordinales, temporales, de evidencia y de rol.

Comparación por posición:
- posiciones cubiertas: GK / CB / FB / DM / CM / AM / W / ST;
- si se pregunta quién ha rendido mejor en un rol, el criterio explícito es Match Rating medio en la muestra;
- métricas adicionales son evidencia descriptiva;
- no se crea un score nuevo.

Guardrails comprobados:
- fatiga/cansancio;
- riesgo de lesión;
- titularidad/XI;
- recomendaciones tácticas no validadas;
- `mejor jugador`, `más completo` y `más determinante` sin definición analítica aprobada.

Preflight comprobado:
- entrada basura (`sss`) → aclaración inmediata, sin LLM;
- meta-consulta → capacidades, sin LLM;
- fuera de dominio obvio → rechazo inmediato, sin LLM.

Proveedor externo opcional:

```text
OpenAI API · clave propia
```

Contrato:
- preguntas claras → ruta determinista, sin llamada API;
- preguntas ambiguas → OpenAI puede seleccionar únicamente tools FPS bounded/read-only;
- toda tool call externa se revalida localmente;
- la API key pertenece al usuario y no se persiste en DuckDB ni archivos del proyecto;
- OpenAI no accede directamente a DuckDB;
- contract tests + CI PASS;
- benchmark live con API key real: no validado.

Anonimización demo:

```text
Equipo Demo
Jugador 01, Jugador 02, ...
Rival 01, Rival 02, ...
```

La traducción a identidades internas se limita al boundary de tools y se revierte antes de renderizar.

Figura asociada:
- `docs/figures/tfm_llm_grounding.svg`.

---

# Anexo H — QA end-to-end

```text
Fase 1 — Data/Core          PASS
Fase 2 — Analytics/Expert   PASS
Fase 3A — Product           PASS
Fase 3B — Delivery          PASS
GLOBAL END-TO-END QA        PASS
```

Cobertura:

```text
Collector
→ DB
→ Features
→ Analytics
→ Match Rating
→ GPS
→ Expert
→ Dashboard
→ Access Control
→ Attention
→ Coach Copilot
→ PDF
→ Publication
```

La matriz completa de claims está en:
- `docs/TFM_EVIDENCE_MATRIX.md`.

---

# Anexo I — Demo sintética y reproducibilidad

```text
demo_version=synthetic_public_demo_v0.1.0
matches=12
players=18
player_match=216
played=192
FEATURE-01=6048
FEATURE-02=42336
FEATURE-03=30456
analytics_rows=12096
expert_rows=39960
N13000=648
ratings=192
performance_index=192
gps=192
professional_source_rows=0
redistribution_status=REDISTRIBUTABLE_SYNTHETIC_DEMO
```

Regla:
- la demo demuestra integración/reproducibilidad;
- no revalida científicamente las calibraciones del caso profesional.

---

# Anexo J — Integración continua

Workflow:

```text
.github/workflows/tests.yml
```

Triggers:

```text
push
pull_request
workflow_dispatch
```

Pipeline:

```text
checkout
→ Python 3.13
→ requirements
→ pytest
→ synthetic demo build
→ synthetic demo validator
→ Coach Copilot query-space contract
```

Runs de referencia del cierre:

```text
37167083614 = SUCCESS — query-space + preflight contract
37167157174 = SUCCESS — code gate previo al smoke final
37168110570 = SUCCESS — documentación/defensa sincronizada
```

---

# Anexo K — Capturas del producto

Capturas reales disponibles según:

```text
docs/TFM_SCREENSHOT_CHECKLIST.md
```

Capturas previstas:
1. Collector;
2. Team Mode;
3. Player Mode;
4. Match Mode;
5. GPS;
6. Attention Centre;
7. Coach Copilot;
8. PDF Team;
9. PDF Player;
10. PDF Match.

Todas las capturas de producto deben utilizar modo demo/anónimo cuando corresponda y no mostrar API keys, rutas privadas ni identidades profesionales reales.

---

# Anexo L — Protocolos de evaluación empírica

El protocolo de fiabilidad interobservador del Collector y el piloto de utilidad con staff están preparados en:

```text
docs/TFM_EVALUATION_PROTOCOLS.md
```

No se ejecutaron durante este TFM. Se incluyen como diseño de evaluación posterior y no como resultados empíricos.

---

# Regla de maquetación final

Si la universidad limita extensión o número de anexos:

Prioridad alta:
- A Taxonomía;
- D Sistema experto;
- H QA;
- I Reproducibilidad.

Prioridad media:
- B Modelo de datos;
- C Features;
- E Match Rating;
- F GPS;
- G Coach Copilot.

Las capturas pueden dividirse entre cuerpo principal y anexo según espacio.
