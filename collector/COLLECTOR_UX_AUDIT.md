# COLLECTOR-01 — Auditoría final UX / contrato

Fecha: 02/10/2026
Estado: **REVISIÓN FINAL ABIERTA**

Objetivo: cerrar el Data Collector como herramienta realmente utilizable durante o después de un partido de 90 minutos, sin cambiar la taxonomía aprobada `event_catalog v0.3.0` ni introducir métricas nuevas.

## Qué se conserva

La lógica de eventos aprobada se mantiene:

- PASS NORMAL / LONG / CROSS, SUCCESS / FAIL;
- DRIBBLE SUCCESS / FAIL;
- LOSS OTHER;
- SHOT GOAL / ON_TARGET / OFF_TARGET / BLOCKED;
- TACKLE SUCCESS / FAIL;
- INTERCEPTION / BLOCK / CLEARANCE;
- FOUL COMMITTED / RECEIVED con x/y;
- CARD YELLOW / RED y segunda amarilla;
- PENALTY WON / CONCEDED;
- CORNER FOR / AGAINST y resultado ABP;
- GK SAVE / GOAL_CONCEDED;
- key pass / assist como qualifiers del pase;
- autosave, undo, CSV y JSON.

No se reabre la taxonomía de variables.

## Hallazgos que deben corregirse antes de cerrar COLLECTOR-01

### 1. Contexto jugador incompleto respecto al contrato

El contrato funcional aprobado incluye `jugador + dorsal + titular/suplente + minutos + rol/lado`.

La implementación actual:

- crea un dorsal por orden (`1..25`) pero no permite editarlo;
- no guarda explícitamente `titular/suplente`;
- sí guarda entrada/salida y minutos;
- sí guarda rol/lado y cambios de rol.

**Acción:** hacer editable el dorsal y almacenar explícitamente titular/suplente sin inferirlo silenciosamente de `minuteIn`.

### 2. Rival no está estructurado

El contrato menciona `partido + fecha + equipo + rival`, pero la UI actual solo dispone de `matchName` y `teamName`; el rival queda implícito dentro del nombre del partido.

**Acción:** añadir `opponentName` como metadato explícito, manteniendo `matchName` por compatibilidad.

### 3. Resumen de remates a puerta infracontabiliza goles

Los outcomes de SHOT son exclusivos: `GOAL`, `ON_TARGET`, `OFF_TARGET`, `BLOCKED`.

Actualmente el resumen `A puerta` cuenta solo `ON_TARGET`. Un `GOAL` también debe formar parte del total derivado de remates a puerta.

**Acción:** derivar `shots_on_target = GOAL + ON_TARGET`. No cambia el evento raw; corrige únicamente el agregado derivado.

### 4. La interfaz todavía no es castellano completo

Persisten textos visibles como `Passada`, `Llarga`, `Centre`, `Assistència`, `Tackle`, `Clearance`, `Save` y `Goal conceded`.

**Acción:** traducir toda la interfaz visible a castellano manteniendo intactos los códigos técnicos internos (`PASS`, `SHOT`, etc.).

### 5. Responsive existe, pero no es todavía mobile-first

A menos de 900 px la UI pasa a una sola columna y también convierte `.two-col` en una sola columna. Esto hace que las familias de acciones frecuentes ocupen demasiada altura y obliga a mucho scroll durante captura.

**Acción:**

- mantener botones de acciones en dos columnas cuando el ancho lo permita;
- aumentar targets táctiles a ~44–48 px;
- reducir altura del roster en modo captura;
- priorizar jugador activo + minuto + acciones por encima de exportación/configuración;
- mantener navegación anterior/siguiente y deshacer accesibles;
- no introducir menús que añadan clics a las acciones frecuentes.

### 6. Jerarquía de uso

La configuración de partido, roster y exportaciones compite visualmente con la captura durante el partido.

**Acción:** separar conceptualmente:

1. preparación del partido;
2. captura rápida;
3. revisión/resumen/exportación.

La captura debe ser la zona dominante durante el uso real.

## Criterios de cierre

COLLECTOR-01 solo se cerrará cuando:

- `event_catalog v0.3.0` permanezca intacto;
- dorsal y titular/suplente queden guardados explícitamente;
- rival quede estructurado;
- `A puerta` derive correctamente `GOAL + ON_TARGET`;
- toda la UI visible esté en castellano;
- la captura móvil sea operable sin scroll excesivo entre acciones frecuentes;
- se mantengan autosave, undo, CSV, JSON, x/y de faltas, ABP y cambios de rol/formación;
- `collector/validate_collector_mvp.py` y `tests/test_collector_contract.py` sigan pasando tras ampliar los gates de contexto/UX.

## Fuera de alcance de esta fase

- nuevas métricas;
- posesión, xG, PPDA o pressing;
- computer vision / detección automática de eventos;
- integración médica;
- cambios en Match Rating, Feature Engine o sistema experto;
- rediseño del esquema analítico downstream.

La automatización del Collector mediante vídeo queda como extensión futura; el objetivo actual es cerrar una captura manual rápida, consistente y defendible.
