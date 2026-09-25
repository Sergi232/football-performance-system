# PROJECT_STATE

Última actualización: 25/09/2026

Memoria técnica operativa del proyecto. Si contradice un chat antiguo, prevalece este archivo.

## 1. Estado actual

```text
DATA-01/02/03/04                    CERRADO / VALIDADO
COLLECTOR-01 MVP                    CERRADO FUNCIONALMENTE
GPS-01                              CERRADO / VALIDADO
FEATURE-01/02/03                    CERRADO / VALIDADO
EXPERT-01..07 N1000-N13000          BASELINE CERRADO / VALIDADO
LLM-01/02                           PROTOTYPE v0.1 / CONTRATOS PASS
REPORTS-01                          PROTOTYPE v0.1 / CONTRATO PASS
PUBLICATION-01                      CERRADO / VALIDADO TÉCNICAMENTE
DASHBOARD-01                        PROTOTYPE v0.1 / CONTRACT PASS
ARCHITECTURE-01                     CERRADO — ISSUE #25
ANALYTICS-01                        IMPLEMENTADO / HOTFIX VALIDACIÓN PENDIENTE — ISSUE #26
FINAL-01                            BLOQUEADO HASTA REDISEÑO DE PRODUCTO
```

## 2. Forma de trabajo vigente

El proyecto usa flujo **architecture-first + gated**.

No se añaden parches de producto antes de cerrar la capa propietaria de la lógica. GitHub es la memoria técnica definitiva.

Fuente de verdad:
1. `PROJECT_STATE.md` — estado operativo;
2. `docs/ARCHITECTURE.md` — arquitectura vigente;
3. `docs/DECISIONS.md` — decisiones estructurales/gates;
4. `docs/WORKFLOW.md` — agentes, orden y desbloqueos;
5. `docs/DATA_SCIENCE_AI_STRATEGY.md` — prioridad académica DS/IA;
6. `README.md` — presentación e instalación.

## 3. Prioridad académica del TFM — Data Science + IA

El máster es de Data Science e Inteligencia Artificial. La aplicación web es el producto final, pero la contribución académica principal debe quedar demostrada en datos, feature engineering, analytics, sistema experto, ML, validación y explicabilidad.

Cadena metodológica prioritaria:

```text
DATA
→ FEATURE ENGINE
→ ANALYTICS / STATISTICS
→ EXPERT SYSTEM
→ ML / EXPERIMENTS
→ VALIDATION / EXPLAINABILITY
→ PRODUCT
→ LLM
```

Regla: no convertir el proyecto en un dashboard con un LLM añadido. El rediseño visual no debe absorber tiempo que corresponda al núcleo científico.

Documento específico: `docs/DATA_SCIENCE_AI_STRATEGY.md`.

## 4. Arquitectura vigente

```text
CAPTURE / IMPORT
      ↓
RAW + NORMALIZED DATA
      ↓
FEATURE ENGINE
      ↓
ANALYTICS ENGINE
      ↓
DECISION ENGINE
      ↓
PRODUCT SERVICE LAYER
      ↓
WEB / REPORTS / AI ASSISTANT
      ↓
QA / PUBLICATION
```

Regla: una capa superior no puede inventar métricas, rankings, evaluaciones o recomendaciones que no existan en una capa inferior validada.

## 5. Orden obligatorio de trabajo

```text
ARCHITECTURE-01              CERRADO
        ↓
ANALYTICS-01                 IMPLEMENTADO / REVALIDACIÓN PENDIENTE
        ↓
DECISION POLICY / N13000
        ↓
DS/AI EXPERIMENTAL CORE
  ├─ validación estadística
  ├─ player similarity / profiles
  ├─ change detection
  └─ expert vs ML cuando sea metodológicamente válido
        ↓
PRODUCT UX
        ↓
REPORTS-02 + ASSISTANT ARCHITECTURE
        ↓
FINAL PRODUCT / PUBLICATION / TFM
```

La fase ML/IA experimental no es un adorno opcional: debe existir al menos un bloque experimental serio y reproducible. Si una tarea concreta no dispone de datos/labels suficientes, el resultado puede ser no desplegar ese modelo, pero el estudio de viabilidad y la justificación deben quedar documentados.

## 6. Estado real del prototipo

Se reutiliza como infraestructura válida:
- DuckDB y esquema;
- Collector funcional;
- GPS normalization;
- FEATURE-01/02/03;
- baseline experto N1000-N13000;
- acceso read-only a datos;
- guardrails LLM;
- tooling PDF;
- tooling de anonimización;
- tests existentes.

No se considera definitivo:
- UX Streamlit actual, demasiado orientada a tablas;
- PDF ReportLab actual, prueba técnica y no informe profesional;
- proveedor/arquitectura final del LLM;
- política final N13000;
- Product Service Layer común para web/report/assistant.

## 7. Caso de desarrollo

Deportivo Alavés 2025/26: 38 partidos, 36 jugadores, 835 `player_match`.

Los datos profesionales sirven para desarrollo/validación. No se publicarán raw files originales. La demo anonimizada está técnicamente validada, pero redistribución sigue condicionada a licencia.

## 8. Datos y features cerrados como baseline

DATA-04: 27 raw stats player-match aprobadas. `key_passes` no se aproxima sin fuente verificada.

FEATURE-01 `0.1.0`: 28 features.

FEATURE-02 `0.2.0`: historial strict-past (`history_n`, `prev`, `prior_mean`, `prior_std`, `delta_prev`, `delta_prior_mean`, `prior_slope`).

FEATURE-03 `0.3.0`: historial jugador + rol observado + feature; 590/835 player-match con rol; 23 roles.

El Feature Engine no decide si una métrica es buena/mala.

## 9. Sistema experto baseline

Motor `expert_0.7.0`: 154.475 decisiones; 2.505 N13000.

N13000 mantiene `RECOMMENDATION_NOT_ISSUED_*` mientras no exista policy validada.

El árbol existente se conserva como baseline auditable. La futura policy debe construirse encima de Analytics validado, no mediante intuición ni LLM.

## 10. ANALYTICS-01

Issue #26.

### DG-AN-01 — APROBADO

Sergi aprueba opción **C**: usar ambas comparaciones de forma separada y etiquetada.

```text
SELF_ROLE_PRIOR
jugador vs su propio historial strict-past en el mismo rol observado

PEER_ROLE_PRIOR
jugador vs otros jugadores del mismo equipo y mismo rol observado,
utilizando solo información strict-past
```

La comparación peer:
- excluye al jugador actual;
- excluye misma fecha y futuro;
- calcula primero la media previa de cada peer en ese rol;
- resume después esas medias, dando el mismo peso a cada peer.

Implementación:

```text
analytics/__init__.py
analytics/contract.json
analytics/build_stage1.py
analytics/validate_stage1.py
analytics/README.md
```

Output: tabla `analytics_evidence` con dos scopes por cada fila FEATURE-01.

Analytics-01 no crea score, ranking, percentil, etiqueta bueno/malo, mínimo de muestra, confianza de recomendación ni recomendación táctica. Expone conteos y estadísticos para que la policy posterior pueda validarlos.

### Última validación local

El build completó correctamente y escribió 46.760 filas. La validación detectó un bug del propio test en `peer_std`: DuckDB devolvía `0` para un único peer mientras el contrato del builder define desviación estándar como `NULL` cuando hay menos de 2 peers.

Hotfix aplicado en GitHub: el validador ahora exige `STDDEV_POP` solo cuando `COUNT(*) >= 2`, manteniendo el contrato estadístico sin debilitar la prueba.

Pendiente: repetir `python analytics\\validate_stage1.py`.

## 11. Núcleo Data Science / ML posterior a Analytics

Antes del cierre de producto se deberá trabajar y documentar:

1. **Player profiles / similarity** — clustering o similitud condicionada a rol;
2. **Change detection / evolución** — métodos estadísticos o ML comparados con baselines simples;
3. **Role/player fit** — solo con target/labels defendibles y sin circularidad con el sistema experto;
4. **Expert vs ML** — al menos un caso comparable si los datos lo permiten;
5. **Validación** — temporal split cuando proceda, leakage control, métricas, análisis de error, incertidumbre, reproducibilidad y ablations cuando aporten valor.

No se obliga a desplegar un modelo que no sea válido. Sí se obliga a que la parte DS/IA tenga experimentación y evaluación explícitas.

## 12. Prototipos de producto

### Dashboard
Contract PASS. TEAM / PLAYER / MATCH / ASSISTANT funcionan técnicamente. Problema detectado: predominio de tablas y falta de insights estructurados.

### Reports
REPORTS-01 PASS. Los tres PDF se generan. Problema detectado: son prueba técnica, no informes finales entregables.

### Assistant
LLM-01/02 PASS en contratos y guardrails. Decisión final local/cloud/híbrida pendiente. El assistant final solo explicará outputs estructurados. La IA generativa es una capa de interacción, no el núcleo científico del TFM.

## 13. Agents / ownership

Definidos en `docs/WORKFLOW.md`:
- A0 Architect/Integrator;
- A1 Data & Collector;
- A2 Feature Engine;
- A3 Analytics;
- A4 Expert/Decision Engine;
- A5 ML/Validation;
- A6 Product/UX;
- A7 Reporting;
- A8 AI Assistant;
- A9 QA/Publication.

A0 y A9 acompañan todo el proyecto. A5 gana prioridad académica antes del pulido final de producto. Los agentes de interfaz no crean lógica analítica.

## 14. Decision gates

Registro: `docs/DECISIONS.md`.

- `DG-AN-01` comparaciones analíticas — **APPROVED C**;
- `DG-N13-01` policy de recomendación — pendiente;
- `DG-UX-01` jerarquía de producto — pendiente;
- `DG-LLM-01` local/cloud/híbrido — pendiente;
- `DG-REP-01` estructura final de informes — pendiente;
- `DG-PUB-01` dataset público — pendiente/derechos.

Solo se pide intervención de Sergi cuando el gate bloquea la fase siguiente.

## 15. Restricciones vigentes

- no inventar eventos atómicos desde agregados ambiguos;
- no inferir rol/formación sin evidencia;
- no crear scores/umbrales por intuición;
- no mezclar self-history y peer comparison silenciosamente;
- no usar LLM para cálculo crítico;
- no emitir recomendación N13000 sin policy validada;
- no crear targets ML circulares a partir del propio sistema experto;
- no publicar datos profesionales solo por estar anonimizados;
- no rediseñar web/report/assistant antes de cerrar Analytics correspondiente.

## 16. Siguiente paso exacto

Sergi debe repetir una sola validación local, sin instalar nada:

```powershell
cd C:\\Users\\sergi\\Desktop\\football-performance-system
git pull
python analytics\\validate_stage1.py
```

Esperado: `ANALYTICS-01 EVIDENCE CONTRACT: PASS`.

Si pasa, cerrar ANALYTICS-01 y abrir el siguiente gate estructural: `DG-N13-01`. Después de la policy de decisión, el siguiente macrobloque prioritario será DS/AI experimental antes del pulido final de producto.
