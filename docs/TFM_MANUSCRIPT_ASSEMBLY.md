# TFM — Estructura canónica de ensamblaje de la memoria

Fecha: 03/10/2026
Estado: estructura académica de referencia hasta disponer de la plantilla/rúbrica oficial.
Idioma: castellano.

## Objetivo

Evitar que la memoria final se convierta en una suma de documentos técnicos inconexos. Este archivo define el orden académico final, qué documento alimenta cada capítulo y qué contenido debe quedar en cuerpo principal o en anexos.

La memoria final deberá redactarse como un único texto. Los documentos auxiliares de `docs/TFM_*` son fuentes de trabajo, no capítulos independientes para entregar tal cual.

---

# Estructura final propuesta

## Portada

Pendiente de adaptar a la plantilla oficial de la universidad.

## Resumen

Fuente principal:
- `docs/TFM_MEMORIA_BASE.md`.

Debe explicar en 200–300 palabras:
- problema;
- objetivo;
- arquitectura;
- validación;
- principal resultado;
- limitación principal.

No incluir métricas secundarias ni lista de tecnologías.

## Abstract

Traducción académica del resumen final al inglés.

## Palabras clave

Propuesta:

```text
football analytics
performance analysis
expert systems
data engineering
GPS
large language models
reproducibility
```

---

# 1. Introducción

Fuente:
- `docs/TFM_MEMORIA_BASE.md`;
- `docs/TFM_MARCO_TEORICO_REFERENCIAS.md`.

Contenido:
- problema de accesibilidad analítica en fútbol amateur/semiprofesional;
- diferencia respecto a soluciones profesionales;
- motivación del producto;
- alcance real;
- contribución del TFM.

La introducción no debe adelantar todo el detalle técnico.

---

# 2. Estado del arte y marco teórico

Fuente canónica:
- `docs/TFM_MARCO_TEORICO_REFERENCIAS.md`.

Subapartados:

```text
2.1 Performance analysis en fútbol
2.2 Metodología observacional y análisis notacional
2.3 Contexto, indicadores y evolución
2.4 GPS y carga externa
2.5 Data leakage en datos longitudinales
2.6 Sistemas expertos e interpretabilidad
2.7 LLM, grounding y uso de herramientas
2.8 Reproducibilidad computacional
```

Regla:
- literatura externa justifica principios;
- no utilizar literatura para atribuir al producto validaciones que no se han realizado.

---

# 3. Hipótesis y objetivos

Fuente:
- `PROJECT_STATE.md`;
- `docs/TFM_MEMORIA_BASE.md`.

## 3.1 Hipótesis

> Un equipo de fútbol amateur o semiprofesional puede disponer de un sistema integral y auditable de soporte a la decisión a partir de datos de vídeo y GPS opcional, capaz de transformarlos en información sobre rendimiento, evolución, rol y comportamiento físico de los jugadores y del equipo.

Aclarar que se contrasta como hipótesis de viabilidad técnica/arquitectónica, no como hipótesis causal de mejora deportiva.

## 3.2 Objetivo general

Diseñar, implementar y validar un sistema reproducible de análisis de rendimiento basado en datos realistas para un contexto sin departamento profesional de análisis.

## 3.3 Objetivos específicos

Usar la lista ya definida en `TFM_MEMORIA_BASE.md`.

---

# 4. Metodología

Fuente canónica:
- `docs/TFM_METHODOLOGY_DRAFT.md`.

Orden final:

```text
4.1 Enfoque metodológico
4.2 Selección de variables y Collector
4.3 Modelo de datos
4.4 Feature Engine
4.5 Analytics Engine
4.6 Match Rating / Performance Index
4.7 Sistema experto
4.8 ML experimental
4.9 GPS opcional
4.10 Aplicación web
4.11 Coach Copilot
4.12 Informes PDF
4.13 Estrategia de validación
4.14 Reproducibilidad y CI
```

No convertir esta sección en documentación de API o listado de archivos. El detalle de scripts debe ir a anexos.

---

# 5. Arquitectura e implementación del producto

Fuentes:
- `docs/ARCHITECTURE.md`;
- `README.md`;
- `docs/TFM_FIGURES_TABLES_PLAN.md`.

Objetivo: mostrar cómo la metodología se materializa en producto.

Figuras prioritarias:
- arquitectura general;
- DATA → ANALYTICS → DECISION → LLM;
- modelo de datos simplificado;
- strict-past;
- sistema experto N1000-N13000.

Mantener esta sección visual y estructural; evitar repetir toda la metodología.

---

# 6. Resultados

Fuente canónica:
- `docs/TFM_RESULTS_DRAFT.md`;
- control mediante `docs/TFM_EVIDENCE_MATRIX.md`.

Orden recomendado:

```text
6.1 Collector
6.2 Data / Feature Engine
6.3 Analytics
6.4 Sistema experto
6.5 Match Rating
6.6 GPS
6.7 Producto / dashboard
6.8 Coach Copilot
6.9 Reports
6.10 QA global
6.11 Demo sintética y CI
6.12 Contraste técnico de la hipótesis
```

Regla estricta:
- un resultado cuantitativo solo entra si existe gate/validator reproducible;
- separar siempre caso profesional de desarrollo y demo sintética.

---

# 7. Discusión

Fuente canónica:
- `docs/TFM_DISCUSSION_CONCLUSIONS_DRAFT.md`.

Estructura:

```text
7.1 Viabilidad general del sistema
7.2 Collector y coste de captura
7.3 Separación de capas y auditabilidad
7.4 Leakage y análisis longitudinal
7.5 Match Rating y generalización
7.6 Sistema experto y abstención
7.7 ML como complemento
7.8 GPS y límites fisiológicos
7.9 Coach Copilot y grounding
7.10 Reproducibilidad
7.11 Contraste de la hipótesis
```

La discusión debe relacionar resultados propios con literatura, no repetir cifras.

---

# 8. Limitaciones

Fuente:
- `docs/TFM_DISCUSSION_CONCLUSIONS_DRAFT.md`;
- `docs/TFM_EVIDENCE_MATRIX.md`.

Limitaciones obligatorias:
- sin validación formal con entrenadores;
- sin estudio interobservador;
- Match Rating sin ground truth universal externo;
- GPS real insuficiente para cerrar inferencias físicas expertas;
- N13000 sin policy de recomendación validada;
- autenticación real no implementada;
- derechos del dataset profesional no resueltos para redistribución.

---

# 9. Conclusiones y trabajo futuro

Fuente:
- `docs/TFM_DISCUSSION_CONCLUSIONS_DRAFT.md`.

Conclusión central:

> La propuesta es técnicamente viable, funcional y reproducible como arquitectura de soporte al análisis de rendimiento. Su impacto real sobre decisiones de entrenadores y rendimiento deportivo requiere validación adicional con usuarios, datos reales adicionales y ground truth independiente.

Trabajo futuro prioritario:
- interobservador;
- entrenadores/analistas reales;
- GPS real;
- validación externa Match Rating;
- policy N13000;
- experto vs ML;
- automatización parcial por visión artificial;
- autenticación/despliegue si se resuelven derechos.

---

# Referencias

Fuente canónica:
- bibliografía de `docs/TFM_MARCO_TEORICO_REFERENCIAS.md`.

Formato final pendiente de la norma bibliográfica exigida por la universidad.

---

# Anexos

## Anexo A — Taxonomía Collector

Fuente:
- `collector/event_catalog.json`;
- `collector/COLLECTOR_MVP.md`.

## Anexo B — Esquema de datos

Fuente:
- `data/schema.sql`;
- `data/migrations/`.

## Anexo C — Catálogo de features

Fuente:
- `features/`.

## Anexo D — Sistema experto

Fuente:
- `decision_tree/`;
- tabla N1000-N13000.

## Anexo E — Validadores y QA

Fuente:
- tests;
- validators;
- `TFM_EVIDENCE_MATRIX.md`.

## Anexo F — Reproducibilidad

Fuente:
- `publication/README.md`;
- `.github/workflows/tests.yml`.

## Anexo G — Capturas de producto

- Collector;
- Team Mode;
- Player Mode;
- Match Mode;
- GPS;
- Coach Copilot;
- PDF.

---

# Qué debe quedarse fuera del cuerpo principal

Mover a anexos o repositorio:

- logs completos de tests;
- rutas locales de Windows;
- comandos de PowerShell;
- nombres de commits salvo cuando sean relevantes para trazabilidad;
- listados completos de tablas y campos;
- cada versión histórica de scripts;
- errores de desarrollo ya resueltos;
- detalles de implementación sin función metodológica.

---

# Estado actual de redacción

```text
Introducción / hipótesis       BASE DISPONIBLE
Marco teórico                  BORRADOR COMPLETO
Metodología                    BORRADOR COMPLETO
Arquitectura                   DOCUMENTADA
Resultados                     BORRADOR COMPLETO
Discusión                      BORRADOR COMPLETO
Limitaciones                   BORRADOR COMPLETO
Conclusiones                   BORRADOR COMPLETO
Bibliografía                   BASE CURADA
Plan de figuras/tablas         DEFINIDO
Anexos                         ESTRUCTURA DEFINIDA
Plantilla universitaria        PENDIENTE
Figuras/capturas finales       PENDIENTE
Maquetación final              PENDIENTE
Defensa                        PENDIENTE
```

## Próximo paso

La siguiente fase no es redactar más texto genérico. Es producir **evidencia visual y tablas reproducibles** y después ensamblar el manuscrito según la plantilla oficial cuando esté disponible.