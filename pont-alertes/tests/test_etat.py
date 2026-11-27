import json

from pont.etat import Etat


def test_aller_retour_sur_disque(tmp_path):
    chemin = tmp_path / "sous-dossier" / "etat.json"
    etat = Etat()
    etat.alertes[Etat.cle("node//a", "service", "Spooler")] = {"ticket": "123456", "depuis": 1.0}
    etat.hors_ligne["node//b"] = {"depuis": 2.0, "ticket": None, "appareil": "srv"}
    etat.enregistrer(str(chemin))

    relu = Etat.charger(str(chemin))
    assert relu.alertes == etat.alertes
    assert relu.hors_ligne == etat.hors_ligne
    assert json.loads(chemin.read_text())["version"] == 1
    assert not list(chemin.parent.glob(".etat-*"))   # aucun fichier temporaire oublié


def test_fichier_absent_ou_corrompu(tmp_path):
    assert Etat.charger(str(tmp_path / "absent.json")).alertes == {}
    corrompu = tmp_path / "etat.json"
    corrompu.write_text("{ pas du json")
    etat = Etat.charger(str(corrompu))
    assert etat.alertes == {} and etat.hors_ligne == {}
