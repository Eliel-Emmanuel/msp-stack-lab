COMPOSE := docker compose
.DEFAULT_GOAL := help
.PHONY: help env up down ps logs clean ca

help: ## Liste des commandes
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  %-10s %s\n",$$1,$$2}'

env: ## Crée .env depuis .env.example
	@test -f .env && echo ".env existe déjà" || cp .env.example .env

up: ## Démarre la pile et attend qu'elle soit saine
	$(COMPOSE) up -d --wait

down: ## Arrête la pile
	$(COMPOSE) down

ps: ## État des services
	$(COMPOSE) ps

logs: ## Journaux de tous les services
	$(COMPOSE) logs -f --tail=50

clean: ## Arrête ET supprime les données
	$(COMPOSE) down -v

ca: ## Exporte le certificat racine de Caddy
	$(COMPOSE) cp caddy:/data/caddy/pki/authorities/local/root.crt ./caddy-root.crt
	@echo "Certificat exporté : caddy-root.crt"
	
reload: ## Valide puis recharge la configuration de Caddy sans couper le service
	docker run --rm -v "$(PWD)/caddy/Caddyfile:/etc/caddy/Caddyfile:ro" caddy:$$(grep ^CADDY_VERSION .env | cut -d= -f2) caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
	docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile
