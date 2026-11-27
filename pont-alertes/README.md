# Pont d'alertes MeshCentral → osTicket

Service Python (bibliothèque standard uniquement) qui transforme les alertes de supervision en tickets.

## Fonctionnement

Toutes les `PONT_INTERVALLE_SECONDES` (300 s par défaut) :

1. `meshctrl ListDevices` : liste les appareils visibles par le compte de service `svc-pont-alertes`.
2. Appareil **connecté** : `meshctrl RunCommand --reply` lance les scripts de vérification
   (`check-service`, `check-disque`) et lit leurs lignes JSON.
   - `statut` = `ALERTE` ou `ERREUR` → ticket « [ALERTE] … » (une seule fois par problème) ;
   - retour à `OK` → l'alerte est oubliée ; une nouvelle panne créera un nouveau ticket.
3. Appareil **hors ligne** : ticket « [HORS LIGNE] … » seulement après `PONT_DELAI_HORS_LIGNE_SECONDES`
   (600 s par défaut), pour ignorer les simples redémarrages.

Les tickets sont créés par l'API osTicket dans la catégorie « Alerte supervision (automatique) »
(priorité High, SLA Haute - 8h). L'état (alertes déjà signalées) est conservé dans `/data/etat.json`.

## Sécurité

| Élément | Mesure |
|---|---|
| MeshCentral | Compte de service dédié, droit « Commandes à distance » sur un seul groupe, jeton révocable |
| osTicket | Clé d'API « création de tickets » uniquement, liée à l'adresse fixe `172.30.10.50` |
| Conteneur | Utilisateur non root, système de fichiers en lecture seule, aucune capacité Linux |
| Secrets | Uniquement dans `.env` ; jamais écrits dans les journaux |

## Variables d'environnement

| Variable | Défaut | Rôle |
|---|---|---|
| `MESHCENTRAL_TOKEN_USER` / `_PASSWORD` | — (obligatoire) | Jeton de connexion du compte de service |
| `OSTICKET_API_KEY` | — (obligatoire) | Clé d'API osTicket |
| `OSTICKET_TOPIC_ID` | — (obligatoire) | Identifiant de la catégorie « Alerte supervision » |
| `MESHCENTRAL_URL` | `ws://meshcentral:4430` | MeshCentral en interne, sans passer par Caddy |
| `OSTICKET_URL` | `http://osticket/api/tickets.json` | API osTicket en interne |
| `PONT_INTERVALLE_SECONDES` | `300` | Fréquence des vérifications |
| `PONT_DELAI_HORS_LIGNE_SECONDES` | `600` | Délai avant ticket « hors ligne » |
| `PONT_DELAI_COMMANDE_SECONDES` | `90` | Délai maximal d'un RunCommand |

## Tests

```bash
make test-pont
```
