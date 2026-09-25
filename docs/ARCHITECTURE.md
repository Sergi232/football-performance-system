# Arquitectura v1 — Football Performance System

Estado: **ARCHITECTURE-01 / propuesta congelable**  
Fecha: 25/09/2026

Este documento define la arquitectura de referencia del producto. Si un cambio futuro contradice esta arquitectura, debe justificarse mediante una decisión documentada en `docs/DECISIONS.md`.

## 1. Objetivo del producto

Producto web para equipos amateur o semiprofesionales sin departamento de análisis que transforme datos realistas de vídeo y GPS opcional en información útil, auditable y explicable para el cuerpo técnico.

La web es el producto principal. El LLM y los PDF son capas de interacción/presentación, no motores de cálculo.

## 2. Principio arquitectónico central

```text
CAPTURA / IMPORT
        ↓
RAW DATA
        ↓
NORMALIZED DATA
        ↓
FEATURE ENGINE
        ↓
ANALYTICS ENGINE
        ↓
DECISION ENGINE
        ↓
PRODUCT SERVICE LAYER
        ↓
WEB / REPORTS / AI ASSISTANT
```

Regla: **una capa superior no puede inventar cálculos, métricas, rankings o recomendaciones que no existan en una capa inferior validada**.

## 3. Capas y responsabilidades

### L0 — Governance / Architecture

Responsable de:
- contratos entre módulos;
- decisiones arquitectónicas;
- gates de aprobación;
- orden de trabajo;
- estado del proyecto;
- evitar duplicidades y parches incompatibles.

Fuente de verdad: GitHub (`PROJECT_STATE.md`, `docs/ARCHITECTURE.md`, `docs/WORKFLOW.md`, `docs/DECISIONS.md`).

### L1 — Capture / Import

Incluye:
- Data Collector de vídeo;
- imports de datos externos;
- GPS opcional y multi-proveedor.

Responsabilidad: recoger hechos observables y trazables con coste realista para fútbol amateur.

No calcula conclusiones.

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

Debe preservar ausencia y ambigüedad. No rellena datos mediante supuestos silenciosos.

### L3 — Feature Engine

Responsabilidad: convertir raw data en variables derivadas reproducibles.

Permitido:
- ratios;
- per90;
- históricos strict-past;
- tendencias matemáticas;
- variabilidad;
- features condicionadas a rol;
- features físicas cuando exista GPS y definición validada.

No decide si un valor es bueno/malo ni recomienda.

### L4 — Analytics Engine

Esta es la principal capa todavía incompleta.

Responsabilidad: convertir features en evidencia analítica estructurada.

Debe resolver, de forma explícita y validada:
- evolución;
- cambio;
- consistencia;
- comparación;
- contexto;
- suficiencia de muestra;
- incertidumbre;
- alertas analíticas descriptivas.

Salida esperada: objetos/resultados estructurados que puedan consumir Expert System, dashboard, reports y assistant.

### L5 — Decision Engine

Incluye el sistema experto N1000–N13000 y, cuando proceda, modelos validados.

Cada resultado debe conservar:

```text
input → condition → result → confidence → justification
```

No se emite recomendación final sin política validada.

### L6 — ML Layer

ML es complementario y posterior al baseline determinista/experto.

Casos posibles:
- similitud entre jugadores;
- clasificación de perfiles;
- detección de cambios;
- role-fit;
- comparación Expert vs ML.

No se incorpora si no existe dataset suficiente y una hipótesis clara.

### L7 — Product Service Layer

Capa intermedia obligatoria entre motores y interfaces.

Responsabilidad:
- consultas comunes TEAM / PLAYER / MATCH;
- payloads estructurados;
- provenance;
- restricciones de acceso;
- selección de insights;
- evitar que web, PDF y LLM reimplementen lógica.

Objetivo: una misma verdad analítica alimenta todas las salidas.

### L8 — Web Product

Modos:
- TEAM MODE — principal;
- PLAYER MODE — complementario;
- MATCH VIEW;
- RIVAL MODE — futuro.

La interfaz final será **insight-first**, no table-first. Las tablas quedan como auditoría/detalle.

La web debe responder preguntas del entrenador antes de mostrar el detalle numérico.

### L9 — AI Assistant

Arquitectura obligatoria:

```text
DATA → ANALYTICS → DECISION ENGINE → PRODUCT CONTEXT → LLM → COACH
```

El LLM puede:
- interpretar preguntas;
- explicar resultados;
- resumir;
- redactar texto;
- navegar evidencia.

No puede:
- crear métricas críticas;
- inventar datos;
- recalcular rankings;
- saltarse N13000;
- sustituir el motor analítico.

Proveedor final (local/cloud/híbrido) se decide mediante gate específico.

### L10 — Reporting

Player / Match / Team-period reports.

Los informes consumen la misma Product Service Layer que la web.

Principio final: el PDF debe ser una representación estática profesional de insights ya calculados, no una tabla exportada ni una segunda lógica de negocio.

### L11 — QA / Publication

Responsabilidad:
- tests;
- regresión;
- leakage checks;
- privacidad;
- anonimización;
- instalación limpia;
- demo publicable;
- GitHub;
- documentación TFM.

## 4. Orden obligatorio de desarrollo

```text
ARCHITECTURE-01
        ↓
ANALYTICS-01
        ↓
DECISION POLICY / N13000
        ↓
PRODUCT UX
        ↓
REPORTS-02
        ↓
ASSISTANT ARCHITECTURE
        ↓
ML (solo si aporta valor)
        ↓
FINAL PRODUCT / PUBLICATION
```

No se continúa una capa si necesita una definición no cerrada de la capa anterior.

## 5. Qué reutilizamos del prototipo v0.1

Se conserva como infraestructura válida:
- DuckDB y esquema base;
- Collector funcional;
- normalización GPS;
- FEATURE-01/02/03;
- sistema experto N1000–N13000 como baseline auditable;
- `app.data_access` y contratos read-only;
- guardrails del assistant;
- tooling de PDF como prueba técnica;
- tooling de anonimización/publication;
- tests existentes.

No se considera producto final todavía:
- UX actual de Streamlit;
- PDF actual de ReportLab;
- routing LLM definitivo;
- política final N13000;
- presentación de insights.

## 6. Regla de decisiones

No se pide aprobación para decisiones técnicas reversibles u ordinarias.

Se abre un **Decision Gate** solo si la elección puede alterar uno de estos elementos:
1. significado deportivo;
2. arquitectura o dependencias entre capas;
3. política de recomendación;
4. experiencia principal del usuario;
5. privacidad / proveedor LLM;
6. derechos de publicación;
7. metodología académica relevante.

El resto lo decide el responsable técnico/arquitecto y se documenta si es necesario.

## 7. Gates estructurales previstos

- `DG-AN-01` — comparaciones analíticas válidas;
- `DG-N13-01` — qué constituye una recomendación y con qué evidencia;
- `DG-UX-01` — jerarquía final TEAM / PLAYER / MATCH;
- `DG-LLM-01` — local / cloud / híbrido;
- `DG-REP-01` — estructura de informes profesionales;
- `DG-PUB-01` — dataset públicamente redistribuible.

Solo estos gates, o equivalentes de impacto comparable, requieren intervención explícita del usuario.

## 8. Regla de transición entre fases

Cada fase debe terminar con:

```text
INPUT CONTRACT
IMPLEMENTATION
VALIDATION
OUTPUT CONTRACT
OPEN RISKS
NEXT UNLOCKED PHASE
```

Si la validación falla, no se parchea la interfaz para ocultarlo: se corrige en la capa propietaria del problema.

## 9. Fuente de verdad

Orden de prioridad:

1. `PROJECT_STATE.md` — estado operativo actual;
2. `docs/ARCHITECTURE.md` — arquitectura vigente;
3. `docs/DECISIONS.md` — decisiones estructurales y gates;
4. `docs/WORKFLOW.md` — orden de trabajo y agentes;
5. README — presentación e instalación.

Los chats sirven para trabajar, pero GitHub conserva la memoria técnica definitiva.
