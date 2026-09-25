# PROJECT_STATE

Última actualización: 25/09/2026

Este archivo es la memoria técnica operativa del proyecto. Si contradice un chat antiguo, prevalece este estado documentado.

## 1. Fase actual

```text
Arquitectura base                         HECHO
DATA-01 fixtures + player_match          CERRADO / VALIDADO
DATA-02 lineups + titularidad/rol        CERRADO / VALIDADO
DATA-03 shots + cards                    CERRADO / VALIDADO
DATA-04 player-match raw stats           CERRADO / VALIDADO
COLLECTOR-01 MVP                         CERRADO FUNCIONALMENTE
GPS-01 contrato multi-proveedor          CERRADO / VALIDADO
FEATURE-01 base determinista             CERRADO / VALIDADO
FEATURE-02 evolución temporal            CERRADO / VALIDADO
EXPERT-01 N1000-N3000                    CERRADO / VALIDADO
EXPERT-02 N4000-N7000                    CERRADO / VALIDADO
EXPERT-03 N8000-N9000                    CERRADO / VALIDADO
FEATURE-03 historial condicionado a rol  PREPARADO / PENDIENTE VALIDACIÓN LOCAL
N10000 rol / encaje                      DESPUÉS DE FEATURE-03
Dashboard                                DESPUÉS DEL MOTOR BASE
LLM / PDF                                DESPUÉS DEL DASHBOARD BASE
```

El Collector puede recibir mejoras visuales/UX posteriormente, pero su contrato de datos ya no bloquea el desarrollo.

## 2. Producto

Aplicación web para equipos amateur o semiprofesionales sin departamento de análisis:

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

TEAM MODE es principal. PLAYER MODE es complementario. RIVAL MODE queda como extensión futura; el sistema principal no depende de datos del rival.

## 3. Principios aprobados

- GPS opcional y complementario.
- Separación estricta raw → features → motor → conclusiones.
- Ninguna conclusión importante depende exclusivamente de un LLM.
- Evitar data leakage.
- Toda regla, umbral o peso requiere datos, literatura, validación o experimento.
- No rellenar datos ausentes mediante supuestos silenciosos.
- PannaData/Opta sirve para desarrollar/validar; no define el producto amateur.
- GitHub es la fuente de verdad técnica.
- Priorizar MVP funcional antes de aumentar complejidad.

## 4. Arquitectura materializada

```text
collector/       captura manual/vídeo
data/            esquema, imports y datos normalizados
gps/             normalización multi-proveedor
features/        variables deterministas, temporales y condicionadas a rol
engine/          análisis determinista
decision_tree/   sistema experto auditable
models/          ML opcional
app/             dashboard web
llm/             consulta y explicación
reports/         PDF
tests/           regresión y validación
```

DuckDB. Unidad principal: `player_match = jugador + partido`.

Tablas clave: `teams`, `players`, `matches`, `team_match`, `player_match`, `player_role_stints`, `match_events`, `player_match_raw_stats`, `collector_sessions`, `gps_imports`, `gps_player_map`, `gps_observations`, `player_match_features`, `decision_results`.

Versiones de esquema:

```text
0.1.0 core
0.2.0 player_match_raw_stats
0.3.0 tackles_won + goals_conceded
0.4.0 GPS normalization
```

## 5. Caso demostrador

```text
Deportivo Alavés — LaLiga 2025/26
team id: 4dtdjgnpdq9uw4sdutti0vaar
38 partidos
36 jugadores
835 player_match
```

Antes de publicar se anonimizará como TEAM_001 / PLAYER_001 / OPP_001. No se publicarán datasets completos originales de PannaData/Opta.

## 6. DATA — CERRADO

### DATA-01
- 38 fixtures.
- validación PASS.

### DATA-02
- 835 `player_match`.
- 418 titulares = 38×11.
- 245 suplentes con 0 minutos.
- 36 jugadores.
- no se infiere formación.
- no se crean role stints ficticios.

### DATA-03
`opta_events.parquet` no es feed atómico completo. No se inventan pases, regates, tackles, intercepciones o faltas.

```text
shot_events fuente 464
autogol excluido 1
SHOT importados 463
cobertura 38/38
CARD 98
CARD sin player_id 2
```

`shots_blocked` queda `AGGREGATE_CANONICAL`.

### DATA-04
835/835 filas, 38/38 partidos, 36 jugadores. Validación PASS.

27 raw stats aprobadas: pases total/completados, asistencias, largos, centros, regates, turnovers, dispossessed, remates, bloqueados, goles, tackles total/ganados, intercepciones, blocked passes, despejes, faltas cometidas/recibidas, tarjetas, penaltis concedidos/ganados, paradas y goles encajados.

`key_passes` no tiene columna verificada en este export. No se aproxima. Los NULL se preservan.

### Fechas
`opta_fixtures.match_date` usa `YYYY-MM-DDZ`. Los 38 `matches.match_date` fueron reparados desde fuente real; no se infirió cronología por ID u orden.

## 7. COLLECTOR-01 — CERRADO FUNCIONALMENTE

Catálogo `collector/event_catalog.json` v0.3.0.

Acciones: PASS NORMAL/LONG/CROSS SUCCESS/FAIL; DRIBBLE; SHOT GOAL/ON_TARGET/OFF_TARGET/BLOCKED; TACKLE; INTERCEPTION; BLOCK; CLEARANCE; FOUL; CARD; LOSS OTHER; PENALTY WON/CONCEDED GOAL/MISSED; CORNER FOR/AGAINST; GK SAVE/GOAL_CONCEDED.

Qualifiers: `key_pass`, `assist`, `second_yellow`, `set_piece_result`, `penalty_taker_player_id`.

Decisiones: LONG/CROSS cuentan como pase; PASS FAIL y DRIBBLE FAIL generan pérdida derivada; LOSS solo otras pérdidas; falta peligrosa se derivará desde x/y; clips ABP conservan tiempo partido/vídeo.

`collector/data_collector_futbol_mvp.html`. Validación local PASS 20/20. Retocs UX no bloqueantes.

## 8. GPS-01 — CERRADO / VALIDADO

Contrato multi-proveedor normalizado. Unidades canónicas: ms, m, m/s, m/s² y x/y cuando el mapping espacial es seguro. Mapping declarativo, conversiones, acumulada→incremental, `gps_player_map`, metadatos y QC. Sin fuzzy matching silencioso ni umbrales sprint/HIE/carga inventados.

`GPS-01 VALIDATION: PASS`.

## 9. FEATURE-01 — CERRADO / VALIDADO

`features/catalog.json` v0.1.0. 28 features: 7 ratios + 21 por90.

Reglas: ratio solo con numerador/denominador válidos y denominador >0; por90 solo con minutos >0; NULL raw permanece NULL; sin ratings/pesos/percentiles/umbrales.

```text
FEATURE-01 VALIDATION: PASS
feature rows 23380/23380
non-null 6324
coverage 38 matches / 36 players
```

## 10. FEATURE-02 — CERRADO / VALIDADO

`features/temporal_catalog.json` v0.2.0. Por cada feature: `history_n`, `prev`, `prior_mean`, `prior_std`, `delta_prev`, `delta_prior_mean`, `prior_slope`.

Strict-past: solo fechas anteriores; partido actual y misma fecha no entran; futuros no entran; NULL no se vuelve 0; sin ventanas arbitrarias 3/5/10.

```text
FEATURE-02 VALIDATION: PASS
feature rows 163660/163660
coverage 38 / 36
history_n PASS
prior_std PASS
first-date strict-past PASS
```

## 11. Sistema experto

Arquitectura:

```text
N1000  disponibilidad / actividad
N2000  perfil estructural
N3000  forma / evolución
N4000  amenaza ofensiva
N5000  creación / progresión
N6000  contribución defensiva
N7000  finalización
N8000  contexto del equipo
N9000  componente físico opcional
N10000 rol y encaje táctico
N11000 consistencia / tendencia
N12000 player fit
N13000 recomendación final
```

Cada nodo: `entrada → condición → resultado → confianza → justificación`.

### EXPERT-01 — CERRADO / VALIDADO
Motor `expert_0.1.0`.

N1000 actividad observada; N2000 rol observado; N3000 diferencia frente media strict-past + pendiente strict-past. `confidence=1.0` = regla determinista, no probabilidad.

```text
EXPERT-01 VALIDATION: PASS
48430/48430 decisiones
N1000=835
N2000=835
N3000=46760
duplicados=0
```

### EXPERT-02 — CERRADO / VALIDADO
Motor `expert_0.2.0`.

N4000 amenaza ofensiva, N5000 creación/progresión, N6000 defensa, N7000 finalización. Cada señal compara al jugador solo con su propio historial strict-past. `metric_role` es metadata, no peso.

```text
EXPERT-02 VALIDATION: PASS
player_match 835
domain nodes/player-match 24
decision rows 68470/68470
N1000-N3000 exact carry-forward PASS
confidence contract PASS
no evaluative/recommendation labels PASS
```

### EXPERT-03 — CERRADO / VALIDADO
Motor `expert_0.3.0`.

N8000 usa solo contexto del propio equipo:
- N8000.100 HOME/AWAY/UNKNOWN;
- N8000.110 WIN/DRAW/LOSS/UNKNOWN;
- N8000.120 signo del goal difference;
- N8000.130 formación observada o `FORMATION_UNKNOWN`, nunca inferida.

N9000 es degradable:
- `GPS_OBSERVED` si existen `gps_observations` para jugador-partido;
- `GPS_NOT_AVAILABLE` si no existen;
- no estima datos físicos cuando falta GPS.

Validación local 25/09/2026:

```text
EXPERT-03 VALIDATION: PASS
engine_version expert_0.3.0
parent expert_0.2.0
player_match 835
decision rows 72645/72645
N8000=3340
N9000=835
N1000-N7000 exact carry-forward PASS
N8000 own-team context PASS
N9000 optional GPS contract PASS
GPS observed player-match 0
```

No se creó estimación física, umbral sprint/HIE/load, score, peso, percentil ni recomendación.

## 12. FEATURE-03 — PREPARADO / PENDIENTE VALIDACIÓN LOCAL

Motivo: N10000 no debe medir el encaje de un jugador en un rol usando un historial que mezcle otros roles. Antes del nodo experto se crea una capa estrictamente derivada y auditable.

Archivos:

```text
features/role_temporal_catalog.json
features/build_role_temporal_features.py
features/validate_stage3.py
features/run_stage3.py
tests/test_role_temporal_features.py
```

Contrato `feature_version=0.3.0`:
- rol tomado exactamente de `player_match.primary_role`;
- ningún rol se infiere;
- solo partidos con `match_date` estrictamente anterior;
- partidos de la misma fecha no se informan entre sí;
- historial separado por jugador + rol observado + feature;
- rol ausente permanece NULL;
- `role_match_history_n` cuenta partidos previos en el mismo rol con `minutes_played > 0`.

Para cada una de las 28 features base:

```text
role_history_n
role_prior_mean
role_prior_std
role_delta_prior_mean
role_prior_slope
```

Además:

```text
role_match_history_n
```

Esta fase no introduce mínimo de muestra, score, peso, percentil ni juicio de fit. La muestra observada se expone como dato para que N10000 pueda justificar después su confianza sin inventar un corte.

## 13. LLM

Arquitectura obligatoria: `DATA → ANALYTICS → DECISION ENGINE → LLM → COACH`.

El LLM explica/consulta resultados estructurados. No inventa métricas ni sustituye cálculos críticos.

## 14. Restricciones vigentes

- No usar variables Opta solo porque existan.
- No duplicar pérdidas derivadas.
- No inferir formación ni rol sin evidencia.
- No crear role stints ficticios.
- No forzar eventos atómicos desde agregados ambiguos.
- No inventar umbrales GPS.
- No usar fuzzy matching silencioso GPS.
- No convertir dirección matemática en juicio de rendimiento sin regla validada por métrica.
- No usar score global/recomendación final antes de validar reglas y pesos.
- No mezclar historiales de roles distintos para evaluar encaje de rol.

## 15. Problemas abiertos

- validar localmente FEATURE-03;
- después construir N10000 rol/encaje sobre evidencia condicionada al rol;
- definir muestra mínima/significancia práctica mediante validación, no intuición;
- añadir features físicas cuando haya GPS real o definiciones justificadas;
- script de anonimización para publicación;
- mejorar reejecución incremental;
- retocar UX Collector al final;
- localizar fuente fiable de `key_passes` si aparece otro export.

## 16. Siguiente paso exacto

```powershell
python features\run_stage3.py
```

Si pasa:
1. cerrar FEATURE-03;
2. construir N10000 como capa auditable de evidencia de rol, sin score arbitrario;
3. después N11000 consistencia/tendencia;
4. N12000 player fit requerirá reglas comparativas validadas;
5. N13000 recomendación final solo tras validar reglas/pesos.
