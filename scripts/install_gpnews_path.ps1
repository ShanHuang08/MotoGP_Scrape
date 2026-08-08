[CmdletBinding(SupportsShouldProcess = $true)]
param()

$projectRoot = Split-Path -Parent $PSScriptRoot
$binPath = [System.IO.Path]::GetFullPath((Join-Path $projectRoot "bin"))
$currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
$pathEntries = @($currentPath -split ";" | Where-Object { $_.Trim() })

$alreadyInstalled = $pathEntries | Where-Object {
    $entry = $_.Trim().TrimEnd("\")
    $candidate = $binPath.TrimEnd("\")
    [string]::Equals($entry, $candidate, [System.StringComparison]::OrdinalIgnoreCase)
}

if ($alreadyInstalled) {
    Write-Host "gpnews is already on PATH: $binPath"
    exit 0
}

$newPath = (($pathEntries + $binPath) -join ";")
if ($PSCmdlet.ShouldProcess("User PATH", "Add $binPath")) {
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
    Write-Host "Added gpnews to PATH: $binPath"
    Write-Host "Open a new PowerShell window, then run: gpnews --help"
}
