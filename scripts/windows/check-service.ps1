# Vérifie qu'un service Windows tourne (par défaut : Spooler).
param([string]$Nom = 'Spooler')

$service = Get-Service -Name $Nom -ErrorAction SilentlyContinue
if (-not $service) {
    [pscustomobject]@{ check = 'service'; cible = $Nom; etat = 'absent'; statut = 'ERREUR' } | ConvertTo-Json -Compress
    exit 2
}

$statut = if ($service.Status -eq 'Running') { 'OK' } else { 'ALERTE' }
[pscustomobject]@{ check = 'service'; cible = $Nom; etat = "$($service.Status)"; statut = $statut } | ConvertTo-Json -Compress
if ($statut -eq 'OK') { exit 0 } else { exit 1 }
