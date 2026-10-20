#Requires -RunAsAdministrator
[CmdletBinding()]
param(
    [string]$ReportPath = (Join-Path $env:TEMP 'hadoop-windows-components.json')
)
$ErrorActionPreference = 'Stop'
$report = [ordered]@{
    CheckedAt = (Get-Date).ToString('o')
    Success = $false
    RestartRequired = $false
    Features = @()
    HypervisorLaunchChanged = $false
    Error = $null
}
try {
    foreach ($featureName in @('VirtualMachinePlatform', 'Microsoft-Windows-Subsystem-Linux')) {
        $before = Get-WindowsOptionalFeature -Online -FeatureName $featureName
        if ($before.State -eq 'EnablePending') {
            $report.RestartRequired = $true
        } elseif ($before.State -ne 'Enabled') {
            $result = Enable-WindowsOptionalFeature -Online -FeatureName $featureName -All -NoRestart
            if ($result.RestartNeeded) { $report.RestartRequired = $true }
        }
        $after = Get-WindowsOptionalFeature -Online -FeatureName $featureName
        $report.Features += [ordered]@{
            Name = $featureName
            Before = [string]$before.State
            After = [string]$after.State
        }
    }
    # Only change an explicitly disabled boot setting; leave the default alone.
    $bootConfig = & bcdedit.exe /enum '{current}'
    if ($LASTEXITCODE -ne 0) { throw 'Unable to inspect hypervisor boot configuration.' }
    if (($bootConfig -join "`n") -match '(?im)^hypervisorlaunchtype\s+Off\s*$') {
        & bcdedit.exe /set hypervisorlaunchtype Auto
        if ($LASTEXITCODE -ne 0) { throw 'Unable to enable hypervisor launch.' }
        $report.HypervisorLaunchChanged = $true
        $report.RestartRequired = $true
    }
    $report.Success = $true
} catch {
    $report.Error = $_.Exception.Message
} finally {
    $report | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $ReportPath -Encoding UTF8
}
if (-not $report.Success) { Write-Error $report.Error; exit 1 }
Write-Output "Windows components prepared. Restart required: $($report.RestartRequired)"
Write-Output "Report: $ReportPath"
# Deliberately no Restart-Computer; the user chooses when to reboot.
