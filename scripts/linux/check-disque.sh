#!/usr/bin/env bash
# Vérifie l'espace libre des systèmes de fichiers locaux. Alerte sous le seuil (EF : < 15 %).
# Sortie : une ligne JSON par système de fichiers. Code : 0 = OK, 1 = alerte.
set -euo pipefail

seuil="${1:-15}"
code=0

while read -r cible taille dispo; do
    [[ "$taille" -gt 0 ]] || continue
    [[ "$cible" == "/init" ]] && continue   # artefact WSL, pas un vrai disque
    libre=$(( 100 * dispo / taille ))
    statut=OK
    if (( libre < seuil )); then statut=ALERTE; code=1; fi
    printf '{"check":"disque","cible":"%s","libre_pct":%d,"statut":"%s"}\n' "$cible" "$libre" "$statut"
done < <(df -B1 -x tmpfs -x devtmpfs -x overlay -x squashfs -x 9p -x drvfs \
            --output=target,size,avail | tail -n +2)

exit "$code"
