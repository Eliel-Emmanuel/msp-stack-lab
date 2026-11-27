"""Création de tickets via l'API d'osTicket (POST /api/tickets.json)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from .config import Config


class ErreurOsTicket(Exception):
    pass


def construire_requete(config: Config, sujet: str, message: str) -> urllib.request.Request:
    corps = {
        "name": config.demandeur_nom,
        "email": config.demandeur_email,
        "subject": sujet,
        "message": "data:text/plain;charset=utf-8," + message,
        "topicId": config.osticket_topic_id,
        "source": "API",
        "alert": True,          # prévient les techniciens du département
        "autorespond": False,   # pas d'accusé de réception vers l'adresse de supervision
    }
    return urllib.request.Request(
        config.osticket_url,
        data=json.dumps(corps, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={
            "X-API-Key": config.osticket_cle_api,
            # La requête arrive en HTTP interne : on indique à osTicket qu'elle est
            # considérée comme sécurisée, sinon « Force HTTPS » répond par un 302.
            "X-Forwarded-Proto": "https",
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "pont-alertes/1.0",
        },
    )


class ClientOsTicket:
    def __init__(self, config: Config, delai: int = 30):
        self._config = config
        self._delai = delai

    def creer_ticket(self, sujet: str, message: str) -> str:
        """Crée le ticket et renvoie son numéro."""
        requete = construire_requete(self._config, sujet, message)
        try:
            with urllib.request.urlopen(requete, timeout=self._delai) as reponse:
                statut = reponse.status
                corps = reponse.read().decode("utf-8", errors="replace").strip()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace").strip()[:200]
            raise ErreurOsTicket(f"HTTP {exc.code} : {detail or exc.reason}") from exc
        except (urllib.error.URLError, OSError) as exc:
            raise ErreurOsTicket(f"osTicket injoignable : {exc}") from exc
        if statut != 201 or not corps:
            raise ErreurOsTicket(f"réponse inattendue (HTTP {statut}) : {corps[:200]}")
        return corps
