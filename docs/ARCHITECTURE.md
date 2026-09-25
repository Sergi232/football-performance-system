# Arquitectura del Football Performance System

## Principio de trabajo

El proyecto se divide en capas independientes para evitar bloquear el desarrollo completo por decisiones pendientes del Data Collector.

```text
Collector / importadores
        ↓
Capa de datos normalizada
        ↓
Feature Engine
        ↓
Motor analítico
        ↓
Sistema experto / ML
        ↓
Aplicación web
        ↓
LLM
        ↓
Informes
```

Cada capa consume salidas estructuradas de la capa anterior. Ninguna conclusión crítica depende del LLM.

## 1. Collector

Responsabilidad: registrar acciones observables con el mínimo número de clics.

Formato lógico principal:

```text
action_type + subtype + outcome + contexto mínimo
```

El Collector no calcula métricas avanzadas. Genera eventos atómicos.

## 2. Data layer

Responsabilidad: almacenar de forma estable jugadores, equipos, partidos, participación, roles, eventos y GPS normalizado.

La base se diseña orientada a eventos. Esto permite cerrar o ampliar posteriormente la taxonomía del Collector sin modificar la estructura central de la base de datos.

La unidad analítica principal es `player_match`, pero los eventos se conservan a nivel atómico para permitir reconstruir agregados y clips.

Capas lógicas:

```text
master data     → teams, players, matches
context         → team_match, player_match, player_role_stints
events          → match_events
physical data   → gps_imports, gps_observations
derived data    → player_match_features
analytics       → decision_results
```

## 3. Feature Engine

Responsabilidad: transformar datos normalizados en variables derivadas reproducibles.

Ejemplos de operaciones permitidas:

- agregaciones por jugador-partido;
- tasas por minuto;
- ventanas temporales;
- tendencias;
- consistencia;
- carga física;
- variables por rol.

Las métricas concretas no se consideran aprobadas hasta ser definidas y validadas.

## 4. Motor analítico

Responsabilidad: producir resultados estadísticos y analíticos deterministas a partir de las features.

No depende del LLM.

## 5. Sistema experto / ML

Responsabilidad: convertir resultados analíticos en evaluaciones auditables.

Cada decisión del sistema experto debe poder expresarse como:

```text
entrada → condición → resultado → confianza → justificación
```

ML se incorporará solamente cuando exista un dataset suficiente y una comparación metodológica válida.

## 6. Aplicación web

Producto principal del TFM.

Modos:

- Team Mode — principal.
- Player Mode — complementario.
- Rival Mode — extensión futura.

## 7. LLM

Arquitectura obligatoria:

```text
DATA → ANALYTICS → DECISION ENGINE → LLM → COACH
```

El LLM consulta resultados ya calculados. Puede explicar, resumir y generar texto, pero no sustituye los cálculos críticos.

## División práctica del desarrollo

El trabajo se ejecutará en módulos que puedan avanzar parcialmente en paralelo:

1. `collector/`: cerrar y simplificar la interfaz y taxonomía de eventos.
2. `data/`: esquema estable, importación PannaData y dataset demostrador.
3. `gps/`: normalización multi-proveedor.
4. `features/`: transformaciones reproducibles.
5. `engine/`: agregaciones y análisis.
6. `decision_tree/`: sistema experto auditable.
7. `models/`: ML opcional y comparativas.
8. `app/`: dashboard web.
9. `llm/`: capa de consulta y explicación.
10. `reports/`: exportaciones PDF.
11. `tests/`: tests de datos, lógica y regresión.

## Regla de desbloqueo

Una decisión pendiente del Collector no debe bloquear la infraestructura cuando el modelo de datos ya pueda representarla de forma genérica. Por ejemplo, `CORNER`, una futura etiqueta de falta peligrosa o nuevos resultados de ABP pueden almacenarse como eventos sin alterar el esquema central.
