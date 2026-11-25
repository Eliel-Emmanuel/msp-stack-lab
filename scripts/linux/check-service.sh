#!/usr/bin/env bash
# Vérifie qu'un service systemd est actif (par défaut : ssh).
set -uo pipefail

nom="${1:-ssh}"
etat="$(systemctl is-active "$nom" 2>/dev/null || true)"

if [[ "$etat" == "active" ]]; then statut=OK; code=0; else statut=ALERTE; code=1; fi
printf '{"check":"service","cible":"%s","etat":"%s","statut":"%s"}\n' "$nom" "$etat" "$statut"
exit "$code"
