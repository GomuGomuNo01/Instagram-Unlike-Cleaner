#!/usr/bin/env bash
# Installation de la vraie version d'IUC dans le Codespace, une seule fois à sa création :
# dépendances Python (versions figées), Chromium et interface compilée.
set -euo pipefail

python -m pip install --upgrade pip
python -m pip install -e . -c constraints.txt
python -m playwright install --with-deps chromium

cd frontend
npm ci
npm run build
