# Contribuer à IUC

Merci de ton intérêt ! IUC est un petit projet personnel : les signalements de bugs, les
corrections et les adaptations aux changements d’interface d’Instagram sont les bienvenus.

## Avant de commencer

- Lis l’avertissement du [README](README.md) : l’automatisation n’est pas autorisée par les
  conditions d’utilisation d’Instagram. Teste uniquement sur un **compte secondaire**.
- Les principes de sécurité ne sont pas négociables : aucun champ de connexion lu ni rempli,
  aucune donnée envoyée ailleurs que sur l’ordinateur de l’utilisateur, arrêt au moindre
  signal d’Instagram. Une contribution qui les affaiblit sera refusée.
- Pour un changement important, ouvre d’abord une *issue* pour en discuter.

## Installation pour le développement

Voir la section [Installation](README.md#installation) du README, puis :

```bash
pre-commit install
python scripts/demo.py      # interface avec des données fictives, sur http://127.0.0.1:8799
```

## Avant chaque proposition

Tout doit être vert, comme dans l’intégration continue :

```bash
ruff check backend scripts && ruff format --check backend scripts && mypy
pytest
cd frontend
npm run lint && npm run typecheck && npm run format:check && npm test && npm run build
```

Définition de « terminé » :

- code typé, formaté (Ruff, Prettier) et sans erreur de lint ;
- tests écrits et verts, en local et en CI ;
- aucun secret ni donnée personnelle dans le dépôt : jamais de vrai nom de compte, de cookie,
  de capture ou de diagnostic issu d’un vrai compte (utilise `scripts/demo.py` ou les fausses
  pages de `backend/tests/fake_instagram.py`) ;
- documentation mise à jour ;
- démo en ligne alignée sur l’API : une route ou un champ ajouté au backend se reproduit dans
  la fausse API de `frontend/src/demo/` (vérifier avec `npm run build:demo` puis
  `npm run preview:demo`).

## Quand Instagram change son interface

1. Lance `iuc probe` sur un compte secondaire : il enregistre des diagnostics dans
   `DATA_DIR/diagnostics` sans rien retirer.
2. Ajuste uniquement `backend/app/browser/locators.py` (tous les sélecteurs y sont réunis),
   puis la fausse page des tests si besoin.
3. Ne partage jamais un diagnostic brut : il contient les noms des comptes aimés.

## Style

- Textes de l’interface, messages et commentaires en français.
- Messages de commit au format `type(portée): description` (par exemple
  `fix(browser): nouveau libellé du bouton « Je n’aime plus »`).
