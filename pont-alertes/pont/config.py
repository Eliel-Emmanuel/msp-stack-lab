"""Configuration du pont, lue uniquement depuis les variables d'environnement."""

from __future__ import annotations

import os
from dataclasses import dataclass


class ConfigurationInvalide(Exception):
    """Une variable obligatoire manque ou une valeur est incorrecte."""


def _obligatoire(env: dict[str, str], nom: str) -> str:
    valeur = env.get(nom, "").strip()
    if not valeur:
        raise ConfigurationInvalide(f"variable d'environnement obligatoire manquante : {nom}")
    return valeur


def _entier(env: dict[str, str], nom: str, defaut: int, minimum: int = 1) -> int:
    brut = env.get(nom, "").strip()
    if not brut:
        return defaut
    try:
        valeur = int(brut)
    except ValueError as exc:
        raise ConfigurationInvalide(f"{nom} doit être un entier (reçu : {brut!r})") from exc
    if valeur < minimum:
        raise ConfigurationInvalide(f"{nom} doit être supérieur ou égal à {minimum}")
    return valeur


@dataclass(frozen=True)
class Config:
    meshctrl: str
    meshcentral_url: str
    mesh_utilisateur: str
    mesh_mot_de_passe: str
    osticket_url: str
    osticket_cle_api: str
    osticket_topic_id: int
    demandeur_nom: str
    demandeur_email: str
    intervalle_secondes: int
    delai_hors_ligne_secondes: int
    delai_commande_secondes: int
    fichier_etat: str
    fichier_battement: str

    @classmethod
    def depuis_env(cls, env: dict[str, str] | None = None) -> "Config":
        env = dict(os.environ if env is None else env)
        return cls(
            meshctrl=env.get("MESHCTRL", "/opt/meshcentral/meshcentral/meshctrl.js"),
            meshcentral_url=env.get("MESHCENTRAL_URL", "ws://meshcentral:4430"),
            mesh_utilisateur=_obligatoire(env, "MESHCENTRAL_TOKEN_USER"),
            mesh_mot_de_passe=_obligatoire(env, "MESHCENTRAL_TOKEN_PASSWORD"),
            osticket_url=env.get("OSTICKET_URL", "http://osticket/api/tickets.json"),
            osticket_cle_api=_obligatoire(env, "OSTICKET_API_KEY"),
            osticket_topic_id=_entier(env, "OSTICKET_TOPIC_ID", defaut=0),
            demandeur_nom=env.get("PONT_DEMANDEUR_NOM", "Supervision RMM"),
            demandeur_email=env.get("PONT_DEMANDEUR_EMAIL", "supervision@horizon.lan"),
            intervalle_secondes=_entier(env, "PONT_INTERVALLE_SECONDES", defaut=300, minimum=30),
            delai_hors_ligne_secondes=_entier(env, "PONT_DELAI_HORS_LIGNE_SECONDES", defaut=600, minimum=60),
            delai_commande_secondes=_entier(env, "PONT_DELAI_COMMANDE_SECONDES", defaut=90, minimum=10),
            fichier_etat=env.get("PONT_FICHIER_ETAT", "/data/etat.json"),
            fichier_battement=env.get("PONT_FICHIER_BATTEMENT", "/data/battement"),
        )

    def valider(self) -> None:
        if self.osticket_topic_id <= 0:
            raise ConfigurationInvalide("OSTICKET_TOPIC_ID doit désigner la catégorie « Alerte supervision »")
