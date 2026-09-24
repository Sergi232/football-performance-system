# PROJECT_STATE

Última actualización: 24/09/2026

Este archivo es la memoria técnica operativa del proyecto. Debe reflejar siempre el estado más reciente confirmado y prevalecer sobre conversaciones antiguas cuando exista una contradicción.

## 1. Fase actual

**Auditoría de datos y cierre del Data Collector.**

Antes de definir el esquema de datos, el Feature Engine o el sistema experto, se está comprobando qué variables reales están disponibles y cuáles son razonables de recoger en fútbol amateur o semiprofesional.

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

Decisión de diseño provisional:

```text
action_type + subtype + outcome
```

Ejemplos:

```text
PASS | NORMAL/LONG/CROSS | SUCCESS/FAIL
SHOT | GOAL/ON_TARGET/OFF_TARGET/BLOCKED
PENALTY | WON/CONCEDED | GOAL/MISSED
```

La lógica de penalti acordada es:

```text
PENALTI → RECIBIDO / CONCEDIDO → GOL / NO GOL
```

No se utilizará un botón persistente separado para "gol de penalti".

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

También existen ficheros de eventos por competición para:

```text
EPL
La Liga
Serie A
Bundesliga
Ligue 1
UCL
UEL
Conference League
UEFA Super Cup
World Cup
UEFA Euros
Copa America
```

Existe además una base local:

```text
C:\Users\sergi\Desktop\analisi_futbol\outputs\base_pannadata.duckdb
```

con tablas originales y derivadas. Entre las fuentes Opta disponibles dentro de la base aparecen:

```text
ext_opta_fixtures
ext_opta_lineups
ext_opta_match_xg
ext_opta_player_stats
ext_opta_players
ext_opta_shot_events
ext_opta_shots
```

También existen tablas derivadas de proyectos anteriores. No deben confundirse con la fuente original ni utilizarse automáticamente como base del TFM.

## 6. Criterio para el caso demostrador

Se reconstruirá una temporada completa de un **equipo real de la temporada 2025/26 que no disputara competición europea**, utilizando únicamente sus partidos de liga si ello permite mantener un caso limpio y homogéneo.

El equipo todavía **no está seleccionado definitivamente**.

Criterios de selección:

- temporada completa disponible;
- buena cobertura de fixtures, alineaciones, player stats y eventos;
- sin necesidad de cruzar competiciones europeas;
- adecuado para demostrar un producto orientado a fútbol amateur/semi-profesional.

## 7. Política de anonimización del dataset demostrador

Los datos reales se utilizarán localmente para construir y validar el sistema.

Antes de incorporar un dataset demostrador al repositorio se anonimizarán:

```text
club real        → TEAM_001
jugadores reales → PLAYER_001, PLAYER_002, ...
oponentes         → OPP_001, OPP_002, ...
identificadores   → identificadores internos
```

Se mantendrán las estadísticas, minutos, posiciones y secuencia temporal necesarias para reproducir los análisis.

Está previsto crear un proceso reproducible, por ejemplo:

```text
scripts/build_anonymized_demo.py
```

El repositorio no debe contener una copia completa de los datasets originales de PannaData/Opta.

## 8. Arquitectura analítica prevista

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

## 9. Sistema experto previsto

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

## 10. LLM / asistente IA

Arquitectura obligatoria:

```text
DATA → ANALYTICS → DECISION ENGINE → LLM → COACH
```

El LLM podrá interpretar preguntas, explicar resultados, resumir tendencias y generar informes, pero no podrá inventar métricas ni sustituir cálculos críticos del motor analítico.

## 11. Pendientes abiertos

- Auditar las columnas reales de los Parquet originales.
- Mapear PannaData/Opta → variables potenciales del Data Collector.
- Revisar específicamente regate, defensa, pérdida, penalti, tarjetas y acciones de portero.
- Determinar si registrar todos los pases normales es viable para el contexto amateur.
- Cerrar definitivamente las variables del Data Collector.
- Seleccionar el equipo demostrador 2025/26.
- Comprobar cobertura completa de su temporada.
- Definir el esquema de datos estándar del proyecto.
- Definir la capa de normalización GPS.

## 12. Decisiones descartadas o no aprobadas

- No usar directamente todas las variables profesionales disponibles solo porque existan en Opta.
- No construir todavía el árbol experto detallado.
- No construir todavía el Feature Engine definitivo.
- No usar datos ficticios como caso principal si puede reconstruirse una temporada real.
- No publicar los datasets completos de PannaData/Opta dentro del repositorio.

## 13. Siguiente paso exacto

**Auditar las columnas de los Parquet originales y elegir el equipo 2025/26 con mejor cobertura que cumpla el criterio de no disputar competición europea.**

Después:

```text
selección del equipo
→ mapping Opta → Collector
→ cierre de variables
→ checkpoint GitHub
→ esquema de datos
```
