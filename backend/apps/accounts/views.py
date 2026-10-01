from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, status, viewsets
from rest_framework.filters import SearchFilter
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from rest_framework.decorators import action

from apps.audit.utils import log_action
from apps.notifications.services import send_reminder, send_transactional_email

from .permissions import IsAdmin
from .serializers import (
    AdminUserSerializer,
    ChangePasswordSerializer,
    CustomTokenObtainPairSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    UserSerializer,
)
User = get_user_model()


FAILED_LOGIN_MAX_ATTEMPTS = 5
FAILED_LOGIN_WINDOW_SECONDS = 15 * 60
FAILED_LOGIN_LOCKOUT_SECONDS = 15 * 60


def _login_attempts_key(identifier):
    return f"login_failed:{identifier.strip().lower()}"


def _login_lockout_key(identifier):
    return f"login_lockout:{identifier.strip().lower()}"


class CustomTokenObtainPairView(TokenObtainPairView):
    """Le rate limiting DRF (`throttle_scope="auth"`, 10/min) protège déjà par
    IP, mais un attaquant distribué (IP rotatives) pourrait rester sous ce seuil
    tout en martelant un seul compte précis — ce verrouillage par IDENTIFIANT
    (compteur Redis, fenêtre glissante) comble ce trou (section 12 du CDC)."""

    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request, *args, **kwargs):
        from django.core.cache import cache

        identifier = str(request.data.get("username") or "").strip()
        if identifier:
            if cache.get(_login_lockout_key(identifier)):
                # Message générique — ne confirme jamais que le compte existe.
                return Response(
                    {"detail": "Trop de tentatives échouées. Réessayez dans quelques minutes."},
                    status=429,
                )

        # `TokenObtainPairView.post` lève `AuthenticationFailed` (via
        # `serializer.is_valid(raise_exception=True)`) plutôt que de renvoyer
        # une Response 401 — il faut l'intercepter ici pour compter l'échec,
        # puis la relaisser remonter pour que DRF produise la même réponse
        # qu'avant (comportement API inchangé).
        try:
            response = super().post(request, *args, **kwargs)
        except Exception:
            if identifier:
                attempts_key = _login_attempts_key(identifier)
                attempts = cache.get(attempts_key, 0) + 1
                cache.set(attempts_key, attempts, timeout=FAILED_LOGIN_WINDOW_SECONDS)
                if attempts >= FAILED_LOGIN_MAX_ATTEMPTS:
                    cache.set(_login_lockout_key(identifier), True, timeout=FAILED_LOGIN_LOCKOUT_SECONDS)
                    log_action(actor=None, action="auth.account_lockout", metadata={"identifier": identifier})
            raise

        if identifier and response.status_code == 200:
            cache.delete(_login_attempts_key(identifier))
        return response


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        log_action(actor=None, action="user.register", metadata={"email": request.data.get("email")})
        return response


class AdminUserViewSet(viewsets.ModelViewSet):
    """Gestion des comptes utilisateurs, réservée aux administrateurs (section 22)."""

    queryset = User.objects.all().order_by("-date_joined")
    serializer_class = AdminUserSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ["role", "is_active"]
    search_fields = ["username", "email", "first_name", "last_name"]

    def perform_create(self, serializer):
        user = serializer.save()
        log_action(actor=self.request.user, action="user.admin_create", metadata={"user_id": user.id, "role": user.role})

    def perform_update(self, serializer):
        user = serializer.save()
        log_action(actor=self.request.user, action="user.admin_update", metadata={"user_id": user.id, "role": user.role})

    @action(detail=True, methods=["post"])
    def remind(self, request, pk=None):
        """Relance manuelle d'un client (ex: réservation ou paiement en attente),
        envoyée en notification in-app + email + SMS."""
        user = self.get_object()
        message = request.data.get("message", "")
        send_reminder(user, custom_message=message)
        log_action(actor=request.user, action="user.remind", metadata={"user_id": user.id})
        return Response({"detail": f"Rappel envoyé à {user.get_full_name() or user.username}."})


class LogoutView(APIView):
    """Invalide le refresh token courant (blacklist SimpleJWT)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response({"detail": "Le champ 'refresh' est requis."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            return Response({"detail": "Token invalide ou déjà expiré."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_205_RESET_CONTENT)


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(serializer.validated_data["old_password"]):
            return Response({"old_password": "Mot de passe actuel incorrect."}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])
        log_action(actor=user, action="user.change_password")
        return Response({"detail": "Mot de passe mis à jour."})


class PasswordResetRequestView(APIView):
    """Envoie un email de réinitialisation. Répond toujours 200, y compris si
    l'email est inconnu, pour ne pas révéler l'existence d'un compte."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        user = User.objects.filter(email__iexact=email).first()
        if user:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_link = f"{settings.CORS_ALLOWED_ORIGINS[0] if settings.CORS_ALLOWED_ORIGINS else ''}/reset-password?uid={uid}&token={token}"
            send_transactional_email(
                recipient_email=user.email,
                subject="InnovEvent-GS — Réinitialisation de votre mot de passe",
                template_name="password_reset",
                context={"user": user, "reset_link": reset_link},
            )
        return Response({"detail": "Si un compte existe pour cet email, un lien de réinitialisation a été envoyé."})


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            uid = force_str(urlsafe_base64_decode(data["uid"]))
            user = User.objects.get(pk=uid)
        except (User.DoesNotExist, ValueError, TypeError, OverflowError):
            return Response({"detail": "Lien de réinitialisation invalide."}, status=status.HTTP_400_BAD_REQUEST)

        if not default_token_generator.check_token(user, data["token"]):
            return Response({"detail": "Lien de réinitialisation invalide ou expiré."}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(data["new_password"])
        user.save(update_fields=["password"])
        log_action(actor=user, action="user.reset_password")
        return Response({"detail": "Mot de passe réinitialisé avec succès."})
