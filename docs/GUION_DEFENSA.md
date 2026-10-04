# Guion de defensa — Football Performance System

**Duración prevista:** 8:55 con demostración en vivo (margen de 65 segundos hasta 10:00).  
**Formato:** 9 diapositivas + demostración entre las diapositivas 6 y 7.  
**Regla de exposición:** presentar la evidencia como validación técnico-funcional y arquitectónica, sin afirmar validez deportiva externa, causalidad ni utilidad percibida por entrenadores.

## Diapositiva 1 — Portada

- **Objetivo:** situar el trabajo y anticipar su propuesta de valor.
- **Duración:** 0:20 · **Acumulado:** 0:20.
- **Texto oral:**

  «Buenos días. Presento *Football Performance System*, un sistema auditable de análisis del rendimiento para equipos amateur y semiprofesionales. El trabajo parte de una pregunta sencilla: cómo convertir datos observables y accesibles en información estructurada que un cuerpo técnico pueda consultar, revisar y contrastar.»

- **Transición:** «Primero, el problema que motivó el sistema.»
- **Recorte de emergencia (0:10):** «Es un sistema auditable que transforma datos observables en análisis consultable para fútbol amateur y semiprofesional.»

## Diapositiva 2 — Problema

- **Objetivo:** explicar por qué existe el sistema y delimitar el contexto.
- **Duración:** 0:45 · **Acumulado:** 1:05.
- **Texto oral:**

  «En muchos equipos de este contexto hay vídeo, en algunos casos GPS, y conocimiento del entrenador; pero falta una infraestructura analítica que conecte esos elementos. Las restricciones son pocos recursos, poco tiempo y datos manuales necesariamente limitados. Por eso el propósito no es reproducir proveedores profesionales, sino construir una solución viable que preserve el contexto de cada acción y permita convertirlo en evidencia útil.»

- **Transición:** «Para responderlo se diseñó una arquitectura trazable de extremo a extremo.»
- **Recorte de emergencia (0:25):** «El problema no es la ausencia total de datos, sino que vídeo, GPS opcional y observación del entrenador no llegan a una capa analítica trazable y viable con recursos limitados.»

## Diapositiva 3 — Arquitectura y trazabilidad

- **Objetivo:** mostrar el recorrido completo del dato y la unidad analítica.
- **Duración:** 0:55 · **Acumulado:** 2:00.
- **Texto oral:**

  «La unidad principal es jugador-partido. El flujo comienza en el Collector, continúa en DuckDB y separa datos brutos, features, analytics y decisión. Sobre esas capas se materializan Match Rating V5 y el motor experto; después se exponen en Dashboard, Coach Copilot y PDF. El GPS es opcional: su ausencia no interrumpe el sistema. Esta separación permite saber qué dato entra, qué transformación se aplica y qué resultado llega al usuario.»

- **Transición:** «El primer requisito para que esa trazabilidad sea fiable es controlar qué se registra y cuándo puede utilizarse.»
- **Recorte de emergencia (0:30):** «Cada salida tiene una cadena verificable: Collector, DuckDB, features, analytics, decisión y superficie final.»

## Diapositiva 4 — Dato y strict-past

- **Objetivo:** diferenciar hechos observables de métricas derivadas y explicar el control temporal.
- **Duración:** 1:00 · **Acumulado:** 3:00.
- **Texto oral:**

  «El Data Collector recoge hechos observables: minutos, rol y lado, pases, remates, acciones de uno contra uno, defensa, disciplina, ABP y acciones de portero. No registra métricas avanzadas como si fueran hechos: estas se derivan posteriormente. Además, el Feature Engine aplica strict-past: para un partido solo usa encuentros con fecha estrictamente anterior. Así se evita que la información futura entre en las variables históricas del mismo partido.»

- **Transición:** «Con el dato controlado, el sistema genera dos capas de evaluación con funciones distintas.»
- **Recorte de emergencia (0:35):** «El Collector registra hechos; las métricas se derivan. strict-past asegura que cada feature histórica usa únicamente partidos anteriores.»

## Diapositiva 5 — Match Rating V5 y motor experto

- **Objetivo:** explicar la lógica de rutas y la auditabilidad del motor experto.
- **Duración:** 1:10 · **Acumulado:** 4:10.
- **Texto oral:**

  «Match Rating V5 asigna exactamente una ruta a cada aparición jugada. Con un rol de campo fiable utiliza V4.1; con portero observado utiliza la ruta GK; y cuando el rol no es fiable aplica el fallback V2. El sistema no infiere una posición desde las estadísticas. En paralelo, el motor experto N1000–N13000 conserva una traza de entrada, condición, resultado, confianza y justificación. N13000 es un gate: se abstiene si no hay evidencia o policy validada. Por tanto, el sistema estructura evidencia, pero no presenta recomendaciones tácticas finales como si estuvieran validadas.»

- **Transición:** «Estas capas no se quedan en scripts: se integran en un producto consultable.»
- **Recorte de emergencia (0:45):** «V5 cubre cada aparición con una sola ruta sin inventar el rol; el motor experto deja una traza auditable y se abstiene cuando falta base suficiente.»

## Diapositiva 6 — Despliegue

- **Objetivo:** mostrar que el resultado está disponible para uso real, no solo como prototipo analítico.
- **Duración:** 0:55 · **Acumulado:** 5:05.
- **Texto oral:**

  «El producto expone tres modos principales: equipo, jugador y partido. El dashboard da acceso a los resultados materializados; Coach Copilot consulta resultados estructurados y los informes PDF fijan una salida exportable. La ejecución está automatizada con pipeline local, launcher y comprobaciones de CI. Ahora muestro el recorrido mínimo desde la captura de un partido hasta su aparición en las superficies finales.»

- **Transición:** «Paso a la demostración en vivo.»
- **Recorte de emergencia (0:30):** «El pipeline local conecta captura, cálculo, dashboard, Coach Copilot y PDF sin cambiar las reglas analíticas.»

## Demostración en vivo — 60 a 75 segundos

- **Objetivo:** demostrar un recorrido pequeño, reproducible y seguro.
- **Duración:** 1:10 · **Acumulado:** 6:15.
- **Secuencia:**
  1. Abrir el Collector desde el launcher local y mostrar rol/lado de un jugador.
  2. Pulsar **FINALIZAR PARTIDO** con un partido ya preparado; mostrar estado de procesamiento.
  3. Abrir Match Mode y señalar resultado, eventos y ruta/Match Rating disponible.
  4. Abrir Team o Player Mode y mostrar que el partido aparece en el periodo.
  5. Hacer una consulta breve y grounded en Coach Copilot, por ejemplo: «resume los datos del último partido».
  6. Mostrar el acceso a un PDF existente, sin detenerse a leerlo.

- **Plan B sin demo:** mantener la diapositiva 6, explicar el mismo flujo sobre las capturas, y decir: «Para evitar depender del entorno local, muestro las superficies resultantes ya verificadas: Team, Player y Match. La misma ejecución fue validada end-to-end mediante fixture controlada y pruebas reproducibles.» Pasar directamente a la diapositiva 7.

## Diapositiva 7 — Validación y resultados

- **Objetivo:** presentar evidencia comprobable, distinguiendo sus alcances.
- **Duración:** 1:25 · **Acumulado:** 7:40.
- **Texto oral:**

  «La validación se organizó en tres evidencias. En la showcase histórica privada se conservaron 38 partidos y 835 registros jugador-partido; 590 corresponden a apariciones jugadas y V5 cubrió 590 de 590: 380 por ruta de campo, 38 de portero y 172 por fallback. En una fixture controlada del Collector se verificó el recorrido completo con resultado 2 a 1, GF 2, GC 1, corners 3 y 2, y faltas recibidas y cometidas de 4 y 5. Finalmente, los gates técnicos registraron 28 de 28 smoke tests de Coach, PDFs de 4, 3 y 3 páginas, QA end-to-end y CI en PASS. La showcase histórica sigue siendo privada; la demo pública utiliza datos sintéticos anonimizados. Esto valida integración y trazabilidad, no validez deportiva externa.»

- **Transición:** «Esa distinción define con precisión las limitaciones del trabajo.»
- **Recorte de emergencia (0:55):** «V5 cubre las 590 apariciones jugadas. La fixture prueba trazabilidad controlada y los gates verifican reproducibilidad. No se reclama validación deportiva externa.»

## Diapositiva 8 — Limitaciones

- **Objetivo:** anticipar límites sin disminuir la contribución demostrada.
- **Duración:** 0:45 · **Acumulado:** 8:25.
- **Texto oral:**

  «Las limitaciones son explícitas: no hay validación con entrenadores ni estudio interobservador; Match Rating no cuenta con ground truth externo universal; GPS no ha sido validado fisiológicamente; N13000 no recomienda un XI ni un rol óptimo; y no se demuestra impacto causal en resultados deportivos. La contribución es técnico-funcional y arquitectónica: demuestra cómo construir y verificar el sistema, no que ya mejore por sí mismo el rendimiento competitivo.»

- **Transición:** «Con esto, cierro respondiendo a la pregunta central.»
- **Recorte de emergencia (0:25):** «Se demuestra viabilidad técnica y funcional; la eficacia deportiva requiere validación externa posterior.»

## Diapositiva 9 — Conclusión

- **Objetivo:** responder la pregunta de investigación y cerrar con el alcance correcto.
- **Duración:** 0:30 · **Acumulado:** 8:55.
- **Texto oral:**

  «La conclusión es que es viable transformar datos simples y observables en un sistema integral, reproducible y auditable de soporte al análisis futbolístico. El trabajo aporta accesibilidad en la captura, trazabilidad de dato a salida y un producto funcional. El siguiente paso no es añadir más complejidad, sino validar externamente con clubes y entrenadores. Muchas gracias; quedo a disposición para las preguntas.»

- **Recorte de emergencia (0:15):** «El sistema demuestra accesibilidad, trazabilidad y producto funcional; la validación externa es el siguiente paso.»

# Preguntas probables del tribunal

1. **¿Por qué utiliza sistema experto y no solo ML?**  
   Porque el objetivo exige explicabilidad y auditabilidad con datos limitados. El motor experto conserva evidencia, condición, resultado, confianza y justificación; el ML no se ha desplegado para sustituir ese mecanismo.

2. **¿Cómo se justifica Match Rating V5?**  
   Se valida su consistencia interna, sensibilidad, cobertura de rutas y trazabilidad. No se afirma una validez externa universal: esa validación queda pendiente con una fuente independiente o evaluación experta.

3. **¿Cómo evita leakage?**  
   El Feature Engine aplica strict-past: cada feature histórica usa solo partidos de fecha estrictamente anterior. La separación raw/features/analytics/decision permite auditarlo.

4. **¿Qué variables captura el sistema?**  
   Hechos manuales observables: minutos, rol, lado, pases, remates, 1v1, defensa, disciplina, ABP y acciones de portero. Las métricas derivadas se calculan después.

5. **¿Cuál es el papel real del LLM?**  
   Coach Copilot consulta resultados estructurados del sistema. No calcula el rating, no crea hechos y debe abstenerse cuando no existe evidencia suficiente.

6. **¿Qué aporta el GPS?**  
   Es una integración opcional descriptiva. La ausencia de GPS no interrumpe el pipeline y no se han hecho inferencias fisiológicas sin GPS real validado.

7. **¿Cómo validaría esto con un club real?**  
   Con un protocolo prospectivo: formación de observadores, fiabilidad interobservador, comparación con fuente externa cuando exista y evaluación de utilidad por entrenadores, sin alterar la trazabilidad actual.

8. **¿El sistema recomienda titulares o el mejor rol?**  
   No. N13000 actúa como gate de recomendación y se abstiene sin policy validada o evidencia suficiente. El rol por partido procede de la observación, no de una predicción desplegada.

9. **¿Por qué DuckDB y Streamlit?**  
   DuckDB permite una base local analítica reproducible y auditable; Streamlit permite exponer las materializaciones en una interfaz funcional sin introducir una infraestructura innecesaria para el alcance del TFM.

10. **¿Dónde está la aportación de Data Science?**  
    En el modelo de datos jugador-partido, el Feature Engine temporal strict-past, las transformaciones analíticas, la evaluación consistente del rating, la validación funcional y la trazabilidad de todo el pipeline.

11. **¿Qué haría con seis meses más?**  
    Priorizaría validación externa: observación compartida con clubes, fiabilidad interobservador, datos GPS reales y comparación con valoración independiente. Añadiría complejidad solo después de validar el uso actual.

12. **¿Cuál es la principal limitación?**  
    La falta de validación externa con entrenadores y una referencia independiente para el Match Rating. Por eso las conclusiones se limitan a viabilidad técnico-funcional y arquitectónica.

13. **¿Qué ocurre si falta rol observado?**  
    Una aparición jugada sin rol fiable entra en V2 fallback. No se inventa posición a partir de sus estadísticas y el motor experto puede abstenerse si falta evidencia.

14. **¿Qué diferencia hay entre Match Rating V5 y Performance Index experimental?**  
    Match Rating V5 es la evaluación materializada y trazable usada en producción. Performance Index se mantiene como componente experimental y no sustituye V5 en la decisión final.

15. **¿Cómo evita Coach Copilot alucinaciones?**  
    Se apoya en resultados estructurados, evidencia y políticas de abstención. No debe inventar métricas, conclusiones ni recomendaciones cuando el sistema no aporta base suficiente.
