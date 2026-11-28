# Remédiation : redémarre un service arrêté puis vérifie son état.
param([string]$Nom = 'Spooler')

try {
    Start-Service -Name $Nom -ErrorAction Stop
    Start-Sleep -Seconds 3
} catch {
    [pscustomobject]@{ action = 'redemarrage'; cible = $Nom; statut = 'ERREUR'; detail = $_.Exception.Message } | ConvertTo-Json -Compress
    exit 2
}

$etat = (Get-Service -Name $Nom).Status
$statut = if ($etat -eq 'Running') { 'OK' } else { 'ECHEC' }
[pscustomobject]@{ action = 'redemarrage'; cible = $Nom; etat = "$etat"; statut = $statut } | ConvertTo-Json -Compress
if ($statut -eq 'OK') { exit 0 } else { exit 1 }
