# Revisión crítica pre-defensa y de evolución del producto

Fecha: 04/10/2026  
Alcance: código y documentación de `main`, CI, demo sintética, material de defensa y estado de sincronización local. Esta revisión distingue evidencia observada de propuestas; no convierte trabajo futuro en un resultado del TFM.

## Diagnóstico ejecutivo

El objetivo del TFM es de Ciencia de Datos e Inteligencia Artificial: demostrar que datos observacionales de vídeo y GPS opcional pueden recorrer una cadena reproducible de datos, features, analytics, decisión explicable y lenguaje natural grounded sin trasladar el cálculo crítico a un LLM. La aplicación web y la futura empresa son vehículos de demostración, no el objeto académico principal.

El proyecto ya tiene una base poco habitual para ese objetivo: arquitectura separada por capas, control de leakage, features strict-past, sistema experto auditable, contrato composicional para el Coach, demo sintética y validación automática. El mayor margen de mejora de la nota está en hacer explícita la pregunta científica, el método de evaluación y las amenazas a la validez de cada resultado. No está en añadir otra métrica, otra pantalla ni un modelo sin target independiente.

La sección de servicio comercial se mantiene como una consecuencia posterior: indica qué tendría que cambiar para convertir el prototipo validado técnicamente en un producto de clientes, sin convertir esas necesidades en requisitos del TFM.

## Hallazgos prioritarios

| Prioridad | Hallazgo verificable | Impacto | Acción recomendada |
|---|---|---|---|
| P0 | `main` está dos commits por delante de `origin/main`: `b393a41` y `1b7c047` todavía no están en GitHub. | La versión pública y su CI no incluyen las capturas ni el deck. | Hacer push, comprobar el workflow del commit resultante y etiquetar el punto de entrega. |
| P0 | El workflow ejecuta `publication.final_delivery_check --allow-missing-screenshots`. | CI puede quedar verde aunque desaparezcan las diez capturas exigidas para la memoria. | En la rama de entrega, eliminar esa excepción o crear un gate de release separado que obligue a las diez capturas. |
| P0 | `app/access_control.py` usa variables de entorno y el rol local por defecto es `SUPERADMIN`; `docs/ACCESS_CONTROL.md` documenta que aún faltan login, sesiones, administración y audit log. | Es correcto para el MVP local, pero no protege un servicio multi-club en producción. | No desplegar con datos de clientes hasta integrar autenticación, scope de organización persistente, logs de acceso y pruebas de autorización end-to-end. |
| P0 | No hay política de privacidad, retención, contrato de encargado, inventario de tratamientos ni proceso de incidentes versionados. | Los datos de rendimiento identificables requieren gobierno antes de un piloto comercial. | Definir responsable/encargado por flujo, finalidad, retención, derechos, subencargados, controles técnicos y evaluación de impacto cuando el riesgo lo requiera. |
| P1 | `requirements.txt` usa rangos mínimos sin fichero de bloqueo; CI instala las versiones disponibles en cada ejecución. | La demo es reproducible funcionalmente, pero no queda fijada de forma determinista a nivel de dependencias. | Añadir lockfile o constraints generados y validar una instalación limpia contra esas versiones. |
| P1 | No hay licencia, aviso de uso comercial ni documento de contribución en la raíz. | La titularidad y el uso del código no quedan claros para colaboradores, clientes ni inversores. | Decidir estrategia de propiedad intelectual antes de publicar: código cerrado, licencia comercial o licencia open source compatible con el plan de negocio. |
| P1 | CI cubre tests, demo y contrato, pero no ejecuta lint, type-check, cobertura, auditoría de dependencias ni análisis estático de seguridad. | Reduce la señal de madurez de ingeniería y deja regresiones de mantenimiento fuera del gate. | Añadir estas comprobaciones gradualmente, con umbrales realistas y sin convertir métricas de tooling en claims deportivos. |
| P1 | La memoria tiene hipótesis y objetivos, pero no formula preguntas de investigación ni una tabla única que vincule cada objetivo con método, evidencia y amenaza a la validez. | Un tribunal puede percibir el trabajo como una gran implementación bien documentada, pero con evaluación académica menos nítida. | Añadir un bloque de preguntas de investigación y una matriz de evaluación derivada de la actual matriz de evidencias. |
| P1 | No existe estudio con entrenadores/analistas ni fiabilidad interobservador del Collector. El propio manuscrito lo reconoce. | Es el límite principal de validez externa y de utilidad operativa. | Preparar un protocolo de piloto y explicarlo como trabajo futuro listo para ejecutar, sin presentar resultados inexistentes. |
| P2 | El fallback Qwen y OpenAI BYOK tienen contratos, pero no benchmark live de calidad, coste y latencia para ambigüedad real. | La propuesta de IA es técnicamente sólida, aunque no hay evidencia de valor adicional del LLM para usuarios. | Medirlo solo después de definir tareas de usuario y una muestra de preguntas ambiguas reales. |

## Mejoras que elevarían la nota del TFM de Ciencia de Datos e IA

### 1. Hacer evaluable la contribución académica

Añadir tres preguntas de investigación explícitas y responderlas con evidencia existente:

| Pregunta propuesta | Evidencia que ya existe | Límite que debe permanecer visible |
|---|---|---|
| ¿Puede una arquitectura basada en datos observables producir análisis reproducibles sin leakage temporal? | FEATURE-01/02/03, validadores strict-past y demo sintética. | No valida superioridad deportiva. |
| ¿Puede un asistente en lenguaje natural mantener grounding y trazabilidad sin calcular métricas críticas? | Contrato composicional, CI y smoke 28/28 con `rounds=0`. | No mide satisfacción ni cobertura de ambigüedad real. |
| ¿Puede el sistema servir como prototipo de trabajo para un cuerpo técnico con recursos limitados? | Collector, dashboard, PDF, demo y arquitectura desplegable localmente. | Falta evaluación de uso con personal técnico. |

La memoria debe presentar cada respuesta como una **validación técnica**. La evaluación con entrenadores, la fiabilidad interobservador y la validez externa del Match Rating deben aparecer en una tabla de amenazas a la validez, no como notas dispersas.

### 2. Poner la contribución de Ciencia de Datos e IA en primer plano

El manuscrito explica muchas capas con precisión. Para una defensa y una memoria más fuertes, conviene priorizar cuatro artefactos visuales que conecten problema, método y resultado científico:

1. arquitectura completa;
2. strict-past;
3. trazabilidad de una pregunta del Coach hasta DuckDB;
4. matriz de validación con qué demuestra y qué no demuestra cada gate.

La enumeración exhaustiva de módulos, nombres internos y estados `PASS` debe pasar a anexos cuando no cambie la interpretación metodológica. En el cuerpo deben quedar claros: unidad jugador-partido, preservación de valores ausentes, strict-past, separación entre analytics y decisión, criterios de abstención del sistema experto, y grounding del Coach.

### 3. Convertir limitaciones en un plan de evaluación serio

Preparar, sin inventar resultados, dos protocolos anexos:

- **Fiabilidad del Collector:** dos observadores codifican una misma muestra de partidos; se define unidad de observación, categorías, acuerdo por categoría, criterio de discrepancia y procedimiento de revisión.
- **Piloto con staff:** cada participante completa tareas representativas sobre Team, Player, Match y Coach; se registran tiempo por tarea, éxito, errores de interpretación, confianza declarada y entrevistas breves sobre utilidad.

Esto mejora el rigor del trabajo futuro y permite responder a la pregunta del tribunal "¿cómo validarías esto en un club?" con un diseño concreto.

### 4. Asegurar el cierre reproducible

Antes de la defensa, el repositorio debe publicar los dos commits locales y el CI debe comprobar el paquete de entrega completo, incluidas las capturas. Después se recomienda crear una etiqueta de versión y conservar el hash de la demo sintética utilizada en la defensa.

## Evolución a producto o servicio después del TFM

### Propuesta de valor defendible

El producto no debe presentarse como una alternativa de bajo coste a todos los proveedores profesionales. La propuesta defendible es:

> Para clubes amateur y semiprofesionales que ya disponen de vídeo y, en algunos casos, GPS, FPS convierte observaciones de partido en un historial auditable de equipo, jugador y partido, con una explicación verificable de cada resultado.

La diferenciación no es "tener IA". Es preservar el vínculo entre dato, cálculo, evidencia y explicación, incluso cuando el usuario pregunta en lenguaje natural.

### Segmento inicial y flujo de trabajo

El primer segmento debe ser estrecho: un club semiprofesional o academia con analista o ayudante que ya revisa vídeo cada semana. El flujo a validar es semanal:

```text
vídeo / eventos observados
→ revisión y validación del partido
→ informe de equipo y jugadores
→ conversación de staff
→ decisión humana documentada
```

No hay evidencia todavía de cuánto tarda la captura, de qué funciones se usan cada semana ni de qué resultado ahorra tiempo. Por eso el primer piloto debe medir el flujo completo antes de invertir en más modelos.

### Métricas de producto que faltan

Definirlas antes del piloto, sin fijar objetivos numéricos ficticios:

| Área | Métrica que conviene medir | Decisión que informa |
|---|---|---|
| Activación | tiempo hasta primer partido analizado e informe compartible | si el onboarding es viable |
| Valor recurrente | semanas con revisión de Team, Player o Match por el staff | si el flujo entra en la rutina |
| Eficiencia | tiempo de codificación y preparación frente al proceso actual | si reduce carga operativa |
| Confianza | proporción de salidas que el staff entiende, considera trazables y revisa | si la explicación aporta valor |
| Calidad de datos | cobertura, correcciones y discrepancias entre observadores | si la entrada sostiene el producto |
| Retención | continuidad de uso por club y equipo | si existe problema recurrente |

### Ruta de producto recomendada

**Fase 1: piloto controlado.** Un reducido número de clubes, datos propios, un flujo semanal acotado y revisión humana obligatoria. Priorizar Collector, Team/Player/Match, PDF y trazabilidad. No vender recomendaciones de XI, fatiga o lesión.

**Fase 2: producto operable.** Autenticación, multi-tenancy persistente, permisos por equipo y módulo, logs de auditoría, backups, migraciones, monitorización y soporte de importación.

**Fase 3: evidencia comercial.** Comparar el flujo del club antes y después, entrevistar usuarios, medir adopción y decidir si el Coach semántico aporta valor medible frente a la ruta determinista.

## Privacidad, seguridad y gobierno antes de comercializar

La demo protege identidades y excluye la DuckDB profesional del repositorio. Eso no equivale a un programa de privacidad para producción. La Comisión Europea resume que el RGPD exige finalidad definida, minimización, retención limitada y medidas adecuadas contra accesos no autorizados; también recomienda protección de datos desde el diseño y por defecto. [Comisión Europea: principios del RGPD](https://commission.europa.eu/law/law-topic/data-protection/reform/rules-business-and-organisations/principles-gdpr/overview-principles/what-data-can-we-process-and-under-which-conditions_en) y [obligaciones de seguridad](https://commission.europa.eu/law/law-topic/data-protection/information-business-and-organisations/obligations_en).

Antes de un piloto comercial se deben acordar, con asesoramiento jurídico especializado cuando corresponda:

- base jurídica, roles de responsable y encargado, y contratos con cada club;
- inventario de datos, finalidades, retención y procedimiento de borrado/exportación;
- clasificación de datos GPS y cualquier dato que pudiera revelar información de salud;
- autenticación, mínimo privilegio, logs, backups cifrados y respuesta a incidentes;
- evaluación de impacto si el tratamiento puede implicar alto riesgo. El EDPB explica que una DPIA es necesaria antes de tratamientos que probablemente generen alto riesgo para derechos y libertades. [EDPB: DPIA](https://www.edpb.europa.eu/topics/accountability-and-compliance-tools/data-protection-impact-assessment_en).

## Orden de ejecución recomendado

1. Añadir preguntas de investigación, matriz objetivo-evidencia-límite y amenazas a la validez a la memoria.
2. Crear los protocolos de fiabilidad del Collector y piloto de staff como anexos, sin resultados simulados.
3. Adaptar formato, bibliografía y referencias cruzadas a la plantilla universitaria.
4. Publicar los commits locales, ejecutar y registrar CI de la versión final.
5. Preparar la defensa alrededor de la cadena de Ciencia de Datos e IA: datos observados, strict-past, analytics, sistema experto, Coach grounded y límites.
6. Tras la entrega, definir ICP, flujo semanal y métricas de piloto antes de ampliar funcionalidades comerciales.
7. Antes de procesar datos de clientes, completar identidad, multi-tenancy, observabilidad, seguridad y gobierno de datos.

## Lo que no conviene hacer ahora

- añadir métricas deportivas, scores o recomendaciones sin nueva evidencia;
- presentar 28/28 como validación de usuarios o de valor comercial;
- vender GPS descriptivo como prevención de fatiga o lesión;
- desplegar el MVP con datos de clientes solo porque la demo sintética pase CI;
- ampliar el uso de LLM antes de demostrar que resuelve una necesidad de usuario mejor que la ruta determinista;
- confundir la preparación comercial con evidencia de Ciencia de Datos e IA.
