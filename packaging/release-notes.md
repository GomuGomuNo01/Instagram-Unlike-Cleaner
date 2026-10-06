## Installer IUC sur Windows

Deux formats, le même programme :

- **IUC-Setup-&lt;version&gt;.exe** : installeur classique, sans droit administrateur. IUC
  apparaît dans le menu Démarrer et se désinstalle comme une application Windows.
- **IUC-&lt;version&gt;-portable.zip** : sans installation. Décompresse le dossier où tu veux,
  puis double-clique sur `IUC.exe`. Pour l’enlever, supprime le dossier.

Au premier lancement, Windows peut afficher « Windows a protégé votre ordinateur » : IUC
n’est pas signé (la signature de code est payante). Clique sur **Informations
complémentaires**, puis **Exécuter quand même**.

L’interface s’ouvre dans ton navigateur. Garde la fenêtre noire ouverte pendant
l’utilisation ; la fermer arrête IUC.

**Prérequis** : Google Chrome ou Microsoft Edge, que IUC pilote dans une fenêtre dédiée.

**Tes données** restent sur ton ordinateur, dans `%LOCALAPPDATA%\IUC`, quel que soit le
format. La désinstallation les conserve ; supprime-les depuis IUC (« Supprimer mes données
locales »).

> L’automatisation n’est pas autorisée par les conditions d’utilisation d’Instagram : teste
> d’abord sur un compte secondaire. Voir le [README](https://github.com/GomuGomuNo01/Instagram-Unlike-Cleaner#readme).
