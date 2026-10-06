# IUC : nettoyer ses « J’aime » Instagram, en local et sans risque inutile

*Contenu prêt à reprendre pour la page portfolio du projet.*

## Fiche projet

**Instagram Unlike Cleaner : effacer ses likes sans confier son compte**

Une personne veut effacer des années de « J’aime » Instagram, mais l’application ne permet de
les retirer qu’à la main, et les outils existants demandent souvent le mot de passe ou envoient
les données à un tiers. IUC cible les likes avec le filtre d’Instagram (tri, dates du like),
liste chaque like pour validation, puis les retire par lots avec pauses et limite quotidienne,
sans jamais voir le mot de passe ni rien envoyer hors de l’ordinateur. Sur un vrai compte,
1 493 likes ont été recensés en 14 minutes et chaque lot retiré est contrôlé ; 273 tests
automatisés prouvent qu’aucun identifiant n’est lu ni conservé.

Technologies : Python, Playwright, FastAPI, SQLite, React, TypeScript, Tailwind CSS, GitHub
Actions.

## Le problème

Des années de likes Instagram laissent une trace visible et parfois gênante, au moment d’une
recherche de stage ou d’emploi par exemple. Instagram permet de les retirer, mais à la main.
Les outils existants demandent souvent le mot de passe ou envoient les données à un serveur
tiers : on échange un problème de confidentialité contre un autre.

## La réponse apportée

- La personne se connecte elle-même dans une fenêtre Chromium dédiée : IUC ne voit jamais le
  mot de passe et reconnaît la session à son seul cookie.
- Le ciblage reprend exactement le filtre de la version web d’Instagram (tri, date de début, date
  de fin du like), sans critère inventé que la plateforme ne permet pas de vérifier.
- Un aperçu obligatoire liste chaque like ciblé avec son compte et son type ; rien n’est retiré
  sans validation.
- Le retrait se fait par lots, avec pauses aléatoires, limite quotidienne et arrêt immédiat au
  moindre signal d’Instagram ; un nettoyage interrompu reprend sans rien retraiter.
- Une interface web locale guide les cinq étapes (connexion, critères, aperçu, suivi, rapport) ;
  une ligne de commande offre les mêmes fonctions.

## Le résultat

- Essais sur un vrai compte : 1 493 likes recensés en 14 minutes, puis des lots retirés et
  vérifiés un à un au rechargement de la page.
- 273 tests automatisés (227 côté serveur, 46 côté interface), relancés à chaque envoi par
  l’intégration continue ; ils prouvent notamment qu’aucun identifiant tapé n’est lu ni écrit sur
  le disque, et que le nettoyage s’arrête sur déconnexion, vérification ou message de limite.
- Aucune vulnérabilité connue dans les dépendances (audits pip-audit et npm audit).

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

- Démo en ligne, sans installation : https://gomugomuno01.github.io/Instagram-Unlike-Cleaner/
- Code source : https://github.com/GomuGomuNo01/Instagram-Unlike-Cleaner
- Avertissement : l’automatisation n’est pas autorisée par les conditions d’utilisation
  d’Instagram ; projet indépendant, sans lien avec Instagram ni Meta.
