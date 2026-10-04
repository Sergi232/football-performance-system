# TFM — Borrador de discusión y conclusiones

Fecha: 04/10/2026
Estado: borrador académico para integrar en la memoria final.
Idioma: castellano.

Este documento interpreta los resultados del prototipo a la luz del marco teórico documentado en `docs/TFM_MARCO_TEORICO_REFERENCIAS.md`. La discusión distingue explícitamente entre viabilidad técnica demostrada y eficacia deportiva no demostrada.

---

# 1. Discusión general

El principal resultado del TFM es la construcción de un sistema end-to-end capaz de transformar datos simples de vídeo y GPS opcional en información estructurada para equipo, jugador y partido. El sistema no se limita a una métrica aislada: integra captura, almacenamiento, feature engineering, analítica, sistema experto, dashboard, asistente IA y reporting dentro de una arquitectura auditable.

Este resultado encaja con la literatura de performance analysis que defiende una lectura contextual y multidimensional del rendimiento en fútbol. Mackenzie y Cushion (2013), Sarmento et al. (2014) y Sarmento et al. (2022) advierten contra interpretaciones reduccionistas basadas en un único indicador. La arquitectura implementada responde a este problema separando observaciones, features, evidencia analítica y decisión.

La aportación del trabajo no consiste en afirmar que la arquitectura sea óptima universalmente, sino en demostrar que es técnicamente viable construir una solución relativamente ligera sin depender de un proveedor profesional de tracking o de un LLM como motor principal de cálculo.

---

# 2. Data Collector: utilidad práctica frente a complejidad

Una de las decisiones más relevantes fue limitar el Collector a hechos observables y razonablemente registrables.

La literatura de análisis notacional y metodología observacional insiste en la necesidad de definiciones operacionales claras y categorías estandarizadas (James, 2006; Sarmento et al., 2014; Ortega-Toro et al., 2019). El Collector V1.1 adopta esta lógica mediante una taxonomía explícita y congelada.

El trade-off es deliberado. El sistema renuncia a capturar manualmente variables avanzadas como xG, PPDA o pressing estructural si su coste operativo o ambigüedad supera su utilidad en un contexto amateur.

Esta simplificación mejora la viabilidad práctica del producto, pero introduce una limitación importante: el TFM ha validado el contrato técnico del Collector, no su fiabilidad interobservador en un estudio experimental con varios analistas. Por tanto, no puede afirmarse todavía que dos observadores distintos produzcan exactamente la misma codificación ante un mismo partido.

---

# 3. Separación raw → features → analytics → decisión

La separación por capas constituye una de las fortalezas metodológicas del sistema.

En lugar de guardar directamente interpretaciones finales, el producto conserva los hechos observados y deriva después features, evidencia y decisiones. Esto permite auditar una salida y evita que una conclusión quede oculta dentro de una única función o modelo opaco.

La literatura sobre interpretabilidad apoya el valor de modelos intrínsecamente comprensibles cuando la trazabilidad es importante (Rudin, 2019). El TFM aplica este principio no solo al sistema experto, sino a toda la arquitectura.

Esta decisión también facilita corregir errores sin reconstruir el producto completo. Por ejemplo, la corrección de N9000 permitió cambiar qué GPS se consideraba evidencia observada sin alterar la taxonomía del Collector, el Match Rating o la capa LLM.

---

# 4. Control temporal y data leakage

El uso de `strict-past` en FEATURE-02, FEATURE-03 y ANALYTICS-01 es metodológicamente relevante.

Kaufman et al. (2012) muestran que el leakage puede producir resultados aparentemente sólidos pero inviables en producción. En un sistema longitudinal de fútbol, utilizar información del futuro o del mismo momento que la decisión invalidaría cualquier evaluación de evolución o contexto previo.

El proyecto evita este problema utilizando únicamente observaciones con fecha estrictamente anterior.

Esta elección fortalece la validez interna de las comparaciones históricas del prototipo. Sin embargo, controlar leakage no garantiza por sí mismo que una feature sea deportivamente relevante: solo garantiza que la información utilizada era legítimamente disponible en ese momento.

---

# 5. Match Rating: cobertura frente a validez universal

El Match Rating V5 cubre las 590 apariciones jugadas del caso profesional de desarrollo y mantiene rutas específicas para jugadores de campo y porteros, además de un fallback explícito cuando no existe rol fiable.

Desde el punto de vista de producto, la cobertura completa resuelve una necesidad práctica: disponer de una valoración inmediata desde el primer partido.

No obstante, la cobertura técnica no equivale a validez universal. El rating está diseñado sobre un conjunto concreto de variables, reglas y pesos. La literatura de performance analysis señala que los indicadores dependen del contexto, posición y situación competitiva. Por tanto, el Match Rating debe interpretarse como una herramienta interna del sistema y no como una verdad objetiva sobre el rendimiento futbolístico.

La decisión de congelar V5 tras su validación técnica evita modificar pesos de forma arbitraria. Una futura revalidación con entrenadores, analistas o outcomes independientes permitiría evaluar si la nota se alinea con criterios externos de rendimiento.

---

# 6. Sistema experto y decisión conservadora

El sistema experto N1000-N13000 fue diseñado para mantener trazabilidad y degradar de forma explícita cuando falta evidencia.

Esta estrategia es coherente con el uso de sistemas basados en reglas descrito por Liu et al. (2016) y con la preferencia por interpretabilidad defendida por Rudin (2019) cuando una decisión necesita explicación.

El resultado más importante del sistema experto no es que emita muchas recomendaciones, sino precisamente que puede abstenerse de hacerlo.

N13000 devuelve estados como:

```text
NO_EVIDENCE
POLICY_UNVALIDATED
ROLE_UNKNOWN
```

Esto evita convertir diferencias estadísticas en recomendaciones tácticas sin una policy defendible.

La limitación es clara: el sistema todavía no puede presentarse como un motor validado de optimización de roles o alineaciones. Para ello sería necesario definir ground truth, pesos, thresholds y una estrategia de evaluación independiente.

---

# 7. Machine Learning: complejidad solo cuando aporta valor

El proyecto no utiliza ML como requisito decorativo.

Las líneas experimentales de change detection, similitud y clasificación de posición se trataron como pruebas separadas del producto principal. La política fue comparar modelos con reglas simples y no desplegar un modelo cuando no existiera una mejora defendible o un target independiente.

Este criterio evita dos problemas frecuentes:

- introducir complejidad sin necesidad;
- entrenar modelos sobre targets construidos circularmente a partir de la misma lógica que se pretende evaluar.

La conclusión no es que ML sea innecesario, sino que su incorporación debe depender de la calidad y volumen de datos disponibles.

---

# 8. GPS: integración funcional sin sobreinterpretación fisiológica

La integración GPS demuestra que el sistema puede normalizar observaciones de distintos proveedores y producir resúmenes físicos descriptivos.

La literatura muestra que GPS puede ser útil para cuantificar carga externa, pero que su validez depende del dispositivo y de la variable, con mayores limitaciones en velocidad alta, cambios rápidos y determinados movimientos (Scott et al., 2016). Miguel et al. (2021) también muestran heterogeneidad en las medidas de carga utilizadas en fútbol.

El proyecto responde de forma conservadora:

```text
GPS raw
→ normalización
→ resumen descriptivo
```

No se transforma automáticamente distancia o velocidad en fatiga, readiness o riesgo de lesión.

Hader et al. (2019) refuerzan la prudencia ante inferencias fuertes a partir de variables simples de carga externa.

Esta limitación es una fortaleza metodológica del TFM: la ausencia de una conclusión no se trata como un fallo cuando la evidencia no permite sostenerla.

---

# 9. Coach Copilot: lenguaje natural sin trasladar el cálculo al LLM

La evolución del Coach Copilot mostró que usar un LLM en cada turno no era la solución más robusta ni eficiente para el hardware objetivo. Los benchmarks previos con distintos modelos permitieron comprobar que el routing semántico podía funcionar, pero con latencias elevadas y comportamientos espontáneos inconsistentes en algunas consultas.

La arquitectura final cambió el problema: en lugar de validar una lista creciente de frases, se modeló un espacio de consultas composicional basado en:

```text
entidad + operación + métrica + agregación + rol + filtros + ventana + contexto conversacional
```

Además, un preflight determinista resuelve ruido, meta-consultas y preguntas claramente fuera del dominio antes de considerar cualquier modelo generativo.

Las consultas de alta confianza se resuelven de forma determinista:

```text
QUESTION
→ PREFLIGHT / GUARDRAILS
→ DETERMINISTIC ROUTER
→ READ-ONLY TOOL
→ PYTHON / DUCKDB
→ STRUCTURED EVIDENCE
→ FACTUAL ANSWER
```

Solo el lenguaje ambiguo que permanece dentro del dominio puede activar `qwen3.5:4b` como router semántico local. El modelo no calcula métricas ni redacta por su cuenta rankings numéricos críticos.

La validación real final obtuvo:

```text
SMOKE CONTRACT: PASS (28/28)
average_elapsed=0.4s
semantic rounds=0 en los 28 casos finales
```

El dato de 0,4 s debe interpretarse correctamente: corresponde a esa batería concreta en el PC de desarrollo y a una ruta final completamente determinista/preflight. No es un SLA universal ni mide la latencia del fallback Qwen. Las consultas ambiguas que sí requieran inferencia semántica local pueden seguir siendo considerablemente más lentas en CPU.

La ampliación del contrato a comparaciones por posición también evita introducir nuevos scores ad hoc. Cuando se pregunta quién ha rendido mejor dentro de una posición, se utiliza como criterio explícito el Match Rating medio dentro de la muestra de ese rol y el resto de métricas se presenta como evidencia descriptiva.

La arquitectura reduce dos riesgos documentados en la literatura:

- hallucinations y falta de fidelidad factual en LLM (Huang et al., 2025);
- dependencia innecesaria de un modelo generativo cuando la consulta puede resolverse con herramientas estructuradas (Lewis et al., 2020; Schick et al., 2023).

## 9.1 Proveedor OpenAI opcional

La aplicación incorpora además un modo `OpenAI API · clave propia`.

Este modo no sustituye el motor analítico ni obliga a enviar cada consulta al proveedor externo. Las preguntas claras continúan siendo deterministas y no consumen API. Para lenguaje ambiguo, OpenAI puede seleccionar únicamente tools FPS bounded/read-only y cada llamada se revalida localmente antes de ejecutarse.

Por tanto, el flujo mantiene:

```text
OPENAI
→ intención / tool request
→ validación local
→ Python / DuckDB / analytics / expert
→ evidencia estructurada
→ respuesta grounded
```

La API key pertenece al usuario y la UI no la persiste en DuckDB ni en archivos del proyecto.

La integración dispone de contract tests y CI, pero no se ha realizado todavía un benchmark live con una API key real. En consecuencia, no se presentan como resultados demostrados su latencia, coste o calidad externa.

## 9.2 Identidades y privacidad de la demo

El Assistant comparte el mismo boundary de presentación que el resto de la demo. Las identidades visibles `Equipo Demo`, `Jugador XX` y `Rival XX` se traducen internamente únicamente para consultar las tools y se vuelven a anonimizar antes de renderizar.

Esta decisión evita que la capa conversacional reintroduzca nombres profesionales que la interfaz ya había ocultado. En modo demo, una identidad interna conocida detectada en la respuesta final provoca el bloqueo de esa respuesta.

---

# 10. Reproducibilidad y separación de datos privados

La reproducibilidad era un problema importante porque el caso profesional de desarrollo no puede asumirse redistribuible.

La solución fue crear una demo sintética desde cero y validarla en un entorno limpio mediante GitHub Actions.

Esto permite diferenciar dos conceptos:

```text
reproducir el software
≠
redistribuir el dataset profesional
```

Sandve et al. (2013) defienden registrar versiones, automatizar procesos y permitir repetir análisis. El repositorio implementa estos principios mediante Git, versiones explícitas, validators, CI y una demo sintética reproducible.

La principal limitación de la demo es que no revalida deportivamente los modelos. Su función es demostrar integración y reproducibilidad técnica.

---

# 11. Contraste de la hipótesis

Hipótesis principal:

> Un equipo de fútbol amateur o semiprofesional puede disponer de un sistema integral y auditable de soporte a la decisión a partir de datos de vídeo y GPS opcional, capaz de transformarlos en información sobre rendimiento, evolución, rol y comportamiento físico de los jugadores y del equipo.

Los resultados permiten contrastarla favorablemente en su dimensión técnica y arquitectónica.

Esta conclusión responde a las preguntas de investigación técnicas del trabajo: PI1 sobre reproducibilidad y control temporal, PI2 sobre grounding del Coach y PI3 sobre integración funcional. La matriz de evidencias identifica los gates concretos y evita extender esas respuestas a utilidad percibida, impacto deportivo o validación externa.

Existe evidencia de que:

1. el sistema cubre el flujo completo desde captura/importación hasta visualización y reporting;
2. las capas críticas están separadas y versionadas;
3. existen controles explícitos contra leakage temporal;
4. el sistema experto conserva trazabilidad y puede abstenerse de recomendar;
5. GPS puede integrarse de forma opcional sin contaminar otras capas;
6. el asistente IA funciona downstream de lógica determinista y herramientas read-only;
7. el espacio de consultas del Assistant se valida mediante contrato, tests y CI, no mediante una colección informal de frases;
8. el repositorio puede reconstruir una demo sintética en un entorno limpio.

La hipótesis no queda contrastada en términos de impacto causal sobre decisiones, victorias, rendimiento deportivo o prevención de lesiones.

---

# 12. Limitaciones

Las principales limitaciones del trabajo son:

## 12.1 Validación con usuarios reales

No se ha realizado una evaluación formal con entrenadores o analistas para medir utilidad percibida, facilidad de uso o impacto sobre decisiones.

El protocolo de piloto está preparado en `docs/TFM_EVALUATION_PROTOCOLS.md`, pero no se ha ejecutado y no debe citarse como resultado.

## 12.2 Fiabilidad interobservador

El Collector tiene validación funcional, pero no se ha ejecutado un estudio experimental de acuerdo entre observadores.

El diseño de muestreo, medidas y tratamiento de discrepancias queda documentado en `docs/TFM_EVALUATION_PROTOCOLS.md` para una evaluación posterior.

## 12.3 Generalización del Match Rating

V5 está validado técnicamente sobre el caso de desarrollo, pero no se ha comparado con un ground truth externo universal.

## 12.4 GPS real

El sistema soporta GPS real, pero el experto actual no dispone de observaciones reales no sintéticas en la base utilizada para cerrar el QA.

## 12.5 Recomendación táctica

N13000 no dispone de una policy validada para recomendar un rol óptimo, XI ideal o cambios tácticos.

## 12.6 Autenticación

Existe control de acceso estructural, pero no autenticación completa de usuarios.

## 12.7 Derechos del dataset profesional

La base de desarrollo no puede tratarse como dataset público mientras no exista confirmación explícita de derechos/licencia.

## 12.8 Latencia del fallback local

La ruta determinista es rápida en el gate final, pero una consulta ambigua que requiera Qwen puede ser mucho más lenta en CPU. El smoke final no mide ese caso porque sus 28 consultas se resolvieron con `rounds=0`.

## 12.9 Proveedor OpenAI

El modo BYOK está integrado y validado contractualmente, pero no dispone todavía de benchmark live con una API key real.

---

# 13. Conclusiones

El TFM demuestra que es posible construir un sistema funcional y auditable de análisis de rendimiento para un contexto amateur o semiprofesional utilizando una combinación de vídeo, datos estructurados y GPS opcional.

Las principales contribuciones son:

- un Collector orientado a hechos observables;
- una arquitectura de datos separada por capas;
- feature engineering temporal con control de leakage;
- Analytics independiente de la decisión;
- un sistema experto modular N1000-N13000;
- Match Rating inmediato y Performance Index separado;
- integración GPS descriptiva y opcional;
- dashboard Team/Player/Match;
- Coach Copilot grounded con preflight, routing determinista y fallback semántico local;
- comparaciones por posición con criterio explícito sin crear un score nuevo;
- integración OpenAI BYOK opcional bajo el mismo contrato de tools;
- anonimización coherente también en la capa conversacional de la demo;
- informes PDF downstream de analytics;
- QA end-to-end;
- demo sintética reproducible;
- CI automático en GitHub.

El valor principal del proyecto no reside en maximizar el número de métricas o modelos, sino en mantener trazabilidad entre dato, cálculo, evidencia, decisión y explicación.

La conclusión académica debe formularse de manera precisa:

> **La propuesta es técnicamente viable, funcional y reproducible como arquitectura de soporte al análisis de rendimiento. Su impacto real sobre decisiones de entrenadores y rendimiento deportivo requiere validación adicional con usuarios, datos reales adicionales y ground truth independiente.**

---

# 14. Trabajo futuro prioritario

El desarrollo futuro debe priorizar evidencia, no complejidad.

Orden recomendado:

1. estudio de fiabilidad interobservador del Collector;
2. validación con entrenadores/analistas reales;
3. incorporación de GPS real y evaluación de calidad por proveedor;
4. validación externa del Match Rating;
5. definición y evaluación de una policy de recomendación para N13000;
6. comparación experto vs ML con ground truth independiente;
7. automatización parcial del Collector mediante visión por computador si reduce coste real de captura;
8. autenticación completa y despliegue solo cuando derechos/licencias estén resueltos;
9. validación live de proveedores externos del asistente si aporta valor real;
10. posible exposición futura de las tools mediante un protocolo estándar, sin convertirlo en dependencia del MVP.

No debe priorizarse añadir nuevas métricas si no existe evidencia de que mejoran una decisión final del producto.
