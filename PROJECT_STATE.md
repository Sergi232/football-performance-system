# PROJECT_STATE

Última actualización: 25/09/2026

Memoria técnica operativa del proyecto. Si contradice un chat antiguo, prevalece este archivo.

## 1. Estado actual

```text
DATA-01/02/03/04                    CERRADO / VALIDADO
COLLECTOR-01 MVP                    CERRADO FUNCIONALMENTE
GPS-01                              CERRADO / VALIDADO
FEATURE-01/02/03                    CERRADO / VALIDADO
EXPERT-01..07 N1000-N13000          CERRADO / VALIDADO
LLM-01/02                           CERRADO / VALIDADO
REPORTS-01 Team/Player/Match PDF    CERRADO / VALIDADO
DASHBOARD-01 Streamlit MVP          CONTRACT PASS / REVISIÓN VISUAL ABIERTA
PUBLICATION-01 demo anonimizada     PREPARADO / PENDIENTE VALIDACIÓN LOCAL
```

## 2. Producto

Aplicación web para equipos amateur o semiprofesionales sin departamento de análisis:

```text
VÍDEO / DATA COLLECTOR + GPS OPCIONAL
→ DUCKDB
→ FEATURE ENGINE
→ MOTOR ANALÍTICO
→ SISTEMA EXPERTO / ML
→ STREAMLIT
→ ASISTENTE IA
→ PDF
```

TEAM MODE es principal. PLAYER MODE es complementario. RIVAL MODE queda como extensión futura.

## 3. Principios aprobados

- GPS opcional.
- Separación estricta raw → features → motor → conclusiones.
- Evitar data leakage.
- Ninguna conclusión importante depende exclusivamente de un LLM.
- Reglas, umbrales y pesos requieren datos, literatura, validación o experimento.
- No inferir datos ausentes silenciosamente.
- PannaData/Opta sirve para desarrollo y validación, no define el producto amateur.
- No crear score de fit ni recomendación sin política validada.
- El LLM explica resultados estructurados; no recalcula métricas críticas.
- La capa PDF tampoco crea métricas, rankings o recomendaciones nuevas.
- No repetir instalaciones salvo cambio de dependencias o entorno limpio.
- Anonimizar datos no equivale a tener derecho a redistribuirlos.

## 4. Caso de desarrollo

Deportivo Alavés 2025/26: 38 partidos, 36 jugadores, 835 player_match.

Los datos profesionales se usan localmente para desarrollar/validar. No se publicarán raw files originales.

## 5. Variables y datos aprobados

Collector v0.3.0: PASS NORMAL/LONG/CROSS SUCCESS/FAIL; DRIBBLE; SHOT GOAL/ON_TARGET/OFF_TARGET/BLOCKED; TACKLE; INTERCEPTION; BLOCK; CLEARANCE; FOUL; CARD; LOSS OTHER; PENALTY WON/CONCEDED GOAL/MISSED; CORNER FOR/AGAINST; GK SAVE/GOAL_CONCEDED.

Qualifiers: key_pass, assist, second_yellow, set_piece_result, penalty_taker_player_id.

DATA-04: 27 raw stats player-match aprobadas: pases total/completados, asistencias, largos, centros, regates, turnovers, dispossessed, remates, bloqueados, goles, tackles total/ganados, intercepciones, blocked passes, despejes, faltas cometidas/recibidas, tarjetas, penaltis concedidos/ganados, paradas y goles encajados. key_passes no se aproxima si no existe fuente verificada.

## 6. Feature Engine

FEATURE-01 `0.1.0`: 28 features, 23.380 filas.

FEATURE-02 `0.2.0`: history_n, prev, prior_mean, prior_std, delta_prev, delta_prior_mean, prior_slope. Strict-past; partido actual, misma fecha y futuro excluidos.

FEATURE-03 `0.3.0`: historial jugador + rol observado + feature; 117.735 filas; 590/835 player-match con rol; 23 roles. No se infiere rol.

## 7. Sistema experto

```text
N1000 disponibilidad / actividad
N2000 perfil estructural
N3000 forma / evolución
N4000 amenaza ofensiva
N5000 creación / progresión
N6000 contribución defensiva
N7000 finalización
N8000 contexto del equipo
N9000 componente físico opcional
N10000 rol y encaje táctico
N11000 consistencia / tendencia
N12000 player-fit evidence
N13000 recommendation gate
```

Motor final `expert_0.7.0`: 154.475 decisiones; 2.505 N13000. Carry-forward validado. N13000 solo devuelve estados RECOMMENDATION_NOT_ISSUED_* mientras no exista política final validada.

## 8. Dashboard / LLM / PDF

DASHBOARD-01 DATA CONTRACT PASS: 38 partidos, 36 jugadores, 28 métricas FEATURE-01, 154.475 decisiones y N13000 seguro. Streamlit arrancó correctamente en localhost:8501 después de la integración final.

Pendiente para cerrar DASHBOARD-01: revisar visualmente TEAM, PLAYER, PARTITS y ASSISTENT, incluyendo los tres botones PDF.

LLM-01 y LLM-02: PASS. OpenAI es opcional; sin clave funciona fallback determinista. Rankings/recomendaciones no validadas se bloquean antes de proveedor externo.

REPORTS-01: PASS. Motor único ReportLab para Team / Player / Match, ya integrado en Streamlit. PDF demo: equipo 10.638 bytes; jugador 6.291; partido 5.562. Guardrails PASS.

## 9. PUBLICATION-01 — PREPARADO

Issue #23.

Archivos:

```text
publication/build_public_demo.py
publication/validate_public_demo.py
publication/validate_public_demo.ps1
publication/README.md
```

La demo local sustituye identidades por TEAM_001, OPP_001..., PLAYER_001... y MATCH_001.... Incluye solo las tablas necesarias para ejecutar el producto web actual: teams, players, matches, team_match, player_match, player_match_raw_stats, player_match_features y decision_results.

La validación debe comprobar:
- identidad de número de filas source/output;
- ausencia de nombres e IDs originales;
- aliases válidos;
- compatibilidad con app.data_access;
- N13000 sin estados inseguros.

`publication/output/` y `reports/output/` están ignorados por Git.

La demo generada permanece local. Solo se publicará si la licencia de la fuente permite redistribución; si no, el GitHub público usará datos sintéticos o con licencia compatible.

README.md principal actualizado al MVP funcional real.

## 10. Decisiones descartadas / restricciones

- No inventar eventos atómicos desde agregados ambiguos.
- No inferir formación ni rol sin evidencia.
- No crear role stints ficticios.
- No inventar umbrales GPS.
- No usar fuzzy matching GPS silencioso.
- No etiquetar consistencia o tendencia como buena/mala sin regla validada.
- No interpretar N12000 como score de fit.
- No emitir recomendación N13000 mientras la política siga sin validar.
- No publicar datos profesionales solo porque estén anonimizados.

## 11. Problemas abiertos

- validar localmente PUBLICATION-01;
- cerrar revisión visual DASHBOARD-01;
- decidir dataset público según derechos de redistribución;
- test global / instalación limpia / capturas para GitHub;
- futura validación de política de recomendación;
- ML posterior si existe base suficiente;
- features físicas cuando haya GPS real;
- mejorar reejecución incremental;
- retoque UX Collector final.

## 12. Siguiente paso exacto

Sin instalar nada nuevo, abrir una segunda PowerShell mientras Streamlit sigue abierto y ejecutar:

```powershell
cd C:\Users\sergi\Desktop\football-performance-system
git pull
python publication\validate_public_demo.py
```

Esperado: `PUBLICATION-01 ANONYMIZED DEMO CONTRACT: PASS`.
