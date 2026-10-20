[CmdletBinding()]
param(
    [ValidateSet('doctor', 'config', 'build', 'verify', 'shell')]
    [string]$Action = 'doctor'
)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
Push-Location $repoRoot
try {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw 'Docker is missing. See docs/windows-setup.md.'
    }
    & docker compose version
    if ($LASTEXITCODE -ne 0) { throw 'Docker Compose v2 or later is required.' }
    $composeArgs = @('compose', '--env-file', '.development', '-f', 'compose/bootstrap.yaml')
    if ($Action -eq 'config') {
        & docker @composeArgs config --quiet
    } else {
        $containerOs = & docker info --format '{{.OSType}}'
        if ($LASTEXITCODE -ne 0) { throw 'Start Docker Desktop with Linux containers. See docs/windows-setup.md.' }
        if ($containerOs -ne 'linux') { throw 'Switch Docker Desktop to Linux containers.' }
        Write-Output "Docker engine: $containerOs"
        switch ($Action) {
            'doctor' { & docker @composeArgs config --quiet }
            'build'  { & docker @composeArgs build }
            'verify' { & docker @composeArgs run --rm -T dev bash tests/common/verify-base.sh }
            'shell'  { & docker @composeArgs run --rm dev bash }
        }
    }
    if ($LASTEXITCODE -ne 0) { throw "Action failed: $Action (exit $LASTEXITCODE)" }
} finally {
    Pop-Location
}
