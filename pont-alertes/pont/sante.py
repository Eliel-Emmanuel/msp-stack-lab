"""Healthcheck Docker : le dernier cycle réussi doit être récent (python -m pont.sante)."""

from __future__ import annotations

import os
import sys
import time


def main() -> int:
    fichier = os.environ.get("PONT_FICHIER_BATTEMENT", "/data/battement")
    intervalle = int(os.environ.get("PONT_INTERVALLE_SECONDES", "300") or 300)
    tolerance = 2 * intervalle + 60
    try:
        age = time.time() - os.path.getmtime(fichier)
    except OSError:
        print("aucun cycle réussi pour l'instant", file=sys.stderr)
        return 1
    if age > tolerance:
        print(f"dernier cycle réussi il y a {int(age)} s (tolérance {tolerance} s)", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
