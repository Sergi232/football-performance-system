# TFM — Marco teórico y referencias académicas

Fecha: 03/10/2026
Estado: base académica curada para integrar en la memoria final.
Idioma: castellano.

## Alcance

Este documento justifica las principales decisiones metodológicas del Football Performance System mediante literatura académica. No se presenta como una revisión sistemática propia: es una selección razonada de revisiones, estudios metodológicos y trabajos fundacionales directamente relacionados con las decisiones implementadas.

Regla de uso:

```text
literatura externa
→ justifica principios y riesgos metodológicos

repositorio + tests + validators
→ demuestra qué se ha implementado y qué funciona en este TFM
```

Una referencia externa no sustituye la validación del producto y un test del producto no sustituye la evidencia científica externa.

---

# 1. Análisis del rendimiento en fútbol

El análisis de rendimiento en fútbol combina información técnica, táctica, física y contextual. La literatura sobre match analysis ha evolucionado desde análisis descriptivos y notacionales hacia enfoques más integrados, pero continúa señalando problemas de definición operacional, contextualización y generalización.

Sarmento et al. (2014) revisaron la literatura de match analysis en fútbol y destacaron la necesidad de utilizar definiciones operacionales claras, categorías estandarizadas y variables situacionales y de interacción. La revisión también muestra que posición, nivel competitivo, localización del partido, calidad del rival y estado del marcador pueden condicionar la interpretación de indicadores de rendimiento.

Mackenzie y Cushion (2013) remarcan que las variables de performance analysis deben evaluarse también por su utilidad práctica y por la validez de las inferencias realizadas, no únicamente por la capacidad de producir grandes cantidades de datos.

La umbrella review de Sarmento et al. (2022) refuerza una visión multidimensional del rendimiento en deportes colectivos y señala la conveniencia de integrar dimensiones físicas, técnicas y tácticas en lugar de reducir el rendimiento a una sola familia de indicadores.

### Implicación para este TFM

Estas evidencias apoyan tres decisiones del sistema:

1. no intentar resumir el rendimiento completo mediante una única estadística bruta;
2. conservar contexto de rol, partido y equipo cuando está disponible;
3. separar datos observados, features, evidencia analítica y juicio final.

No justifican por sí mismas los pesos concretos del Match Rating ni una recomendación táctica específica; esos elementos requieren validación propia.

---

# 2. Metodología observacional y Data Collector

El análisis notacional y la metodología observacional son enfoques consolidados en fútbol, pero la calidad del resultado depende de que las categorías sean comprensibles, mutuamente interpretables y suficientemente fiables entre observadores.

James (2006) describe el papel histórico del análisis notacional en fútbol y señala cuestiones metodológicas como la definición de indicadores, el análisis longitudinal y la interpretación del comportamiento observado.

Ortega-Toro et al. (2019) diseñaron y validaron un instrumento observacional para acciones técnico-tácticas ofensivas. El estudio muestra que un instrumento de observación debe definir explícitamente criterios y categorías, someterlos a validación y comprobar fiabilidad intra e interobservador.

Sarmento et al. (2014) también señalan como necesidad recurrente el uso de definiciones operacionales completas y categorías estandarizadas.

### Implicación para este TFM

El Collector V1.1 sigue esta lógica:

```text
hecho observable
→ categoría operacional explícita
→ almacenamiento raw
→ derivación posterior
```

Por ello se evita pedir al operador que introduzca directamente conceptos avanzados o ambiguos como xG, PPDA, fatiga, pressing efectivo o una valoración subjetiva general de la acción.

La validación académica de instrumentos observacionales no permite afirmar automáticamente que nuestro Collector tenga fiabilidad interobservador real. El TFM ha validado su contrato técnico y funcional; una prueba formal con varios observadores queda como trabajo futuro si se dispone de participantes.

---

# 3. Indicadores técnicos, contexto y evolución

La literatura de match analysis muestra que los indicadores técnicos deben interpretarse en contexto. Sarmento et al. (2014) identifican posición de juego y variables situacionales como elementos frecuentes y relevantes en la investigación. La literatura posterior mantiene la necesidad de integrar varias dimensiones del rendimiento.

Esto es especialmente importante para un sistema longitudinal: comparar un jugador consigo mismo o con otros jugadores requiere controlar qué información estaba realmente disponible en cada momento y no confundir diferencia estadística con superioridad deportiva universal.

### Implicación para este TFM

El sistema diferencia:

- `SELF_ROLE_PRIOR`: comparación con el pasado del propio jugador en el rol observado;
- `PEER_ROLE_PRIOR`: comparación con compañeros del mismo rol utilizando únicamente pasado disponible;
- Match Rating: valoración inmediata jugador-partido;
- Performance Index: capa histórica/posicional experimental.

El sistema evita interpretar automáticamente una desviación positiva como recomendación táctica.

---

# 4. GPS, carga externa y límites de interpretación

Los sistemas GPS y otras microtecnologías son utilizados habitualmente para cuantificar carga externa en deportes de equipo. Sin embargo, su validez y fiabilidad dependen del dispositivo, frecuencia de muestreo, tipo de movimiento y variable analizada.

Scott, Scott y Kelly (2016) revisaron la validez y fiabilidad del GPS en deportes colectivos. La revisión muestra que la distancia total puede medirse con fiabilidad razonable en numerosas condiciones, pero que existen mayores limitaciones en velocidad alta, movimientos cortos y cambios de dirección, especialmente con frecuencias de muestreo bajas.

Miguel et al. (2021), en una revisión sistemática sobre monitorización de carga en fútbol, muestran la gran diversidad de medidas internas y externas utilizadas y la necesidad de seleccionar variables relevantes y estandarizar su clasificación. Entre las medidas externas habituales aparecen distancia, velocidad, aceleraciones y desaceleraciones.

Hader et al. (2019) analizaron si variables de carga externa podían predecir fatiga postpartido. Sus resultados muestran que no todas las métricas externas son igualmente informativas y que, por ejemplo, la distancia total no presentó una relación clara con todos los marcadores de fatiga evaluados. Esto desaconseja transformar automáticamente una métrica GPS simple en una inferencia clínica o fisiológica fuerte.

### Implicación para este TFM

El diseño adoptado es deliberadamente conservador:

```text
GPS raw normalizado
→ resumen físico descriptivo
→ visualización / contexto
```

No se deriva automáticamente:

- fatiga;
- readiness;
- riesgo de lesión;
- carga fisiológica interna;
- zonas HSR o sprint universales sin validación de umbrales.

El GPS sintético se utiliza para integración técnica y se excluye como evidencia física observada en el sistema experto.

---

# 5. Data leakage y validación temporal

Kaufman et al. (2012) definen data leakage como la incorporación al proceso de modelado de información que no estaría legítimamente disponible en el momento en que se realiza la predicción o decisión. Este problema puede producir estimaciones excesivamente optimistas y modelos que fallan cuando pasan a producción.

En datos longitudinales deportivos, el riesgo aparece cuando información de partidos futuros, del partido actual o de agregaciones calculadas con toda la temporada entra en una feature que pretende representar el conocimiento disponible antes de ese momento.

### Implicación para este TFM

FEATURE-02, FEATURE-03 y ANALYTICS-01 aplican una regla `strict-past`:

```text
para una fila de fecha t
solo pueden entrar observaciones con fecha < t
```

Los partidos de la misma fecha tampoco se informan mutuamente. Esta decisión es metodológica, no simplemente de implementación.

El control de leakage está además validado mediante contratos y tests del repositorio.

---

# 6. Sistemas expertos, reglas e interpretabilidad

Un sistema experto basado en reglas representa conocimiento mediante condiciones explícitas y una lógica de inferencia trazable. Liu, Gegov y Cocea (2016) describen los rule-based systems como una forma de sistema experto basada típicamente en reglas `if–then`.

Rudin (2019) argumenta que cuando la interpretabilidad es importante resulta preferible, siempre que sea posible, utilizar modelos intrínsecamente interpretables en lugar de depender exclusivamente de explicaciones post-hoc de modelos opacos.

El objetivo de este TFM no es afirmar que un sistema basado en reglas sea siempre superior a ML. La elección responde a la fase del producto y a la necesidad de que cada conclusión pueda rastrearse hasta evidencia observable, una condición especialmente importante cuando todavía no existe suficiente ground truth independiente para entrenar y validar recomendaciones complejas.

### Implicación para este TFM

El árbol N1000-N13000 utiliza el contrato:

```text
entrada
→ condición
→ resultado
→ confianza
→ justificación
```

N13000 funciona como gate: si no existe una policy validada, el sistema conserva la evidencia pero no emite la recomendación.

ML se mantiene como capa experimental y se incorpora únicamente cuando existe un target y una estrategia de validación defendibles.

---

# 7. LLM como capa de interacción, no como motor analítico

Los modelos de lenguaje pueden generar respuestas plausibles pero incorrectas. Huang et al. (2025) revisan el fenómeno de hallucination en LLM y distinguen, entre otros problemas, inconsistencias de factualidad y de fidelidad respecto al contexto proporcionado.

Lewis et al. (2020) muestran que combinar generación con acceso a memoria externa explícita puede mejorar tareas intensivas en conocimiento y facilitar el uso de información recuperada frente a depender exclusivamente del conocimiento paramétrico del modelo.

Schick et al. (2023) muestran que los modelos de lenguaje pueden beneficiarse del uso de herramientas externas para funciones como consulta factual o cálculo, tareas en las que sistemas especializados pueden ser más fiables.

El Coach Copilot de este TFM no implementa exactamente RAG ni Toolformer; estas referencias justifican el principio arquitectónico general de separar lenguaje de fuentes estructuradas y herramientas deterministas.

### Implicación para este TFM

La arquitectura es:

```text
DATA
→ ANALYTICS
→ DECISION ENGINE
→ READ-ONLY TOOLS
→ ROUTER
→ LOCAL LLM
→ SEMANTIC GUARD
→ COACH
```

El LLM:

- explica;
- resume;
- transforma preguntas en consultas permitidas;
- verbaliza resultados ya calculados.

El LLM no:

- inventa nuevas métricas;
- recalcula Match Rating;
- decide pesos del sistema experto;
- crea recomendaciones tácticas no validadas;
- sustituye al motor analítico.

---

# 8. Reproducibilidad computacional

Sandve et al. (2013) proponen principios básicos para investigación computacional reproducible, entre ellos registrar cómo se produjo cada resultado, conservar versiones y parámetros, automatizar pasos y facilitar que otra persona pueda repetir el análisis.

### Implicación para este TFM

La reproducibilidad se implementa mediante:

- Git como historial de cambios;
- `PROJECT_STATE.md` como estado técnico;
- versiones explícitas de features, rating, experto y GPS;
- tests y validators;
- GitHub Actions en `push` y `pull_request`;
- una DuckDB sintética generable desde cero;
- separación entre datos profesionales privados y demo redistribuible.

El objetivo es que el evaluador pueda distinguir claramente entre reproducir el producto y redistribuir datos de terceros, que son cuestiones distintas.

---

# 9. Correspondencia literatura → decisión de diseño

| Tema | Evidencia académica | Decisión en Football Performance System |
|---|---|---|
| Match/performance analysis | Mackenzie & Cushion (2013); Sarmento et al. (2014, 2022) | análisis multidimensional y contextual |
| Observación/notación | James (2006); Ortega-Toro et al. (2019) | Collector de categorías observables y definidas |
| Calidad de categorías | Sarmento et al. (2014); Ortega-Toro et al. (2019) | taxonomía congelada y contratos del Collector |
| GPS | Scott et al. (2016); Miguel et al. (2021) | normalización + capa física descriptiva |
| Fatiga desde carga externa | Hader et al. (2019) | no inferir fatiga/readiness desde métricas simples |
| Leakage | Kaufman et al. (2012) | strict-past FEATURE-02/03 y Analytics |
| Interpretabilidad | Liu et al. (2016); Rudin (2019) | experto modular y auditable |
| LLM grounding/tools | Lewis et al. (2020); Schick et al. (2023) | tools read-only antes de la síntesis lingüística |
| Hallucinations | Huang et al. (2025) | semantic guard y prohibición de cálculo crítico por LLM |
| Reproducibilidad | Sandve et al. (2013) | Git, versiones, CI y demo sintética |

---

# 10. Qué NO demuestra esta literatura

No debe utilizarse ninguna de estas referencias para afirmar que:

- nuestro Collector ya tiene una fiabilidad interobservador científicamente demostrada;
- nuestro Match Rating es una medida universalmente válida del rendimiento;
- el sistema experto mejora las decisiones reales de entrenadores;
- el GPS sintético representa fisiología real;
- el sistema detecta fatiga, lesiones o readiness;
- el LLM es factual por definición;
- el producto genera una mejora causal en resultados deportivos.

Esos claims necesitarían experimentos adicionales específicos del sistema.

---

# Referencias

Hader, K., Rumpf, M. C., Hertzog, M., Kilduff, L. P., Girard, O., & Silva, J. R. (2019). Monitoring the Athlete Match Response: Can External Load Variables Predict Post-match Acute and Residual Fatigue in Soccer? A Systematic Review with Meta-analysis. *Sports Medicine - Open, 5*, 48. https://doi.org/10.1186/s40798-019-0219-7

Huang, L., Yu, W., Ma, W., Zhong, W., Feng, Z., Wang, H., Chen, Q., Peng, W., Feng, X., Qin, B., & Liu, T. (2025). A Survey on Hallucination in Large Language Models: Principles, Taxonomy, Challenges, and Open Questions. *ACM Transactions on Information Systems, 43*(2), Article 42. https://doi.org/10.1145/3703155

James, N. (2006). Notational analysis in soccer: past, present and future. *International Journal of Performance Analysis in Sport, 6*(2), 67–81. https://doi.org/10.1080/24748668.2006.11868373

Kaufman, S., Rosset, S., Perlich, C., & Stitelman, O. (2012). Leakage in data mining: Formulation, detection, and avoidance. *ACM Transactions on Knowledge Discovery from Data, 6*(4), Article 15. https://doi.org/10.1145/2382577.2382579

Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., Küttler, H., Lewis, M., Yih, W.-t., Rocktäschel, T., Riedel, S., & Kiela, D. (2020). Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. *Advances in Neural Information Processing Systems, 33*.

Liu, H., Gegov, A., & Cocea, M. (2016). Rule-based systems: a granular computing perspective. *Granular Computing, 1*, 259–274. https://doi.org/10.1007/s41066-016-0021-6

Mackenzie, R., & Cushion, C. (2013). Performance analysis in football: A critical review and implications for future research. *Journal of Sports Sciences, 31*(6), 639–676. https://doi.org/10.1080/02640414.2012.746720

Miguel, M., Oliveira, R., Loureiro, N., García-Rubio, J., & Ibáñez, S. J. (2021). Load Measures in Training/Match Monitoring in Soccer: A Systematic Review. *International Journal of Environmental Research and Public Health, 18*(5), 2721. https://doi.org/10.3390/ijerph18052721

Ortega-Toro, E., García-Angulo, A., Giménez-Egido, J. M., García-Angulo, F. J., & Palao, J. M. (2019). Design, Validation, and Reliability of an Observation Instrument for Technical and Tactical Actions of the Offense Phase in Soccer. *Frontiers in Psychology, 10*, 22. https://doi.org/10.3389/fpsyg.2019.00022

Rudin, C. (2019). Stop explaining black box machine learning models for high stakes decisions and use interpretable models instead. *Nature Machine Intelligence, 1*, 206–215. https://doi.org/10.1038/s42256-019-0048-x

Sandve, G. K., Nekrutenko, A., Taylor, J., & Hovig, E. (2013). Ten Simple Rules for Reproducible Computational Research. *PLoS Computational Biology, 9*(10), e1003285. https://doi.org/10.1371/journal.pcbi.1003285

Sarmento, H., Marcelino, R., Anguera, M. T., Campaniço, J., Matos, N., & Leitão, J. C. (2014). Match analysis in football: a systematic review. *Journal of Sports Sciences, 32*(20), 1831–1843. https://doi.org/10.1080/02640414.2014.898852

Sarmento, H., Clemente, F. M., Afonso, J., Araújo, D., Fachada, M., Nobre, P., & Davids, K. (2022). Match Analysis in Team Ball Sports: An Umbrella Review of Systematic Reviews and Meta-Analyses. *Sports Medicine - Open, 8*, 66. https://doi.org/10.1186/s40798-022-00454-7

Schick, T., Dwivedi-Yu, J., Dessì, R., Raileanu, R., Lomeli, M., Hambro, E., Zettlemoyer, L., Cancedda, N., & Scialom, T. (2023). Toolformer: Language Models Can Teach Themselves to Use Tools. *Advances in Neural Information Processing Systems, 36*, 68539–68551.

Scott, M. T. U., Scott, T. J., & Kelly, V. G. (2016). The Validity and Reliability of Global Positioning Systems in Team Sport: A Brief Review. *Journal of Strength and Conditioning Research, 30*(5), 1470–1490. https://doi.org/10.1519/JSC.0000000000001221

---

## Próximo uso en la memoria

Este documento debe integrarse principalmente en:

```text
Introducción / estado del arte
Marco teórico
Justificación metodológica del Collector
Justificación de GPS
Metodología de leakage control
Justificación del sistema experto
Arquitectura del Coach Copilot
Reproducibilidad
Limitaciones
```

La memoria final debe mantener pocas referencias, pero bien conectadas con decisiones reales; no convertir la bibliografía en una lista extensa sin función argumental.
