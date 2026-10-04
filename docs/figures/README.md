# Figuras reproducibles del TFM

Fecha: 03/10/2026

Estas figuras están construidas como SVG versionables en Git. Representan arquitectura y contratos del producto; no contienen datos deportivos inventados.

## Figura 1 — Arquitectura general

Archivo: `tfm_architecture_overview.svg`

Pie recomendado:

> **Figura 1. Arquitectura general del Football Performance System.** El flujo separa captura/normalización, generación de features, analítica, sistema de decisión y capas de presentación. El GPS es opcional y el asistente IA opera downstream de resultados estructurados.

Fuente: elaboración propia a partir de la arquitectura implementada.

## Figura 2 — Coach Copilot y grounding

Archivo: `tfm_llm_grounding.svg`

Pie recomendado:

> **Figura 2. Arquitectura del Coach Copilot.** El modelo de lenguaje recibe evidencia a través de herramientas de solo lectura después de las capas de analítica y decisión. El LLM no recalcula métricas críticas ni crea recomendaciones no validadas.

Fuente: elaboración propia.

## Figura 3 — Control temporal strict-past

Archivo: `tfm_strict_past.svg`

Pie recomendado:

> **Figura 3. Estrategia de control temporal strict-past.** Para una observación en fecha t solo se utilizan datos con fecha estrictamente anterior, evitando contaminación con información futura o del mismo instante de evaluación.

Fuente: elaboración propia.

## Figura 4 — Sistema experto

Archivo: `tfm_expert_system.svg`

Pie recomendado:

> **Figura 4. Estructura jerárquica del sistema experto N1000–N13000.** Las familias de evidencia convergen hacia capas de rol, consistencia y player-fit; N13000 actúa como gate final y puede abstenerse de emitir una recomendación cuando no existe una policy validada.

Fuente: elaboración propia.

## Figura 5 — Modelo de datos simplificado

Archivo: `tfm_data_model.svg`

Pie recomendado:

> **Figura 5. Modelo de datos simplificado.** El diseño separa entidades maestras, observaciones raw/normalizadas, variables derivadas y resultados de decisión, utilizando player-match como unidad analítica principal.

Fuente: elaboración propia.

---

## Reglas de uso

- No utilizar estos diagramas como evidencia de eficacia deportiva; representan diseño e implementación.
- Mantener los pies en castellano en la memoria.
- Si la plantilla de la universidad exige PNG, exportar estos SVG sin modificar su contenido.
- Las capturas reales de Collector, dashboard, Coach Copilot y PDF ya están disponibles en `docs/screenshots/` y deben integrarse en la memoria durante la maquetación.
- No sustituir las capturas reales por mockups.
