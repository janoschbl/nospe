param(
    [string]$OutputDir = (Join-Path $PSScriptRoot "..\dist\emulator")
)

$backendRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$workDir = Join-Path $backendRoot "build\pyinstaller-emulator"

Push-Location $backendRoot
try {
    uv run pyinstaller --clean --noconfirm `
        --distpath $OutputDir `
        --workpath $workDir `
        nospe_emulator.spec
}
finally {
    Pop-Location
}
