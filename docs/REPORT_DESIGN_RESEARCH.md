# REPORT DESIGN RESEARCH — ELITE TECHNICAL STAFF

Fecha: 2026-10-01
Estado: base de diseño aprobada para REPORTS-03.

## Objetivo

Diseñar informes Team / Player / Match que sean útiles para un cuerpo técnico y no meras exportaciones de tablas o copias de la web. El diseño toma referencias de flujos profesionales públicos, sin copiar layouts, fórmulas o métricas propietarias.

## Referencias revisadas

### Opta / Stats Perform — ProVision

Fuentes públicas:
- https://www.statsperform.com/products/opta-provision/
- https://www.statsperform.com/team-performance/performance-solutions-for-football/football-match-analysis/

Principios extraídos:
- KPI personalizados según modelo de juego / posición;
- contexto de partido y estado de juego;
- comparación longitudinal de equipo y jugador;
- visualizaciones claras (barras, radars, heat maps cuando los datos lo permiten);
- informes y dashboards adaptados al staff.

Aplicación FPS:
- se priorizan cambios temporales y contexto de rol;
- no se imitan métricas Opta Vision ni tracking que no existen en nuestra fuente.

### Hudl Wyscout Reports

Fuentes públicas:
- https://www.hudl.com/releases/wyscout
- https://www.hudl.com/support/wyscout/guides/analysis-reports

Principios extraídos:
- productos diferenciados de Match Report, Player Report y Team Report;
- Match Report: match sheet, jugadores, dinámica, stats, formaciones y eventos;
- Player Report: información relevante por posición, acciones, distribución de pase, duelos y comparación;
- Team Report: plantilla, player stats, formaciones, build-up, set pieces y eventos;
- personalización por bloque ofensivo / defensivo / passing / finishing / goalkeeping.

Aplicación FPS:
- cada tipo de informe tiene narrativa propia;
- no mostramos build-up, mapas de pase o ABP cuantificada si la base actual no lo soporta de forma fiable.

### Hudl StatsBomb

Fuentes públicas:
- https://statsbomb.com/articles/soccer/explaining-xgchain-passing-networks/
- https://statsbomb.com/es/articulos/futbol/scouting-de-mediapuntas-con-datos-statsbomb-iq/
- https://statsbomb.com/es/articulos/futbol/introduccion-a-la-interpretacion-de-los-radares-de-statsbomb/

Principios extraídos:
- combinar visualización + números + vídeo/contexto;
- usar redes de pase / shot maps / radars solo cuando el dato subyacente lo permite;
- contextualizar las visualizaciones y explicar sus limitaciones;
- métricas diferentes según posición y objetivo analítico.

Aplicación FPS:
- gráfico + tabla detallada, nunca solo uno de los dos;
- la lectura del PDF debe indicar qué revisar, sin convertir correlación en causa;
- no se incluyen xG, OBV, pressures, passing networks o shot maps si no existen datos válidos para generarlos.

### UEFA Technical Reports / Performance Insights

Fuentes públicas:
- https://www.uefa.com/development/performance-analysis/technical-reports/
- https://www.uefa.com/uefachampionsleague/news/02a4-207d3e47819e-f92d393cfd51-1000--champions-league-performance-insights-how-semi-finalists-sho/

Principios extraídos:
- lectura por fases: organización ofensiva, transición defensiva, organización defensiva, transición ofensiva;
- importancia específica de set pieces;
- estadísticas y gráficos subordinados a una pregunta de fútbol concreta.

Aplicación FPS:
- la estructura visual agrupa información en `Con balón`, `Finalización`, `Recuperación defensiva` y `Pérdidas` porque son los bloques soportados por nuestros datos actuales;
- no se etiqueta un bloque como transición/pressing/organización si no se puede medir directamente.

### Evidencia sobre preferencias de practitioners

1. Davidson et al. (2024), PLOS One, Category 1 academy case study.
   - métricas de partido consideradas importantes: regains, pass completion, lost balls;
   - visual reporting preferido;
   - time constraints y staffing son barreras principales;
   - el dato objetivo debe complementar, no sustituir, conocimiento contextual del entrenador.
   - DOI: 10.1371/journal.pone.0298346

2. Goes et al. (2021), Attacking KPIs in Soccer.
   - 145 practitioners / 42 países;
   - preferencia práctica por event data y KPIs simples relacionados con finalización;
   - DOI / PubMed: 33707999.

3. Asimakidis et al. (2026), Journal of Strength and Conditioning Research.
   - 145 practitioners;
   - tracking de cambios: 91%; benchmark: 61%; comparación por posición: 58%;
   - raw scores preferidos: 62.1%;
   - bar charts para comparar jugadores: 77.2%;
   - line charts para evolución temporal: 51.7%;
   - radar charts para perfil individual vs grupo: 59.3%;
   - quadrant charts: 87.6%;
   - DOI: 10.1519/JSC.0000000000005355.

### Catapult / physical performance

Fuentes públicas:
- https://www.catapult.com/blog/leeds-united-sports-science-optimise-performance
- https://www.catapult.com/blog/vector-efforts-breakdown-game-speed-insights

Variables recurrentes en practitioners y soluciones GPS:
- total distance;
- high-speed running distance;
- sprint distance / sprint efforts;
- accelerations;
- decelerations;
- maximum velocity exposure, según contexto.

Aplicación FPS:
- estas variables se reservan al bloque Physical/GPS y solo entrarán en PDF cuando existan datos GPS normalizados reales o un ejemplo explícitamente etiquetado;
- no se infieren fatigue/readiness/injury risk.

## Criterios de diseño adoptados

1. **Cada informe responde preguntas concretas.**
   - Team: qué está cambiando, dónde mirar y quién cambia.
   - Player: cómo evoluciona, qué produce y con qué contexto/rol.
   - Match: qué ocurrió, qué cambió respecto a la referencia inmediata y qué jugadores revisar.

2. **Cambios temporales antes que rankings.**
   El principal benchmark es el propio historial: último / últimos 5 / 5 anteriores.

3. **Raw / transparent data antes que composite scores.**
   Match Rating se mantiene como score principal validado, pero se acompaña de acciones observables.

4. **Visual + detalle.**
   Línea para evolución, cuadrante para plantilla, barras para distribución y tablas para trazabilidad.

5. **Contexto de posición.**
   El perfil técnico del jugador selecciona indicadores útiles según grupo posicional sin crear pesos nuevos.

6. **No usar rojo/verde para declarar bueno/malo.**
   Deltas técnicos son descriptivos; el staff interpreta el contexto.

7. **No inventar métricas profesionales.**
   Sin xG, xA, PPDA, pressures, progressive passes, box entries, possessions, pitch control o tracking hasta que la capa de datos los soporte y valide.

8. **No data leakage.**
   En Match Report, la referencia del partido seleccionado solo usa los 5 partidos estrictamente anteriores.

## Métricas soportadas ahora en REPORTS-03

### Equipo / partido
- precisión de pase;
- remates;
- goles;
- entradas ganadas;
- intercepciones;
- pérdidas;
- desposesiones;
- Match Rating materializado;
- confianza del rating;
- rol/contexto disponible.

### Jugador
- precisión de pase;
- pases completados / 90;
- remates / 90;
- goles / 90;
- asistencias / 90;
- entradas ganadas / 90;
- intercepciones / 90;
- pérdidas / 90;
- desposesiones / 90;
- Match Rating y dimensiones materializadas;
- Performance Index complementario cuando exista;
- estado del motor experto y cobertura.

## Métricas no incluidas por falta de soporte actual

- xG / xA / post-shot xG;
- posesión;
- pressures / PPDA / counterpressing;
- progressive passes / line-breaking passes;
- box entries / final-third entries;
- pass networks / average positions;
- heat maps / shot maps;
- set-piece efficiency completa;
- HSR / sprint / acceleration / deceleration cuando no haya GPS real normalizado.

Estas métricas son candidatas futuras, no huecos a rellenar artificialmente.
