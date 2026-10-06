# Tester la vraie version d’IUC dans ce Codespace

Ce Codespace est **ta** machine temporaire, créée sur **ton** compte GitHub. IUC y tourne
exactement comme sur un ordinateur : ton mot de passe, ta session Instagram et tes likes
restent ici, et personne d’autre n’y a accès, pas même l’auteur du projet.

> **Avertissement** : l’automatisation n’est pas autorisée par les conditions d’utilisation
> d’Instagram. Utilise de préférence un **compte secondaire**. Comme la connexion vient d’un
> centre de données, Instagram peut te demander une vérification de sécurité : fais-la toi-même.

## En 4 étapes

1. **Attends la fin de l’installation** (quelques minutes à la première ouverture). Un onglet
   « IUC » s’ouvre ; sinon, onglet **Ports** en bas, ligne « IUC (interface) », icône du globe.
2. **Ouvre le bureau distant** : onglet **Ports**, ligne « Bureau (fenêtre Chromium) », icône du
   globe. L’écran « Connexion » d’IUC propose aussi un lien direct.
3. Dans IUC, clique sur **« Ouvrir Instagram »**, puis **connecte-toi toi-même dans le bureau
   distant**, double authentification comprise.
4. Choisis le filtre d’Instagram, vérifie l’aperçu, lance le nettoyage, puis lis le rapport.

## Effacer toutes tes données

Rapport d’IUC → « Supprimer mes données locales », ou supprime simplement le Codespace :
<https://github.com/codespaces>. Pense aussi à l’arrêter quand tu as fini, pour ne pas
consommer ton quota gratuit.

## En cas de souci

- IUC ne répond pas : relance-le dans le terminal avec `bash .devcontainer/start.sh`, et lis
  le journal avec `cat /tmp/iuc-serve.log`.
- Le bureau distant est noir : recharge son onglet.
