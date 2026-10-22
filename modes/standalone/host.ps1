param(
    [string]$Mode,
    [string]$Action = 'doctor',
    [string]$RunId = '',
    [Parameter(ValueFromRemainingArguments=$true)][string[]]$Extra
)
$ErrorActionPreference = 'Stop'
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$actions = @('doctor', 'run', 'verify', 'shell', 'test')
if ($Mode -eq 'pseudo') { $actions += @('init', 'up', 'status', 'logs', 'restart', 'stop', 'down') }
if ($Mode -notin @('standalone', 'pseudo') -or $Action -notin $actions -or $Extra.Count -gt 0) {
    Write-Output 'Usage: manage.ps1 <doctor|run|verify|shell|test|init|up|status|logs|restart|stop|down> [run-id]'
    exit 2
}
if ($Action -in @('run', 'verify')) {
    if ($RunId -cnotmatch '^[a-zA-Z0-9_-]+$') { Write-Output 'Invalid or missing run-id.'; exit 2 }
} elseif ($RunId) { Write-Output 'Unexpected run-id.'; exit 2 }
$project = "hadoop-m5-$Mode"
$compose = @('compose', '--env-file', (Join-Path $repo '.development'), '-f',
    (Join-Path $repo "modes/$Mode/compose.yaml"), '-p', $project)
$runtime = Join-Path $repo 'runtime/member5'
New-Item -ItemType Directory -Force (Join-Path $runtime 'standalone') | Out-Null
New-Item -ItemType Directory -Force (Join-Path $runtime "$Mode/control") | Out-Null
$log = Join-Path $runtime ("$Mode/control/" + [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfff') + '-' + [guid]::NewGuid().ToString('N').Substring(0,8) + '.log')

function Invoke-M5Docker([string[]]$DockerArgs) {
    # Windows PowerShell reports native stderr as ErrorRecords even on success.
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    & docker @DockerArgs 2>&1 | ForEach-Object { $_.ToString() } | Tee-Object -FilePath $log -Append | Out-Host
    $nativeCode = $LASTEXITCODE
    $ErrorActionPreference = $previousPreference
    if ($nativeCode -ne 0) { throw "Docker command failed (exit $nativeCode). Evidence: $log" }
}
function Invoke-M5Compose([string[]]$ComposeArgs) { Invoke-M5Docker ($compose + $ComposeArgs) }
function Wait-M5Pseudo {
    try { Invoke-M5Compose @('up', '-d', '--no-build', '--wait', '--wait-timeout', '180', 'pseudo') }
    catch {
        $failure = $_
        try { Invoke-M5Compose @('ps', '-a'); Invoke-M5Compose @('logs', '--no-color', '--tail', '100', 'pseudo') } catch {}
        throw $failure
    }
}
try {
    if ($Action -eq 'test') {
        $python = Get-Command python3,python -ErrorAction SilentlyContinue | Where-Object { $_.Source -notlike '*WindowsApps*' } | Select-Object -First 1
        if (-not $python) { throw 'Python 3 is required only for automated tests.' }
        & $python.Source (Join-Path $repo "tests/$Mode/check-$Mode.py")
        exit $LASTEXITCODE
    }
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Docker is missing.' }
    $os = & docker info --format '{{.OSType}}'
    if ($LASTEXITCODE -ne 0 -or $os -ne 'linux') { throw 'Start Docker Desktop with Linux containers.' }
    Invoke-M5Compose @('config', '--quiet')
    switch ($Action) {
        doctor {
            Invoke-M5Docker @('compose', 'version')
            Invoke-M5Docker @('image', 'inspect', 'hadoop-base:v0.1', '--format', '{{.Id}}')
            Write-Output "DOCTOR_PASS mode=$Mode project=$project"
        }
        run {
            if ($Mode -eq 'standalone') { Invoke-M5Compose @('run', '--rm', '-T', '--no-deps', 'standalone', 'bash', '/workspace/modes/standalone/run.sh', $RunId) }
            else { Invoke-M5Compose @('exec', '-T', 'pseudo', 'bash', '/workspace/modes/pseudo/run.sh', $RunId) }
        }
        verify {
            if ($Mode -eq 'standalone') { Invoke-M5Compose @('run', '--rm', '-T', '--no-deps', 'standalone', 'bash', '/workspace/modes/standalone/verify.sh', $RunId) }
            else { Invoke-M5Compose @('exec', '-T', 'pseudo', 'bash', '/workspace/modes/pseudo/verify.sh', $RunId) }
        }
        shell {
            if ($Mode -eq 'standalone') { & docker @compose run --rm standalone bash }
            else { & docker @compose exec pseudo bash }
            if ($LASTEXITCODE -ne 0) { throw 'Shell command failed.' }
        }
        init {
            $running = @(& docker ps --filter "label=com.docker.compose.project=$project" --format '{{.ID}}')
            if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect running containers.' }
            if ($running.Count -gt 0) { throw 'Pseudo services or initialization already running; stop before init.' }
            Invoke-M5Compose @('run', '--rm', '-T', '--no-deps', 'pseudo', 'bash', '/workspace/modes/pseudo/node.sh', 'init')
        }
        up { Wait-M5Pseudo }
        restart { Invoke-M5Compose @('restart', 'pseudo'); Wait-M5Pseudo }
        status {
            Invoke-M5Compose @('ps', '-a')
            Invoke-M5Compose @('exec', '-T', 'pseudo', 'bash', '/workspace/modes/pseudo/healthcheck.sh')
            Invoke-M5Compose @('exec', '-T', 'pseudo', 'jps')
        }
        logs { Invoke-M5Compose @('logs', '--no-color', '--tail', '200', 'pseudo') }
        stop { Invoke-M5Compose @('stop', 'pseudo') }
        down { Invoke-M5Compose @('down') }
    }
    Write-Output "Evidence: $log"
    exit 0
} catch {
    Write-Output "FAIL: $($_.Exception.Message)"
    exit 1
}
