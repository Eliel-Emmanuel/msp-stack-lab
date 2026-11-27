# Pont d'alertes MeshCentral -> osTicket
# Construit sur l'image MeshCentral elle-même : on réutilise exactement le même
# node et le même meshctrl.js que le serveur (aucun écart de version possible).
ARG MESHCENTRAL_VERSION=1.3.1-slim
FROM ghcr.io/ylianst/meshcentral:${MESHCENTRAL_VERSION}

RUN apk add --no-cache python3 \
 && adduser -D -H -u 10001 -s /sbin/nologin pont \
 && mkdir -p /data /app \
 && chown pont:pont /data

WORKDIR /app
COPY pont/ /app/pont/

USER pont
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

ENTRYPOINT ["python3", "-m", "pont"]
