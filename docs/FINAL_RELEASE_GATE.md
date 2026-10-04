# Final Release Gate — 04/10/2026

Estado: **PRODUCT FREEZE CANDIDATE**

Este documento resume el gate técnico final previo a capturas, maquetación y entrega. No sustituye `PROJECT_STATE.md`; lo complementa con una evidencia de cierre compacta.

## 1. Gate funcional

```text
GLOBAL END-TO-END QA                 PASS
SYNTHETIC PUBLIC DEMO                PASS
REPRODUCIBILITY                      PASS
CI QUERY-SPACE CONTRACT              PASS
COACH COPILOT REAL SMOKE             PASS 28/28
COACH COPILOT AVG ELAPSED            0.4s
OPENAI BYOK CONTRACT                 PASS
REPORTS V6                           PASS
```

El smoke real final se ejecutó sobre la DuckDB profesional con `qwen3.5:4b` configurado como fallback semántico. Los 28 casos finales se resolvieron con `rounds=0`, por lo que ninguna de esas consultas necesitó invocar el LLM.

## 2. Cobertura del smoke final

El gate real cubre:

- ranking por Match Rating;
- Match Rating medio en ventana temporal;
- distancia GPS media;
- top-N por remates;
- asistencias;
- perfil/evolución de jugador;
- GPS de jugador;
- comparación entre jugadores;
- partido contra rival;
- estado de equipo;
- calidad/cobertura de datos;
- guardrails de fatiga;
- guardrails de riesgo de lesión;
- guardrails de titularidad;
- criterios no validados (`más completo`, `más determinante`);
- comparación de delanteros;
- comparación de centrales con criterio explícito;
- fuera de dominio;
- ruido (`sss`);
- meta-consulta (`no puedes hacer nada`);
- follow-up ordinal;
- follow-up temporal;
- evidencia/provenance;
- follow-up de comparación por posición.

## 3. Contrato del Coach Copilot

Flujo final:

```text
QUESTION
→ PREFLIGHT / GUARDRAILS
→ DETERMINISTIC HIGH-CONFIDENCE ROUTER
→ READ-ONLY FPS TOOLS
→ PYTHON / DUCKDB / ANALYTICS / EXPERT SYSTEM
→ STRUCTURED EVIDENCE
→ ANSWER
```

Fallback únicamente cuando persiste ambigüedad dentro del dominio:

```text
Qwen local
or
OpenAI BYOK
```

Los proveedores LLM:

- no tienen acceso directo a DuckDB;
- no recalculan Match Rating ni Performance Index;
- no inventan métricas o policies;
- no sustituyen el sistema experto;
- no reciben autorización para fatiga, riesgo de lesión, XI o táctica no validada.

## 4. Comparaciones por posición

Capacidad aprobada:

```text
GK / CB / FB / DM / CM / AM / W / ST
```

Si la pregunta es `quién ha rendido mejor` dentro de una posición:

```text
criterio de ordenación = Match Rating medio en la muestra del rol
métricas adicionales = evidencia descriptiva
nuevo score = NO
```

## 5. Privacidad / demo

La demo pública utiliza:

```text
Equipo Demo
Jugador 01, Jugador 02, ...
Rival 01, Rival 02, ...
```

El Assistant traduce alias visibles a identidades internas solo en el boundary de tools y vuelve a anonimizar antes de renderizar. Si detecta una identidad interna conocida en demo mode, la respuesta se bloquea.

No debe aparecer en capturas finales:

- API keys;
- rutas locales privadas;
- nombres profesionales reales;
- dataset profesional distribuido;
- claims médicos/no validados.

## 6. Regla de freeze

A partir de este gate:

> **No se añade nueva funcionalidad deportiva antes de la entrega salvo defecto reproducible que invalide un contrato cerrado.**

No volver al patrón:

```text
pregunta manual aleatoria
→ fallo aislado
→ nueva regla ad hoc
```

La cobertura funcional del Assistant se gobierna mediante:

```text
COACH_COPILOT_CONTRACT.md
+ tests paramétricos
+ validate_coach_contract.py
+ CI
+ smoke real reproducible
```

## 7. Sincronización académica

Documentos actualizados al gate final 28/28:

```text
TFM_MANUSCRIPT_DRAFT.md
TFM_METHODOLOGY_DRAFT.md
TFM_RESULTS_DRAFT.md
TFM_DISCUSSION_CONCLUSIONS_DRAFT.md
TFM_EVIDENCE_MATRIX.md
TFM_TABLES_RESULTS.md
TFM_ANNEXES_DRAFT.md
TFM_FIGURES_TABLES_PLAN.md
TFM_DEFENSE_OUTLINE.md
TFM_SCREENSHOT_CHECKLIST.md
TFM_SUBMISSION_CHECKLIST.md
ARCHITECTURE.md
DATA_SCIENCE_AI_STRATEGY.md
DECISIONS.md
WORKFLOW.md
```

Las cifras antiguas de 16/16 y 22/22 quedan como histórico de desarrollo, no como resultado final de la memoria.

## 8. Pendiente para entrega

Solo quedan tareas de cierre:

```text
1. revisión visual final en FPS_DEMO_MODE=1
2. 10 capturas canónicas
3. adaptación a plantilla / bibliografía / numeración
4. presentación y backup estático
5. entrega
```

## 9. Ejecución de la demo final

Launcher Windows recomendado:

```powershell
.\run_final_demo.ps1
```

Hace automáticamente:

```text
rebuild + validate synthetic demo
→ FPS_DB_PATH = synthetic demo
→ FPS_DEMO_MODE = 1
→ Qwen fallback por defecto si no existe otra configuración
→ Streamlit
```

Para reabrir la demo sin reconstruir la base:

```powershell
.\run_final_demo.ps1 -SkipRebuild
```

Comandos manuales equivalentes:

```powershell
python -m publication.validate_synthetic_demo --rebuild
$env:FPS_DB_PATH="$PWD\data\football_performance_synthetic_demo.duckdb"
$env:FPS_DEMO_MODE="1"
streamlit run app\streamlit_app.py
```

Gate Coach sobre una DuckDB local compatible:

```powershell
python llm\smoke_test_coach_agent.py
```

Gate CI del espacio de consultas:

```powershell
python -m llm.validate_coach_contract --db data\football_performance_synthetic_demo.duckdb
```
