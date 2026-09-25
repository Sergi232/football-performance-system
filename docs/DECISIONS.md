# Registro de decisiones estructurales

Fecha: 25/09/2026

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

## Gates pendientes

### DG-AN-01 — Comparaciones analíticas válidas
Estado: `PENDING SERGI`

**Por qué importa:** define Analytics, Player Fit, rankings futuros y parte de N13000.

Opciones:
- A. jugador vs su propio historial, condicionado a rol;
- B. jugador vs pares del mismo rol;
- C. ambas, separadas y explícitamente etiquetadas.

Recomendación arquitectónica: **C**, manteniendo self-history y peer comparison como evidencias distintas, nunca mezcladas silenciosamente.

No bloquea definir la infraestructura de Analytics, pero debe cerrarse antes de emitir comparaciones evaluativas finales.

### DG-N13-01 — Política final de recomendación
Estado: `PENDING SERGI`

**Por qué importa:** determina si el sistema solo describe, alerta o recomienda acciones/roles.

Opciones:
- A. evidencia y alertas, sin recomendación final;
- B. recomendación solo cuando se superan criterios validados;
- C. recomendación + confianza + justificación + alternativa/limitaciones.

Recomendación arquitectónica: **C como objetivo final**, construida de forma incremental; mientras no esté validada, mantener el gate actual sin recomendación.

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
