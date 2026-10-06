#!/usr/bin/env bash
# Lance IUC à chaque démarrage du Codespace, en arrière-plan. Journal : /tmp/iuc-serve.log.
set -euo pipefail

if curl --silent --output /dev/null http://127.0.0.1:8765/; then
  exit 0 # déjà lancé
fi
export PATH="$HOME/.local/bin:$PATH"
# setsid : le serveur survit à la fin de cette commande de démarrage.
setsid nohup iuc serve --no-open >/tmp/iuc-serve.log 2>&1 </dev/null &
