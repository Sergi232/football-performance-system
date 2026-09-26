# Registro de decisiones estructurales

Fecha: 26/09/2026

Este archivo contiene únicamente decisiones que pueden cambiar arquitectura, metodología, producto, privacidad o publicación. No se usa para detalles técnicos rutinarios.

Estados:
- `APPROVED`
- `PENDING SERGI`
- `DEFERRED`
- `REJECTED`

## Decisiones ya aprobadas

### D-001 — TEAM MODE como producto principal
Estado: `APPROVED`

TEAM MODE es el modo principal. PLAYER MODE es complementario. RIVAL MODE queda como extensión futura y el sistema principal no depende de datos del rival.

### D-002 — GPS opcional
Estado: `APPROVED`

El producto funciona sin GPS. GPS añade contexto físico cuando existe.

### D-003 — LLM fuera del cálculo crítico
Estado: `APPROVED`

Arquitectura obligatoria:

```text
DATA → ANALYTICS → DECISION ENGINE → LLM → COACH
```

El LLM no crea métricas críticas ni sustituye decisiones del motor.

### D-004 — Sistema experto auditable antes de ML
Estado: `APPROVED`

El baseline principal es un sistema jerárquico N1000–N13000. ML se añade después y debe compararse con el baseline cuando tenga sentido.

### D-005 — No recomendación N13000 sin policy validada
Estado: `APPROVED`

Hasta validar evidencia, mínimos de muestra, reglas y significancia práctica, N13000 no emite recomendación táctica final.

### D-006 — Web como producto principal
Estado: `APPROVED`

Los PDF son exportaciones/entregables estáticos. No sustituyen la aplicación web.

### D-007 — GitHub como fuente de verdad
Estado: `APPROVED`

`PROJECT_STATE.md`, arquitectura, workflow y decisiones documentadas prevalecen sobre conversaciones antiguas.

### D-008 — Rendimiento como objetivo analítico principal
Estado: `APPROVED`

El objetivo central de la capa analítica/DS es construir un **score de rendimiento jugador-partido** defendible, auditable y útil para el entrenador.

El flujo objetivo pasa a ser:

```text
PLAYER-MATCH DATA
→ DIMENSIONES DE RENDIMIENTO
→ SCORE GLOBAL VALIDADO
→ EVOLUCIÓN / CONSISTENCIA
→ CONTEXTO DE ROL
→ CONCLUSIONES / RECOMENDACIONES
```

El rol o la posición no son el target principal. Se usan para contextualizar, normalizar o comparar rendimiento cuando existe una etiqueta observada fiable.

No se autoriza todavía ninguna fórmula de score, peso, signo, percentil o escala final. Esos elementos deben justificarse con datos, literatura, validación externa, criterio experto o experimentación reproducible.

### D-009 — Anchor externo: semántica antes que coincidencia lexical
Estado: `APPROVED`

Un campo profesional solo puede actuar como candidato a anchor externo del score si representa una **valoración individual holística e independiente** del jugador.

No basta con que el nombre contenga `score`, `rating`, `grade`, `index` o `rank`.

Quedan excluidos como anchors:
- resultados/contexto de partido o equipo (`home_score`, `away_score`);
- estadísticas componentes del propio rendimiento (`bigChanceScored`, goles, tiros, pases, etc.);
- variables que después formen parte de los inputs del producto.

Un anchor válido, si existe, se usa únicamente para validación/aprendizaje experimental y nunca como input obligatorio del sistema amateur.

### DG-AN-01 — Comparaciones analíticas válidas
Estado: `APPROVED`

Decisión: **C — ambas, separadas y explícitamente etiquetadas**.

Analytics conserva dos evidencias distintas:
- `SELF_ROLE_PRIOR`: jugador vs su propio historial estrictamente anterior en el mismo rol observado;
- `PEER_ROLE_PRIOR`: jugador vs otros jugadores del mismo equipo con el mismo rol observado, usando solo información estrictamente anterior.

No se mezclan silenciosamente en un único score. La comparación peer excluye al jugador actual y cada peer aporta su media strict-past en ese rol antes de construir la distribución de referencia.

### DG-N13-01 — Política final de recomendación
Estado: `APPROVED`

Decisión: **C — recomendación + confianza + justificación + alternativa/limitaciones** como contrato objetivo de N13000.

Cuando la policy esté validada, una salida final podrá incluir:
- recomendación;
- confianza o calibración;
- evidencia que la soporta;
- justificación auditable;
- limitaciones;
- alternativa cuando proceda.

Esta aprobación no fija todavía umbrales, pesos ni reglas de confianza. Esos componentes deben validarse con estadística, experimentos DS/ML y literatura cuando corresponda. Hasta entonces N13000 mantiene `RECOMMENDATION_NOT_ISSUED_*`.

## Gates pendientes

### DG-UX-01 — Jerarquía de producto
Estado: `PENDING SERGI`

**Por qué importa:** define el rediseño de TEAM / PLAYER / MATCH.

Opciones:
- A. exploración de tablas/datos como vista principal;
- B. insights/alertas como vista principal y datos como segundo nivel;
- C. híbrido con igual peso.

Recomendación arquitectónica: **B**.

### DG-LLM-01 — Arquitectura final del asistente
Estado: `PENDING SERGI`

**Por qué importa:** privacidad, instalación, coste, rendimiento y despliegue.

Opciones:
- A. cloud only;
- B. local only;
- C. local-first + cloud opcional + fallback determinista;
- D. determinista sin LLM generativo.

Recomendación arquitectónica: **C**, si el hardware objetivo lo permite. El provider debe ser intercambiable y no afectar a Analytics/Decision Engine.

### DG-REP-01 — Estructura final de informes
Estado: `PENDING SERGI`

**Por qué importa:** el PDF actual es prueba técnica, no entregable final.

Opciones:
- A. export directo del dashboard;
- B. informe profesional específico para entrenador, alimentado por los mismos insights;
- C. ambos.

Recomendación arquitectónica: **C**, con B como entregable principal y A como export rápido opcional.

### DG-PUB-01 — Dataset público
Estado: `PENDING SERGI / DEPENDE DE DERECHOS`

Opciones:
- A. dataset profesional anonimizado si existe permiso explícito;
- B. dataset sintético reproducible;
- C. dataset abierto con licencia compatible.

Regla: no publicar la DB profesional anonimizando únicamente nombres si la licencia no permite redistribución.

## Regla de uso

No se deben preguntar todos estos gates a la vez si no son necesarios para la fase activa.

El Architect solo presenta a Sergi el gate que bloquea el siguiente trabajo. La decisión se registra aquí y se actualiza `PROJECT_STATE.md`.
