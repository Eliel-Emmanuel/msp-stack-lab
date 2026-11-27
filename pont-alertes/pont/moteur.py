"""Un cycle de supervision : appareils -> vérifications -> tickets.

Le moteur ne dépend que d'interfaces simples (lister_appareils, verifier,
creer_ticket), ce qui permet de le tester sans MeshCentral ni osTicket.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Protocol

from .analyse import Resultat, lire_resultats
from .etat import Etat
from .meshcentral import Appareil

journal = logging.getLogger("pont.moteur")


class SourceAppareils(Protocol):
    def lister_appareils(self) -> list[Appareil]: ...
    def verifier(self, appareil: Appareil) -> str: ...


class Billetterie(Protocol):
    def creer_ticket(self, sujet: str, message: str) -> str: ...


def _horodatage(instant: float) -> str:
    return datetime.fromtimestamp(instant, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def message_alerte(appareil: Appareil, resultat: Resultat, instant: float) -> str:
    return (
        f"Alerte détectée automatiquement par le pont de supervision.\n\n"
        f"Appareil : {appareil.nom}\n"
        f"Système : {appareil.systeme or 'inconnu'}\n"
        f"Vérification : {resultat.check} ({resultat.cible})\n"
        f"Statut : {resultat.statut}\n"
        f"Détecté le : {_horodatage(instant)}\n\n"
        f"Résultat brut du script :\n{json.dumps(resultat.donnees, ensure_ascii=False)}\n\n"
        f"Ticket créé par le pont d'alertes MeshCentral -> osTicket. "
        f"Diagnostic et remédiation à effectuer via MeshCentral (groupe Horizon Conseil)."
    )


def message_hors_ligne(appareil: Appareil, depuis: float, instant: float) -> str:
    minutes = int((instant - depuis) // 60)
    return (
        f"Appareil injoignable détecté automatiquement par le pont de supervision.\n\n"
        f"Appareil : {appareil.nom}\n"
        f"Système : {appareil.systeme or 'inconnu'}\n"
        f"Hors ligne depuis : {_horodatage(depuis)} (environ {minutes} min)\n\n"
        f"L'agent MeshCentral ne répond plus. Vérifier l'alimentation, le réseau "
        f"et le service « Mesh Agent » de la machine."
    )


class Moteur:
    def __init__(self, source: SourceAppareils, billetterie: Billetterie, etat: Etat, delai_hors_ligne: int):
        self.source = source
        self.billetterie = billetterie
        self.etat = etat
        self.delai_hors_ligne = delai_hors_ligne

    # ------------------------------------------------------------------ cycle
    def cycle(self, instant: float) -> list[str]:
        """Exécute un cycle complet. Renvoie les numéros des tickets créés."""
        crees: list[str] = []
        appareils = self.source.lister_appareils()
        ids_presents = {a.id for a in appareils}

        for appareil in appareils:
            if appareil.connecte:
                self._retour_en_ligne(appareil)
                crees.extend(self._verifier(appareil, instant))
            else:
                ticket = self._hors_ligne(appareil, instant)
                if ticket:
                    crees.append(ticket)

        # Appareils retirés de MeshCentral : on oublie leur suivi hors ligne.
        for nodeid in list(self.etat.hors_ligne):
            if nodeid not in ids_presents:
                del self.etat.hors_ligne[nodeid]
        return crees

    # ------------------------------------------------------------ hors ligne
    def _hors_ligne(self, appareil: Appareil, instant: float) -> str | None:
        suivi = self.etat.hors_ligne.setdefault(
            appareil.id, {"depuis": instant, "ticket": None, "appareil": appareil.nom}
        )
        if suivi["ticket"] is not None:
            return None
        duree = instant - suivi["depuis"]
        if duree < self.delai_hors_ligne:
            journal.info("%s hors ligne depuis %d s (seuil %d s)", appareil.nom, duree, self.delai_hors_ligne)
            return None
        sujet = f"[HORS LIGNE] {appareil.nom} injoignable depuis plus de {self.delai_hors_ligne // 60} min"
        ticket = self._creer(sujet, message_hors_ligne(appareil, suivi["depuis"], instant))
        if ticket:
            suivi["ticket"] = ticket
        return ticket

    def _retour_en_ligne(self, appareil: Appareil) -> None:
        suivi = self.etat.hors_ligne.pop(appareil.id, None)
        if suivi and suivi.get("ticket"):
            journal.info("%s de nouveau en ligne (ticket #%s à clôturer par le technicien)",
                         appareil.nom, suivi["ticket"])

    # --------------------------------------------------------- vérifications
    def _verifier(self, appareil: Appareil, instant: float) -> list[str]:
        try:
            sortie = self.source.verifier(appareil)
        except Exception as exc:  # une machine en échec ne doit pas bloquer les autres
            journal.warning("vérification impossible sur %s : %s", appareil.nom, exc)
            return []

        resultats = lire_resultats(sortie)
        if not resultats:
            journal.warning("aucun résultat exploitable renvoyé par %s (scripts absents ?)", appareil.nom)
            return []

        crees = []
        for resultat in resultats:
            cle = Etat.cle(appareil.id, resultat.check, resultat.cible)
            deja = self.etat.alertes.get(cle)
            if resultat.en_defaut and deja is None:
                sujet = f"[ALERTE] {appareil.nom} - {resultat.resume()}"
                ticket = self._creer(sujet, message_alerte(appareil, resultat, instant))
                if ticket:
                    self.etat.alertes[cle] = {
                        "ticket": ticket, "depuis": instant,
                        "appareil": appareil.nom, "resume": resultat.resume(),
                    }
                    crees.append(ticket)
            elif resultat.en_defaut:
                journal.info("%s : %s, déjà signalé (ticket #%s)", appareil.nom, resultat.resume(), deja["ticket"])
            elif deja is not None:
                del self.etat.alertes[cle]
                journal.info("%s : %s rétabli (ticket #%s à clôturer par le technicien)",
                             appareil.nom, resultat.resume(), deja["ticket"])
        return crees

    # ---------------------------------------------------------------- outils
    def _creer(self, sujet: str, message: str) -> str | None:
        try:
            ticket = self.billetterie.creer_ticket(sujet, message)
        except Exception as exc:
            # Pas d'enregistrement dans l'état : le ticket sera retenté au cycle suivant.
            journal.error("création du ticket « %s » impossible : %s", sujet, exc)
            return None
        journal.warning("ticket #%s créé : %s", ticket, sujet)
        return ticket
