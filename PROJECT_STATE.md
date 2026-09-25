# PROJECT_STATE

Última actualización: 25/09/2026

Este archivo es la memoria técnica operativa del proyecto. Debe reflejar siempre el estado más reciente confirmado y prevalecer sobre conversaciones antiguas cuando exista una contradicción.

## 1. Fase actual

**Base de datos v0.1 en construcción + cierre del Data Collector en paralelo.**

Ya no se espera a cerrar el 100 % de la taxonomía del Collector para avanzar con la infraestructura. Se ha aprobado una arquitectura orientada a eventos que permite representar acciones pendientes (`CORNER`, falta peligrosa, ABP, etc.) sin rediseñar la base central.

El siguiente objetivo técnico es conectar los Parquet reales de PannaData/Opta con el esquema normalizado y construir el caso demostrador Deportivo Alavés 2025/26.

## 2. Objetivo confirmado

Desarrollar una aplicación web funcional para equipos de fútbol amateur o semiprofesional sin departamento de análisis propio.

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

## 3. Principios y decisiones aprobadas

- Team Mode es el modo principal.
- Player Mode será complementario.
- Rival Mode será una extensión futura.
- El sistema principal debe funcionar sin datos del rival.
- GPS complementario, no obligatorio.
- Separación estricta entre datos brutos, features, modelos y conclusiones.
- Ninguna conclusión importante dependerá exclusivamente de un LLM.
- Evitar data leakage.
- Toda regla, umbral o peso deberá justificarse con datos, literatura, validación o experimentación.
- Priorizar MVP funcional antes de aumentar complejidad.
- GitHub es la fuente de verdad técnica.
- Documentación oficial en castellano.
- Código puede usar nombres técnicos en inglés.
- Caso demostrador real reconstruido con PannaData/Opta y anonimizado antes de publicarse.

## 4. Arquitectura materializada

Documento creado:

```text
docs/ARCHITECTURE.md
```

Módulos del proyecto:

```text
collector/       captura y taxonomía de eventos
data/            esquema, imports y dataset normalizado
gps/             normalización multi-proveedor
features/        variables derivadas
engine/          análisis determinista
decision_tree/   sistema experto auditable
models/          ML opcional
app/             dashboard web
llm/             consulta y explicación
reports/         PDF
tests/           tests de datos/lógica/regresión
```

Regla de desbloqueo: una decisión pendiente de interfaz no debe bloquear infraestructura si el modelo de datos ya puede representarla de forma genérica.

## 5. Base de datos — v0.1 creada

Archivos:

```text
data/schema.sql
data/init_database.py
data/README.md
requirements.txt
```

Motor inicial: **DuckDB**.

Unidad analítica principal:

```text
player_match = jugador + partido
```

Tablas/capas definidas:

```text
teams
players
matches
team_match
player_match
player_role_stints
match_events
collector_sessions
gps_imports
gps_observations
player_match_features
decision_results
```

La tabla estable de eventos es `match_events`:

```text
action_type + subtype + outcome + contexto + qualifiers
```

La taxonomía se guarda como datos, no como columnas fijas. Esto permite añadir o cerrar eventos sin rehacer el esquema.

La base mantiene trazabilidad temporal, vídeo, fuente de origen y posibilidad de enlazar eventos.

Ya está implementada como lógica derivada aprobada la vista de pérdidas:

```text
PASS | ... | FAIL    → FAILED_PASS
DRIBBLE | FAIL       → FAILED_DRIBBLE
LOSS                 → OTHER_TURNOVER / subtipo
```

No debe existir doble conteo de pérdidas.

## 6. Auditoría automática de fuentes

Archivo creado:

```text
data/audit_pannadata_sources.py
```

Objetivo: inspeccionar los Parquet locales reales y generar:

```text
data/source_schema_audit.json
```

El script obtiene para cada fuente:

- existencia;
- número de filas;
- número de columnas;
- nombres reales de columnas;
- tipos de datos.

Esto evita construir el importador suponiendo nombres de campos que no se hayan comprobado.

Fuentes objetivo:

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

Ruta local confirmada:

```text
C:\Users\sergi\Desktop\analisi_futbol\input\pannadata\
```

## 7. Data Collector — estado actual

Catálogo versionado creado:

```text
collector/event_catalog.json
```

### Aprobado

Pases:

```text
PASS | NORMAL | SUCCESS/FAIL
PASS | LONG   | SUCCESS/FAIL
PASS | CROSS  | SUCCESS/FAIL
```

`LONG` y `CROSS` cuentan automáticamente como pases totales.

Regate:

```text
DRIBBLE | SUCCESS/FAIL
```

Remate:

```text
SHOT | GOAL
SHOT | ON_TARGET
SHOT | OFF_TARGET
SHOT | BLOCKED
```

Poste se agrupa en `OFF_TARGET` en el MVP.

Defensa:

```text
TACKLE
INTERCEPTION
BLOCK
CLEARANCE
```

Falta y disciplina:

```text
FOUL | COMMITTED
FOUL | RECEIVED
CARD | YELLOW
CARD | RED
```

Pérdida:

```text
LOSS | OTHER
```

solo cuando no está ya explicada por pase/regate fallado.

### Parcial

Penalti:

```text
PENALTY → WON / CONCEDED → GOAL / MISSED
```

La lógica general está aprobada; falta validar el mapping técnico completo.

### Pendiente

- criterio operativo de falta peligrosa;
- confirmar `CORNER | FOR/AGAINST` en el MVP;
- resultado de ABP (`SHOT`, `CHANCE`, `GOAL`, etc.) solo si es reproducible y recogible;
- interfaz exacta de portero;
- reconstrucción exacta de remate a portería/penaltis desde eventos y qualifiers.

Estas decisiones ya no bloquean la base de datos.

## 8. Datos de desarrollo

Base local existente:

```text
C:\Users\sergi\Desktop\analisi_futbol\outputs\base_pannadata.duckdb
```

Las tablas derivadas de proyectos anteriores no deben utilizarse automáticamente como fuente original del TFM.

Auditoría LaLiga 2025/26 confirmada:

```text
20 equipos
380 partidos
38 partidos por equipo
100 % fixtures
100 % player stats
100 % lineups
100 % events
```

## 9. Caso demostrador aprobado

**Fuente local: Deportivo Alavés — LaLiga 2025/26.**

Opta team id:

```text
4dtdjgnpdq9uw4sdutti0vaar
```

Motivos:

- temporada completa;
- sin competición europea;
- perfil menos extremo y más adecuado como demostrador que alternativas analizadas;
- equilibrio razonable entre pase, juego directo, centros, defensa y faltas.

Los valores profesionales sirven para validar el sistema, no para aprobar automáticamente métricas finales.

## 10. Mapping PannaData/Opta conocido

Variables disponibles relevantes:

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

Type IDs de eventos conocidos:

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

## 11. Anonimización

Antes de publicar el dataset demostrador:

```text
Deportivo Alavés → TEAM_001
jugadores         → PLAYER_001, PLAYER_002, ...
oponentes         → OPP_001, OPP_002, ...
IDs originales    → IDs internos
```

Se mantendrán estadísticas, minutos, roles y estructura temporal.

Script previsto:

```text
scripts/build_anonymized_demo.py
```

Nunca se publicarán los datasets completos originales de PannaData/Opta.

## 12. Sistema experto previsto

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

Cada nodo:

```text
entrada → condición → resultado → confianza → justificación
```

No se detallan ramas todavía.

## 13. LLM

Arquitectura obligatoria:

```text
DATA → ANALYTICS → DECISION ENGINE → LLM → COACH
```

El LLM explica resultados ya calculados; no inventa métricas ni sustituye cálculos críticos.

## 14. Decisiones descartadas

- No usar todas las variables Opta solo porque existan.
- No construir todavía el árbol experto detallado.
- No construir el Feature Engine definitivo antes de cerrar/madurar la capa de datos.
- No usar datos ficticios como caso principal pudiendo reconstruir una temporada real.
- No publicar datasets completos de PannaData/Opta.
- No usar Getafe como demostrador principal.
- No duplicar pérdidas derivadas de pase/regate fallado.
- No crear botón separado para remate al poste en el MVP.

## 15. Siguiente paso exacto

### Track A — Datos, prioritario

```text
1. ejecutar data/audit_pannadata_sources.py sobre los Parquet locales
2. guardar/revisar source_schema_audit.json
3. construir import_pannadata_demo.py contra columnas reales
4. cargar Alavés 2025/26 en el esquema v0.1
5. validar 38 partidos, jugadores, minutos, roles y eventos
6. reconstruir shots/penaltis
7. generar dataset demostrador anonimizado
```

### Track B — Collector, en paralelo

```text
1. cerrar falta peligrosa
2. cerrar córners/ABP
3. cerrar penalti/portero
4. actualizar event_catalog.json
5. simplificar el HTML usando el catálogo versionado
```

### Después

```text
Feature Engine → sistema experto → dashboard → LLM → PDF
```
