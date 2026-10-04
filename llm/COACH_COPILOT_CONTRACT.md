# Coach Copilot — contrato funcional canónico

Fecha de cierre MVP: 04/10/2026  
Estado: **contrato de producto y validación**

Este documento define qué debe entender y responder el Coach Copilot, qué debe rechazar y cómo se valida. No se amplía el comportamiento mediante parches frase-a-frase: cualquier cambio debe encajar en este espacio de consultas y conservar los guardrails.

## 1. Principio arquitectónico

```text
DATA
→ FEATURES / ANALYTICS
→ DECISION ENGINE
→ TOOLS READ-ONLY
→ ROUTER DETERMINISTA
→ LLM SOLO SI SIGUE HABIENDO AMBIGÜEDAD
→ RESPUESTA
→ CAPA DE PRESENTACIÓN / ANONIMIZACIÓN
→ COACH
```

El LLM no calcula métricas, rankings, Match Rating, Performance Index ni decisiones expertas. Solo interpreta lenguaje cuando las reglas deterministas no son suficientes y, en el modo externo, puede redactar a partir de evidencia estructurada.

## 2. Regla de trabajo

La calidad del asistente se valida sobre **familias de consulta**, no esperando a que un usuario encuentre una frase que falle.

Cada consulta se descompone en:

```text
ENTIDAD
+ OPERACIÓN
+ MÉTRICA / CONJUNTO DE MÉTRICAS
+ AGREGACIÓN
+ FILTROS
+ VENTANA TEMPORAL
+ CONTEXTO CONVERSACIONAL
```

Si una frase nueva expresa una combinación ya soportada, debe resolverse por composición. No se crea una regla futbolística nueva solo porque cambie la redacción.

## 3. Entidades soportadas

- equipo;
- jugador;
- grupo posicional / rol;
- partido / rival;
- GPS descriptivo;
- calidad y cobertura de datos.

## 4. Operaciones soportadas

- `retrieve`: obtener perfil, historial, partido o GPS;
- `rank`: ordenar jugadores por una métrica aprobada;
- `compare`: comparar jugadores concretos;
- `compare_role`: comparar jugadores de una posición;
- `trend`: describir evolución/tendencia materializada;
- `aggregate`: total, media, máximo, mínimo o último valor cuando la métrica lo permita;
- `explain_evidence`: explicar qué datos/herramientas sustentan la respuesta;
- `quality`: describir cobertura y limitaciones.

## 5. Métricas consultables

### Estadísticas observadas

- goles;
- asistencias;
- remates;
- pases totales;
- pases completados;
- entradas;
- entradas ganadas;
- intercepciones;
- pérdidas;
- desposesiones;
- minutos;
- apariciones.

### GPS descriptivo

- distancia total;
- velocidad máxima;
- aceleración máxima;
- aceleración mínima / desaceleración máxima observada.

### Rendimiento materializado

- Match Rating más reciente;
- Match Rating medio últimos 5 cuando existe;
- tendencia 5 vs 5 materializada.

No se inventa ninguna métrica que no esté en esta lista o en una capa inferior versionada.

## 6. Agregaciones y orden

Se interpretan de forma composicional:

```text
"total", "acumulado"              → sum
"por partido", "promedio", "media" → mean
"máximo", "pico"                  → max
"mínimo"                           → min
"último", "actual"                → latest cuando aplica
"más", "mayor", "mejor valor"    → desc
"menos", "menor", "peor valor"   → asc
```

En métricas de rating materializadas se respeta el campo precomputado; el asistente no recalcula ratings.

## 7. Ventanas temporales

Se soporta:

- periodo disponible;
- últimos `N` partidos del equipo cuando la herramienta lo admite;
- últimos 5 en los campos materializados específicos.

Las ventanas se aplican a datos observados/materializados y no pueden introducir información futura.

## 8. Roles / posiciones

Grupos canónicos:

```text
GK  portero / guardameta
CB  central / defensa central
FB  lateral / carrilero
DM  pivote / mediocentro defensivo
CM  mediocentro / centrocampista / interior
AM  mediapunta
W   extremo
ST  delantero / delantero centro / punta / atacante
```

Consultas válidas:

- comparar las principales estadísticas de los delanteros;
- comparar centrales;
- mostrar métricas de laterales;
- quién ha rendido mejor como central;
- quién ha rendido mejor como delantero en los últimos N partidos.

Cuando se pregunta **quién ha rendido mejor dentro de una posición**, el criterio debe declararse explícitamente: **Match Rating medio en la muestra seleccionada**. Las demás métricas son apoyo descriptivo; no se crea un nuevo score de posición.

## 9. Métricas descriptivas por posición

El conjunto mostrado depende del rol, usando únicamente variables ya disponibles:

- ST: rating medio, minutos, goles, asistencias, remates;
- CB: rating medio, minutos, entradas ganadas, intercepciones, precisión de pase, pérdidas;
- FB: rating medio, minutos, asistencias, entradas ganadas, intercepciones, precisión de pase;
- DM/CM: rating medio, minutos, pases completados, precisión de pase, entradas ganadas, intercepciones, asistencias;
- AM/W: rating medio, minutos, goles, asistencias, remates, pases completados;
- GK: rating medio, minutos, paradas, goles encajados, precisión de pase.

Este conjunto es una vista descriptiva de datos existentes. No equivale a una valoración científica específica de cada posición.

## 10. Comparación de jugadores concretos

Si el usuario nombra dos o más jugadores existentes, el sistema puede compararlos mediante los campos estructurados disponibles.

Ejemplos:

- `Compara Jugador 03 con Jugador 07`;
- `¿Cómo están A y B?` si la referencia conversacional es inequívoca;
- `¿Y cuál tiene mejor media últimos 5?` como follow-up de una comparación soportada.

No se inventan jugadores ni se completa un nombre ambiguo sin evidencia suficiente.

## 11. Follow-ups obligatorios

El asistente debe preservar el último **ancla sustantiva** y resolver, cuando sea posible:

- `¿Y el segundo?`;
- `¿Y el tercero?`;
- `¿Y en los últimos 5 partidos?`;
- `¿Qué evidencias tienes?`;
- `Sí, compáralos`;
- `Muéstrame las métricas`;
- `¿Y los delanteros?` cuando el cambio de rol sea explícito.

Un follow-up no puede anclarse a otro follow-up vacío perdiendo la consulta original.

## 12. Guardrails

Debe rechazar o limitar explícitamente:

- fatiga/cansancio como inferencia fisiológica;
- readiness;
- riesgo de lesión;
- XI ideal / quién debería ser titular;
- recomendación táctica automática;
- rol óptimo no validado;
- jugador "más completo" o "más determinante" sin criterio analítico explícito;
- causalidad no demostrada;
- métricas inexistentes.

El rechazo debe proponer alternativas soportadas cuando sean obvias, por ejemplo métricas GPS descriptivas o Match Rating.

## 13. "Mejor jugador" y lenguaje evaluativo

Casos diferentes:

```text
"mejor rating"                  → válido: métrica explícita
"mejor central"                 → válido: rol explícito + criterio Match Rating medio declarado
"mejor jugador del equipo"      → no válido sin criterio explícito
"más completo"                  → no válido sin definición aprobada
"más determinante"              → no válido sin definición aprobada
```

## 14. Identidad y anonimización

La identidad visible del asistente debe ser **exactamente la misma que la visible en la plataforma**.

En modo demo:

- equipo: alias de la plataforma (`Equipo Demo`, etc.);
- jugadores: `Jugador XX` estable por `player_id`;
- rivales: `Rival XX` estable;
- el usuario escribe esos aliases;
- justo antes de consultar las tools, la capa de identidad traduce alias → identidad runtime canónica;
- antes de mostrar cualquier texto, se aplica identidad runtime → alias;
- ninguna respuesta, historial o texto generado puede exponer nombres reales conocidos.

La traducción inversa de `Jugador XX` debe apuntar al **nombre completo canónico**, no a un apellido o abreviatura.

En modo privado (`FPS_DEMO_MODE=0`) se pueden mostrar identidades reales localmente.

## 15. Proveedores

### Local

```text
reglas deterministas
→ tools
→ respuesta determinista
```

Solo si la intención sigue siendo ambigua:

```text
Qwen local
→ selección de tools
→ tools
→ respuesta grounded
```

### OpenAI con API key del usuario

Las mismas reglas deterministas se ejecutan primero. Solo si no bastan:

```text
OpenAI
→ selección de tools permitidas
→ tools FPS
→ evidencia estructurada
→ síntesis grounded
```

Las capacidades deterministas —incluida comparación por posición— deben comportarse igual con Qwen u OpenAI y no generar coste API.

## 16. Política de respuesta

Una respuesta válida debe:

1. contestar directamente a la pregunta;
2. indicar el criterio cuando pueda ser ambiguo;
3. utilizar únicamente cifras de tools/evidencia;
4. declarar falta de datos cuando corresponda;
5. evitar lenguaje causal no soportado;
6. mantener identidad/anónimos de la plataforma;
7. ser breve y útil para un entrenador.

## 17. Política de fallback

No se debe enviar automáticamente toda consulta rara al LLM si puede clasificarse como:

- basura/entrada sin intención (`sss`, etc.);
- fuera de dominio;
- criterio prohibido;
- ausencia de datos.

En esos casos se devuelve una respuesta inmediata y no se consume 20–30 s de Qwen ni API externa.

## 18. Validación obligatoria

El contrato se valida automáticamente en CI sobre la demo sintética:

- rankings por métricas principales;
- agregaciones;
- ventanas;
- perfiles;
- GPS;
- partidos;
- equipo;
- calidad;
- comparaciones de jugadores;
- comparaciones de todos los grupos posicionales;
- follow-ups;
- guardrails;
- alias → runtime → alias;
- ausencia de nombres runtime en presentación demo;
- cero uso de LLM en consultas deterministas del core.

La prueba manual del usuario queda reservada a **revisión visual final**, no a descubrir funcionalidad básica una pregunta cada vez.

## 19. Criterio de cierre

Coach Copilot puede considerarse cerrado para entrega cuando:

```text
CI query-space contract = PASS
privacy/alias contract  = PASS
core deterministic      = PASS sin Ollama
local real-DB smoke      = PASS
visual UI check          = PASS
```

Los nuevos casos encontrados posteriormente se clasifican primero dentro del espacio anterior. Solo se añade una nueva capacidad si requiere una operación, métrica o inferencia realmente distinta.
