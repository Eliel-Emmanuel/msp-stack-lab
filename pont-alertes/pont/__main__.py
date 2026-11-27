"""Point d'entrée : boucle de supervision (python -m pont)."""

from __future__ import annotations

import logging
import signal
import sys
import threading
import time
from pathlib import Path

from . import __version__
from .config import Config, ConfigurationInvalide
from .etat import Etat
from .meshcentral import ClientMeshCentral
from .moteur import Moteur
from .osticket import ClientOsTicket

journal = logging.getLogger("pont")


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s : %(message)s",
        stream=sys.stdout,
    )
    try:
        config = Config.depuis_env()
        config.valider()
    except ConfigurationInvalide as exc:
        journal.critical("configuration invalide : %s", exc)
        return 2

    arret = threading.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: arret.set())

    journal.info(
        "pont d'alertes %s démarré : cycle toutes les %d s, seuil hors ligne %d s",
        __version__, config.intervalle_secondes, config.delai_hors_ligne_secondes,
    )

    while not arret.is_set():
        debut = time.time()
        etat = Etat.charger(config.fichier_etat)
        moteur = Moteur(
            source=ClientMeshCentral(config),
            billetterie=ClientOsTicket(config),
            etat=etat,
            delai_hors_ligne=config.delai_hors_ligne_secondes,
        )
        try:
            crees = moteur.cycle(debut)
            etat.enregistrer(config.fichier_etat)
            Path(config.fichier_battement).write_text(str(int(time.time())), encoding="utf-8")
            journal.info(
                "cycle terminé en %.1f s : %d ticket(s) créé(s), %d alerte(s) ouverte(s), %d appareil(s) hors ligne",
                time.time() - debut, len(crees), len(etat.alertes), len(etat.hors_ligne),
            )
        except Exception:
            # Pas de battement écrit : le healthcheck signalera un pont bloqué.
            journal.exception("cycle en échec")
        arret.wait(config.intervalle_secondes)

    journal.info("arrêt demandé, pont d'alertes arrêté proprement")
    return 0


if __name__ == "__main__":
    sys.exit(main())
