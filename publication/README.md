# Publicación y demo anonimizada

Este bloque prepara una base de datos de demostración para probar el producto sin exponer identificadores ni nombres del caso real de desarrollo.

## Regla principal

La anonimización técnica **no equivale a permiso de redistribución**. Los datos de desarrollo pueden estar sujetos a condiciones de licencia del proveedor. Por este motivo, la base generada queda ignorada por Git y no debe publicarse hasta confirmar que la licencia permite redistribuir esos datos derivados. Si no existe ese permiso, el repositorio público deberá usar un dataset sintético o un ejemplo con licencia compatible.

## Qué genera

`validate_public_demo.py` crea localmente `publication/output/football_performance_public_demo.duckdb` y valida:

- `TEAM_001` para el equipo principal;
- `OPP_001...` para rivales;
- `PLAYER_001...` para jugadores;
- `MATCH_001...` para partidos;
- nombres públicos coherentes con esos alias;
- conservación exacta del número de filas de las tablas necesarias para la aplicación;
- ausencia de nombres e identificadores originales en las tablas públicas;
- compatibilidad con el dashboard y el motor `expert_0.7.0`;
- mantenimiento del gate seguro N13000.

Tablas incluidas en la demo de presentación:

```text
teams
players
matches
team_match
player_match
player_match_raw_stats
player_match_features
decision_results
```

No se copian los ficheros raw originales de PannaData/Opta ni rutas locales de importación.

## Ejecución

Desde la raíz del repositorio:

```powershell
python publication\validate_public_demo.py
```

No requiere instalar ninguna dependencia nueva respecto al MVP actual.

Para arrancar la web usando la copia anonimizada:

```powershell
$env:FPS_DB_PATH = "$PWD\publication\output\football_performance_public_demo.duckdb"
streamlit run app\streamlit_app.py
```

Al cerrar PowerShell se pierde esa variable de entorno y la aplicación vuelve a utilizar la base configurada por defecto.
