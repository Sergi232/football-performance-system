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
PUBLICATION-01 demo anonimizada     CERRADO / VALIDADO
DASHBOARD-01 Streamlit MVP          CONTRACT PASS / REVISIÓN VISUAL ABIERTA
FINAL-01                            SIGUIENTE MACROBLOQUE
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

Deportivo Alavés 2025/26: 38 partidos, 36 jugadores, 835 `player_match`.

Los datos profesionales se usan localmente para desarrollo/validación. No se publicarán raw files originales.

## 5. Datos / features / motor

Collector v0.3.0 cerrado funcionalmente. DATA-04 contiene 27 raw stats player-match aprobadas. `key_passes` no se aproxima si no existe fuente verificada.

FEATURE-01 `0.1.0`: 28 features, 23.380 filas.

FEATURE-02 `0.2.0`: evolución strict-past (`history_n`, `prev`, `prior_mean`, `prior_std`, `delta_prev`, `delta_prior_mean`, `prior_slope`).

FEATURE-03 `0.3.0`: historial jugador + rol observado + feature; 117.735 filas; 590/835 player-match con rol; 23 roles.

Motor experto final `expert_0.7.0`: 154.475 decisiones; 2.505 N13000. N13000 solo devuelve `RECOMMENDATION_NOT_ISSUED_*` mientras no exista política final validada.

## 6. Dashboard / LLM / PDF

DASHBOARD-01 DATA CONTRACT PASS: 38 partidos, 36 jugadores, 28 métricas FEATURE-01, 154.475 decisiones y N13000 seguro. Streamlit arrancó correctamente en `localhost:8501` después de la integración final.

Pendiente para cerrar DASHBOARD-01: revisar visualmente TEAM, PLAYER, PARTITS y ASSISTENT, incluyendo los tres botones PDF.

LLM-01 y LLM-02: PASS. OpenAI es opcional; sin clave funciona fallback determinista. Rankings/recomendaciones no validadas se bloquean antes del proveedor externo.

REPORTS-01: PASS. Motor único ReportLab para Team / Player / Match, integrado en Streamlit. PDF demo: equipo 10.638 bytes; jugador 6.291; partido 5.562. Guardrails PASS.

## 7. PUBLICATION-01 — CERRADO / VALIDADO

Issue #23 cerrado.

Archivos principales:

```text
publication/build_public_demo.py
publication/validate_public_demo.py
publication/README.md
```

Validación local 25/09/2026:

```text
PUBLICATION-01 ANONYMIZED DEMO CONTRACT: PASS
team: TEAM 001
matches: 38
players: 36
decision rows: 154475
N13000 rows: 2505
sensitive text columns checked: 43
source/output row-count identity: PASS
source identifiers/names absent from public tables: PASS
source provenance IDs neutralized: PASS
is_anonymized flags: PASS
recommendation gate safety: PASS
metadata: public_demo_0.1.0 / ANONYMIZED_LOCAL_EXPORT
```

La demo local sustituye identidades por `TEAM_001`, `OPP_001...`, `PLAYER_001...`, `MATCH_001...`, neutraliza `source_*_id`, anonimiza `source_name` y marca `is_anonymized=TRUE`.

**Redistribución no autorizada por defecto.** La demo generada queda local/ignorada por Git hasta confirmar la licencia. Si no existe permiso explícito, el GitHub público utilizará datos sintéticos o con licencia compatible.

## 8. Restricciones vigentes

- No inventar eventos atómicos desde agregados ambiguos.
- No inferir formación ni rol sin evidencia.
- No crear role stints ficticios.
- No inventar umbrales GPS.
- No usar fuzzy matching GPS silencioso.
- No etiquetar consistencia/tendencia como buena/mala sin regla validada.
- No interpretar N12000 como score de fit.
- No emitir recomendación N13000 mientras la política siga sin validar.
- No publicar datos profesionales solo porque estén anonimizados.

## 9. Problemas abiertos

- cerrar revisión visual DASHBOARD-01;
- decidir dataset público final según derechos de redistribución;
- ejecutar tests globales y empaquetado limpio;
- preparar capturas y README final para GitHub;
- futura validación de política de recomendación;
- ML posterior si existe base suficiente;
- features físicas cuando haya GPS real;
- mejorar reejecución incremental;
- retoque UX Collector final.

## 10. Siguiente paso exacto

FINAL-01 debe agrupar, sin microfases:

1. test global de módulos ya validados;
2. ejecución limpia del producto;
3. cierre visual de DASHBOARD-01;
4. dataset público compatible (sintético/licencia válida si no hay permiso de redistribución);
5. README/capturas/estructura final de GitHub.

No añadir nuevas métricas ni rediseñar el sistema antes de cerrar este bloque.