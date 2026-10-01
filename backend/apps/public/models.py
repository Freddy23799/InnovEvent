from django.db import models


class PackItem(models.Model):
    """Élément constitutif d'un pack (« Nos packs », LandingMedia.category=pack) :
    relie le pack à une ressource réellement réservable (salle, prestataire ou
    matériel), afin que le client puisse consulter le détail d'un pack via
    « Découvrir le pack » et commander séparément tel ou tel élément, avec sa
    propre quantité, en réutilisant le parcours de réservation existant."""

    class ResourceType(models.TextChoices):
        VENUE = "venue", "Salle"
        PROVIDER = "provider", "Prestataire"
        EQUIPMENT = "equipment", "Matériel"

    pack = models.ForeignKey(
        "LandingMedia", on_delete=models.CASCADE, related_name="items",
        limit_choices_to={"category": "pack"},
    )
    resource_type = models.CharField(max_length=20, choices=ResourceType.choices)
    venue = models.ForeignKey("venues.Venue", on_delete=models.CASCADE, null=True, blank=True, related_name="pack_items")
    provider = models.ForeignKey("providers.Provider", on_delete=models.CASCADE, null=True, blank=True, related_name="pack_items")
    equipment = models.ForeignKey("equipment.Equipment", on_delete=models.CASCADE, null=True, blank=True, related_name="pack_items")
    default_quantity = models.PositiveIntegerField(default=1, help_text="Utilisé pour le matériel (nombre d'unités suggéré)")
    is_optional = models.BooleanField(default=False, help_text="Élément additionnel proposé en option, non inclus par défaut dans le pack")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["pack", "order", "id"]

    def __str__(self):
        return f"{self.pack.label} — {self.resource_name}"

    @property
    def resource(self):
        return {"venue": self.venue, "provider": self.provider, "equipment": self.equipment}.get(self.resource_type)

    @property
    def resource_name(self):
        resource = self.resource
        return resource.name if resource else "—"


class LandingMedia(models.Model):
    """Photothèque de la page d'accueil publique (vitrine « INNOVEVENT GROUP »).

    Gérée entièrement par l'administration (ajout/modification/suppression) mais
    lue sans authentification par la page publique, catégorie par catégorie
    (décoration, formation, réalisations, location de matériel)."""

    class Category(models.TextChoices):
        DECO = "deco", "Décoration"
        FORMATION = "formation", "Formation (Academy)"
        REALISATION = "realisation", "Réalisations (portfolio)"
        ACCESSOIRE = "accessoire", "Location de matériel"
        PACK = "pack", "Nos packs (offres tarifées)"

    class Scope(models.TextChoices):
        PRIVE = "prive", "Événements privés"
        PUBLIC = "public", "Événements grand public"

    class Tier(models.TextChoices):
        HAUT = "haut", "Haut de gamme"
        MOYEN = "moyen", "Moyenne gamme"
        PETIT = "petit", "Petite gamme"

    category = models.CharField(max_length=20, choices=Category.choices)
    scope = models.CharField(
        max_length=10, choices=Scope.choices, blank=True,
        help_text="Événements privés ou grand public — catégorie « Réalisations » uniquement.",
    )
    tag = models.CharField(
        max_length=50, blank=True,
        help_text=(
            "Type d'événement au sein du scope choisi (ex : Mariages Modernes, Anniversaires Adultes, Salons…). "
            "Texte libre : l'administrateur peut créer de nouveaux types à la volée. "
            "Utilisé pour le filtre de la galerie (catégorie « Réalisations » uniquement)."
        ),
    )
    tier = models.CharField(
        max_length=10, choices=Tier.choices, blank=True,
        help_text="Gamme de la réalisation : détermine l'ordre d'affichage (haut de gamme en premier) — catégorie « Réalisations » uniquement.",
    )
    image = models.ImageField(upload_to="landing/")
    label = models.CharField(max_length=150)
    caption = models.CharField(max_length=200, blank=True, help_text="Légende courte / description affichée sous l'image")
    price_label = models.CharField(
        max_length=100, blank=True,
        help_text="Prix indicatif affiché sur la page publique, ex : « 5 000 FCFA / chaise / jour » (catégorie « Location de matériel »)",
    )
    budget_label = models.CharField(
        max_length=100, blank=True,
        help_text="Prix du pack affiché sur la page publique, ex : « 1 200 000 FCFA » (catégorie « Nos packs »)",
    )
    order = models.PositiveIntegerField(default=0, help_text="Ordre d'affichage (croissant)")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category", "order", "-created_at"]
        verbose_name = "Média page d'accueil"
        verbose_name_plural = "Médias page d'accueil"

    def __str__(self):
        return f"[{self.get_category_display()}] {self.label}"
