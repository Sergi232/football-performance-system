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
FEATURE-03 historial condicionado a rol  CERRADO / VALIDADO
EXPERT-01 N1000-N3000                    CERRADO / VALIDADO
EXPERT-02 N4000-N7000                    CERRADO / VALIDADO
EXPERT-03 N8000-N9000                    CERRADO / VALIDADO
EXPERT-04 N10000 rol/encaje              CERRADO / VALIDADO
EXPERT-05 N11000 consistencia/tendencia  CERRADO / VALIDADO
EXPERT-06 N12000 player-fit evidence     CERRADO / VALIDADO
EXPERT-07 N13000 recommendation gate     PREPARADO / PENDIENTE VALIDACIÓN LOCAL
Dashboard                                DESPUÉS DE EXPERT-07
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
- No crear scores de fit/recomendación antes de disponer de reglas validadas.

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

## 9. FEATURE ENGINE

### FEATURE-01 — CERRADO / VALIDADO
`features/catalog.json` v0.1.0. 28 features: 7 ratios + 21 por90.

```text
FEATURE-01 VALIDATION: PASS
feature rows 23380/23380
non-null 6324
coverage 38 matches / 36 players
```

Reglas: ratio solo con numerador/denominador válidos y denominador >0; por90 solo con minutos >0; NULL raw permanece NULL; sin ratings/pesos/percentiles/umbrales.

### FEATURE-02 — CERRADO / VALIDADO
`features/temporal_catalog.json` v0.2.0. Por cada feature: `history_n`, `prev`, `prior_mean`, `prior_std`, `delta_prev`, `delta_prior_mean`, `prior_slope`.

```text
FEATURE-02 VALIDATION: PASS
feature rows 163660/163660
coverage 38 / 36
history_n PASS
prior_std PASS
first-date strict-past PASS
```

Strict-past: solo fechas anteriores; partido actual y misma fecha no entran; futuros no entran; NULL no se vuelve 0; sin ventanas arbitrarias 3/5/10.

### FEATURE-03 — CERRADO / VALIDADO
`features/role_temporal_catalog.json` v0.3.0. Historial separado por jugador + rol observado + feature.

```text
FEATURE-03 VALIDATION: PASS
feature rows 117735/117735
non-null 43060
player_match con rol observado 590/835
roles observados distintos 23
role source identity PASS
missing-role NULL PASS
strict-past first-observation PASS
role history count + std domains PASS
```

Para cada feature: `role_history_n`, `role_prior_mean`, `role_prior_std`, `role_delta_prior_mean`, `role_prior_slope`; además `role_match_history_n`. No se infiere rol ni se crea score de fit.

## 10. Sistema experto

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

```text
48430/48430 decisiones
N1000=835
N2000=835
N3000=46760
duplicados=0
```

N3000 usa diferencia frente media strict-past y pendiente strict-past. `confidence=1.0` significa ejecución determinista, no probabilidad.

### EXPERT-02 — CERRADO / VALIDADO
Motor `expert_0.2.0`. N4000 amenaza ofensiva, N5000 creación/progresión, N6000 defensa, N7000 finalización.

```text
decision rows 68470/68470
N1000-N3000 exact carry-forward PASS
confidence contract PASS
no evaluative/recommendation labels PASS
```

Cada señal compara al jugador solo con su propio historial strict-past. Sin scores/pesos/percentiles.

### EXPERT-03 — CERRADO / VALIDADO
Motor `expert_0.3.0`.

```text
decision rows 72645/72645
N8000=3340
N9000=835
N1000-N7000 exact carry-forward PASS
N8000 own-team context PASS
N9000 optional GPS contract PASS
GPS observed player-match 0
```

N8000 usa contexto del propio equipo. N9000 devuelve `GPS_OBSERVED` o `GPS_NOT_AVAILABLE`; ausencia GPS no genera estimación física.

### EXPERT-04 — CERRADO / VALIDADO
Motor `expert_0.4.0`. N10000 usa el rol observado y FEATURE-03 same-role strict-past.

```text
EXPERT-04 VALIDATION: PASS
player_match 835
N10000 nodes/player-match 26
decision rows 94355/94355
N10000 rows 21710/21710
role-conditioned evidence rows 20040/20040
observed-role player_match 590/835
N1000-N9000 exact carry-forward PASS
observed role identity PASS
same-role evidence justification PASS
confidence contract PASS
```

N10000 contiene rol observado, número de partidos previos en el mismo rol y 24 señales N4000-N7000 condicionadas al mismo rol. `ABOVE/BELOW_ROLE_PRIOR_MEAN` es dirección descriptiva, no un score de fit. Sin mínimo de muestra, peso, percentil, ranking o recomendación.

### EXPERT-05 — CERRADO / VALIDADO
Motor `expert_0.5.0`. N11000 usa FEATURE-02 strict-past.

```text
EXPERT-05 VALIDATION: PASS
decision rows 141115/141115
N11000 rows 46760/46760
N1000-N10000 exact carry-forward PASS
strict-past prior_std/prior_slope identity PASS
```

N11000 expone por cada una de las 28 features la desviación estándar histórica exacta y la pendiente OLS strict-past. Menos de dos observaciones es `INSUFFICIENT_PRIOR_HISTORY` por requisito matemático, no por umbral de rendimiento. No se etiqueta consistencia alta/baja ni improving/declining.

### EXPERT-06 — CERRADO / VALIDADO
Motor `expert_0.6.0`. N12000 sintetiza la evidencia same-role de N10000 sin score.

```text
EXPERT-06 VALIDATION: PASS
player_match rows 835
N12000 nodes/player-match 13
decision rows 151970/151970
N12000 rows 10855/10855
N12000 outputs checked 10855
player-match con evidencia same-role evaluable 501
N1000-N11000 exact carry-forward PASS
N10000 evidence partition + coverage identity PASS
confidence contract PASS
```

N12000 expone rol, historial en rol, número de señales evaluables/no evaluables, ABOVE/BELOW/EQUAL, cobertura exacta y recuento evaluable por N4000/N5000/N6000/N7000. `ABOVE` no significa favorable ni `BELOW` desfavorable. Sin score de fit, pesos, percentiles, ranking, mínimo de muestra o recomendación.

### EXPERT-07 — PREPARADO / PENDIENTE VALIDACIÓN LOCAL
Motor `expert_0.7.0`. N13000 es un gate final seguro, no un generador de recomendaciones.

Archivos:

```text
decision_tree/recommendation_gate_catalog.json
decision_tree/build_stage7.py
decision_tree/validate_stage7.py
decision_tree/run_stage7.py
tests/test_decision_tree_stage7.py
```

N13000 añade 3 nodos por jugador-partido:

- `N13000.100`: gate de disponibilidad de evidencia (`ROLE_UNKNOWN`, `NO_EVALUABLE_ROLE_EVIDENCE`, `EVIDENCE_AVAILABLE`);
- `N13000.110`: estado de política, actualmente `RECOMMENDATION_POLICY_NOT_VALIDATED`;
- `N13000.120`: estado final de no emisión de recomendación.

Estados finales posibles:

```text
RECOMMENDATION_NOT_ISSUED_ROLE_UNKNOWN
RECOMMENDATION_NOT_ISSUED_NO_EVIDENCE
RECOMMENDATION_NOT_ISSUED_POLICY_UNVALIDATED
```

Esta decisión es intencional: todavía no existe una política final validada de pesos, muestra mínima o significancia práctica. El motor debe negarse a inventarla. N1000-N12000 se arrastra exactamente desde `expert_0.6.0`.

## 11. LLM

Arquitectura obligatoria: `DATA → ANALYTICS → DECISION ENGINE → LLM → COACH`.

El LLM explica/consulta resultados estructurados. No inventa métricas ni sustituye cálculos críticos.

## 12. Restricciones vigentes

- No usar variables Opta solo porque existan.
- No duplicar pérdidas derivadas.
- No inferir formación ni rol sin evidencia.
- No crear role stints ficticios.
- No forzar eventos atómicos desde agregados ambiguos.
- No inventar umbrales GPS.
- No usar fuzzy matching silencioso GPS.
- No convertir dirección matemática en juicio de rendimiento sin regla validada por métrica.
- No mezclar historiales de roles distintos para evaluar encaje de rol.
- No fijar mínimo de muestra de rol por intuición.
- No etiquetar consistencia alta/baja o tendencia improving/declining sin validación.
- No usar score global o recomendación táctica antes de validar reglas y pesos.
- N13000 debe devolver explícitamente que la recomendación no se emite mientras la política final siga sin validar.

## 13. Problemas abiertos

- validar localmente EXPERT-07;
- después cerrar el motor base y construir el primer dashboard funcional;
- estudiar/validar una política futura de recomendación con literatura, datos o experimentación antes de sustituir el gate conservador de N13000;
- añadir features físicas cuando haya GPS real o definiciones justificadas;
- script de anonimización para publicación;
- mejorar reejecución incremental;
- retocar UX Collector al final;
- localizar fuente fiable de `key_passes` si aparece otro export.

## 14. Siguiente paso exacto

```powershell
python decision_tree\run_stage7.py
```

Si pasa:
1. cerrar EXPERT-07;
2. declarar cerrado el motor experto base N1000-N13000;
3. construir el primer dashboard funcional;
4. después integrar asistente IA y exportación PDF.
