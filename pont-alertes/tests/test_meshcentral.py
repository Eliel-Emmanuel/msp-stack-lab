import json

import pytest

from pont.meshcentral import COMMANDE_LINUX, COMMANDE_WINDOWS, ErreurMeshCentral, lire_appareils

LISTDEVICES = [
    {"type": "node", "_id": "node//$6oBCj", "name": "DESKTOP-UEJ0H1E", "conn": 1,
     "osdesc": "Microsoft Windows 11 Professionnel - 25H2/26200"},
    {"type": "node", "_id": "node//NV3tc", "name": "srv-horizon01", "conn": 0, "osdesc": "Debian GNU/Linux 13"},
    {"type": "mesh", "_id": "mesh//abc", "name": "pas un appareil"},
]


def test_lire_appareils():
    appareils = lire_appareils(json.dumps(LISTDEVICES))
    assert [a.nom for a in appareils] == ["DESKTOP-UEJ0H1E", "srv-horizon01"]
    assert appareils[0].connecte and appareils[0].est_windows
    assert not appareils[1].connecte and not appareils[1].est_windows


def test_conn_est_un_champ_de_bits():
    # bit 1 = agent ; 4 = Intel AMT seul -> agent non connecté
    (a, b) = lire_appareils(json.dumps([
        {"type": "node", "_id": "n1", "conn": 5},
        {"type": "node", "_id": "n2", "conn": 4},
    ]))
    assert a.connecte is True
    assert b.connecte is False


def test_reponse_illisible():
    with pytest.raises(ErreurMeshCentral):
        lire_appareils("Invalid login.")


def test_commandes_appellent_les_scripts_de_la_phase_2d():
    assert "check-service.ps1" in COMMANDE_WINDOWS and "check-disque.ps1" in COMMANDE_WINDOWS
    assert "check-service.sh ssh" in COMMANDE_LINUX and "check-disque.sh" in COMMANDE_LINUX
