# Recette manuelle

Les tests automatiques tournent sur une fausse page des likes : ils ne remplacent pas un essai
sur le vrai Instagram. Cette recette se fait **sur un compte secondaire**, avec quelques dizaines
de likes, avant chaque version et après tout changement de `backend/app/browser/locators.py`.

Note pour chaque étape : date, résultat, et le numéro du nettoyage concerné.

## Préparation

- [ ] Installation propre en suivant le README (`pip install -e ".[dev]" -c constraints.txt`,
      `playwright install chromium`, `npm ci`, `npm run build`).
- [ ] `pytest` et `npm test` verts.
- [ ] Compte secondaire avec au moins 50 likes, dont plusieurs sur un même compte « à protéger ».

## Connexion

- [ ] `iuc serve` ouvre l’interface ; l’avertissement bloque tant que la case n’est pas cochée.
- [ ] « Ouvrir Instagram » ouvre une fenêtre Chromium ; la connexion manuelle (2FA comprise) est
      détectée sans rien saisir côté IUC.
- [ ] La fenêtre « Enregistrer vos informations de connexion ? » n’est jamais validée par IUC.
- [ ] Chromium ne propose pas d’enregistrer le mot de passe.

## Aperçu

- [ ] Critères : période, ordre, type, un compte ciblé, un compte protégé ; la liste des comptes
      s’affiche après un premier aperçu.
- [ ] L’aperçu ne contient que des likes conformes aux critères ; le compte protégé est absent.
- [ ] Décocher un like le garde ; « Tout décocher » puis « Tout cocher » fonctionnent.

## Nettoyage réel (quelques dizaines de likes)

- [ ] « Limiter ce lancement » à 20 : exactement 20 likes retirés, puis pause.
- [ ] Sur Instagram (page des likes rechargée, puis l’application mobile), les likes retirés ont
      disparu et les likes gardés sont toujours là.
- [ ] Pause pendant un lot : le lot se termine, puis le nettoyage passe en pause.
- [ ] Reprise : aucun like n’est retraité (le rapport ne compte aucun doublon).
- [ ] `DAILY_LIMIT` bas (par exemple 10) : arrêt à la limite avec le bon message.
- [ ] Le rapport, le CSV et le JSON concordent avec ce qui s’est passé.

## Robustesse

- [ ] Fermer la fenêtre Chromium pendant un nettoyage : arrêt propre, statut « en pause ».
- [ ] Se déconnecter d’Instagram dans la fenêtre entre deux lots : arrêt immédiat, message
      « Instagram t’a déconnecté », statut « en pause ».
- [ ] `Ctrl+C` sur `iuc serve` pendant un nettoyage : statut « en pause », reprise possible.
- [ ] Message d’Instagram (limite, vérification) s’il apparaît : arrêt immédiat, consigné ici.

## Données et confidentialité

- [ ] Aucun mot de passe ni cookie dans `data/logs` ni `data/diagnostics`
      (rechercher par exemple les premières lettres du mot de passe).
- [ ] « Se déconnecter d’Instagram » supprime seulement le profil du navigateur.
- [ ] « Supprimer mes données locales » vide `DATA_DIR` (le fichier `.env` est conservé).

## Interface

- [ ] Thèmes clair, sombre et système ; navigation au clavier ; affichage mobile (largeur 375).
- [ ] Aucune erreur dans la console du navigateur, aucune requête vers un autre hôte que
      `127.0.0.1`.
