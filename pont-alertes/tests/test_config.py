import pytest

from pont.config import Config, ConfigurationInvalide

ENV = {
    "MESHCENTRAL_TOKEN_USER": "~t:jeton",
    "MESHCENTRAL_TOKEN_PASSWORD": "secret",
    "OSTICKET_API_KEY": "CLE",
    "OSTICKET_TOPIC_ID": "16",
}


def test_valeurs_par_defaut_du_cahier_des_charges():
    config = Config.depuis_env(ENV)
    config.valider()
    assert config.intervalle_secondes == 300          # vérification toutes les 5 min
    assert config.delai_hors_ligne_secondes == 600    # hors ligne > 10 min
    assert config.meshcentral_url == "ws://meshcentral:4430"


@pytest.mark.parametrize("manquante", ["MESHCENTRAL_TOKEN_USER", "MESHCENTRAL_TOKEN_PASSWORD", "OSTICKET_API_KEY"])
def test_secret_manquant(manquante):
    env = {k: v for k, v in ENV.items() if k != manquante}
    with pytest.raises(ConfigurationInvalide, match=manquante):
        Config.depuis_env(env)


def test_topic_obligatoire():
    env = {k: v for k, v in ENV.items() if k != "OSTICKET_TOPIC_ID"}
    with pytest.raises(ConfigurationInvalide):
        Config.depuis_env(env).valider()


def test_intervalle_trop_court_refuse():
    with pytest.raises(ConfigurationInvalide):
        Config.depuis_env({**ENV, "PONT_INTERVALLE_SECONDES": "5"})
