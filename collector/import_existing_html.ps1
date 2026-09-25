param(
    [switch]$Push
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Target = Join-Path $PSScriptRoot "data_collector_futbol.html"

$Roots = @(
    (Join-Path $HOME "Desktop"),
    (Join-Path $HOME "Downloads"),
    (Join-Path $HOME "OneDrive")
) | Where-Object { Test-Path $_ }

$PreferredNames = @(
    "data_collector_futbol_fijo_compacto.html",
    "data_collector_futbol_compacto.html",
    "data_collector_futbol.html"
)

$candidates = foreach ($root in $Roots) {
    Get-ChildItem -Path $root -File -Recurse -Filter "data_collector_futbol*.html" -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -ne $Target }
}

if (-not $candidates) {
    Write-Host "No s'ha trobat cap data_collector_futbol*.html a Desktop, Downloads o OneDrive."
    exit 2
}

$ranked = $candidates | ForEach-Object {
    $nameRank = [array]::IndexOf($PreferredNames, $_.Name)
    if ($nameRank -lt 0) { $nameRank = 999 }
    [PSCustomObject]@{
        File = $_
        NameRank = $nameRank
        LastWriteTime = $_.LastWriteTime
    }
} | Sort-Object NameRank, @{Expression="LastWriteTime";Descending=$true}

Write-Host "Candidats trobats:"
$ranked | ForEach-Object {
    Write-Host ("  [{0}] {1}  ({2})" -f $_.NameRank, $_.File.FullName, $_.LastWriteTime)
}

$chosen = $ranked[0].File
Copy-Item -LiteralPath $chosen.FullName -Destination $Target -Force
Write-Host ""
Write-Host "Collector importat a: $Target"
Write-Host "Origen: $($chosen.FullName)"

if ($Push) {
    Push-Location $RepoRoot
    try {
        git add -- "collector/data_collector_futbol.html"
        if ($LASTEXITCODE -ne 0) { throw "git add ha fallat." }

        $status = git status --porcelain -- "collector/data_collector_futbol.html"
        if ($status) {
            git -c user.name="Sergi232" -c user.email="215590015+Sergi232@users.noreply.github.com" commit -m "Import existing data collector prototype"
            if ($LASTEXITCODE -ne 0) { throw "git commit ha fallat; l'HTML NO s'ha pujat." }

            git push origin main
            if ($LASTEXITCODE -ne 0) { throw "git push ha fallat; el commit existeix només en local." }

            Write-Host "HTML pujat correctament a GitHub."
        } else {
            Write-Host "L'HTML ja coincideix amb la versio del repositori; no cal commit."
        }
    }
    finally {
        Pop-Location
    }
} else {
    Write-Host "Per pujar-lo directament a GitHub, torna a executar amb -Push."
}
