$ErrorActionPreference = 'Stop'
$python = Get-Command python3,python -ErrorAction SilentlyContinue | Where-Object { $_.Source -notlike '*WindowsApps*' } | Select-Object -First 1
if (-not $python) { Write-Output 'Python 3.10+ is required for the member 5 console.'; exit 1 }
& $python.Source -B "$PSScriptRoot/console.py" @args
exit $LASTEXITCODE
