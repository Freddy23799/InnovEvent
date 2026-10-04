# Sécurité du déploiement

## Protections intégrées

- Les API exigent une authentification par défaut. Les vues définissent leurs
  permissions et filtrent généralement leurs objets selon le propriétaire.
- Le JWT d'accès reste en mémoire dans le navigateur. Le JWT de renouvellement
  est un cookie `HttpOnly`, `SameSite=Lax`, limité aux routes d'authentification
  et marqué `Secure` quand `DJANGO_DEBUG=False`. Le renouvellement exige aussi
  l'en-tête `X-Requested-With`; les origines CORS doivent donc rester précises.
- Les WebSockets vérifient l'origine via `ALLOWED_HOSTS`, refusent les comptes
  inactifs et ne journalisent pas leur query string dans le Nginx fourni.
- Les paiements simulés sont activés par défaut seulement en mode DEBUG. Les
  webhooks exigent un secret, comparent ce secret en temps constant et verrouillent
  la transaction pour éviter le double traitement simultané.
- Les pièces jointes de messagerie sont validées, chiffrées au repos et servies
  avec un jeton signé de durée limitée. Les fichiers media autres que la
  photothèque publique ne sont pas exposés par les URL Django de production.
- Le conteneur backend n'expose plus directement son port sur l'hôte ; il reste
  accessible sur le réseau interne Docker par le reverse proxy.

## Configuration obligatoire en production

1. Garder `DJANGO_DEBUG=False`, définir `DJANGO_SECRET_KEY` avec une valeur
   aléatoire propre à l'environnement et régler `DJANGO_ALLOWED_HOSTS` sur les
   seuls noms d'hôte utilisés.
2. Terminer TLS sur un reverse proxy de confiance, transmettre
   `X-Forwarded-Proto: https` jusqu'à Nginx/Django et empêcher l'accès public
   direct à l'origine. Django active la redirection HTTPS et HSTS hors DEBUG.
   Le Nginx fourni est un proxy HTTP de développement/recette : il ne termine
   pas TLS. Ne publiez pas son port sans avoir mis en place l'ingress HTTPS et
   la restriction réseau attendus.
3. Renseigner `CORS_ALLOWED_ORIGINS` avec les origines exactes du frontend, sans
   joker. Les cookies d'authentification dépendent de cette liste pour tout
   appel frontend/backend cross-origin.
4. Définir `MESSAGING_ENCRYPTION_KEY` et `QR_SIGNING_SECRET` comme secrets
   aléatoires distincts, puis les sauvegarder de façon sûre. La clé de messages
   doit rester stable : la changer rend les messages historiques illisibles.
5. Mettre `PAYMENTS_DEMO_MODE=False` avant toute exposition publique. Les
   passerelles réelles PayPal, FreemoPay, KOB et carte ne sont pas encore
   implémentées dans `backend/apps/payments/gateways.py`; tant qu'elles ne le
   sont pas, aucun paiement réel ne peut être traité de façon fiable. Le secret
   webhook partagé actuel n'est pas un substitut aux signatures officielles
   des fournisseurs.
6. Garder PostgreSQL et Redis sur le réseau privé Docker, appliquer les mises à
   jour de dépendances, surveiller les journaux d'audit et tester régulièrement
   la restauration des sauvegardes.

## À traiter avant une mise en production financière

- Intégrer et vérifier les signatures webhook propres à chaque fournisseur,
  ainsi que le montant, la devise, la référence et l'état côté fournisseur.
- Ajouter une authentification multifacteur pour les comptes administrateurs.
- Ajouter des tests d'autorisation négatifs (IDOR) couvrant chaque rôle,
  notamment réservations, documents, événements et conversations.
- Définir une CSP adaptée au frontend et vérifier les en-têtes sur le domaine
  public après configuration de l'ingress HTTPS.
- Faire vérifier l'accès aux justificatifs d'identité et documents d'entreprise
  sur le serveur réel. Les répertoires de stockage privés ne doivent jamais être
  publiés directement par Apache/Nginx ou le panneau d'hébergement.

Ce document décrit les contrôles du dépôt. Il ne certifie pas la configuration
du fournisseur cloud, du DNS, du pare-feu, du proxy TLS ou des sauvegardes.
