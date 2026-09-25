# Data Collector MVP — contrato funcional

## Objetivo

Registrar durante o después de un partido de 90 minutos solo acciones observables, rápidas de introducir y útiles para el sistema final. El Collector no calcula métricas avanzadas: guarda eventos y contexto; el Feature Engine calcula después tasas, tendencias, consistencia y perfiles.

## Contexto de partido y jugador

El Collector debe conservar:

- partido, fecha, equipo y rival;
- jugador, dorsal, titular/suplente;
- minuto de entrada y salida y minutos calculados automáticamente;
- posición/rol, lado y cambios de posición;
- formación cuando el usuario la conoce de forma explícita.

No se debe inferir automáticamente una formación que el usuario no haya indicado.

## Flujo de interacción

Prioridad: un clic por acción siempre que sea posible.

### Pase

Botones directos:

- `Passada ✓` → `PASS | NORMAL | SUCCESS`
- `Passada ✗` → `PASS | NORMAL | FAIL`
- `Llarga ✓` → `PASS | LONG | SUCCESS`
- `Llarga ✗` → `PASS | LONG | FAIL`
- `Centre ✓` → `PASS | CROSS | SUCCESS`
- `Centre ✗` → `PASS | CROSS | FAIL`

Una pasada `LONG` o `CROSS` ya cuenta como pase total. No se registra además una `NORMAL`.

Dos marcadores contextuales pueden añadirse sin crear una segunda acción de pase:

- `key_pass=true`: pase que conduce directamente a un remate de un compañero antes de cambiar la posesión;
- `assist=true`: último pase que conduce directamente a gol. Implica pase completado y `key_pass=true`.

Para mantener pocos clics, la interfaz puede ofrecer `Passada clau` tras un remate y `Assistència` tras un gol, vinculando la última pasada válida.

### Regate y pérdida

- `DRIBBLE | SUCCESS`
- `DRIBBLE | FAIL`
- `LOSS | OTHER`

Un regate fallado ya genera pérdida derivada. `LOSS` se reserva para pérdidas no explicadas por pase o regate fallado.

### Remate

- `SHOT | GOAL`
- `SHOT | ON_TARGET`
- `SHOT | OFF_TARGET`
- `SHOT | BLOCKED`

El poste se incluye en `OFF_TARGET` en el MVP. Cada resultado cuenta automáticamente como remate total.

### Defensa

- `TACKLE | SUCCESS`
- `TACKLE | FAIL`
- `INTERCEPTION`
- `BLOCK`
- `CLEARANCE`

Todos los tackles cuentan en `tackles_total`; solo `SUCCESS` cuenta en `tackles_won`.

### Falta y disciplina

- `FOUL | COMMITTED`
- `FOUL | RECEIVED`
- `CARD | YELLOW`
- `CARD | RED`

Para las faltas se captura una localización rápida `x/y` sobre el campo. No existe un botón subjetivo de “falta peligrosa”. Esa condición se derivará más adelante a partir de la posición con un umbral espacial validado con datos/literatura/experimento.

Una expulsión por segunda amarilla se guarda como `CARD | RED` con `second_yellow=true`; la capa derivada conserva las dos consecuencias disciplinarias.

### Penalti

- `PENALTY | WON | GOAL/MISSED`
- `PENALTY | CONCEDED | GOAL/MISSED`

`player_id` identifica al jugador que gana o concede el penalti cuando se conoce. El evento `PENALTY` no suma por sí mismo un remate o gol al jugador, porque el lanzador puede ser otro. Cuando el lanzador propio se conoce, la interfaz puede crear automáticamente un `SHOT` enlazado para ese jugador.

### Porter

- `GK | SAVE`
- `GK | GOAL_CONCEDED`

No se añade granularidad como tipo de parada en el MVP.

## Córners y ABP

Se aprueban como eventos de equipo:

- `CORNER | FOR`
- `CORNER | AGAINST`

El contexto ataque/defensa de ABP se deriva automáticamente:

- `CORNER FOR` / `FOUL RECEIVED` → ABP ataque;
- `CORNER AGAINST` / `FOUL COMMITTED` → ABP defensa.

Cada córner y falta conserva `match_second`/`video_second` para poder extraer clips más adelante.

Cuando realmente hay una reanudación a balón parado, se puede cerrar la secuencia con `set_piece_result`:

- `DIRECT_SHOT`: remate directo desde la ABP;
- `SHOT_AFTER_RESTART`: la secuencia produce un remate después de la reanudación;
- `GOAL`: la secuencia produce gol;
- `NO_SHOT`: termina sin remate.

No se usa una categoría manual `CHANCE`, porque sería menos reproducible. El objetivo es poder filtrar y revisar clips de córners y faltas en ataque/defensa sin introducir una valoración subjetiva durante la captura.

## Automatismos obligatorios

- `PASS LONG/CROSS` suma también a pase total.
- `PASS FAIL` genera pérdida `FAILED_PASS`.
- `DRIBBLE FAIL` genera pérdida `FAILED_DRIBBLE`.
- `SHOT` siempre suma a remate total.
- `TACKLE SUCCESS` suma a tackle total y ganado.
- `assist=true` implica `key_pass=true` y pase completado.
- los agregados de equipo no se escriben manualmente si pueden derivarse de los eventos.

## Funciones del prototipo que deben conservarse al simplificar el HTML

- selección rápida de jugador;
- roster editable y carga rápida de nombres;
- botones agrupados por familias;
- atajos de teclado cuando realmente reduzcan tiempo;
- entrada/salida y cálculo automático de minutos;
- tabla en directo de acciones/estadísticas;
- deshacer última acción;
- exportación CSV;
- guardado JSON;
- autosave local del navegador.

La simplificación debe eliminar pasos innecesarios, no estas funciones operativas.

## Variables que NO se capturan manualmente en el MVP

- posesión;
- xG;
- PPDA;
- pressing estructurado;
- heatmaps manuales;
- métricas avanzadas de zonas/transiciones;
- tasas, porcentajes, tendencias o índices ya derivados.

## Estado

La taxonomía MVP queda cerrada en `collector/event_catalog.json` v0.3.0. El siguiente trabajo de Collector es adaptar el HTML existente a este contrato, no rediseñar el producto desde cero.
