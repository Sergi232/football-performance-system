# REPORTS-02 — professional exports

## Objectiu

Convertir els PDF de jugador, partit i equip en lliurables presentables per al cos tècnic, mantenint-los com a exportacions estàtiques de dades i analytics ja calculats.

## Principis

- El PDF no recalcula Match Rating ni Performance Index.
- El PDF no crea rankings, llindars de rendiment o recomanacions tàctiques.
- Match Rating és la nota player-match principal.
- Performance Index és la capa històrica/posicional complementària.
- Els insights de partit són observacions deterministes derivades de dades observades.
- GPS només apareix quan existeix evidència real importada.

## Disseny v0.2

- capçalera visual comuna;
- jerarquia de títols coherent amb el dashboard;
- targetes KPI;
- taules amb zebra i millor llegibilitat;
- Match Rating destacat en jugador i partit;
- Performance Index inclòs a jugador quan existeix;
- observacions postpartit incloses al PDF de partit;
- notes metodològiques discretes al final de la secció, no com a contingut principal.

## Gate

`reports/validate_reports.py` ha de continuar passant per equip, jugador i partit. Després cal inspecció visual d'almenys un PDF renderitzat abans de considerar REPORTS-02 tancat.
