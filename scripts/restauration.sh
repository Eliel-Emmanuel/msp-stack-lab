#!/usr/bin/env bash
# Restauration complète de la stack MSP depuis un dossier produit par sauvegarde.sh.
#   1. Vérifie les empreintes SHA-256 (sauvegarde intacte)
#   2. Exige un .env identique à celui de la sauvegarde (clés de chiffrement)
#   3. Demande une confirmation explicite : les données actuelles sont REMPLACÉES
#   4. Restaure chaque volume, puis la base MariaDB, puis redémarre tout
#
# Usage : scripts/restauration.sh sauvegardes/2026-11-28_171500
#         CONFIRMER=RESTAURER scripts/restauration.sh ...   (sans question, pour un test scripté)
set -euo pipefail
cd "$(dirname "$0")/.."

IMAGE_OUTIL="alpine:3.22"

log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*"; }
echec() { log "ÉCHEC : $*"; exit 1; }

dossier="${1:-}"
[ -n "$dossier" ] && [ -d "$dossier" ] || echec "usage : $0 <dossier de sauvegarde>"
dossier_abs="$(realpath "$dossier")"

# --- 1. Intégrité -------------------------------------------------------------
log "1/5 Vérification des empreintes"
( cd "$dossier_abs" && sha256sum --quiet -c SHA256SUMS ) || echec "sauvegarde altérée ou incomplète"
[ -f "$dossier_abs/mariadb.sql.gz" ] || echec "mariadb.sql.gz absent"

# --- 2. Secrets ---------------------------------------------------------------
log "2/5 Contrôle du fichier .env"
if [ ! -f .env ]; then
  cp "$dossier_abs/env.sauvegarde" .env
  chmod 600 .env
  log "   .env absent : repris depuis la sauvegarde"
elif ! cmp -s .env "$dossier_abs/env.sauvegarde"; then
  echec ".env différent de celui de la sauvegarde (APP_KEY, jetons, mots de passe).
       Pour restaurer avec les secrets d'origine : cp \"$dossier/env.sauvegarde\" .env"
fi
projet="$(docker compose config --format json | python3 -c 'import json,sys; print(json.load(sys.stdin)["name"])')"

# --- 3. Confirmation ----------------------------------------------------------
echo
echo "  Restauration de : $dossier"
sed -n 's/^date=/  Sauvegarde du   : /p' "$dossier_abs/MANIFESTE.txt"
echo "  Projet Docker   : $projet"
echo "  Les données ACTUELLES des volumes seront REMPLACÉES."
echo
if [ "${CONFIRMER:-}" != "RESTAURER" ]; then
  read -r -p "  Tapez RESTAURER pour continuer : " reponse
  [ "$reponse" = "RESTAURER" ] || echec "restauration annulée"
fi

# --- 4. Volumes ---------------------------------------------------------------
log "3/5 Arrêt de la stack et création des volumes manquants"
docker compose down >/dev/null
docker compose up --no-start >/dev/null

log "4/5 Restauration des volumes"
for archive in "$dossier_abs"/volume-*.tar.gz; do
  fichier="$(basename "$archive")"
  volume="${fichier#volume-}"
  volume="${volume%.tar.gz}"
  docker run --rm \
    -v "${projet}_${volume}:/cible" \
    -v "$dossier_abs:/sauvegarde:ro" \
    "$IMAGE_OUTIL" sh -c \
      'find /cible -mindepth 1 -delete && tar xzf "/sauvegarde/$1" -C /cible' _ "$fichier"
  log "   $volume restauré"
done

# --- 5. Base de données puis redémarrage ---------------------------------------
log "5/5 Restauration de MariaDB puis démarrage complet"
docker compose up -d --wait mariadb >/dev/null
gzip -dc "$dossier_abs/mariadb.sql.gz" \
  | docker compose exec -T mariadb sh -c 'exec mariadb -uroot -p"$MARIADB_ROOT_PASSWORD"'
docker compose up -d --wait

log "Restauration terminée. Vérifier : make ps, connexions MeshCentral / osTicket / BookStack / Vaultwarden, agents reconnectés."
