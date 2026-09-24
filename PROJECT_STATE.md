# PROJECT_STATE

Última actualización: 24/09/2026

Este archivo es la memoria técnica operativa del proyecto. Debe reflejar siempre el estado más reciente confirmado y prevalecer sobre conversaciones antiguas cuando exista una contradicción.

## 1. Fase actual

**Cierre del Data Collector y construcción del caso demostrador real.**

La auditoría de cobertura de LaLiga 2025/26 ya está completada y también se ha realizado una primera auditoría específica de variables para el equipo demostrador. El siguiente trabajo es cerrar qué acciones son realmente recogibles en fútbol amateur/semi-profesional y fijar el mapping definitivo PannaData/Opta → Data Collector.

## 2. Objetivo confirmado

Desarrollar una aplicación web funcional para equipos de fútbol amateur o semiprofesional sin departamento de análisis propio.

Flujo principal:

```text
VÍDEO / DATA COLLECTOR + GPS OPCIONAL
→ BASE DE DATOS
→ FEATURE ENGINE
→ MOTOR ANALÍTICO
→ SISTEMA EXPERTO / ML
→ DASHBOARD
→ ASISTENTE IA
→ INFORMES PDF
```

La aplicación web es el producto principal del TFM.

## 3. Decisiones aprobadas

- El sistema principal será **Team Mode**.
- **Player Mode** será complementario.
- **Rival Mode** será una extensión futura y no condicionará el TFM.
- El sistema principal debe funcionar sin datos del rival.
- El GPS será complementario y no obligatorio.
- Los datos brutos, features, modelos y conclusiones deben mantenerse separados.
- Las conclusiones importantes no pueden depender exclusivamente de un LLM.
- Debe evitarse data leakage.
- Toda regla, umbral o peso deberá justificarse mediante datos, literatura, validación o experimentación.
- Se priorizará un MVP funcional antes de aumentar la complejidad.
- GitHub será la fuente de verdad técnica del proyecto.
- La documentación oficial del TFM y del repositorio se redactará en castellano.
- Los nombres técnicos internos de código pueden mantenerse en inglés cuando sea estándar.
- El caso demostrador utilizará una temporada real completa reconstruida a partir de PannaData/Opta, pero el dataset publicable será anonimizado.

## 4. Data Collector — estado actual

Existe un prototipo HTML previo que debe simplificarse, no sustituirse sin una razón clara.

Familias de acciones actualmente en revisión:

- Pase
- Regate
- Remate
- Defensa
- Falta
- Pérdida
- Penalti
- Tarjeta
- Portero
- Contexto / eventos de equipo

Estructura base:

```text
action_type + subtype + outcome
```

### Pase — aprobado

Se registrarán también las pasadas normales porque el volumen y la efectividad de pase son variables centrales para el análisis de perfil, evolución y encaje de rol.

Diseño aprobado para maximizar rapidez y evitar dobles clics:

```text
PASS | NORMAL | SUCCESS/FAIL
PASS | LONG   | SUCCESS/FAIL
PASS | CROSS  | SUCCESS/FAIL
```

Una acción `LONG` o `CROSS` cuenta automáticamente también como pase total. El usuario no debe registrar adicionalmente una pasada normal para la misma acción.

La efectividad no se recoge manualmente; se deriva posteriormente a partir de completadas / totales.

### Regate — aprobado

```text
DRIBBLE | SUCCESS
DRIBBLE | FAIL
```

Un regate fallado genera automáticamente una pérdida derivada y no debe registrarse además como `LOSS`.

### Defensa — aprobado

Se mantienen como acciones separadas:

```text
TACKLE
INTERCEPTION
BLOCK
CLEARANCE
```

El despeje se mantiene en el MVP como acción defensiva propia.

### Pérdida — aprobado

`LOSS` se utilizará únicamente para pérdidas de posesión no explicadas ya por una pasada fallada o un regate fallado.

No se generará una segunda acción de pérdida cuando el origen ya esté registrado en la propia acción. La capa derivada podrá clasificar el motivo de la pérdida, por ejemplo:

```text
PASS | ... | FAIL      → possession_lost = 1 | loss_reason = FAILED_PASS
DRIBBLE | ... | FAIL   → possession_lost = 1 | loss_reason = FAILED_DRIBBLE
LOSS | OTHER           → possession_lost = 1 | loss_reason = OTHER_TURNOVER
```

Objetivo: evitar doble conteo y poder obtener tanto pérdidas totales como pérdidas por origen.

### Remate — aprobado

El Collector usará una única selección por remate:

```text
SHOT | GOAL
SHOT | ON_TARGET
SHOT | OFF_TARGET
SHOT | BLOCKED
```

Cada opción cuenta automáticamente como remate total. No debe registrarse primero una acción genérica de remate.

Los remates al poste se agrupan dentro de `OFF_TARGET` para mantener la interfaz simple.

### Falta y disciplina — aprobado

Diseño base:

```text
FOUL | COMMITTED
FOUL | RECEIVED
CARD | YELLOW
CARD | RED
```

Las tarjetas se registran como eventos propios y no dependen obligatoriamente de una falta, ya que pueden producirse por otros motivos. En caso de segunda amarilla con expulsión se conservarán ambas consecuencias disciplinarias.

Se ha propuesto añadir una distinción de **falta peligrosa** cometida/recibida. El concepto se considera útil, pero su criterio operativo exacto debe cerrarse antes de aprobarlo para evitar subjetividad.

### Penalti — aprobado parcialmente

La lógica acordada es:

```text
PENALTY → WON / CONCEDED → GOAL / MISSED
```

No se utilizará un botón persistente separado para "gol de penalti".

### Contexto / eventos de equipo — pendiente de cierre

Se ha identificado la necesidad de una capa de eventos de equipo que no obligue a duplicar las acciones ya registradas a nivel jugador.

Candidatos prioritarios:

```text
CORNER | FOR
CORNER | AGAINST
```

Las estadísticas de equipo que puedan agregarse desde acciones de jugador (pases, remates, faltas, tarjetas, defensa, etc.) se derivarán automáticamente y no se volverán a introducir manualmente.

La posible etiqueta de falta peligrosa deberá agregarse sobre la propia acción de falta, permitiendo derivar después faltas peligrosas a favor/en contra sin doble registro.

Las variables definitivas todavía no están cerradas.

## 5. Datos de desarrollo disponibles

Fuente de desarrollo y validación: **PannaData / Opta**.

Inventario local confirmado en:

```text
C:\Users\sergi\Desktop\analisi_futbol\input\pannadata\
```

Fuentes relevantes disponibles:

```text
opta_fixtures.parquet
opta_lineups.parquet
opta_player_stats.parquet
opta_players.parquet
opta_events.parquet
opta_shot_events.parquet
opta_shots.parquet
opta_match_xg.parquet
```

También existen ficheros de eventos por competición para EPL, La Liga, Serie A, Bundesliga, Ligue 1 y competiciones internacionales.

Existe además una base local:

```text
C:\Users\sergi\Desktop\analisi_futbol\outputs\base_pannadata.duckdb
```

con tablas originales y derivadas. Las tablas derivadas de proyectos anteriores no deben confundirse con la fuente original ni utilizarse automáticamente como base del TFM.

## 6. Auditoría de cobertura LaLiga 2025/26

La auditoría confirma:

```text
20 equipos
380 partidos de liga
38 partidos por equipo
100 % de cobertura en fixtures
100 % de cobertura en player stats
100 % de cobertura en lineups
100 % de cobertura en events
```

Por tanto, la elección del equipo demostrador no depende de disponibilidad de datos, sino de su adecuación metodológica al objetivo del TFM.

## 7. Equipo demostrador aprobado

**Equipo fuente local: Deportivo Alavés — LaLiga 2025/26.**

Identificador Opta detectado localmente:

```text
4dtdjgnpdq9uw4sdutti0vaar
```

Motivos de selección:

- 38 partidos con cobertura completa.
- Clasificado en la auditoría como equipo sin competición europea en 2025/26.
- Perfil estadístico intermedio y razonable para utilizarlo como sustituto de un equipo amateur/semi-profesional, evitando perfiles demasiado extremos.
- Volumen de pase claramente inferior a equipos dominantes pero no tan atípico como el extremo observado en Getafe.
- Perfil equilibrado entre pase, juego directo, centros, defensa y faltas.

Estos valores sirven únicamente para justificar la elección del caso demostrador. No se aprueban automáticamente como métricas finales del producto.

## 8. Auditoría específica Data Collector

La auditoría del equipo demostrador confirma 38/38 partidos en fixtures, player stats, lineups y events.

Variables Opta directamente disponibles y potencialmente mapeables al Collector:

```text
Pase: totalPass / accuratePass
Pase largo: totalLongBalls / accurateLongBalls
Centro: totalCross / accurateCross
Asistencia: goalAssist
Regate: totalContest / wonContest
Remate: totalScoringAtt / blockedScoringAtt / goals
Defensa: totalTackle / wonTackle / interception / blockedPass / totalClearance
Falta: fouls / wasFouled
Pérdida: turnover / dispossessed
Disciplina: yellowCard / redCard
Penalti: penaltyConceded / penaltyWon
Portero: saves / divingSave / goalsConceded
```

La fuente de eventos Opta permite mapear tipos de acción mediante `type_id`. Entre los identificadores relevantes confirmados en la documentación de PannaData se encuentran, entre otros:

```text
1  Pass
3  Take on
4  Foul
7  Tackle
8  Interception
9  Turnover
10 Save
12 Clearance
13 Miss
14 Post
15 Attempt saved
16 Goal
17 Card
32 Blocked pass
67 Dispossessed
77 Key pass
```

Aspectos que requieren resolución antes del cierre:

- El remate a portería debe reconstruirse desde las fuentes de tiro/eventos, separando disparos realmente dirigidos a portería de bloqueos defensivos.
- El resultado de penaltis debe reconstruirse desde eventos de tiro y qualifiers.
- Debe cerrarse el criterio operativo de falta peligrosa.
- Deben cerrarse los eventos de equipo imprescindibles del MVP, empezando por córners a favor/en contra.
- Debe definirse la interfaz exacta de penalti y portero.
- El principal problema metodológico pendiente ya no es disponibilidad de datos, sino equilibrio entre valor analítico y coste de recogida manual.

## 9. Política de anonimización del dataset demostrador

Los datos reales de Deportivo Alavés se utilizarán únicamente de forma local para construir y validar el sistema.

Antes de incorporar un dataset demostrador al repositorio se anonimizarán:

```text
Deportivo Alavés  → TEAM_001
jugadores reales  → PLAYER_001, PLAYER_002, ...
oponentes          → OPP_001, OPP_002, ...
identificadores    → identificadores internos
```

Se mantendrán las estadísticas, minutos, posiciones y secuencia temporal necesarias para reproducir los análisis.

Está previsto crear un proceso reproducible:

```text
scripts/build_anonymized_demo.py
```

El repositorio no debe contener una copia completa de los datasets originales de PannaData/Opta.

## 10. Arquitectura analítica prevista

La unidad principal de análisis será **jugador-partido**.

El sistema deberá relacionar, como mínimo:

```text
jugador
+ partido
+ minutos
+ rol
+ acciones de vídeo
+ GPS opcional
+ contexto del equipo
+ resultados derivados
```

El esquema definitivo de base de datos todavía no está aprobado.

## 11. Sistema experto previsto

Estructura jerárquica inicial:

```text
N1000  disponibilidad / actividad
N2000  perfil estructural
N3000  forma / evolución
N4000  amenaza ofensiva
N5000  creación / progresión
N6000  contribución defensiva
N7000  finalización
N8000  contexto del equipo
N9000  componente físico
N10000 rol y encaje táctico
N11000 consistencia / tendencia
N12000 player fit
N13000 recomendación final
```

Cada nodo deberá tener:

```text
entrada → condición → resultado → confianza → justificación
```

No se construirán ramas detalladas hasta cerrar las variables disponibles.

## 12. LLM / asistente IA

Arquitectura obligatoria:

```text
DATA → ANALYTICS → DECISION ENGINE → LLM → COACH
```

El LLM podrá interpretar preguntas, explicar resultados, resumir tendencias y generar informes, pero no podrá inventar métricas ni sustituir cálculos críticos del motor analítico.

## 13. Pendientes abiertos

- Cerrar el criterio de falta peligrosa cometida/recibida.
- Cerrar los eventos de equipo del MVP, empezando por córners a favor/en contra.
- Cerrar el tratamiento de penalti.
- Definir las acciones de portero del MVP.
- Resolver técnicamente remate a portería y resultado de penaltis desde `shot_events`.
- Cerrar las variables definitivas del Data Collector.
- Extraer la temporada 2025/26 del equipo fuente con las variables aprobadas.
- Crear el proceso reproducible de anonimización.
- Definir el esquema de datos estándar del proyecto.
- Definir la capa de normalización GPS.

## 14. Decisiones descartadas o no aprobadas

- No usar directamente todas las variables profesionales disponibles solo porque existan en Opta.
- No construir todavía el árbol experto detallado.
- No construir todavía el Feature Engine definitivo.
- No usar datos ficticios como caso principal si puede reconstruirse una temporada real.
- No publicar los datasets completos de PannaData/Opta dentro del repositorio.
- No seleccionar Getafe como caso demostrador principal: su perfil de pase y disciplina es más extremo y menos representativo para el caso que se quiere simular.
- No crear una acción adicional de pérdida cuando la pérdida ya está contenida en una pasada o regate fallado.
- No crear un botón separado para remate al poste en el MVP.

## 15. Siguiente paso exacto

**Cerrar la capa de contexto/equipo y las familias restantes del Data Collector.**

Orden inmediato:

```text
1. cerrar criterio de falta peligrosa
2. cerrar córners y otros eventos de equipo imprescindibles
3. cerrar penalti
4. cerrar portero
5. resolver mapping técnico de shot_events
6. aprobar variables definitivas
7. crear esquema de datos
```
