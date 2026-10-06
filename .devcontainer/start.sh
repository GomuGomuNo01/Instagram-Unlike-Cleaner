#!/usr/bin/env bash
# Lance IUC dans le Codespace, en arrière-plan, s'il ne tourne pas déjà : au démarrage du
# Codespace et à chaque ouverture (un Codespace mis en veille repart sans lui).
# Journal : /tmp/iuc-serve.log.
set -euo pipefail

if curl --silent --output /dev/null http://127.0.0.1:8765/; then
  exit 0 # déjà lancé
fi

# Nom et domaine du Codespace : absents de certains contextes de démarrage, alors qu'IUC en a
# besoin pour accepter l'adresse du Codespace et indiquer le bureau distant.
ENV_FILE=/workspaces/.codespaces/shared/.env
if [ -f "$ENV_FILE" ]; then
  while IFS='=' read -r key value; do
    case "$key" in
      CODESPACES | CODESPACE_NAME | GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN)
        value="${value%\"}"
        export "$key=${value#\"}"
        ;;
    esac
  done <"$ENV_FILE"
fi

export PATH="$HOME/.local/bin:$PATH"
# setsid : le serveur survit à la fin de cette commande de démarrage.
setsid nohup iuc serve --no-open >/tmp/iuc-serve.log 2>&1 </dev/null &
