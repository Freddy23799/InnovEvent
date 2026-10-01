from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    is_premium = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name", "city",
            "role", "phone", "avatar", "is_verified", "date_joined",
            "is_premium", "premium_until",
        ]
        read_only_fields = ["id", "role", "is_verified", "date_joined", "is_premium", "premium_until"]


class RegisterSerializer(serializers.ModelSerializer):
    """Inscription différenciée par profil (section 5 du CDC) : les champs
    communs (username/email/.../ville) sont toujours acceptés, et selon
    `profile_type`, des champs propres à Professionnel / Entreprise / Talent
    permettent de créer le profil dédié dans la foulée — sans jamais
    introduire de nouveau `User.Role` (Entreprise et Talent restent des
    comptes `role="partner"`, comme Professionnel, distingués par QUEL profil
    leur est rattaché, exactement le motif déjà utilisé par
    `ProfessionalProfile.user`/`Carrier.user`/`Driver.user`)."""

    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    # L'inscription publique ne permet de choisir qu'entre client, participant et
    # partenaire (prestataire) : les rôles organisateur/employé/admin restent
    # attribués par un administrateur.
    role = serializers.ChoiceField(
        choices=[(User.Role.CLIENT, "Client"), (User.Role.PARTICIPANT, "Participant"), (User.Role.PARTNER, "Prestataire")],
        default=User.Role.PARTICIPANT,
    )
    referral_code = serializers.CharField(write_only=True, required=False, allow_blank=True)

    # Détermine QUEL profil dédié est créé en plus du compte — indépendant de
    # `role` (client/participant restent des comptes simples ; professionnel/
    # entreprise/talent sont tous les 3 des comptes `role="partner"`).
    profile_type = serializers.ChoiceField(
        choices=[("none", "Aucun"), ("professionnel", "Professionnel"), ("entreprise", "Entreprise"), ("talent", "Talent")],
        required=False, default="none", write_only=True,
    )

    # --- Professionnel (apps.marketplace.ProfessionalProfile) ---
    business_name = serializers.CharField(required=False, allow_blank=True, write_only=True)
    category = serializers.CharField(required=False, allow_blank=True, write_only=True)
    description = serializers.CharField(required=False, allow_blank=True, write_only=True)
    price_range = serializers.CharField(required=False, allow_blank=True, write_only=True)

    # --- Entreprise (apps.companies.CompanyProfile) ---
    raison_sociale = serializers.CharField(required=False, allow_blank=True, write_only=True)
    activite = serializers.CharField(required=False, allow_blank=True, write_only=True)
    rccm = serializers.CharField(required=False, allow_blank=True, write_only=True)
    niu = serializers.CharField(required=False, allow_blank=True, write_only=True)
    adresse = serializers.CharField(required=False, allow_blank=True, write_only=True)
    representant = serializers.CharField(required=False, allow_blank=True, write_only=True)

    # --- Talent (apps.talents.TalentProfile) ---
    formation = serializers.CharField(required=False, allow_blank=True, write_only=True)
    competences = serializers.CharField(required=False, allow_blank=True, write_only=True)
    experience = serializers.CharField(required=False, allow_blank=True, write_only=True)
    disponibilite = serializers.CharField(required=False, allow_blank=True, write_only=True)
    opportunity_type = serializers.CharField(required=False, allow_blank=True, write_only=True)

    class Meta:
        model = User
        fields = [
            "username", "email", "first_name", "last_name", "phone", "city",
            "password", "password_confirm", "role", "referral_code", "profile_type",
            "business_name", "category", "description", "price_range",
            "raison_sociale", "activite", "rccm", "niu", "adresse", "representant",
            "formation", "competences", "experience", "disponibilite", "opportunity_type",
        ]

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password_confirm"):
            raise serializers.ValidationError({"password_confirm": "Les mots de passe ne correspondent pas."})
        profile_type = attrs.get("profile_type", "none")
        if profile_type == "professionnel" and not attrs.get("business_name"):
            raise serializers.ValidationError({"business_name": "Le nom de votre entreprise/activité est requis."})
        if profile_type == "entreprise" and not attrs.get("raison_sociale"):
            raise serializers.ValidationError({"raison_sociale": "La raison sociale est requise."})
        if profile_type == "talent" and not (attrs.get("first_name") or attrs.get("last_name")):
            raise serializers.ValidationError({"first_name": "Votre nom est requis pour un profil talent."})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        referral_code = validated_data.pop("referral_code", "")
        profile_type = validated_data.pop("profile_type", "none")

        professional_fields = {
            key: validated_data.pop(key, "") for key in ["business_name", "category", "description", "price_range"]
        }
        company_fields = {
            key: validated_data.pop(key, "") for key in ["raison_sociale", "activite", "rccm", "niu", "adresse", "representant"]
        }
        talent_fields = {
            key: validated_data.pop(key, "") for key in ["formation", "competences", "experience", "disponibilite", "opportunity_type"]
        }

        # Professionnel/Entreprise/Talent sont tous les 3 des comptes
        # `role="partner"` — le formulaire d'inscription peut envoyer
        # `role=client` par défaut, on le corrige ici selon `profile_type`.
        if profile_type in ("professionnel", "entreprise", "talent"):
            validated_data["role"] = User.Role.PARTNER

        with transaction.atomic():
            user = User(**validated_data)
            user.set_password(password)
            user.save()

            if profile_type == "professionnel":
                from apps.marketplace.models import MarketplaceType, ProfessionalProfile

                ProfessionalProfile.objects.create(
                    user=user,
                    marketplace_type=MarketplaceType.ACTORS,
                    category=professional_fields["category"],
                    business_name=professional_fields["business_name"],
                    description=professional_fields["description"],
                    price_range=professional_fields["price_range"] or "",
                    city=user.city,
                    contact_phone=user.phone,
                    contact_email=user.email,
                )
            elif profile_type == "entreprise":
                from apps.companies.models import CompanyProfile

                CompanyProfile.objects.create(
                    user=user,
                    raison_sociale=company_fields["raison_sociale"],
                    activite=company_fields["activite"],
                    rccm=company_fields["rccm"],
                    niu=company_fields["niu"],
                    adresse=company_fields["adresse"],
                    representant=company_fields["representant"],
                    phone=user.phone,
                    email=user.email,
                )
            elif profile_type == "talent":
                from apps.talents.models import TalentProfile

                TalentProfile.objects.create(
                    user=user,
                    full_name=user.get_full_name() or user.username,
                    formation=talent_fields["formation"],
                    competences=talent_fields["competences"],
                    experience=talent_fields["experience"],
                    city=user.city,
                    disponibilite=talent_fields["disponibilite"] or TalentProfile.Availability.TO_DEFINE,
                    opportunity_type=talent_fields["opportunity_type"] or TalentProfile.OpportunityType.ONE_OFF,
                )

        if referral_code:
            from apps.referrals.services import register_referral

            register_referral(referral_code, user, self.context.get("request"))

        return user


class AdminUserSerializer(serializers.ModelSerializer):
    """Gestion des comptes par un administrateur (section 22 du CDC) : peut fixer
    le rôle et l'état du compte, contrairement à UserSerializer (auto-profil)."""

    password = serializers.CharField(write_only=True, required=False, allow_blank=True, validators=[validate_password])
    is_online = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name", "role",
            "phone", "is_active", "is_verified", "password", "last_seen", "is_online", "date_joined",
        ]
        read_only_fields = ["id", "last_seen", "is_online", "date_joined"]

    def get_is_online(self, obj):
        return obj.is_online()

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Ajoute le rôle dans le payload du JWT pour éviter un aller-retour API
    supplémentaire côté frontend au chargement de l'application."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        token["full_name"] = user.get_full_name() or user.username
        return token


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, validators=[validate_password])


    access_token = serializers.CharField()
