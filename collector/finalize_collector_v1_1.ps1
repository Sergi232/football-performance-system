$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $PSScriptRoot
$HtmlPath = Join-Path $PSScriptRoot 'data_collector_futbol_v1.html'
$ValidatorPath = Join-Path $PSScriptRoot 'validate_collector_v1.py'
$EntryPath = Join-Path $PSScriptRoot 'data_collector_futbol.html'
$TestPath = Join-Path $Root 'tests\test_collector_contract.py'

if (-not (Test-Path $HtmlPath)) { throw "No se encuentra $HtmlPath" }
$html = Get-Content $HtmlPath -Raw -Encoding UTF8

# Responsive: todos los metadatos siguen accesibles en tablet/móvil.
$oldResponsive = '@media(max-width:1400px){.header-inner{grid-template-columns:1.1fr repeat(3,.7fr)}.header-inner .optional-head{display:none}.collector-grid{grid-template-columns:repeat(3,minmax(190px,1fr))}.capture-sticky{top:77px}}'
$newResponsive = '@media(max-width:1400px){header{position:static}.header-inner{grid-template-columns:repeat(3,minmax(0,1fr))}.brand{grid-column:1/-1}.collector-grid{grid-template-columns:repeat(3,minmax(190px,1fr))}.capture-sticky{top:0}}'
if ($html.Contains($oldResponsive)) { $html = $html.Replace($oldResponsive, $newResponsive) }
$html = $html.Replace('.header-inner>div:not(.brand):nth-of-type(n+4){display:none}', '')

# Labels accesibles para los campos creados dinámicamente.
$mutedCss = '.muted{color:var(--muted);font-size:11px;line-height:1.35}'
$srCss = '.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}'
if (-not $html.Contains($srCss)) {
    if (-not $html.Contains($mutedCss)) { throw 'No se encuentra el anclaje CSS .muted.' }
    $html = $html.Replace($mutedCss, "$mutedCss$srCss")
}

# Evitar elemento interactivo dentro de <summary>.
$oldSummary = @'
  <details class="panel" open>
    <summary><span>Últimas acciones</span><button class="btn-light" onclick="event.preventDefault();undoLast()">↶ Deshacer</button></summary>
    <div class="panel-body"><div class="log" id="eventLog"></div></div>
  </details>
'@
$newSummary = @'
  <details class="panel" open>
    <summary><span>Últimas acciones</span><span class="pill">Historial</span></summary>
    <div class="panel-body"><div class="toolbar" style="margin-bottom:6px"><button class="btn-light" type="button" onclick="undoLast()">↶ Deshacer</button></div><div class="log" id="eventLog"></div></div>
  </details>
'@
if ($html.Contains($oldSummary)) { $html = $html.Replace($oldSummary, $newSummary) }
elseif ($html.Contains('<summary><span>Últimas acciones</span><button')) { throw 'No se ha podido corregir el botón dentro de summary.' }

# Migración segura de estados antiguos y coherencia titular/suplente-minutos.
$oldNormalize = 'function normalizeState(saved){const next=createInitialState();if(!saved)return next;next.meta={...next.meta,...(saved.meta||{})};next.players=(saved.players||next.players).slice(0,25).map((p,i)=>({...createPlayer(i),...p,starter:typeof p.starter==="boolean"?p.starter:(Number(p.minuteIn||0)===0&&Number(p.minuteOut||0)>0),roleChanges:Array.isArray(p.roleChanges)?p.roleChanges:[]}));while(next.players.length<25)next.players.push(createPlayer(next.players.length));next.events=Array.isArray(saved.events)?saved.events:[];return next}'
$intermediateNormalize = 'function normalizeState(saved){const next=createInitialState();if(!saved)return next;next.meta={...next.meta,...(saved.meta||{})};next.players=(saved.players||next.players).slice(0,25).map((p,i)=>{const base=createPlayer(i),hasStarter=typeof p.starter==="boolean",starter=hasStarter?p.starter:(Number(p.minuteIn||0)>0?false:i<11),migrated={...base,...p,starter,roleChanges:Array.isArray(p.roleChanges)?p.roleChanges:[]};if(!starter&&Number(migrated.minuteIn||0)===0&&Number(migrated.minuteOut??90)===90)migrated.minuteIn=90;if(starter&&Number(migrated.minuteIn||0)===90&&Number(migrated.minuteOut??90)===90)migrated.minuteIn=0;return migrated});while(next.players.length<25)next.players.push(createPlayer(next.players.length));next.events=Array.isArray(saved.events)?saved.events:[];return next}'
$newNormalize = 'function normalizeState(saved){const next=createInitialState();if(!saved)return next;next.meta={...next.meta,...(saved.meta||{})};const sourcePlayers=Array.isArray(saved.players)?saved.players:next.players,savedEvents=Array.isArray(saved.events)?saved.events:[],starterCount=sourcePlayers.filter(p=>p&&p.starter===true).length,suspiciousStarterState=savedEvents.length===0&&starterCount>11;next.players=sourcePlayers.slice(0,25).map((p,i)=>{const base=createPlayer(i),hasStarter=typeof p.starter==="boolean",starter=suspiciousStarterState?(Number(p.minuteIn||0)>0?false:i<11):(hasStarter?p.starter:(Number(p.minuteIn||0)>0?false:i<11)),migrated={...base,...p,starter,roleChanges:Array.isArray(p.roleChanges)?p.roleChanges:[]};if(!starter&&Number(migrated.minuteIn||0)===0&&Number(migrated.minuteOut??90)===90)migrated.minuteIn=90;if(starter&&Number(migrated.minuteIn||0)===90&&Number(migrated.minuteOut??90)===90)migrated.minuteIn=0;return migrated});while(next.players.length<25)next.players.push(createPlayer(next.players.length));next.events=savedEvents;return next}'
if ($html.Contains($oldNormalize)) { $html = $html.Replace($oldNormalize, $newNormalize) }
elseif ($html.Contains($intermediateNormalize)) { $html = $html.Replace($intermediateNormalize, $newNormalize) }
elseif (-not $html.Contains($newNormalize)) { throw 'No se reconoce normalizeState; no se modifica a ciegas.' }

$oldStarter = 'function updateStarter(i,v){state.players[i].starter=v==="1";renderAll()}'
$newStarter = 'function updateStarter(i,v){const p=state.players[i],next=v==="1";if(next===p.starter)return;p.starter=next;if(next&&Number(p.minuteIn)===90&&Number(p.minuteOut)===90)p.minuteIn=0;if(!next&&Number(p.minuteIn)===0&&Number(p.minuteOut)===90&&!state.events.some(e=>e.player_id===p.id))p.minuteIn=90;renderAll()}'
if ($html.Contains($oldStarter)) { $html = $html.Replace($oldStarter, $newStarter) }
elseif (-not $html.Contains($newStarter)) { throw 'No se reconoce updateStarter; no se modifica a ciegas.' }

# id/name únicos y label asociado para dorsal, nombre y estado.
$oldRender = 'function renderPlayers(){const list=document.getElementById("playerList");list.innerHTML="";state.players.forEach((p,i)=>{const row=document.createElement("div");row.className="player-row"+(i===activeIndex?" active":"");row.onclick=()=>selectPlayer(i);row.innerHTML=`<input aria-label="Dorsal" type="number" min="0" value="${escapeHtml(p.shirtNumber)}" onclick="event.stopPropagation()" onchange="updateShirt(${i},this.value)"><input aria-label="Jugador" value="${escapeHtml(p.name)}" onclick="event.stopPropagation()" onchange="renamePlayer(${i},this.value)"><select aria-label="Estado" onclick="event.stopPropagation()" onchange="updateStarter(${i},this.value)"><option value="1" ${p.starter?"selected":""}>Titular</option><option value="0" ${!p.starter?"selected":""}>Suplente</option></select><div class="mins">${minutesPlayed(p)}''</div>`;list.appendChild(row)});document.getElementById("playerCount").textContent=state.players.length}'
$newRender = 'function renderPlayers(){const list=document.getElementById("playerList");list.innerHTML="";state.players.forEach((p,i)=>{const row=document.createElement("div");row.className="player-row"+(i===activeIndex?" active":"");row.onclick=()=>selectPlayer(i);const shirtId=`shirt-${p.id}`,nameId=`player-${p.id}`,statusId=`status-${p.id}`;row.innerHTML=`<label class="sr-only" for="${shirtId}">Dorsal de ${escapeHtml(p.name)}</label><input id="${shirtId}" name="${shirtId}" aria-label="Dorsal" autocomplete="off" type="number" min="0" value="${escapeHtml(p.shirtNumber)}" onclick="event.stopPropagation()" onchange="updateShirt(${i},this.value)"><label class="sr-only" for="${nameId}">Nombre del jugador ${i+1}</label><input id="${nameId}" name="${nameId}" aria-label="Jugador" autocomplete="off" value="${escapeHtml(p.name)}" onclick="event.stopPropagation()" onchange="renamePlayer(${i},this.value)"><label class="sr-only" for="${statusId}">Estado de ${escapeHtml(p.name)}</label><select id="${statusId}" name="${statusId}" aria-label="Estado" autocomplete="off" onclick="event.stopPropagation()" onchange="updateStarter(${i},this.value)"><option value="1" ${p.starter?"selected":""}>Titular</option><option value="0" ${!p.starter?"selected":""}>Suplente</option></select><div class="mins">${minutesPlayed(p)}''</div>`;list.appendChild(row)});document.getElementById("playerCount").textContent=state.players.length}'
if ($html.Contains($oldRender)) { $html = $html.Replace($oldRender, $newRender) }
elseif (-not $html.Contains('const shirtId=`shirt-${p.id}`,nameId=`player-${p.id}`,statusId=`status-${p.id}`')) { throw 'No se reconoce renderPlayers; no se modifica a ciegas.' }

$html = $html.Replace('Captura manual v1 ·', 'Captura manual v1.1 ·')
$html = $html.Replace('collector_version:"1.0.0"', 'collector_version:"1.1.0"')
Set-Content -Path $HtmlPath -Value $html -Encoding UTF8

# Validator final V1.1.
$validator = @'
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "collector" / "data_collector_futbol_v1.html"
ENTRY = ROOT / "collector" / "data_collector_futbol.html"
CATALOG = ROOT / "collector" / "event_catalog.json"


def fail(message: str) -> None:
    raise RuntimeError(message)


def main() -> None:
    html = HTML.read_text(encoding="utf-8")
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))

    required = [
        'lang="es"', 'Captura manual v1.1', 'collector_version:"1.1.0"',
        'opponentName', 'shirtNumber', 'starter', 'Titular', 'Suplente',
        "recordEvent('PASS','NORMAL','SUCCESS')", "recordEvent('PASS','LONG','FAIL')",
        "recordEvent('PASS','CROSS','SUCCESS')", "recordEvent('DRIBBLE',null,'FAIL')",
        "recordEvent('SHOT',null,'GOAL')", "recordEvent('SHOT',null,'ON_TARGET')",
        "recordEvent('SHOT',null,'BLOCKED')", "recordEvent('TACKLE',null,'SUCCESS')",
        "recordEvent('TACKLE',null,'FAIL')", "recordEvent('INTERCEPTION',null,null)",
        "recordEvent('BLOCK',null,null)", "recordEvent('CLEARANCE',null,null)",
        "beginFoul('RECEIVED')", "beginFoul('COMMITTED')", "recordEvent('CARD','YELLOW',null)",
        "recordEvent('CARD','RED',null)", "recordEvent('LOSS','OTHER',null)",
        "recordEvent('PENALTY','WON','GOAL')", "recordEvent('PENALTY','CONCEDED','MISSED')",
        "recordTeamSetPiece('CORNER','FOR')", "recordTeamSetPiece('CORNER','AGAINST')",
        "recordEvent('GK','SAVE',null)", "recordEvent('GK','GOAL_CONCEDED',null)",
        "tagLastPass('key_pass')", "tagLastPass('assist')", "second_yellow:true", "set_piece_result",
        "match_second", "video_second", "localStorage", "exportEventsCSV", "exportSummaryCSV",
        "downloadJSON", "undoLast", "recordRoleChange", "recordFormationChange",
        'e.outcome==="GOAL"||e.outcome==="ON_TARGET"', '@media(max-width:620px)', 'min-height:48px',
        'class="sr-only" for="${shirtId}"', 'id="${shirtId}" name="${shirtId}"',
        'id="${nameId}" name="${nameId}"', 'id="${statusId}" name="${statusId}"',
        'suspiciousStarterState=savedEvents.length===0&&starterCount>11',
    ]
    missing = [item for item in required if item not in html]
    if missing:
        fail("Collector V1.1 missing required fragments: " + ", ".join(missing))

    forbidden = [
        ">Passada", ">Llarga", ">Centre", ">Assistència", ">Save<", ">Goal conceded<",
        "Clearance defensivo", "Tackle ganado/perdido", "falta_peligrosa",
        '.header-inner .optional-head{display:none}',
        '.header-inner>div:not(.brand):nth-of-type(n+4){display:none}',
        '<summary><span>Últimas acciones</span><button',
        'function updateStarter(i,v){state.players[i].starter=v==="1";renderAll()}',
    ]
    present = [item for item in forbidden if item in html]
    if present:
        fail("Collector V1.1 contains forbidden/legacy fragments: " + ", ".join(present))

    if catalog.get("catalog_version") != "0.3.0":
        fail(f"Unexpected catalog version: {catalog.get('catalog_version')!r}")

    entry = ENTRY.read_text(encoding="utf-8")
    if "data_collector_futbol_v1.html" not in entry:
        fail("Official collector entrypoint does not point to V1.1 implementation")

    print("COLLECTOR V1.1 FINAL GATE: PASS")
    print("catalog_version=0.3.0")
    print("structured_opponent=PASS")
    print("editable_shirt_number=PASS")
    print("starter_substitute_explicit=PASS")
    print("starter_minutes_consistency_guard=PASS")
    print("shots_on_target_goal_plus_on_target=PASS")
    print("spanish_visible_labels=PASS")
    print("responsive_metadata_access=PASS")
    print("mobile_touch_targets=PASS")
    print("dynamic_form_ids_names_labels=PASS")
    print("summary_interactive_element_guard=PASS")
    print("event_taxonomy_unchanged=PASS")
    print("official_entrypoint=PASS")


if __name__ == "__main__":
    main()
'@
Set-Content -Path $ValidatorPath -Value $validator -Encoding UTF8

# Entrada oficial.
$entry = @'
<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8"><meta http-equiv="refresh" content="0; url=data_collector_futbol_v1.html"><title>Football Performance Collector</title></head><body><p>Abriendo Collector V1.1… <a href="data_collector_futbol_v1.html">Abrir manualmente</a>.</p></body></html>
'@
Set-Content -Path $EntryPath -Value $entry -Encoding UTF8

# El test de contrato valida ya la implementación oficial.
$test = Get-Content $TestPath -Raw -Encoding UTF8
$test = $test.Replace('HTML = ROOT / "collector" / "data_collector_futbol_mvp.html"', 'HTML = ROOT / "collector" / "data_collector_futbol_v1.html"')
Set-Content -Path $TestPath -Value $test -Encoding UTF8

Push-Location $Root
try {
    python .\collector\validate_collector_v1.py
    if ($LASTEXITCODE -ne 0) { throw 'validate_collector_v1.py ha fallado.' }

    python -c "import pytest" 2>$null
    if ($LASTEXITCODE -eq 0) {
        python -m pytest .\tests\test_collector_contract.py -q
        if ($LASTEXITCODE -ne 0) { throw 'test_collector_contract.py ha fallado con pytest.' }
    }
    else {
        Write-Host 'pytest no está instalado; ejecutando los tests de contrato con el runner Python estándar.'
        $fallback = @'
import importlib.util
from pathlib import Path

path = Path("tests/test_collector_contract.py")
spec = importlib.util.spec_from_file_location("test_collector_contract", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
tests = [getattr(module, name) for name in sorted(dir(module)) if name.startswith("test_") and callable(getattr(module, name))]
for test in tests:
    test()
print(f"{len(tests)} collector contract tests: PASS")
'@
        $fallback | python -
        if ($LASTEXITCODE -ne 0) { throw 'test_collector_contract.py ha fallado con el runner estándar.' }
    }

    git diff --check
    if ($LASTEXITCODE -ne 0) { throw 'git diff --check ha fallado.' }

    git add -- collector/data_collector_futbol_v1.html collector/data_collector_futbol.html collector/validate_collector_v1.py tests/test_collector_contract.py
    git diff --cached --quiet
    if ($LASTEXITCODE -eq 0) {
        Write-Host 'No hay cambios nuevos del Collector para confirmar.'
    }
    else {
        git commit -m "Finalize Collector V1.1"
        if ($LASTEXITCODE -ne 0) { throw 'git commit ha fallado.' }
        git push origin main
        if ($LASTEXITCODE -ne 0) { throw 'git push ha fallado.' }
    }

    Write-Host ''
    Write-Host 'COLLECTOR-01 IMPLEMENTACIÓN FINAL: PASS'
    git status --short
}
finally {
    Pop-Location
}
