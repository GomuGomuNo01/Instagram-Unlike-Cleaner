# IUC : nettoyer ses « J’aime » Instagram, en local et sans risque inutile

*Contenu prêt à reprendre pour la page portfolio du projet.*

## Le contexte

Des années de likes Instagram laissent une trace visible et parfois gênante, au moment d’une
recherche de stage ou d’emploi par exemple. Instagram permet de les retirer, mais un par un ou
par petits lots, à la main. Les outils existants demandent souvent le mot de passe ou envoient
les données à un serveur tiers.

**Objectif** : un outil gratuit, 100 % local, qui ne voit jamais le mot de passe, montre ce
qu’il va faire avant de le faire, et s’arrête au moindre signal d’Instagram.

## La solution

- Une fenêtre Chromium dédiée (Playwright) où l’utilisateur se connecte lui-même ; la session
  est reconnue au seul cookie de session.
- Un parcours en cinq étapes : connexion, critères, aperçu à cocher, nettoyage par lots suivi en
  direct, rapport (CSV, JSON).
- Une interface web React servie par une API locale FastAPI, et une CLI aux mêmes fonctions.

![Démonstration](images/demo.gif)

## Architecture

```
Interface React ──HTTP + SSE──▶ API FastAPI (127.0.0.1, jeton) ──▶ Services (aperçu, nettoyage, rapport)
CLI Typer ─────────────────────────────────────────────────────────▶        │
                                                                             ├──▶ SQLite (journal, reprise)
                                                                             └──▶ Playwright ──▶ Chromium ──▶ instagram.com
```

- **Backend** : Python, Playwright, FastAPI, SQLModel/SQLite, Typer, Pydantic Settings.
- **Frontend** : React 19, TypeScript strict, Vite, Tailwind CSS 4, client d’API typé depuis le
  schéma OpenAPI, progression en direct par Server-Sent Events.
- **Qualité** : Ruff, mypy strict, pytest ; Oxlint, Prettier, Vitest et Testing Library ;
  intégration continue GitHub Actions.

## Les choix qui comptent

- **Aucun mot de passe** : le code ne lit ni ne remplit aucun champ ; des tests le prouvent, en
  tapant de faux identifiants dans une fausse page de connexion puis en les cherchant partout
  sur le disque.
- **Aperçu obligatoire** : rien n’est retiré sans validation ; chaque lot est contrôlé (cases
  cochées = lot prévu, sinon annulation) puis vérifié au rechargement suivant.
- **Prudence** : pauses aléatoires, limite quotidienne, arrêt immédiat et mise en pause sur
  déconnexion forcée, vérification de sécurité ou message de limite.
- **Reprise** : chaque lot est enregistré en base avant le suivant ; une relance reprend sans
  retraiter.
- **API locale durcie** : écoute sur 127.0.0.1, jeton par démarrage, contrôle de l’hôte contre le
  DNS rebinding, CSP stricte qui n’autorise que l’API locale.

## Ce que j’ai appris

- **Automatiser une interface qu’on ne contrôle pas** : la page des likes n’a ni liens ni
  identifiants. Les publications sont reconnues au nom de fichier de leur image, et tous les
  sélecteurs sont isolés dans un seul module, vérifiés au démarrage.
- **Tester sans le vrai service** : une fausse page des likes, fidèle aux diagnostics
  réels (paquets de 18 vignettes, mode sélection, fenêtre de confirmation), sert à des centaines
  de tests, avec le réseau coupé pour qu’aucune requête ne parte sur Internet.
- **La sécurité se vérifie** : une revue ciblée a révélé que l’arbre d’accessibilité de
  Playwright recopie en clair la valeur des champs, mot de passe compris ; les diagnostics sont
  désormais expurgés, et un test échoue si la protection disparaît.
- **Une interface soignée reste sobre** : un système de design à tokens (couleurs, typographie,
  espacements, motion) vérifié par un test, des animations qui respectent le réglage
  « mouvement réduit », et une accessibilité pensée dès le départ (clavier, contrastes, lecteurs
  d’écran).

## Liens

- Code source : https://github.com/GomuGomuNo01/Instagram-Unlike-Cleaner
- Avertissement : l’automatisation n’est pas autorisée par les conditions d’utilisation
  d’Instagram ; projet indépendant, sans lien avec Instagram ni Meta.
