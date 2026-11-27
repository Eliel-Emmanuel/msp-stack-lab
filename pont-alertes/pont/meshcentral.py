"""Dialogue avec MeshCentral via meshctrl.js (livré avec MeshCentral, même version que le serveur)."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass

from .config import Config


class ErreurMeshCentral(Exception):
    pass


@dataclass(frozen=True)
class Appareil:
    id: str
    nom: str
    connecte: bool
    systeme: str

    @property
    def est_windows(self) -> bool:
        return "windows" in self.systeme.lower()


# Commandes de vérification par famille de système (scripts déployés en phase 2d).
COMMANDE_WINDOWS = (
    "powershell -NoProfile -ExecutionPolicy Bypass -File C:\\HorizonScripts\\check-service.ps1; "
    "powershell -NoProfile -ExecutionPolicy Bypass -File C:\\HorizonScripts\\check-disque.ps1"
)
COMMANDE_LINUX = "/opt/horizon-scripts/check-service.sh ssh; /opt/horizon-scripts/check-disque.sh"


def lire_appareils(sortie_json: str) -> list[Appareil]:
    """Transforme la sortie de `meshctrl ListDevices --json` en liste d'appareils."""
    try:
        brut = json.loads(sortie_json)
    except json.JSONDecodeError as exc:
        raise ErreurMeshCentral(f"réponse ListDevices illisible : {exc}") from exc
    if not isinstance(brut, list):
        raise ErreurMeshCentral("réponse ListDevices inattendue (liste attendue)")
    appareils = []
    for noeud in brut:
        if not isinstance(noeud, dict) or noeud.get("type") != "node" or "_id" not in noeud:
            continue
        appareils.append(
            Appareil(
                id=noeud["_id"],
                nom=noeud.get("name") or noeud["_id"],
                # conn est un champ de bits ; le bit 1 indique que l'agent est connecté
                connecte=bool(int(noeud.get("conn", 0) or 0) & 1),
                systeme=noeud.get("osdesc") or "",
            )
        )
    return appareils


class ClientMeshCentral:
    def __init__(self, config: Config):
        self._config = config

    def _executer(self, arguments: list[str], delai: int) -> str:
        commande = [
            "node", self._config.meshctrl, *arguments,
            "--url", self._config.meshcentral_url,
            "--loginuser", self._config.mesh_utilisateur,
            "--loginpass", self._config.mesh_mot_de_passe,
        ]
        try:
            resultat = subprocess.run(commande, capture_output=True, text=True, timeout=delai, check=False)
        except subprocess.TimeoutExpired as exc:
            raise ErreurMeshCentral(f"{arguments[0]} : pas de réponse après {delai} s") from exc
        except OSError as exc:
            raise ErreurMeshCentral(f"impossible de lancer meshctrl : {exc}") from exc
        if resultat.returncode != 0:
            # On n'affiche jamais la ligne de commande : elle contient le jeton.
            message = (resultat.stderr or resultat.stdout).strip().splitlines()[-1:] or ["sans message"]
            raise ErreurMeshCentral(f"{arguments[0]} a échoué (code {resultat.returncode}) : {message[0]}")
        return resultat.stdout

    def lister_appareils(self) -> list[Appareil]:
        return lire_appareils(self._executer(["ListDevices", "--json"], delai=60))

    def verifier(self, appareil: Appareil) -> str:
        """Lance les scripts de vérification sur l'appareil et renvoie leur sortie brute."""
        if appareil.est_windows:
            arguments = ["RunCommand", "--id", appareil.id, "--powershell", "--reply", "--run", COMMANDE_WINDOWS]
        else:
            arguments = ["RunCommand", "--id", appareil.id, "--reply", "--run", COMMANDE_LINUX]
        return self._executer(arguments, delai=self._config.delai_commande_secondes)
