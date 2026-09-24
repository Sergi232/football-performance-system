# PROJECT_STATE

Última actualización: 24/09/2026

Este archivo es la memoria técnica operativa del proyecto. Debe reflejar siempre el estado más reciente confirmado y prevalecer sobre conversaciones antiguas cuando exista una contradicción.

## 1. Fase actual

**Cierre del Data Collector y construcción del caso demostrador real.**

La auditoría de cobertura de LaLiga 2025/26 ya está completada. El siguiente trabajo es mapear las variables disponibles en PannaData/Opta a un conjunto reducido de variables realmente recogibles por un equipo amateur o semiprofesional.

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

## 6. Auditoría de cobertura LaLiga 2025/26

La auditoría de fixtures, player stats, alineaciones y eventos confirma:

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

Motivos de selección:

- 38 partidos con cobertura completa.
- Clasificado en la auditoría como equipo sin competición europea en 2025/26.
- Perfil estadístico intermedio y razonable para utilizarlo como sustituto de un equipo amateur/semi-profesional, evitando perfiles demasiado extremos.
- Volumen de pase claramente inferior a equipos dominantes pero no tan atípico como el extremo observado en Getafe.
- Perfil equilibrado entre pase, juego directo, centros, defensa y faltas.

Perfil de referencia detectado en la auditoría:

```text
Pases por partido: 404,3
Precisión de pase: 80,3 %
Balones largos por partido: 54,8
Centros por partido: 20,0
Entradas por partido: 18,2
Intercepciones por partido: 7,7
Faltas por partido: 14,9
Pérdidas/turnovers por partido: 16,2
Dispossessed por partido: 10,2
Goles: 41
Tarjetas amarillas: 86
Tarjetas rojas: 5
```

Estos valores sirven únicamente para justificar la elección del caso demostrador. No se aprueban automáticamente como métricas finales del producto.

## 8. Política de anonimización del dataset demostrador

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

## 9. Arquitectura analítica prevista

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

## 10. Sistema experto previsto

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

## 11. LLM / asistente IA

Arquitectura obligatoria:

```text
DATA → ANALYTICS → DECISION ENGINE → LLM → COACH
```

El LLM podrá interpretar preguntas, explicar resultados, resumir tendencias y generar informes, pero no podrá inventar métricas ni sustituir cálculos críticos del motor analítico.

## 12. Pendientes abiertos

- Mapear PannaData/Opta → variables potenciales del Data Collector.
- Revisar específicamente regate, defensa, pérdida, penalti, tarjetas, asistencias y acciones de portero.
- Determinar si registrar todos los pases normales es viable para el contexto amateur.
- Cerrar definitivamente las variables del Data Collector.
- Extraer la temporada 2025/26 de Deportivo Alavés con las variables aprobadas.
- Crear el proceso reproducible de anonimización.
- Definir el esquema de datos estándar del proyecto.
- Definir la capa de normalización GPS.

## 13. Decisiones descartadas o no aprobadas

- No usar directamente todas las variables profesionales disponibles solo porque existan en Opta.
- No construir todavía el árbol experto detallado.
- No construir todavía el Feature Engine definitivo.
- No usar datos ficticios como caso principal si puede reconstruirse una temporada real.
- No publicar los datasets completos de PannaData/Opta dentro del repositorio.
- No seleccionar Getafe como caso demostrador principal: su perfil de pase y disciplina es más extremo y menos representativo para el caso que se quiere simular.

## 14. Siguiente paso exacto

**Construir el mapping PannaData/Opta → Data Collector para Deportivo Alavés 2025/26 y cerrar las variables realmente recogibles en fútbol amateur/semi-profesional.**

Orden inmediato:

```text
1. auditar columnas relevantes de player_stats y events
2. mapear cada familia del Collector
3. marcar mantener / descartar / derivar
4. cerrar variables definitivas
5. actualizar GitHub
6. crear esquema de datos
```
