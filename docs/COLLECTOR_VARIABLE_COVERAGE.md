# Cobertura de variables del Collector

Esta matriz documenta la trazabilidad de `event_catalog v0.3.0` y del contrato
JSON V1.1. Una marca significa que la superficie consulta el dato normalizado o
su agregado directo; `—` indica que no lo presenta. No se han creado métricas
nuevas para esta matriz.

| Variable | Collector | JSON | DuckDB | Team | Player | Match | Coach | PDF | Expert | Estado |
|---|---|---|---|---|---|---|---|---|---|---|
| Partido, equipo, rival, fecha, formación | Sí | `meta` | `matches` / `team_match` | ✓ | ✓ | ✓ | ✓ | ✓ | — | USADA |
| Jugador, dorsal, titularidad y minutos | Sí | `players` | `players` / `player_match` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | USADA |
| Rol inicial, lado y cambios de rol | Sí | `role`, `side`, `roleChanges` | `player_match` / `player_role_stints` | — | ✓ | ✓ | ✓ | — | ✓ | USADA |
| Pase normal, completado/fallado | Sí | `PASS/NORMAL` | `match_events` / raw stats | — | ✓ | ✓ | ✓ | ✓ | ✓ | USADA |
| Pase largo, completado/fallado | Sí | `PASS/LONG` | `match_events` / raw stats | — | ✓ | ✓ | ✓ | — | ✓ | USADA |
| Centro, completado/fallado | Sí | `PASS/CROSS` | `match_events` / raw stats | — | ✓ | ✓ | ✓ | — | ✓ | USADA |
| Pase clave | Sí | qualifier `key_pass` | `match_events.qualifiers` | — | ✓ | ✓ (raw) | ✓ | — | — | USADA |
| Asistencia | Sí | qualifier `assist` | `match_events` / raw stats | — | ✓ | ✓ | ✓ | ✓ | ✓ | USADA |
| Regate, ganado/perdido | Sí | `DRIBBLE` | `match_events` / raw stats | — | ✓ | ✓ | ✓ | — | ✓ | USADA |
| Pérdida adicional | Sí | `LOSS/OTHER` | `match_events` / raw stats | — | ✓ | ✓ | ✓ | ✓ | ✓ | USADA |
| Remate: gol, a puerta, fuera, bloqueado | Sí | `SHOT` | `match_events` / raw stats | ✓ (GF) | ✓ | ✓ | ✓ | ✓ | ✓ | USADA |
| Entrada, ganada/no ganada | Sí | `TACKLE` | `match_events` / raw stats | — | ✓ | ✓ | ✓ | ✓ | ✓ | USADA |
| Intercepción | Sí | `INTERCEPTION` | `match_events` / raw stats | — | ✓ | ✓ | ✓ | ✓ | ✓ | USADA |
| Bloqueo | Sí | `BLOCK` | `match_events` / raw stats | — | ✓ | ✓ | ✓ | — | ✓ | USADA |
| Despeje | Sí | `CLEARANCE` | `match_events` / raw stats | — | ✓ | ✓ | ✓ | — | ✓ | USADA |
| Falta cometida/recibida | Sí | `FOUL` | `match_events` / raw stats | ✓ | ✓ | ✓ | ✓ | — | ✓ | USADA |
| Coordenadas de falta | Sí | `x`, `y` | `match_events` | — | — | ✓ (raw) | — | — | — | USADA |
| Amarilla, roja y segunda amarilla | Sí | `CARD` + qualifier | `match_events` / raw stats | ✓ | ✓ | ✓ | ✓ | — | ✓ | USADA |
| Penalti a favor/en contra y resultado | Sí | `PENALTY` | `match_events` / raw stats | ✓ | ✓ | ✓ (raw) | ✓ | — | ✓ | USADA |
| Lanzador de penalti vinculado | Sí | qualifier `penalty_taker_player_id` | `match_events.qualifiers` | — | — | ✓ (raw) | — | — | — | USADA |
| Córner a favor/en contra | Sí | `CORNER` | `match_events` | ✓ | — | ✓ | ✓ | — | ✓ | USADA |
| Resultado de ABP/córner/falta | Sí | qualifier `set_piece_result` | `match_events.qualifiers` | — | — | ✓ (raw) | — | — | — | USADA |
| Parada y gol encajado | Sí | `GK/SAVE`, `GK/GOAL_CONCEDED` | `match_events` / raw stats | ✓ (GC) | ✓ | ✓ | ✓ | — | ✓ | USADA |

## Regla de interpretación

El registro **raw del Collector** de Modo Partido es la superficie de auditoría
para los campos que conservan semántica de evento o qualifier (resultado de ABP,
coordenadas, lanzador vinculado y segunda amarilla). Las tablas de Player y
Match muestran los contadores directos; Team muestra los agregados de equipo
derivados de esos mismos eventos. Cuando un valor no fue registrado por la
fuente, la interfaz muestra `N/D` en lugar de inventar un dato.
