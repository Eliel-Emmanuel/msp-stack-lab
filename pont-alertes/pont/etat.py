"""État persistant du pont : alertes déjà signalées et appareils hors ligne.

Le fichier survit aux redémarrages du conteneur (volume Docker), ce qui évite
de recréer un ticket pour un problème déjà signalé.
"""

from __future__ import annotations

import json
import os
import tempfile
from typing import Any


class Etat:
    def __init__(self, alertes: dict[str, dict] | None = None, hors_ligne: dict[str, dict] | None = None):
        # clé "nodeid|check|cible" -> {"ticket": "123456", "depuis": 1700000000, "appareil": "...", "resume": "..."}
        self.alertes: dict[str, dict[str, Any]] = alertes or {}
        # nodeid -> {"depuis": 1700000000, "ticket": "123456" | None, "appareil": "..."}
        self.hors_ligne: dict[str, dict[str, Any]] = hors_ligne or {}

    @staticmethod
    def cle(nodeid: str, check: str, cible: str) -> str:
        return f"{nodeid}|{check}|{cible}"

    def vers_dict(self) -> dict:
        return {"version": 1, "alertes": self.alertes, "hors_ligne": self.hors_ligne}

    @classmethod
    def charger(cls, chemin: str) -> "Etat":
        try:
            with open(chemin, encoding="utf-8") as f:
                brut = json.load(f)
        except FileNotFoundError:
            return cls()
        except (OSError, json.JSONDecodeError):
            # Fichier illisible : on repart d'un état vide plutôt que de bloquer
            # la supervision. Au pire, une alerte en cours sera re-signalée une fois.
            return cls()
        return cls(alertes=dict(brut.get("alertes", {})), hors_ligne=dict(brut.get("hors_ligne", {})))

    def enregistrer(self, chemin: str) -> None:
        """Écriture atomique : fichier temporaire puis renommage."""
        dossier = os.path.dirname(chemin) or "."
        os.makedirs(dossier, exist_ok=True)
        fd, temporaire = tempfile.mkstemp(dir=dossier, prefix=".etat-", suffix=".json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(self.vers_dict(), f, ensure_ascii=False, indent=2, sort_keys=True)
            os.replace(temporaire, chemin)
        except BaseException:
            if os.path.exists(temporaire):
                os.unlink(temporaire)
            raise
