#Requires -Version 5.1
<#
Read-only collector for Windows 10/11 and Server with NetTCPIP/NetSecurity.
No settings are changed. Do not commit the resulting snapshot to a public repo.
#>
[CmdletBinding()]
param(
    [string]$OutputPath = (Join-Path $PSScriptRoot 'reports/current.json'),
    [ValidatePattern('^[A-Za-z0-9_-]+$')]
    [string[]]$ServiceName = @('Dnscache', 'W32Time', 'Spooler')
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$snapshot = [ordered]@{
    schema_version = 1
    host = $env:COMPUTERNAME
    platform = 'windows'
    timestamp = [DateTime]::UtcNow.ToString('o')
    service_scope = @($ServiceName | Sort-Object -Unique)
    coverage = [ordered]@{}
    errors = @()
}
$adapters = @()
try {
    $adapters = @(Get-NetAdapter -IncludeHidden | Sort-Object InterfaceGuid)
    $allAddresses = @(Get-NetIPAddress -AddressFamily IPv4)
    $allRoutes = @(Get-NetRoute | Where-Object { $_.DestinationPrefix -in @('0.0.0.0/0', '::/0') })
    $section = [ordered]@{}
    foreach ($adapter in $adapters) {
        $index = $adapter.ifIndex
        $addresses = @($allAddresses | Where-Object { $_.InterfaceIndex -eq $index } | Sort-Object IPAddress | ForEach-Object { "$($_.IPAddress)/$($_.PrefixLength)" })
        $routes = @($allRoutes | Where-Object { $_.InterfaceIndex -eq $index } | Sort-Object DestinationPrefix, NextHop, RouteMetric | ForEach-Object {
            [ordered]@{ destination = $_.DestinationPrefix; next_hop = $_.NextHop; metric = [int]$_.RouteMetric }
        })
        $section[[string]$adapter.InterfaceGuid] = [ordered]@{
            alias = [string]$adapter.Name
            status = [string]$adapter.Status
            ipv4 = @($addresses)
            default_routes = @($routes)
        }
    }
    $snapshot['interfaces'] = $section
    $snapshot.coverage['interfaces'] = 'ok'
} catch {
    $snapshot.coverage['interfaces'] = 'error'
    $snapshot.errors += "interfaces: $($_.Exception.Message)"
}
try {
    # Recollect adapters independently if the previous section failed early.
    $dnsAdapters = @(Get-NetAdapter -IncludeHidden | Sort-Object InterfaceGuid)
    $section = [ordered]@{}
    foreach ($adapter in $dnsAdapters) {
        $entries = @(Get-DnsClientServerAddress -InterfaceIndex $adapter.ifIndex)
        $value = [ordered]@{}
        foreach ($entry in $entries) {
            $value[[string]$entry.AddressFamily] = @($entry.ServerAddresses)
        }
        $section[[string]$adapter.InterfaceGuid] = $value
    }
    $snapshot['dns'] = $section
    $snapshot.coverage['dns'] = 'ok'
} catch {
    $snapshot.coverage['dns'] = 'error'
    $snapshot.errors += "dns: $($_.Exception.Message)"
}
try {
    $section = [ordered]@{}
    foreach ($profile in @(Get-NetFirewallProfile -PolicyStore ActiveStore | Sort-Object Name)) {
        $section[[string]$profile.Name] = [ordered]@{ enabled = [string]$profile.Enabled }
    }
    $snapshot['firewall'] = $section
    $snapshot.coverage['firewall'] = 'ok'
} catch {
    $snapshot.coverage['firewall'] = 'error'
    $snapshot.errors += "firewall: $($_.Exception.Message)"
}
try {
    $section = [ordered]@{}
    foreach ($name in @($ServiceName | Sort-Object -Unique)) {
        $service = Get-CimInstance -ClassName Win32_Service -Filter "Name='$name'"
        if ($null -eq $service) { throw "Requested service '$name' was not found" }
        $section[$name] = [ordered]@{ state = [string]$service.State; start_mode = [string]$service.StartMode }
    }
    $snapshot['services'] = $section
    $snapshot.coverage['services'] = 'ok'
} catch {
    $snapshot.coverage['services'] = 'error'
    $snapshot.errors += "services: $($_.Exception.Message)"
}
$absoluteOutput = [System.IO.Path]::GetFullPath($OutputPath)
$null = New-Item -ItemType Directory -Path (Split-Path -Parent $absoluteOutput) -Force
$snapshot | ConvertTo-Json -Depth 15 | Set-Content -LiteralPath $absoluteOutput -Encoding UTF8
Write-Output "Snapshot written: $absoluteOutput"
if (@($snapshot.coverage.Values | Where-Object { $_ -eq 'error' }).Count -gt 0) { exit 2 }
