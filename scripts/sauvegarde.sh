#!/usr/bin/env bash
# Sauvegarde complète de la stack MSP.
#   1. MariaDB exportée à chaud (transaction cohérente, aucune coupure)
#   2. Applications arrêtées le temps d'archiver leurs volumes (cohérence des
#      fichiers SQLite / NeDB), puis redémarrées - même en cas d'erreur
#   3. Manifeste (images, date), copie de .env, empreintes SHA-256
#   4. Rotation (CONSERVATION dernières sauvegardes) et copie externe facultative
#
# Variables : RACINE_SAUVEGARDES (./sauvegardes), CONSERVATION (7),
#             COPIE_EXTERNE (vide = pas de copie, ex. /mnt/d/Sauvegardes-msp)
set -euo pipefail
cd "$(dirname "$0")/.."

RACINE_SAUVEGARDES="${RACINE_SAUVEGARDES:-./sauvegardes}"
CONSERVATION="${CONSERVATION:-7}"
COPIE_EXTERNE="${COPIE_EXTERNE:-}"
IMAGE_OUTIL="alpine:3.22"
A_ARRETER=(meshcentral vaultwarden bookstack osticket pont-alertes)
VOLUMES_EXCLUS=" donnees-mariadb "   # MariaDB est exportée en SQL, pas copiée à chaud

log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*"; }
echec() { log "ÉCHEC : $*"; exit 1; }

[ -f .env ] || echec "fichier .env introuvable (lancer depuis la racine du dépôt)"

horodatage="$(date +%Y-%m-%d_%H%M%S)"
dest="$RACINE_SAUVEGARDES/$horodatage"
mkdir -p "$dest"
chmod 700 "$dest"
dest_abs="$(realpath "$dest")"
projet="$(docker compose config --format json | python3 -c 'import json,sys; print(json.load(sys.stdin)["name"])')"
uid_gid="$(id -u):$(id -g)"

log "Sauvegarde du projet « $projet » vers $dest"

# --- 1. MariaDB -------------------------------------------------------------
log "1/4 Export MariaDB (osticket, bookstack)"
docker compose exec -T mariadb sh -c \
  'exec mariadb-dump -uroot -p"$MARIADB_ROOT_PASSWORD" --single-transaction --routines --triggers --databases osticket bookstack' \
  | gzip -9 > "$dest/mariadb.sql.gz"
gzip -dc "$dest/mariadb.sql.gz" | tail -n 1 | grep -q "Dump completed" \
  || echec "export MariaDB incomplet"

# --- 2. Arrêt des applications -----------------------------------------------
redemarrer() {
  log "Redémarrage des applications"
  docker compose up -d --wait "${A_ARRETER[@]}" >/dev/null 2>&1 \
    || log "ATTENTION : vérifier l'état des services avec « make ps »"
}
log "2/4 Arrêt bref des applications : ${A_ARRETER[*]}"
docker compose stop "${A_ARRETER[@]}" >/dev/null
trap redemarrer EXIT

# --- 3. Volumes ---------------------------------------------------------------
log "3/4 Archivage des volumes"
while read -r volume; do
  [[ "$VOLUMES_EXCLUS" == *" $volume "* ]] && continue
  docker run --rm \
    -v "${projet}_${volume}:/source:ro" \
    -v "$dest_abs:/sauvegarde" \
    "$IMAGE_OUTIL" sh -c \
      'tar czf "/sauvegarde/volume-$1.tar.gz" -C /source . && chown "$2" "/sauvegarde/volume-$1.tar.gz"' \
      _ "$volume" "$uid_gid"
  log "   $volume : $(du -h "$dest/volume-$volume.tar.gz" | cut -f1)"
done < <(docker compose config --volumes)

trap - EXIT
redemarrer

# --- 4. Manifeste, secrets, empreintes ----------------------------------------
log "4/4 Manifeste et empreintes"
cp .env "$dest/env.sauvegarde"
chmod 600 "$dest/env.sauvegarde"
{
  echo "date=$horodatage"
  echo "projet=$projet"
  echo "hote=$(hostname)"
  echo "commit=$(git rev-parse --short HEAD 2>/dev/null || echo inconnu)"
  echo "[images]"
  docker compose config --images | sort
} > "$dest/MANIFESTE.txt"
( cd "$dest" && sha256sum ./*.gz env.sauvegarde MANIFESTE.txt > SHA256SUMS )

# --- Rotation et copie externe ------------------------------------------------
mapfile -t anciennes < <(find "$RACINE_SAUVEGARDES" -mindepth 1 -maxdepth 1 -type d -name '20*' | sort | head -n "-$CONSERVATION")
for ancienne in "${anciennes[@]}"; do
  rm -rf -- "$ancienne"
  log "Rotation : $(basename "$ancienne") supprimée"
done

if [ -n "$COPIE_EXTERNE" ]; then
  mkdir -p "$COPIE_EXTERNE"
  cp -r "$dest" "$COPIE_EXTERNE/"
  ( cd "$COPIE_EXTERNE/$horodatage" && sha256sum --quiet -c SHA256SUMS ) \
    || echec "copie externe corrompue"
  log "Copie externe vérifiée : $COPIE_EXTERNE/$horodatage"
fi

log "Terminé : $dest ($(du -sh "$dest" | cut -f1))"
log "Contient des secrets (env.sauvegarde) : ne jamais committer ni partager ce dossier."
