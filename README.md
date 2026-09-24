# Football Performance System

Sistema de análisis de rendimiento futbolístico para equipos amateur y semiprofesionales sin departamento de análisis propio. El objetivo es transformar datos sencillos obtenidos mediante vídeo y GPS opcional en información útil para el cuerpo técnico.

Este repositorio corresponde al Trabajo Final de Máster y debe culminar en una aplicación web funcional, documentada y publicable.

## Objetivo

Construir un producto que permita analizar el rendimiento de un equipo y sus jugadores a partir de datos que puedan recogerse de forma realista en fútbol amateur o semiprofesional.

El sistema no pretende reproducir plataformas profesionales de tracking o proveedores como Opta o StatsBomb. Las variables utilizadas en el producto final deberán ser recogibles con un coste razonable y aportar valor al análisis.

## Arquitectura prevista

```text
VÍDEO / DATA COLLECTOR + GPS OPCIONAL
        ↓
BASE DE DATOS
        ↓
FEATURE ENGINE
        ↓
MOTOR ANALÍTICO
        ↓
SISTEMA EXPERTO / ML
        ↓
DASHBOARD WEB
        ↓
ASISTENTE IA
        ↓
INFORMES PDF
```

La aplicación web será el producto principal. Los informes PDF serán exportaciones estáticas del sistema.

## Modos previstos

- **Team Mode**: modo principal del TFM. Analiza el equipo y sus jugadores utilizando su propio historial.
- **Player Mode**: análisis individual de un jugador.
- **Rival Mode**: extensión futura condicionada a disponer de datos fiables del rival. El sistema principal no dependerá de este modo.

## Principios metodológicos

- Priorizar variables fáciles de recoger durante o después de un partido de 90 minutos.
- Separar datos brutos, variables derivadas, modelos y conclusiones.
- Evitar data leakage.
- No basar conclusiones importantes exclusivamente en un LLM.
- Justificar reglas, umbrales y pesos mediante datos, literatura, validación o experimentación.
- Mantener el GPS como fuente complementaria, no obligatoria.
- Construir primero un MVP funcional antes de aumentar la complejidad.

## Datos de desarrollo

Durante el desarrollo se utilizarán datos reales de PannaData/Opta como fuente de validación y reconstrucción de una temporada completa.

Los datos profesionales se limitarán deliberadamente a las variables que podrían obtenerse con el Data Collector y, cuando corresponda, GPS. El objetivo es validar el sistema con información real sin convertir el producto en una solución dependiente de datos profesionales.

El caso demostrador utilizará un equipo real de la temporada 2025/26 sin competición europea. Antes de incorporarlo al repositorio público, el club, los jugadores y los identificadores originales serán anonimizados, manteniendo las estadísticas y la estructura temporal necesarias para reproducir el análisis.

## Data Collector

Las familias de acciones actualmente en revisión son:

- Pase
- Regate
- Remate
- Defensa
- Falta
- Pérdida
- Penalti
- Tarjeta

Estas familias todavía no constituyen el esquema definitivo. Primero se está auditando la disponibilidad real de datos y el coste de recogida manual.

## Estado del proyecto

El estado técnico actualizado se mantiene en [`PROJECT_STATE.md`](PROJECT_STATE.md). Ese archivo actúa como memoria operativa del proyecto y debe consultarse antes de continuar el desarrollo en una nueva sesión.

## Estructura objetivo

```text
football-performance-system/
├── collector/
├── data/
├── gps/
├── engine/
├── features/
├── decision_tree/
├── models/
├── llm/
├── app/
├── reports/
├── tests/
├── docs/
├── examples/
├── README.md
└── PROJECT_STATE.md
```

La estructura se irá materializando de forma incremental a medida que se implementen los módulos reales.
