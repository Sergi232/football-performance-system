# Protocolos de evaluación empírica posteriores al cierre técnico

Fecha: 04/10/2026  
Estado: protocolos preparados, no ejecutados. No generan resultados ni modifican los claims validados del TFM.

## Propósito

El TFM demuestra viabilidad técnica y arquitectónica. Estos protocolos definen cómo evaluar posteriormente dos preguntas que el repositorio no puede responder por sí solo: la fiabilidad de la captura manual y la utilidad del producto para un staff técnico.

## Protocolo A — Fiabilidad interobservador del Data Collector

### Pregunta

¿Dos observadores formados registran de forma suficientemente consistente las mismas acciones y el mismo contexto jugador-partido con la taxonomía V1.1?

### Diseño

- Seleccionar antes del análisis una muestra de partidos que incluya diferentes fases y las categorías de eventos más frecuentes y relevantes.
- Formar a dos observadores con el catálogo congelado `event_catalog v0.3.0` y un manual de codificación breve.
- Hacer que ambos registren de forma independiente el mismo vídeo, sin consultar el registro del otro.
- Congelar las exportaciones antes de conciliarlas y conservar el identificador de vídeo, versión de taxonomía y versión del formulario.
- Revisar discrepancias solo después del cálculo inicial; la revisión produce una versión conciliada separada, no sustituye el resultado de fiabilidad.

### Variables y análisis

| Elemento | Medida propuesta | Tratamiento |
|---|---|---|
| Jugador, dorsal, titularidad, minutos y rol | acuerdo exacto y porcentaje de discrepancias | informar por campo y por partido |
| Categoría de evento | acuerdo de eventos emparejados y estimación de concordancia para categorías nominales | publicar matriz de confusión y casos no emparejados |
| Resultado de pase, remate o defensa | acuerdo condicional a que ambos observadores identifiquen el mismo evento | separar detección del evento y clasificación del resultado |
| Marca temporal | diferencia absoluta de tiempo en eventos emparejados | informar distribución, no solo media |
| Cobertura | eventos por observador y proporción de eventos sin pareja | detectar sesgo sistemático de infrarregistro |

El análisis debe informar intervalos de confianza cuando el tamaño de la muestra lo permita, el número de observaciones por categoría y las categorías demasiado escasas para una estimación estable. No se fijan umbrales de aceptación retrospectivos: cualquier criterio de decisión debe acordarse antes de observar resultados y justificarse con la literatura y el contexto de uso.

### Amenazas a la validez

- La concordancia puede variar por formación del observador, calidad del vídeo y complejidad táctica.
- El acuerdo alto en categorías frecuentes no prueba fiabilidad en acciones poco frecuentes.
- La conciliación posterior no debe confundirse con la medición independiente inicial.

## Protocolo B — Piloto de utilidad con cuerpo técnico

### Pregunta

¿Un staff técnico entiende, puede completar y considera trazables las tareas de análisis soportadas por el prototipo?

### Participantes y contexto

Reclutar entrenadores, segundos entrenadores o analistas de clubes del segmento objetivo. Registrar experiencia previa con vídeo, datos y GPS, así como el contexto real de revisión semanal. La participación debe ser voluntaria y la recogida de datos de investigación debe tener información y consentimiento adecuados.

### Tareas representativas

1. Interpretar el estado reciente de un equipo en Team Mode.
2. Localizar la evolución y el contexto de un jugador en Player Mode.
3. Revisar un partido y sus limitaciones de evidencia.
4. Responder una consulta clara mediante el Coach Copilot y abrir la evidencia consultada.
5. Identificar qué afirmación no permite hacer el sistema ante un guardrail de fatiga, lesión o XI.

### Variables a registrar

| Dimensión | Evidencia |
|---|---|
| Eficacia | condición objetiva de finalización de cada tarea y errores observados |
| Eficiencia | tiempo por tarea y necesidad de ayuda |
| Comprensión | explicación del participante sobre origen, criterio y limitación de una salida |
| Confianza | valoración declarada de trazabilidad y de claridad, acompañada de entrevista breve |
| Encaje operativo | momento de uso en la semana, coste de preparación y barreras de adopción |

### Análisis

Combinar estadísticos descriptivos de tareas con análisis temático de entrevistas. Separar siempre la aceptación de la interfaz, la comprensión de la evidencia y cualquier efecto deportivo. El piloto no puede demostrar que el sistema mejora resultados de competición sin un diseño posterior, comparador y outcomes definidos.

## Salvaguardas comunes

- Usar identidades demo o datos para los que exista autorización explícita.
- Separar datos de investigación de los datos operativos del club.
- Documentar versión de software, taxonomía y configuración de acceso.
- Reportar abandonos, incidencias y resultados negativos.
- No convertir una opinión de usuario en validación universal del Match Rating, GPS o recomendaciones tácticas.
