# InnovEvent-GS

Plateforme de gestion événementielle — CDC-INNOVEVENT-2026-001.

Stack : **Django 5 / DRF** (backend) · **Vue 3 / Vite** (frontend) · **PostgreSQL** · **Redis** · **Docker Compose** · **Nginx**.

## 1. État d'avancement

**Priorité P0 — fonctionnelle de bout en bout :**
authentification JWT (inscription, connexion, refresh, déconnexion, mot de passe oublié), rôles
et permissions (admin/client/participant/employé), événements (budget, tâches, participants,
dépenses), salles, prestataires, matériel, réservations avec détection automatique des conflits,
billetterie (types de billets, achat, QR signé, PDF, contrôle d'accès par scan), paiements (mode
démonstration complet ; PayPal/FreemoPay/KOB posés en architecture mais nécessitent les
identifiants marchands réels avant activation), emails transactionnels, journal d'audit,
healthcheck, API documentée (Swagger `/api/docs/`).

**Priorité P1 — modules et interfaces disponibles :** messagerie (conversations/messages par
polling REST), assistant IA (fournisseur démo opérationnel sur les ressources de la base et
fournisseur LLM configurable), formations/enrôlement/attestations/badges, ainsi que RH et paie.
Les écrans correspondants sont présents dans l'application ; l'activation des intégrations externes
reste conditionnée à la configuration de leurs clés et services.

**Frontend Vue** : authentification, layout responsive avec sidebar repliable, design system,
dashboards par rôle, CRUD événements, réservations, billetterie publique, messagerie, assistant,
formations, RH/paie, marketplace et livraisons.

**Non fait à ce stade** : tests automatisés (section 23), graphiques analytiques du dashboard,
TLS/Let's Encrypt (à configurer sur le VPS cible), intégration réelle des passerelles de paiement,
CI/CD.

## 1bis. Connexion sociale (Google / Facebook)

Ajoutée en complément du CDC. Architecture : le frontend obtient un jeton auprès du fournisseur,
le backend le vérifie côté serveur (`apps/accounts/social.py`) puis émet les JWT internes
habituels — aucune API externe n'est appelée depuis le frontend pour la vérification.

Pour l'activer réellement :
1. **Google** : créer un identifiant OAuth "Web application" dans Google Cloud Console, ajouter
   `http://localhost:5173` (et le domaine de prod) aux origines JavaScript autorisées, puis
   renseigner `GOOGLE_CLIENT_ID` (backend/.env) et `VITE_GOOGLE_CLIENT_ID` (frontend/.env) avec le
   même Client ID.
2. **Facebook** : créer une app sur developers.facebook.com, activer "Connexion Facebook", ajouter
   le domaine autorisé, puis renseigner `FACEBOOK_APP_ID` + `FACEBOOK_APP_SECRET` (backend/.env,
   le secret ne quitte jamais le serveur) et `VITE_FACEBOOK_APP_ID` (frontend/.env).

Sans ces variables, les boutons restent visibles mais renvoient un message clair
("non configuré") plutôt qu'une erreur technique. Un compte créé via connexion sociale reçoit
automatiquement le rôle Participant (comme l'inscription classique) et un mot de passe
inutilisable (`set_unusable_password`) puisqu'il ne s'authentifie que via le fournisseur.

## 2. Démarrage rapide (Docker)

```bash
cp backend/.env.example backend/.env      # renseigner les secrets
cp frontend/.env.example frontend/.env    # optionnel en dev (Vite lit VITE_API_BASE_URL)
docker compose up --build
```

Le fichier `backend/.env.example` est réglé pour un déploiement derrière HTTPS.
Pour un lancement local en HTTP, mettez `DJANGO_DEBUG=True` et ajoutez
`http://localhost:5173` à `CORS_ALLOWED_ORIGINS` si le frontend Vite appelle
directement l'API. Pour les paiements simulés locaux, mettez aussi
`PAYMENTS_DEMO_MODE=True`. Avant toute mise en production, remettez `DJANGO_DEBUG=False`,
`PAYMENTS_DEMO_MODE=False` et configurez l'ingress HTTPS décrit dans
[`SECURITY.md`](SECURITY.md). Le proxy Nginx fourni ne termine pas TLS.

Au premier démarrage sur une base vide, le backend crée automatiquement un super-administrateur
complet après les migrations. Renseignez impérativement `INITIAL_ADMIN_PASSWORD` (ainsi que les
identifiants `INITIAL_ADMIN_*`) dans `backend/.env` avant un déploiement : le backend refuse de
démarrer sans ce mot de passe tant qu'aucun super-administrateur actif n'existe. Les secrets ne
sont jamais affichés dans les journaux. Une fois ce compte créé, les redémarrages ne le modifient
pas. Il peut ensuite être administré dans **Administration → Utilisateurs**. Les commandes
`seed_*_demo` sont réservées aux environnements de démonstration et ne doivent pas être exécutées
en production.

Les 30 photos de la vitrine sont intégrées au déploiement et sont importées automatiquement au
premier démarrage uniquement si la photothèque est vide. PostgreSQL conserve les métadonnées et
les chemins des médias ; les fichiers sont conservés durablement dans le volume Docker
`backend_media`. Les images ajoutées ou supprimées depuis l'administration ne sont jamais
écrasées au redémarrage.

### Hébergement cPanel (sans Docker/Nginx)

Sur cPanel, Nginx n'est généralement pas utilisé : le site Python est servi par Apache/Passenger.
Les images et documents ne sont pas stockés dans PostgreSQL : ils sont déposés dans `MEDIA_ROOT`
(par défaut `backend/media/`) et la base conserve leur chemin. Définissez un `MEDIA_ROOT`
persistant dans les variables d'environnement du backend, par exemple
`/home/VOTRE_COMPTE/innovevent/backend/media`, puis configurez Apache/cPanel pour publier ce
dossier sous `MEDIA_URL=/media/`. Si le frontend et l'API sont sur deux domaines différents,
utilisez une URL absolue, par exemple `MEDIA_URL=https://api.votre-domaine.example/media/`.
Sans cette publication `/media/`, les photos téléversées existent sur le disque mais ne peuvent
pas s'afficher dans le navigateur. Les photos publiques de la page d'accueil
(`/media/landing/...`) disposent aussi d'un fallback Django sécurisé sur
cPanel/Passenger : elles restent accessibles même sans alias Apache, tandis
que les documents privés ne sont pas exposés.

Application accessible sur `http://localhost/`, API sur `http://localhost/api/v1/`, documentation
Swagger sur `http://localhost/api/docs/`, admin Django sur `http://localhost/admin/`.

### Développement sans Docker

Backend : `python -m venv .venv && pip install -r backend/requirements.txt`, PostgreSQL et Redis
locaux, puis `python manage.py migrate && python manage.py runserver`.
Frontend : `npm install && npm run dev` dans `frontend/` (nécessite Node 20+).

## 3. Architecture

```
backend/
  config/            # settings, urls, wsgi/asgi
  apps/
    accounts/        # utilisateur unique + rôle, JWT, permissions par rôle
    events/          # événements, tâches, participants, dépenses
    venues/ providers/ equipment/   # catalogues gérés par l'admin
    bookings/        # réservations + vérification de conflits
    tickets/         # types de billets, achat, QR signé, PDF, scan
    payments/        # transactions, passerelles interchangeables
    notifications/   # emails transactionnels (templates HTML brandés)
    messaging/       # conversations internes
    ai_assistant/     # assistant IA, fournisseur interchangeable
    training/        # formations, enrôlement, attestations, badges
    employees/ payroll/   # RH et fiches de paie
    documents/       # gabarits PDF/QR partagés (pas de modèle propre)
    audit/           # journal d'activité + healthcheck

frontend/
  src/
    router/ stores/ services/   # routage, état (Pinia), client API (axios + refresh JWT)
    layouts/ components/        # coquille applicative, sidebar repliable
    views/auth/ dashboard/ events/
    assets/styles/design-system.css   # charte InnovEvent (boutons, cartes, badges, tables…)
```

### Modèle de données — relations clés

- `User` (rôle unique : admin/client/participant/employee) est référencé par la quasi-totalité
  des entités métier (organizer, owner, created_by…), plutôt que 4 tables utilisateur séparées.
- `Event` → `EventTask`, `EventParticipant`, `EventExpense`, `TicketType`, `Booking` (1-N).
- `Booking` référence exactement une ressource (`Venue` **ou** `Provider` **ou** `Equipment`) via
  `resource_type` + FK correspondante ; la détection de conflit interroge les réservations actives
  qui se chevauchent dans le temps sur la même ressource.
- `TicketType` → `Ticket` (1-N) ; `Ticket` → `Payment` (N-1, un paiement peut couvrir plusieurs
  billets achetés en une fois).
- `Enrollment` (formation) génère un `matricule` unique et centralise `Settlement` (règlements) et
  `Certificate` (1-1, délivrée seulement si l'inscription est validée par un administrateur).
- `Badge` référence directement `User` (fonctionne aussi bien pour un participant qu'un employé).

## 4. Principaux endpoints API (`/api/v1/`)

| Domaine | Endpoints clés |
|---|---|
| Auth | `auth/register/`, `auth/login/`, `auth/refresh/`, `auth/logout/`, `auth/me/`, `auth/password-reset/` |
| Événements | `events/`, `events/tasks/`, `events/participants/`, `events/expenses/` |
| Catalogues | `venues/`, `providers/`, `equipment/` |
| Réservations | `bookings/` |
| Billetterie | `tickets/types/`, `tickets/purchase/`, `tickets/my/`, `tickets/my/{id}/pdf/`, `tickets/my/{id}/qr/`, `tickets/scan/` |
| Paiements | `payments/`, `payments/webhooks/{paypal,mobile-money,kob}/` |
| Messagerie | `messaging/conversations/`, `messaging/messages/`, `messaging/messages/mark-read/` |
| Assistant IA | `ai-assistant/ask/`, `ai-assistant/conversations/` |
| Formations | `training/`, `training/enrollments/`, `training/enrollments/{id}/validate/`, `training/settlements/`, `training/certificates/`, `training/badges/` |
| RH / Paie | `employees/`, `payroll/`, `payroll/{id}/pdf/` |
| Système | `health/`, `api/docs/` (Swagger), `api/schema/` |

Toutes les routes (hors inscription/connexion/health) exigent un JWT `Authorization: Bearer …` et
appliquent une permission par rôle (voir `apps/accounts/permissions.py`).

## 5. Design system

Couleurs de la charte InnovEvent (`frontend/src/assets/styles/design-system.css`) :
rouge `#C0272D` (action/accent), bleu-gris `#39495B` (navigation/titres), fond `#FFFFFF`/`#FCFCFC`,
rouge doux `#F6E2E3` (états doux). Composants de base : `.ie-btn` (primary/secondary/danger/ghost),
`.ie-card`, `.ie-input`, `.ie-badge` (success/warning/danger/neutral), `.ie-table`, `.ie-skeleton`,
`.ie-empty-state`, `.ie-toast`. Layout : sidebar fixe desktop / repliable mobile, topbar avec rôle
et déconnexion.

## 6. Sécurité (section 15 du CDC)

JWT access (15 min) + refresh (7 jours) avec rotation et blacklist ; mots de passe hachés par
Django (PBKDF2) avec validateurs renforcés (12+ caractères) ; rate limiting par scope (auth, achat
de billet, scan QR) via le cache Redis ; permissions par rôle sur chaque endpoint ; QR codes de
billets/attestations/badges signés côté serveur (`django.core.signing`) — un QR copié ou modifié
échoue la vérification ; secrets exclusivement en variables d'environnement (`.env`, jamais
commité — voir `.gitignore`) ; middleware d'audit journalisant toute requête API qui modifie des
données ; isolation stricte des données par rôle au niveau des querysets (jamais côté frontend
uniquement).

## 7. Points non précisés par le CDC — décisions prises

- **PDF** : ReportLab retenu plutôt que WeasyPrint (le CDC autorise l'un ou l'autre) — évite les
  dépendances système lourdes (Cairo/Pango complètes) tout en gardant un rendu maîtrisé aux
  couleurs InnovEvent.
- **Paiements réels** : l'architecture de passerelle interchangeable est posée (`apps/payments/gateways.py`)
  mais PayPal/FreemoPay/KOB nécessitent les comptes marchands et secrets réels d'InnovEvent — non
  fournis à ce stade. Le mode démonstration est pleinement opérationnel pour les tests et la
  recette (section 23 du CDC).
- **Assistant IA** : fournisseur démo (règles + données réelles de la base, sans invention de
  ressource) actif par défaut ; un fournisseur compatible API OpenAI est implémenté et prêt, à
  activer via `AI_PROVIDER`/`AI_PROVIDER_API_KEY` une fois une clé fournie.
- **Badges** : modèle unique référençant directement `User`, utilisable aussi bien pour un
  participant que pour un employé, plutôt que deux modèles dupliqués.
- **Messagerie temps réel** : implémentée par polling REST (mécanisme équivalent explicitement
  accepté par le CDC) plutôt que WebSocket, pour limiter la complexité d'infrastructure à ce stade ;
  une migration vers Django Channels reste possible sans changer le modèle de données.

## 8. Prochaines étapes suggérées

1. Compléter les parcours métier encore manquants et poursuivre la revue des erreurs/messages.
2. Suite de tests (pytest-django) couvrant permissions, achat de billet, conflits de réservation,
   validation QR — section 23 du CDC.
3. TLS/Let's Encrypt + nom de domaine sur le VPS cible, sauvegardes automatisées quotidiennes.
4. Activation des passerelles de paiement réelles dès réception des identifiants marchands.
# InnovEvent
