param(
    [ValidateNotNullOrEmpty()]
    [string]$Project = "hadoop-distributed-recovery"
)

$ErrorActionPreference = "Stop"

# Locate the repository from this script's directory.
$repoRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
Push-Location $repoRoot

try {
    $composeArgs = @(
        "compose",
        "--env-file", ".development",
        "-p", $Project,
        "-f", "compose/distributed.yaml"
    )

    & docker @composeArgs config --quiet
    if ($LASTEXITCODE -ne 0) {
        throw "Compose configuration check failed"
    }

    $nodes = @("master", "worker1", "worker2")

    foreach ($node in $nodes) {
        $actual = & docker @composeArgs exec -T $node hostname
        if ($LASTEXITCODE -ne 0) {
            throw "$node is not accessible"
        }
        if (("$actual").Trim() -ne $node) {
            throw "$node hostname mismatch: $actual"
        }

        foreach ($peer in $nodes) {
            if ($peer -eq $node) {
                continue
            }
            & docker @composeArgs exec -T $node getent hosts $peer
            if ($LASTEXITCODE -ne 0) {
                throw "$node cannot resolve $peer"
            }
        }

        $uid = & docker @composeArgs exec -T $node id -u
        if ($LASTEXITCODE -ne 0) {
            throw "$node user check failed"
        }
        if (("$uid").Trim() -ne "1000") {
            throw "$node must run as UID 1000"
        }

        & docker @composeArgs exec -T $node test -w /var/lib/hadoop
        if ($LASTEXITCODE -ne 0) {
            throw "$node data directory is not writable"
        }

        Write-Host "PASS: $node hostname, DNS, UID and volume permissions"
    }

    Write-Host "SKELETON_CHECK_PASS"
    Write-Host "Scope: container skeleton only; HDFS/YARN are not tested."
}
catch {
    [Console]::Error.WriteLine($_.Exception.Message)
    exit 1
}
finally {
    Pop-Location
}
