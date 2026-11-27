"""Lecture des sorties JSON des scripts de vérification (contrat de la phase 2d).

Chaque script écrit une ligne JSON par élément vérifié, par exemple :
    {"check":"service","cible":"Spooler","etat":"Stopped","statut":"ALERTE"}
    {"check":"disque","cible":"C:","libre_pct":14,"statut":"ALERTE"}
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

STATUTS_CONNUS = {"OK", "ALERTE", "ERREUR"}


@dataclass(frozen=True)
class Resultat:
    check: str
    cible: str
    statut: str
    donnees: dict = field(default_factory=dict, compare=False, hash=False)

    @property
    def en_defaut(self) -> bool:
        return self.statut != "OK"

    def resume(self) -> str:
        """Texte court pour l'objet du ticket."""
        if self.check == "disque" and "libre_pct" in self.donnees:
            return f"disque {self.cible} : {self.donnees['libre_pct']} % libre"
        if self.check == "service" and "etat" in self.donnees:
            return f"service {self.cible} : {self.donnees['etat']}"
        return f"{self.check} {self.cible} : {self.statut}"


def lire_resultats(sortie: str) -> list[Resultat]:
    """Extrait les résultats valides d'une sortie brute.

    Les lignes qui ne sont pas du JSON, ou qui ne respectent pas le contrat
    (champs check / cible / statut), sont ignorées : un script peut afficher
    des messages parasites sans faire échouer le pont.
    """
    resultats: list[Resultat] = []
    for ligne in sortie.splitlines():
        ligne = ligne.strip().lstrip("﻿")
        if not ligne.startswith("{"):
            continue
        try:
            objet = json.loads(ligne)
        except json.JSONDecodeError:
            continue
        if not isinstance(objet, dict):
            continue
        check, cible, statut = objet.get("check"), objet.get("cible"), objet.get("statut")
        if not (isinstance(check, str) and isinstance(cible, str) and isinstance(statut, str)):
            continue
        statut = statut.upper()
        if statut not in STATUTS_CONNUS:
            continue
        resultats.append(Resultat(check=check, cible=cible, statut=statut, donnees=objet))
    return resultats
