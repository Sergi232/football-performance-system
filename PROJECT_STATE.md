# PROJECT_STATE

Última actualización: 25/09/2026

Este archivo es la memoria técnica operativa del proyecto. Si contradice un chat antiguo, prevalece este estado documentado.

## 1. Estado actual

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
EXPERT-07 N13000 recommendation gate     CERRADO / VALIDADO
MOTOR EXPERTO BASE N1000-N13000          CERRADO / VALIDADO
LLM-01 contexto + asistente seguro       CERRADO / VALIDADO
LLM-02 proveedor OpenAI opcional         CERRADO / VALIDADO
REPORTS-01 motor PDF común               CERRADO / VALIDADO
DASHBOARD-01 Streamlit MVP               INTEGRACIÓN FINAL / REVISIÓN VISUAL
PUBLICACIÓN / ANONIMIZACIÓN              SIGUIENTE MACROBLOQUE
```

El Collector puede recibir mejoras UX posteriormente, pero su contrato ya no bloquea el producto.

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

TEAM MODE es principal. PLAYER MODE es complementario. RIVAL MODE queda como extensión futura y el sistema principal no depende de datos del rival.

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
- No crear scores de fit/recomendación antes de disponer de política validada.
- Ninguna API key o secreto se sube al repositorio.
- No repetir `pip install -r requirements.txt` en cada fase: solo instalar cuando aparezca una dependencia nueva o al preparar un entorno limpio.

## 4. Arquitectura materializada

```text
collector/       captura manual/vídeo
data/            esquema, imports y datos normalizados
gps/             normalización multi-proveedor
features/        variables deterministas, temporales y condicionadas a rol
decision_tree/   sistema experto auditable
app/             dashboard web Streamlit
llm/             contexto, guardrails y proveedor generativo opcional
reports/         motor común de informes PDF
models/          ML opcional posterior
tests/           regresión y validación
```

DuckDB. Unidad principal: `player_match = jugador + partido`.

Tablas clave: `teams`, `players`, `matches`, `team_match`, `player_match`, `player_role_stints`, `match_events`, `player_match_raw_stats`, `collector_sessions`, `gps_imports`, `gps_player_map`, `gps_observations`, `player_match_features`, `decision_results`.

Versiones de esquema: 0.1.0 core; 0.2.0 player_match_raw_stats; 0.3.0 expansión raw; 0.4.0 GPS normalization.

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

### DATA-01 / DATA-02
- 38 fixtures.
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
835/835 filas, 38/38 partidos, 36 jugadores. Validación PASS. 27 raw stats aprobadas: pases total/completados, asistencias, largos, centros, regates, turnovers, dispossessed, remates, bloqueados, goles, tackles total/ganados, intercepciones, blocked passes, despejes, faltas cometidas/recibidas, tarjetas, penaltis concedidos/ganados, paradas y goles encajados.

`key_passes` no tiene columna verificada. No se aproxima. Los NULL se preservan.

Fechas: `opta_fixtures.match_date` usa `YYYY-MM-DDZ`; 38/38 fechas reparadas desde fuente real, sin inferir cronología por ID u orden.

## 7. COLLECTOR-01 — CERRADO FUNCIONALMENTE

Catálogo `collector/event_catalog.json` v0.3.0. Acciones: PASS NORMAL/LONG/CROSS SUCCESS/FAIL; DRIBBLE; SHOT GOAL/ON_TARGET/OFF_TARGET/BLOCKED; TACKLE; INTERCEPTION; BLOCK; CLEARANCE; FOUL; CARD; LOSS OTHER; PENALTY WON/CONCEDED GOAL/MISSED; CORNER FOR/AGAINST; GK SAVE/GOAL_CONCEDED.

Qualifiers: `key_pass`, `assist`, `second_yellow`, `set_piece_result`, `penalty_taker_player_id`.

Decisiones: LONG/CROSS cuentan como pase; PASS FAIL y DRIBBLE FAIL generan pérdida derivada; LOSS solo otras pérdidas; falta peligrosa se deriva desde x/y; clips ABP conservan tiempo partido/vídeo.

`collector/data_collector_futbol_mvp.html`. Validación local PASS 20/20.

## 8. GPS-01 — CERRADO / VALIDADO

Contrato multi-proveedor normalizado. Unidades canónicas: ms, m, m/s, m/s² y x/y cuando el mapping espacial es seguro. Mapping declarativo, conversiones, acumulada→incremental, `gps_player_map`, metadatos y QC. Sin fuzzy matching silencioso ni umbrales sprint/HIE/carga inventados.

## 9. FEATURE ENGINE — CERRADO / VALIDADO

### FEATURE-01 — `0.1.0`
28 features: 7 ratios + 21 por90. 23.380 filas; 6.324 no nulas; 38 partidos / 36 jugadores. Sin ratings, pesos, percentiles ni umbrales.

### FEATURE-02 — `0.2.0`
Por feature: `history_n`, `prev`, `prior_mean`, `prior_std`, `delta_prev`, `delta_prior_mean`, `prior_slope`. 163.660 filas. Strict-past: solo fechas anteriores; partido actual, misma fecha y futuros excluidos. Sin ventanas arbitrarias 3/5/10.

### FEATURE-03 — `0.3.0`
Historial por jugador + rol observado + feature. 117.735 filas; 43.060 no nulas; 590/835 player-match con rol observado; 23 roles. No se infiere rol ni se crea score de fit.

## 10. SISTEMA EXPERTO — MOTOR BASE CERRADO

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
N12000 player fit evidence
N13000 recommendation gate
```

Cada nodo: `entrada → condición → resultado → confianza → justificación`.

Validaciones cerradas:
- EXPERT-01 `expert_0.1.0`: 48.430 decisiones.
- EXPERT-02 `expert_0.2.0`: 68.470 decisiones.
- EXPERT-03 `expert_0.3.0`: 72.645 decisiones; GPS observado demo = 0 y ausencia explícita.
- EXPERT-04 `expert_0.4.0`: 94.355 decisiones; same-role strict-past; sin fit score.
- EXPERT-05 `expert_0.5.0`: 141.115 decisiones; `prior_std` + `prior_slope`, sin etiquetas evaluativas.
- EXPERT-06 `expert_0.6.0`: 151.970 decisiones; 10.855 N12000; 501 player-match con evidencia same-role evaluable.
- EXPERT-07 `expert_0.7.0`: 154.475 decisiones; 2.505 N13000; carry-forward exacto PASS.

N13000 mantiene tres estados seguros:

```text
RECOMMENDATION_NOT_ISSUED_ROLE_UNKNOWN
RECOMMENDATION_NOT_ISSUED_NO_EVIDENCE
RECOMMENDATION_NOT_ISSUED_POLICY_UNVALIDATED
```

No existe todavía una política final de recomendación validada.

## 11. DASHBOARD-01 — INTEGRACIÓN FINAL / REVISIÓN VISUAL

Archivos: `app/data_access.py`, `app/validate_dashboard.py`, `app/streamlit_app.py`.

```text
DASHBOARD-01 DATA CONTRACT: PASS
team: Deportivo Alavés
matches: 38
players: 36
FEATURE-01 metrics available: 28
final engine: expert_0.7.0
decision rows: 154475
N13000 rows: 2505
Final recommendation gate safety: PASS
```

Streamlit ha arrancado correctamente en `localhost:8501`. Modos disponibles: TEAM / PLAYER / PARTITS / ASSISTENT.

Integración final ya preparada:
- TEAM: botón de descarga PDF del equipo;
- PLAYER: botón de descarga PDF del jugador seleccionado;
- PARTITS: botón de descarga PDF del partido seleccionado;
- ASSISTENT: LLM opcional + fallback determinista + guardrails.

Pendiente: una revisión visual rápida de estas cuatro vistas después del último `git pull`. Si no hay error visual/funcional, DASHBOARD-01 queda cerrado.

## 12. LLM — CERRADO EN MVP

Arquitectura obligatoria: `DATA → ANALYTICS → DECISION ENGINE → LLM → COACH`.

### LLM-01 — CERRADO / VALIDADO

Contextos read-only TEAM / PLAYER / MATCH y asistente determinista con guardrails.

```text
LLM-01 ASSISTANT CONTRACT: PASS
team context matches: 38
team context squad: 36
match lineup rows: 23
unsupported ranking/recommendation question guardrail: PASS
N12000/N13000 provenance explanation: PASS
```

### LLM-02 — CERRADO / VALIDADO

Proveedor OpenAI opcional implementado en `llm/openai_provider.py`; routing y fallback en `llm/assistant_service.py`; validación en `llm/validate_stage2.py`.

```text
LLM-02 PROVIDER ROUTING CONTRACT: PASS
configured model: gpt-5.6-luna
OpenAI API key configured: NO
blocked ranking/recommendation intercepted before external provider: PASS
deterministic fallback: PASS
N12000/N13000 provenance preserved: PASS
No external API call was made by validation.
```

El modo generativo real es opcional. Sin `OPENAI_API_KEY`, el producto funciona con fallback determinista.

## 13. REPORTS-01 — CERRADO / VALIDADO

Motor único TEAM / PLAYER / MATCH con una sola base de código.

Archivos:

```text
reports/__init__.py
reports/data_builder.py
reports/pdf_engine.py
reports/validate_reports.py
tests/test_reports_engine.py
```

Validación local 25/09/2026:

```text
REPORTS-01 PDF CONTRACT: PASS
team: Deportivo Alavés
player: Antonio Sivera
match opponent: Rayo Vallecano de Madrid
team payload matches: 38
team payload squad: 36
match lineup rows: 23
recommendation/report guardrails: PASS
team PDF: 10638 bytes
player PDF: 6291 bytes
match PDF: 5562 bytes
```

Contrato:
- payloads read-only desde `app.data_access`;
- PDF común con ReportLab;
- Team report: resumen, partidos y plantilla;
- Player report: resumen, evidencia N12000/N13000, features observadas e historial reciente;
- Match report: contexto del partido y estadísticas player-match observadas;
- no crea métricas críticas nuevas;
- no crea scores, rankings ni recomendaciones;
- los tres informes ya están integrados como descargas dentro de Streamlit.

## 14. Decisiones descartadas / restricciones vigentes

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
- No etiquetar consistencia alta/baja o improving/declining sin validación.
- No interpretar conteos N12000 como score de fit.
- No emitir recomendación N13000 mientras la política final siga sin validar.
- El LLM no puede recalcular métricas críticas ni sobreescribir el motor analítico.
- La capa reports tampoco puede recalcular métricas críticas ni crear conclusiones nuevas.
- Ninguna API key o secreto se sube al repositorio.

## 15. Problemas abiertos

- confirmar visualmente TEAM / PLAYER / PARTITS / ASSISTENT con la integración final y cerrar DASHBOARD-01;
- construir script de anonimización y dataset demo publicable;
- README final, instalación limpia, tests globales y capturas para GitHub;
- estudiar política futura de recomendación con literatura/datos/experimentos;
- añadir features físicas cuando haya GPS real o definiciones justificadas;
- mejorar reejecución incremental;
- retocar UX Collector al final;
- localizar fuente fiable de `key_passes` si aparece otro export.

## 16. Siguiente paso exacto

No hay ninguna dependencia nueva que instalar. Ejecutar:

```powershell
git pull
python app\validate_dashboard.py
streamlit run app\streamlit_app.py
```

Revisar TEAM / PLAYER / PARTITS / ASSISTENT y probar un botón PDF en cada una de las tres vistas con informe. Si todo abre sin error, cerrar DASHBOARD-01 y pasar directamente al macrobloc de publicación/anonimización.
