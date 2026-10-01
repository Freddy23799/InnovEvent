"""Permissions par rôle, réutilisées dans toute l'API (section 4 du CDC).

Toute vue métier doit déclarer explicitement quels rôles y accèdent : il n'y a pas
de permission par défaut permissive au-delà de IsAuthenticated (voir settings.REST_FRAMEWORK).
"""

from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAdmin(BasePermission):
    message = "Accès réservé aux administrateurs."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_admin_role)


class IsClient(BasePermission):
    message = "Accès réservé aux clients."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_client_role)


class IsOrganizer(BasePermission):
    message = "Accès réservé aux organisateurs."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_organizer_role)


class IsParticipant(BasePermission):
    message = "Accès réservé aux participants."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_participant_role)


class IsEmployee(BasePermission):
    message = "Accès réservé aux employés."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_employee_role)


class IsAdminClientOrOrganizer(BasePermission):
    """Gestion d'événement au sens large (tâches, invités, dépenses, réservations) :
    un client (événement privé) et un organisateur (événement public billetterie)
    gèrent tous deux leurs propres événements, en plus de l'administration."""

    message = "Accès réservé aux administrateurs, clients et organisateurs."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.is_admin_role or request.user.is_client_role or request.user.is_organizer_role)
        )


class IsAdminOrOrganizer(BasePermission):
    """Billetterie publique : seul un organisateur (ou l'administration) peut créer
    des types de billets — un client « particulier » ne vend pas de billets."""

    message = "Accès réservé aux administrateurs et aux organisateurs."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.is_admin_role or request.user.is_organizer_role)
        )


class IsAdminOrReadOnly(BasePermission):
    """Lecture publique/authentifiée, écriture réservée à l'administrateur.

    Utilisé pour les catalogues consultables par les organisateurs (salles,
    prestataires, matériel) mais gérés uniquement par l'administration (section 8).
    """

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        return bool(request.user and request.user.is_authenticated and request.user.is_admin_role)


class IsAdminOrPublicReadOnly(BasePermission):
    """Lecture publique (anonyme, sans authentification), écriture réservée à
    l'administrateur. Utilisé pour les contenus marketing de la page d'accueil
    (photothèque), consultables par tout visiteur mais gérés uniquement par
    l'administration."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated and request.user.is_admin_role)


class IsOwnerOrAdmin(BasePermission):
    """Isolation des données par rôle (section 15) : un objet n'est visible/modifiable
    que par son propriétaire (`owner_field` sur l'objet) ou par un administrateur.
    """

    owner_field = "organizer"

    def has_object_permission(self, request, view, obj):
        if request.user.is_admin_role:
            return True
        owner = getattr(obj, getattr(view, "owner_field", self.owner_field), None)
        return owner == request.user
