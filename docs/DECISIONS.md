# Registro de decisiones estructurales

Fecha: 04/10/2026

Este archivo contiene únicamente decisiones que pueden cambiar arquitectura, metodología, producto, privacidad o publicación. No se usa para detalles técnicos rutinarios.

Estados:

- `APPROVED`
- `PENDING SERGI`
- `DEFERRED`
- `REJECTED`

## Decisiones aprobadas

### D-001 — TEAM MODE como producto principal
Estado: `APPROVED`

TEAM MODE es el modo principal. PLAYER MODE es complementario. MATCH MODE forma parte del producto operativo. RIVAL MODE queda como extensión futura y el sistema principal no depende de datos del rival.

### D-002 — GPS opcional
Estado: `APPROVED`

El producto funciona sin GPS. GPS añade contexto físico cuando existe.

No se exponen HSR, sprint, workload, fatigue, readiness o riesgo de lesión sin definición y validación explícitas.

### D-003 — LLM fuera del cálculo crítico
Estado: `APPROVED`

Arquitectura obligatoria:

```text
DATA → ANALYTICS → DECISION ENGINE → TOOLS READ-ONLY → LLM/ROUTER → COACH
```

El LLM no crea métricas críticas, no recalcula ratings ni sustituye decisiones del motor.

### D-004 — Sistema experto auditable antes de ML
Estado: `APPROVED`

El baseline principal es un sistema jerárquico N1000-N13000. ML es complementario y se incorpora solo cuando existe una hipótesis, target y validación defendibles.

### D-005 — No recomendación N13000 sin policy validada
Estado: `APPROVED`

N13000 no puede emitir una recomendación táctica final si los criterios, mínimos de muestra, reglas y confidence no están validados.

La ausencia de recomendación es una salida válida y auditable.

### D-006 — Web como producto principal
Estado: `APPROVED`

La aplicación Streamlit es el producto principal. Los PDF son entregables estáticos complementarios.

### D-007 — GitHub como fuente de verdad
Estado: `APPROVED`

El repositorio es la memoria técnica definitiva.

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

Si código y documentación divergen, debe investigarse la discrepancia y actualizar la documentación cuando corresponda.

### D-008 — Rendimiento como objetivo analítico principal
Estado: `APPROVED`

El objetivo central es medir rendimiento de jugador de forma defendible, auditable y útil para el entrenador.

Flujo:

```text
PLAYER-MATCH DATA
→ DIMENSIONES DE RENDIMIENTO
→ MATCH RATING
→ EVOLUCIÓN / CONSISTENCIA
→ CONTEXTO DE ROL
→ CONCLUSIONES ESTRUCTURADAS
```

El rol o posición no son el target principal. Se utilizan para contextualizar, normalizar y comparar cuando existe una etiqueta observada fiable.

El Match Rating vigente se rige por D-010.

### D-009 — Anchor externo: semántica antes que coincidencia lexical
Estado: `APPROVED`

Un campo profesional solo puede actuar como candidato a anchor externo si representa una valoración individual holística e independiente del jugador.

No basta con que el nombre contenga `score`, `rating`, `grade`, `index` o `rank`.

Quedan excluidos como anchors:

- resultados/contexto de partido o equipo;
- estadísticas componentes del propio rendimiento;
- variables utilizadas después como inputs del producto.

Un anchor externo se usa para validación/aprendizaje experimental y nunca como input obligatorio del sistema amateur.

### D-010 — Match Rating V5 como baseline activo
Estado: `APPROVED`

Versión activa:

```text
match_rating_v0.5-candidate
```

Principios aprobados:

- rating posicional para jugadores de campo;
- roles CB / FB / DM / CM / AM / W / ST;
- modelo separado para porteros;
- portero: 90% shot-stopping / 10% distribución;
- fallback explícito si no existe rol fiable;
- nunca inventar una posición;
- no convertir missing en zero sin semántica validada;
- no aplicar castigo global automático por resultado del equipo.

El Match Rating V5 queda congelado como baseline vigente. No se modifica fórmula, pesos o arquitectura sin evidencia nueva, experimentación explícita y validación.

### D-011 — Match Rating y Performance Index son capas distintas
Estado: `APPROVED`

```text
MATCH RATING
= nota inmediata jugador-partido
= disponible desde partido 1

PERFORMANCE INDEX
= capa histórica/posicional
= evolución + forma + consistencia + contexto de rol
```

No deben presentarse ni interpretarse como la misma métrica.

### DG-AN-01 — Comparaciones analíticas válidas
Estado: `APPROVED`

Decisión: **C — ambas, separadas y explícitamente etiquetadas**.

Analytics conserva dos evidencias distintas:

- `SELF_ROLE_PRIOR`: jugador vs su propio historial estrictamente anterior en el mismo rol observado;
- `PEER_ROLE_PRIOR`: jugador vs otros jugadores del mismo equipo con el mismo rol observado, usando solo información estrictamente anterior.

No se mezclan silenciosamente en un único score.

### DG-N13-01 — Política final de recomendación
Estado: `APPROVED`

Contrato objetivo:

**recomendación + confianza + justificación + alternativa/limitaciones**.

La aprobación del contrato no autoriza thresholds, pesos o reglas de confidence no validados. Hasta disponer de policy suficiente, N13000 conserva salidas `RECOMMENDATION_NOT_ISSUED_*` cuando corresponda.

### DG-UX-01 — Jerarquía de producto
Estado: `APPROVED`

Decisión: **B — insights/alertas como vista principal y datos como segundo nivel**.

Principio operativo:

```text
insight-first, audit-detail second
```

Home, Team, Player y Match deben responder primero qué necesita entender el entrenador. Tablas, provenance, dimensiones y detalle quedan como segundo nivel de exploración/auditoría.

### DG-LLM-01 — Arquitectura final del asistente
Estado: `APPROVED`

Decisión: **C — deterministic-first + preflight/guardrails + fallback local + provider opcional desacoplado**.

Runtime local final:

```text
pregunta
→ preflight / guardrails
→ router determinista de alta confianza
→ Python tools read-only
→ DuckDB / analytics / expert outputs
→ respuesta factual determinista
```

Solo si la intención sigue siendo ambigua y permanece dentro del dominio:

```text
pregunta ambigua
→ qwen3.5:4b como router semántico
→ tool revalidada
→ Python / DuckDB
→ evidencia estructurada
→ respuesta factual
```

Reglas aprobadas:

- el LLM no accede directamente a DuckDB;
- el LLM no recalcula Match Rating, Performance Index ni decisiones críticas;
- las consultas claras no deben pagar latencia LLM innecesaria;
- ruido, meta-consultas y fuera de dominio obvio se resuelven antes del LLM;
- el espacio de consulta se modela como `entidad + operación + métrica + agregación + rol + filtros + ventana + follow-up`;
- guardrails deterministas son válidos para policies no aprobadas;
- preguntas fuera de cobertura deben declarar la limitación;
- `mejor jugador`, `más completo` o `más determinante` no se resuelven sin definición analítica aprobada;
- sí se permiten comparaciones de rendimiento dentro de una posición cuando el criterio de ordenación se declara explícitamente y no se crea un score nuevo;
- la prioridad de entidad es `jugador concreto > término que también pueda describir una posición`;
- la demo debe mantener identidades anónimas coherentes también dentro del Assistant.

Validación local real final:

```text
SMOKE CONTRACT: PASS (28/28)
average_elapsed=0.4s
all final smoke cases: rounds=0
```

El gate final cubre rankings, ventanas temporales, perfiles, GPS, comparaciones entre jugadores y por posición, partidos, calidad de datos, guardrails, ruido/fuera de dominio y follow-ups encadenados.

Proveedor opcional implementado:

```text
OpenAI API · clave propia
```

Condiciones:
- las consultas claras siguen la ruta determinista y no requieren llamada API;
- OpenAI solo puede seleccionar tools FPS bounded/read-only;
- toda tool call externa se revalida localmente;
- la API key pertenece al usuario y no se persiste en DuckDB ni archivos del proyecto;
- el proveedor cloud no altera Analytics/Decision Engine;
- el modo OpenAI está validado por contrato/CI, pero no se afirma benchmark live sin una prueba real con API key.

No se implementa en el MVP la conexión inversa `ChatGPT → FPS` mediante MCP.

### DG-REP-01 — Estructura final de informes
Estado: `APPROVED`

Decisión: **B — informes profesionales específicos para entrenador, alimentados por los mismos insights estructurados**.

Entregables actuales:

- Team Report;
- Player Report;
- Match Report.

Los PDF son una representación estática profesional y no una segunda lógica de negocio. Un export directo del dashboard no es requisito del TFM actual.

## Gate pendiente

### DG-PUB-01 — Dataset público
Estado: `PENDING SERGI / DEPENDE DE DERECHOS`

Opciones:

- A. dataset profesional anonimizado si existe permiso explícito de redistribución;
- B. dataset sintético reproducible;
- C. dataset abierto con licencia compatible.

Regla: anonimizar técnicamente nombres e identificadores no concede derechos de redistribución.

Mientras no exista permiso explícito, no se publica la base profesional. La demo sintética separada sí es redistribuible según su contrato actual.

## Decisiones operativas derivadas

Estas reglas no requieren un nuevo gate mientras no cambie su significado estructural:

- Collector conserva la semántica actual; sus cambios inmediatos son UX, castellano y responsive;
- Product Spiral solo puede mutar archivos de presentación autorizados y nunca hace push/merge automático;
- el gate visual humano es obligatorio para dashboard y PDF;
- las capas superiores no pueden inventar métricas o recomendaciones no existentes en capas inferiores;
- no reabrir DATA / FEATURES / EXPERT / MATCH RATING sin incidencia concreta o evidencia nueva;
- no volver al patrón `usuario prueba frases al azar → se añade una regla`: la cobertura del Assistant se gobierna mediante contrato + tests + CI;
- despliegue público del dataset profesional continúa bloqueado mientras no se decida expresamente lo contrario.

## Regla de uso

El Architect solo presenta a Sergi un Decision Gate cuando realmente bloquea el siguiente trabajo.

No se piden decisiones sobre detalles técnicos ordinarios o reversibles.

Toda nueva decisión estructural aprobada debe registrarse aquí y, si cambia el estado operativo, reflejarse también en `PROJECT_STATE.md`.
