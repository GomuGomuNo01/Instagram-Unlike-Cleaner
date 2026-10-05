# Instagram Unlike Cleaner (IUC)

[![CI](https://github.com/GomuGomuNo01/Instagram-Unlike-Cleaner/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/GomuGomuNo01/Instagram-Unlike-Cleaner/actions/workflows/ci.yml?query=branch%3Amain)
· Licence MIT · Python 3.11+ · Node.js 22+

Une personne veut effacer des années de « J’aime » Instagram, mais l’application ne permet de
les retirer qu’à la main, et les outils existants demandent souvent le mot de passe ou envoient
les données à un tiers. IUC liste d’abord tous les likes ciblés (période, type, comptes) pour
validation, puis les retire par lots avec pauses et limite quotidienne, sans jamais voir le mot
de passe ni rien envoyer hors de l’ordinateur. Sur un vrai compte, 1 493 likes ont été recensés
en 14 minutes et chaque lot retiré est contrôlé ; 283 tests automatisés prouvent qu’aucun
identifiant n’est lu ni conservé.

Technologies : Python, Playwright, FastAPI, SQLite, React, TypeScript, Tailwind CSS, GitHub
Actions.

> **Avertissement : à lire avant toute utilisation**
>
> Les conditions d’utilisation d’Instagram **n’autorisent pas l’automatisation**. Utiliser IUC
> expose ton compte à un **blocage temporaire** de certaines actions, voire, plus rarement, à
> une **suspension**. IUC limite la cadence et s’arrête au moindre signal d’Instagram, mais le
> risque zéro n’existe pas.
>
> - **Teste d’abord sur un compte secondaire**, avec de petits volumes (option « Faire d’abord
>   un essai », `--limit`).
> - Retirer un like efface la trace visible, pas ce que l’algorithme a déjà appris.
> - IUC est un projet indépendant, **sans lien avec Instagram ni Meta**. Utilise-le uniquement
>   sur ton propre compte, à tes risques.

## Fonctionnement

1. **Connexion** : IUC ouvre une fenêtre Chromium dédiée. Tu t’y connectes toi-même, double
   authentification comprise. IUC ne voit jamais ton mot de passe.
2. **Critères** : période du like, ordre, type de contenu (publications ou reels), comptes à
   cibler ou à protéger, choisis dans la liste des comptes de tes likes.
3. **Aperçu** : chaque like ciblé est listé ; tu décoches ceux à garder. Rien n’est retiré avant
   ton lancement.
4. **Nettoyage** : retrait par lots (« Je n’aime plus »), pauses aléatoires, limite quotidienne,
   suivi en direct, pause, reprise ou arrêt à tout moment.
5. **Rapport** : bilan chiffré, échecs détaillés, export CSV et JSON.

L’interface web (React) est servie par une API locale (FastAPI) ; une CLI (`iuc`) offre les
mêmes fonctions. Un seul navigateur, piloté par Playwright, parle à Instagram.

![Démonstration du parcours, avec des données fictives](docs/images/demo.gif)

## Captures

Toutes les captures utilisent des comptes fictifs (`scripts/demo.py`).

| Critères et liste de tes comptes | Aperçu à cocher |
| --- | --- |
| ![Critères du nettoyage](docs/images/criteres.png) | ![Aperçu du nettoyage](docs/images/apercu.png) |
| **Suivi en direct** | **Rapport final** |
| ![Suivi d'un nettoyage en pause](docs/images/suivi.png) | ![Rapport d'un nettoyage terminé](docs/images/rapport.png) |

| Page d’accueil | Mobile, thème sombre |
| --- | --- |
| ![Page d'accueil](docs/images/accueil.png) | ![Aperçu sur mobile en thème sombre](docs/images/mobile-sombre.png) |

## Sécurité et confidentialité

Chaque garantie est appliquée dans le code et **prouvée par des tests** lancés à chaque
modification (`backend/tests/test_security.py` et `backend/tests/test_cleanup.py`).

| Sujet | Garantie | Preuve |
| --- | --- | --- |
| Identifiants | Aucun champ de connexion lu ni rempli par le script ; aucun mot de passe en mémoire, en base ou dans les journaux. Chromium n’enregistre aucun identifiant, et les diagnostics masquent toute saisie (aucune capture sur une page de connexion ou une fenêtre de ré-authentification). | Analyse du code (aucune saisie ni lecture de champ), identifiants « témoins » tapés dans une fausse page de connexion puis recherchés dans tout `DATA_DIR` |
| Données locales | Profil du navigateur, base, rapports, diagnostics et journaux dans `DATA_DIR` uniquement. Aucun appel réseau du backend ; l’interface est bridée par une politique de sécurité du contenu (CSP) qui n’autorise que l’API locale. | Analyse des imports réseau, en-tête CSP vérifié, chemins de stockage vérifiés |
| Suppression | `iuc logout` (profil du navigateur), `iuc purge` et le bouton « Supprimer mes données locales » (tout effacer) | Tests de la CLI, de l’API et du service de suppression |
| Cadence | Délais aléatoires entre deux cases cochées, entre deux défilements et entre deux lots ; plafond quotidien configurable (`DAILY_LIMIT`) | Tirages aléatoires et bornes vérifiés, limite quotidienne partagée entre nettoyages |
| Alertes Instagram | Message de limite, vérification de sécurité, déconnexion forcée : arrêt immédiat, nettoyage « en pause », marche à suivre affichée | Fausse page des likes qui déconnecte, demande une vérification ou affiche « Réessayer plus tard » en plein nettoyage |
| Reprise | Chaque lot est enregistré en base avant le suivant ; une relance reprend sans retraiter | Interruption, pause, limite puis reprise sur la fausse page |
| Changement d’interface | Sélecteurs isolés (`backend/app/browser/locators.py`), vérification au démarrage que chaque élément attendu existe, message qui nomme l’élément manquant ; `iuc probe` pour étudier la nouvelle interface | Pages modifiées (bouton absent, vignettes illisibles, bouton renommé) |
| API locale | Écoute sur 127.0.0.1 uniquement, jeton aléatoire par démarrage, contrôle de l’hôte (DNS rebinding), CORS limité au serveur de développement, en-têtes de sécurité, aucune page dans un cadre | Tests de l’API et de la commande `iuc serve` |
| Dépendances | Versions figées (`constraints.txt`, `frontend/package-lock.json`), audit avec `pip-audit` et `npm audit` | Test de cohérence des versions figées, audits sans vulnérabilité connue |
| Journaux | Aucun nom de compte aimé ni secret dans les journaux (cookies, jeton masqués) ; niveau réglable (`LOG_LEVEL`) | Comptes « témoins » recherchés dans le journal après un nettoyage complet |

Les diagnostics (`DATA_DIR/diagnostics`) servent à ajuster IUC quand Instagram change son
interface. Ils contiennent les noms des comptes que tu as aimés : masque-les avant de les
partager.

## Installation

Prérequis : Python 3.11 ou plus, Node.js 22 ou plus.

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows ; sous macOS ou Linux : source .venv/bin/activate
pip install -e ".[dev]" -c constraints.txt
playwright install chromium
cd frontend
npm ci
npm run build
cd ..
```

Copie `.env.example` en `.env` pour ajuster les réglages (facultatif).

## Utilisation

```bash
iuc serve
```

L’interface s’ouvre dans ton navigateur, sur `http://127.0.0.1:8765`. Suis le parcours :
avertissement, connexion, critères, aperçu, nettoyage, rapport. `Ctrl+C` arrête le serveur ;
un nettoyage en cours passe en pause et pourra reprendre.

La même chose en ligne de commande :

| Commande | Rôle |
| --- | --- |
| `iuc login` | Ouvre Instagram, attend ta connexion, vérifie la page des likes |
| `iuc preview --start 2021-01-01 --end 2021-12-31 --content reels --exclude-author ami` | Prépare l’aperçu, sans rien retirer |
| `iuc jobs` | Liste les nettoyages et leur avancement |
| `iuc exclude 3 --rank 12 --author ami` | Garde des likes (`--restore` pour les remettre) |
| `iuc run 3 --limit 25` | Lance ou reprend le nettoyage n° 3 (ici, 25 likes au plus) |
| `iuc stop 3` | Arrête définitivement un nettoyage |
| `iuc report 3` | Bilan et export CSV et JSON |
| `iuc probe` | Explore la page des likes sans rien retirer (diagnostics) |
| `iuc logout` / `iuc purge` | Supprime la session Instagram / toutes les données locales |

### Essayer l’interface sans compte Instagram

```bash
python scripts/demo.py
```

Ouvre `http://127.0.0.1:8799` : trois nettoyages fictifs (terminé, en pause, prêt) dans un
dossier `demo-data/` séparé. Tes vraies données ne sont jamais touchées.

## Configuration

| Variable | Défaut | Rôle |
| --- | --- | --- |
| `DATA_DIR` | `./data` | Dossier de toutes les données locales |
| `DAILY_LIMIT` | `150` | Unlikes tentés par jour au maximum, tous nettoyages confondus |
| `DELAY_MIN`, `DELAY_MAX` | `4`, `12` | Pause aléatoire entre deux lots, en secondes |
| `BATCH_SIZE` | `20` | Likes retirés par lot |
| `LOG_LEVEL` | `INFO` | Niveau de détail des journaux |
| `API_PORT` | `8765` | Port de l’API locale (toujours sur 127.0.0.1) |
| `API_DOCS` | `false` | Page `/docs` de l’API, chargée depuis un CDN : à n’activer qu’en développement |

## Questions fréquentes

**Dois-je donner mon mot de passe ?** Non. Tu te connectes toi-même dans la fenêtre Chromium ;
IUC ne lit aucun champ du formulaire et vérifie seulement que la session est ouverte.

**Mon compte risque-t-il quelque chose ?** Instagram n’autorise pas l’automatisation. IUC limite
la cadence et s’arrête au moindre signal, mais le risque zéro n’existe pas : commence par un
compte secondaire.

**Combien de temps faut-il ?** Environ une minute pour vingt-cinq likes. Au-delà de la limite
quotidienne (150 par défaut), le nettoyage reprend le lendemain là où il s’était arrêté.

**Que se passe-t-il si Instagram me déconnecte ou demande une vérification ?** Le nettoyage
s’arrête aussitôt et passe en pause. Règle la situation toi-même dans la fenêtre, puis reprends :
rien n’est retraité.

**Et si Instagram change son interface ?** IUC vérifie au démarrage chaque élément dont il a
besoin et nomme celui qui manque, sans rien retirer. Les sélecteurs sont réunis dans un seul
fichier pour faciliter la mise à jour (voir [CONTRIBUTING.md](CONTRIBUTING.md)).

**Où sont mes données ?** Dans `DATA_DIR` (par défaut `./data`), sur ton ordinateur. `iuc purge`
ou le bouton « Supprimer mes données locales » efface tout.

**IUC est-il lié à Instagram ?** Non, c’est un projet indépendant, sans lien avec Instagram ni
Meta.

## Développement

```bash
pre-commit install                  # contrôles automatiques avant chaque commit
pytest                              # backend ; -m "not browser" pour sauter les tests Chromium
ruff check backend scripts && ruff format --check backend scripts && mypy
pip-audit -r constraints.txt --no-deps --disable-pip   # vulnérabilités connues
cd frontend
npm test && npm run lint && npm run typecheck && npm run format:check
npm run audit                       # vulnérabilités connues des dépendances npm
npm run dev                         # interface en développement (API : iuc serve)
npm run api                         # régénère les types du client après un changement d'API
```

### Tests et qualité

| Niveau | Cible | Outil |
| --- | --- | --- |
| Unitaires | Filtres, limites quotidiennes, pauses aléatoires, machine d’états d’un nettoyage | pytest |
| Intégration | API et base SQLite, reprise après un arrêt | pytest, httpx |
| Automatisation | Navigation, sélection et retrait sur une fausse page des likes, réseau coupé | Playwright |
| Frontend | Composants et parcours principal | Vitest, Testing Library |
| Manuel | Un lot réel de quelques dizaines de likes sur un compte de test | [Recette](docs/recette.md) |

Les tests d’automatisation tournent sur une fausse page des likes, sans aucun accès au réseau
(`backend/tests/fake_instagram.py`) : on ne teste jamais sur le vrai Instagram en continu.
L’intégration continue (GitHub Actions) lance le lint, le typage, tous les tests et les audits
à chaque envoi sur `main` ou `dev`, avec Python 3.11 et 3.14.

Mise à jour des dépendances Python : `pip install -U <paquet>`, tests verts, `pip-audit`, puis
`pip freeze --exclude-editable` dans `constraints.txt` (en gardant son en-tête).

## Structure

```
backend/app/
  browser/    Chromium : session, sélecteurs, grille, filtres, mode sélection
  services/   aperçu, nettoyage, rapport, données locales
  api/        API locale (FastAPI) et sécurité
  core/       configuration, base, journaux, protection des identifiants
  cli.py      commandes `iuc`
backend/tests/  tests, dont la fausse version d'Instagram
frontend/       interface React (Vite, TypeScript, Tailwind)
scripts/        démonstration avec des données fictives
docs/           recette manuelle, images du README
```

## Contribuer, sécurité et licence

- Contributions : voir [CONTRIBUTING.md](CONTRIBUTING.md).
- Vulnérabilité : signalement privé, voir [SECURITY.md](SECURITY.md).
- Licence : [MIT](LICENSE). Instagram est une marque de Meta Platforms, Inc.
