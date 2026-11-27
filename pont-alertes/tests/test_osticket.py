import json

from pont.config import Config
from pont.osticket import construire_requete

ENV = {
    "MESHCENTRAL_TOKEN_USER": "~t:jeton",
    "MESHCENTRAL_TOKEN_PASSWORD": "secret",
    "OSTICKET_API_KEY": "CLE-API",
    "OSTICKET_TOPIC_ID": "16",
}


def test_requete_conforme_au_test_curl_valide():
    config = Config.depuis_env(ENV)
    requete = construire_requete(config, "[ALERTE] PC - service Spooler : Stopped", "détail\nsur deux lignes")

    assert requete.get_method() == "POST"
    assert requete.full_url == "http://osticket/api/tickets.json"
    assert requete.get_header("X-api-key") == "CLE-API"
    assert requete.get_header("X-forwarded-proto") == "https"

    corps = json.loads(requete.data.decode("utf-8"))
    assert corps["topicId"] == 16
    assert corps["email"] == "supervision@horizon.lan"
    assert corps["alert"] is True and corps["autorespond"] is False
    assert corps["message"].startswith("data:text/plain;charset=utf-8,détail")
