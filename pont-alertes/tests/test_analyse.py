from pont.analyse import lire_resultats


def test_lit_les_sorties_reelles_windows_et_linux():
    sortie = (
        '{"check":"service","cible":"Spooler","etat":"Stopped","statut":"ALERTE"}\n'
        '{"check":"disque","cible":"C:","libre_pct":14,"statut":"ALERTE"}\n'
        '{"check":"disque","cible":"D:","libre_pct":73.6,"statut":"OK"}\n'
    )
    resultats = lire_resultats(sortie)
    assert [(r.check, r.cible, r.statut) for r in resultats] == [
        ("service", "Spooler", "ALERTE"),
        ("disque", "C:", "ALERTE"),
        ("disque", "D:", "OK"),
    ]
    assert resultats[0].resume() == "service Spooler : Stopped"
    assert resultats[1].resume() == "disque C: : 14 % libre"
    assert resultats[2].en_defaut is False


def test_ignore_les_lignes_parasites_et_invalides():
    sortie = (
        "Avertissement quelconque\r\n"
        "﻿{\"check\":\"service\",\"cible\":\"ssh\",\"etat\":\"active\",\"statut\":\"ok\"}\r\n"
        "{pas du json}\n"
        '{"check":"service","statut":"ALERTE"}\n'            # cible manquante
        '{"check":"x","cible":"y","statut":"INCONNU"}\n'     # statut hors contrat
        "[1, 2, 3]\n"
    )
    resultats = lire_resultats(sortie)
    assert len(resultats) == 1
    assert resultats[0].statut == "OK"          # statut normalisé en majuscules
    assert resultats[0].en_defaut is False


def test_erreur_est_consideree_comme_un_defaut():
    (r,) = lire_resultats('{"check":"service","cible":"Spooler","etat":"absent","statut":"ERREUR"}')
    assert r.en_defaut is True


def test_sortie_vide():
    assert lire_resultats("") == []
