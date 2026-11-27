"""Scénarios du cahier des charges, avec MeshCentral et osTicket simulés."""

import pytest

from pont.etat import Etat
from pont.meshcentral import Appareil
from pont.moteur import Moteur

PC = Appareil(id="node//pc", nom="DESKTOP-UEJ0H1E", connecte=True, systeme="Microsoft Windows 11 Professionnel")
SRV = Appareil(id="node//srv", nom="srv-horizon01", connecte=True, systeme="Debian GNU/Linux 13")

SPOOLER_OK = '{"check":"service","cible":"Spooler","etat":"Running","statut":"OK"}'
SPOOLER_KO = '{"check":"service","cible":"Spooler","etat":"Stopped","statut":"ALERTE"}'
DISQUE_OK = '{"check":"disque","cible":"C:","libre_pct":40,"statut":"OK"}'
SSH_OK = '{"check":"service","cible":"ssh","etat":"active","statut":"OK"}'


class FausseSource:
    def __init__(self):
        self.appareils = [PC, SRV]
        self.sorties = {PC.id: f"{SPOOLER_OK}\n{DISQUE_OK}", SRV.id: SSH_OK}
        self.pannes = set()

    def lister_appareils(self):
        return list(self.appareils)

    def verifier(self, appareil):
        if appareil.id in self.pannes:
            raise RuntimeError("RunCommand : pas de réponse après 90 s")
        return self.sorties[appareil.id]

    def deconnecter(self, appareil):
        self.appareils = [
            Appareil(a.id, a.nom, False, a.systeme) if a.id == appareil.id else a for a in self.appareils
        ]

    def reconnecter(self, appareil):
        self.appareils = [
            Appareil(a.id, a.nom, True, a.systeme) if a.id == appareil.id else a for a in self.appareils
        ]


class FausseBilletterie:
    def __init__(self):
        self.tickets = []
        self.en_panne = False

    def creer_ticket(self, sujet, message):
        if self.en_panne:
            raise ConnectionError("osTicket injoignable")
        numero = str(100000 + len(self.tickets) + 1)
        self.tickets.append((numero, sujet, message))
        return numero


@pytest.fixture
def banc():
    source, billetterie, etat = FausseSource(), FausseBilletterie(), Etat()
    return source, billetterie, etat, Moteur(source, billetterie, etat, delai_hors_ligne=600)


def test_tout_va_bien_aucun_ticket(banc):
    source, billetterie, etat, moteur = banc
    assert moteur.cycle(0) == []
    assert billetterie.tickets == [] and etat.alertes == {}


def test_scenario_spooler_un_seul_ticket_puis_retablissement(banc):
    source, billetterie, etat, moteur = banc
    source.sorties[PC.id] = f"{SPOOLER_KO}\n{DISQUE_OK}"

    assert moteur.cycle(0) == ["100001"]
    numero, sujet, message = billetterie.tickets[0]
    assert sujet == "[ALERTE] DESKTOP-UEJ0H1E - service Spooler : Stopped"
    assert '"statut": "ALERTE"' in message

    # Cycles suivants, panne toujours présente : pas de doublon
    assert moteur.cycle(300) == []
    assert moteur.cycle(600) == []
    assert len(billetterie.tickets) == 1

    # Le technicien répare : l'alerte est oubliée
    source.sorties[PC.id] = f"{SPOOLER_OK}\n{DISQUE_OK}"
    moteur.cycle(900)
    assert etat.alertes == {}

    # Nouvelle panne plus tard : nouveau ticket
    source.sorties[PC.id] = SPOOLER_KO
    assert moteur.cycle(1200) == ["100002"]


def test_hors_ligne_seulement_apres_10_minutes(banc):
    source, billetterie, etat, moteur = banc
    source.deconnecter(SRV)

    assert moteur.cycle(0) == []        # vient de tomber
    assert moteur.cycle(300) == []      # 5 min : redémarrage possible, on attend
    assert moteur.cycle(600) == ["100001"]   # 10 min : ticket
    assert billetterie.tickets[0][1].startswith("[HORS LIGNE] srv-horizon01")
    assert moteur.cycle(900) == []      # pas de doublon

    source.reconnecter(SRV)
    moteur.cycle(1200)
    assert etat.hors_ligne == {}


def test_redemarrage_rapide_ne_cree_pas_de_ticket(banc):
    source, billetterie, etat, moteur = banc
    source.deconnecter(SRV)
    moteur.cycle(0)
    source.reconnecter(SRV)
    moteur.cycle(300)
    source.deconnecter(SRV)
    moteur.cycle(600)                   # nouvelle coupure : le compteur repart de zéro
    assert billetterie.tickets == []


def test_osticket_en_panne_le_ticket_est_retente(banc):
    source, billetterie, etat, moteur = banc
    source.sorties[PC.id] = SPOOLER_KO
    billetterie.en_panne = True
    assert moteur.cycle(0) == []
    assert etat.alertes == {}           # rien n'est mémorisé...

    billetterie.en_panne = False
    assert moteur.cycle(300) == ["100001"]   # ...donc le ticket est créé au cycle suivant


def test_une_machine_en_erreur_ne_bloque_pas_les_autres(banc):
    source, billetterie, etat, moteur = banc
    source.pannes.add(PC.id)
    source.sorties[SRV.id] = '{"check":"service","cible":"ssh","etat":"inactive","statut":"ALERTE"}'
    assert moteur.cycle(0) == ["100001"]
    assert "srv-horizon01" in billetterie.tickets[0][1]


def test_sortie_sans_json_aucun_ticket(banc):
    source, billetterie, etat, moteur = banc
    source.sorties[PC.id] = "Le terme « C:\\HorizonScripts\\check-service.ps1 » n'est pas reconnu"
    assert moteur.cycle(0) == []


def test_appareil_supprime_de_meshcentral(banc):
    source, billetterie, etat, moteur = banc
    source.deconnecter(SRV)
    moteur.cycle(0)
    source.appareils = [PC]
    moteur.cycle(300)
    assert SRV.id not in etat.hors_ligne


def test_etat_persistant_entre_deux_redemarrages_du_pont(tmp_path):
    chemin = str(tmp_path / "etat.json")
    source, billetterie = FausseSource(), FausseBilletterie()
    source.sorties[PC.id] = SPOOLER_KO

    etat = Etat.charger(chemin)
    Moteur(source, billetterie, etat, 600).cycle(0)
    etat.enregistrer(chemin)

    # Le conteneur redémarre : nouvel objet, même fichier
    etat2 = Etat.charger(chemin)
    assert Moteur(source, billetterie, etat2, 600).cycle(300) == []
    assert len(billetterie.tickets) == 1
