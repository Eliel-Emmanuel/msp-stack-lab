# Vérifie l'espace libre des disques locaux. Alerte sous le seuil (EF : < 15 %).
param([int]$SeuilPourcent = 15)

$resultats = Get-CimInstance Win32_LogicalDisk -Filter "DriveType=3" | ForEach-Object {
    $libre = [math]::Round(100 * $_.FreeSpace / $_.Size, 1)
    [pscustomobject]@{
        check     = 'disque'
        cible     = $_.DeviceID
        libre_pct = $libre
        statut    = if ($libre -lt $SeuilPourcent) { 'ALERTE' } else { 'OK' }
    }
}

$resultats | ForEach-Object { $_ | ConvertTo-Json -Compress }
if ($resultats.statut -contains 'ALERTE') { exit 1 } else { exit 0 }
