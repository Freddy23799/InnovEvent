from django.core.validators import MaxValueValidator
from django.db import models
from django.utils import timezone


class Provider(models.Model):
    class Category(models.TextChoices):
        # --- 1. Organisation & coordination ---
        WEDDING_PLANNER = "wedding_planner", "Wedding Planner / Event Planner"
        MC = "mc", "Maître de Cérémonie (MC) - Bilingue"
        PROTOCOL = "protocol", "Protocole / Hôtesses d'accueil"
        PCO_AGENCY = "pco_agency", "Agence PCO - Organisateur de Conférences / Salons"
        TEAM_BUILDING_COACH = "team_building_coach", "Coach / Formateur Team Building"
        # --- 2. Lieu & logistique de base ---
        VENUE_RENTAL = "venue_rental", "Location de salle / Villa / Domaine / Hôtel / Jardin / Piscine"
        TENT_RENTAL = "tent_rental", "Location de chapiteaux / Tentes / Bâches / Structures"
        FURNITURE_RENTAL = "furniture_rental", "Location de mobilier : Chaises (Tiffany, Chiavari, Plastique), Tables, Nappes, Housses"
        TABLEWARE_RENTAL = "tableware_rental", "Location de vaisselle / Verrerie / Couverts / Chauffe-plats"
        GENERATOR_ELECTRICIAN = "generator_electrician", "Location de Groupe Électrogène + Électricien / Technicien"
        SECURITY = "security", "Service de Sécurité / Agent / Videur / Sécurité rapprochée"
        CLEANING_SERVICE = "cleaning_service", "Service de Nettoyage / Remise en état"
        # --- 3. Décoration & scénographie ---
        DECORATION = "decoration", "Décorateur / Designer Événementiel / Scénographe"
        FLORIST = "florist", "Fleuriste événementiel"
        CENTERPIECE_RENTAL = "centerpiece_rental", "Location Décor : Centre de table, Arche, Backdrop, Moquette, Lustres"
        BALLOON_ARTIST = "balloon_artist", "Artiste Ballon / Décorateur Ballons organiques"
        LIGHTING = "lighting", "Éclairagiste d'ambiance / Éclairage architectural"
        # --- 4. Restauration & boissons ---
        CATERER = "caterer", "Traiteur / Chef à domicile / Buffet / Rôtisseur"
        PASTRY = "pastry", "Pâtissier / Cake Designer / Glacier / Fontaine Chocolat"
        BARTENDER = "bartender", "Barman / Mixologue / Service Bar Mobile"
        WAITSTAFF = "waitstaff", "Serveur / Serveuse Professionnel(le)"
        # --- 5. Image & souvenirs ---
        PHOTOGRAPHY = "photography", "Photographe (Mariage, Corporate, Anniversaire)"
        VIDEO = "video", "Vidéaste / Cameraman / Pilote Drone / Retransmission Live"
        PHOTOBOOTH = "photobooth", "Photobooth / Miroir Photo / 360° Booth / Audioguestbook"
        # --- 6. Son, musique & lumière ---
        DJ = "dj", "DJ / Disc-Jockey"
        SOUND = "sound", "Technicien Sonorisation / Location Sono Complète / Traducteur Simultané"
        STAGE_LIGHTING = "stage_lighting", "Technicien Lumière / Jeux de lumière / Fumigène / Écran LED"
        LIVE_BAND = "live_band", "Groupe Live / Orchestre / Artiste / Chanteur / Saxophoniste"
        # --- 7. Animation & spectacle ---
        ANIMATION = "animation", "Animateur / Danseurs / Troupe de danse"
        ENTERTAINER = "entertainer", "Humoriste / Magicien / Cracheur de feu / Échassier"
        MASCOT = "mascot", "Mascottes / Personnages pour enfants / Clown"
        GAMES_RENTAL = "games_rental", "Location de Jeux : Château Gonflable, Trampoline, Jeux en bois, Baby-foot"
        # --- 8. Beauté, mode & tenue ---
        MAKEUP_ARTIST = "makeup_artist", "Maquilleuse (MUA) / Coiffeuse / Prothésiste Ongulaire"
        STYLIST = "stylist", "Styliste / Créateur de Robes / Tailleur Costume sur-mesure"
        COSTUME_RENTAL = "costume_rental", "Location de Tenues Traditionnelles / Costumes / Voiles"
        JEWELER = "jeweler", "Bijoutier / Créateur d'Alliances / Loueur de Bijoux"
        # --- 9. Transport & hébergement ---
        LUXURY_CAR_RENTAL = "luxury_car_rental", "Location de Voitures de Luxe / Limousine / Voiture Mariés"
        GUEST_TRANSPORT = "guest_transport", "Location de Bus / Navette / Transport Invités / Voiturier"
        HOTEL_BOOKING = "hotel_booking", "Réservation Hôtel / Hébergement Invités / Accueil Aéroport"
        # --- 10. Support & impression ---
        PRINTING = "printing", "Imprimeur : Faire-part, Invitations, Menus, Badges, Roll-up, Kakemono, Banderoles"
        CHILDCARE_SERVICE = "childcare_service", "Service Nounou / Gardiennage d'Enfants pour événement"
        TROPHY_RENTAL = "trophy_rental", "Loueur de Trophées / Awards pour Gala"
        # --- Catégories historiques conservées (anciens profils / autres marketplaces) ---
        ICE_CREAM_FOUNTAIN = "ice_cream_fountain", "Glacier / Fontaine à chocolat"
        GUESTBOOK = "guestbook", "Livre d'or / Audioguest"
        HAIRDRESSER = "hairdresser", "Coiffeuse"
        MANICURE = "manicure", "Manucure / Onglerie"
        WEBSITE_CREATOR = "website_creator", "Créateur de site web pour l'événement"
        IMPRESARIO = "impresario", "Impresario"
        GRAPHIC_DESIGN = "graphic_design", "Graphisme & infographie"
        EQUIPMENT_RENTAL = "equipment_rental", "Location de matériel"
        VENUE_MANAGER = "venue_manager", "Responsable de salle"
        AGENCY = "agency", "Agence événementielle"
        INTERIOR_ARCHITECT = "interior_architect", "Architecte / designer d'intérieur"
        OTHER = "other", "Autre"

        # --- Décoration & design intérieur — 5 familles de métiers (marketplace "interior_design") ---
        # 1. Conception & études
        LANDSCAPE_ARCHITECT = "landscape_architect", "Architecte d'extérieur / Paysagiste"
        INTERIOR_DECORATOR = "interior_decorator", "Décorateur d'intérieur"
        HOME_STAGER = "home_stager", "Home Stager"
        DESIGN_3D_VISUALIZER = "design_3d_visualizer", "Dessinateur 3D / Visualiseur"
        TECHNICAL_DESIGN_OFFICE = "technical_design_office", "Bureau d'études (plans techniques)"
        # 2. Aménagement intérieur — Second œuvre
        CARPENTRY_JOINERY = "carpentry_joinery", "Menuiserie / Ébénisterie (cuisine, dressing sur-mesure)"
        PAINTING_WALL_COVERINGS = "painting_wall_coverings", "Peinture & Revêtements muraux"
        TILING_FLOORING = "tiling_flooring", "Carrelage & Revêtements de sol"
        CEILING_STAFF_WORK = "ceiling_staff_work", "Plafonds & Staff"
        HOME_ELECTRICIAN_LIGHTING = "home_electrician_lighting", "Électricité & Éclairage"
        PLUMBING_SANITARY = "plumbing_sanitary", "Plomberie & Sanitaire"
        # 3. Aménagement extérieur
        GARDEN_LANDSCAPING = "garden_landscaping", "Aménagement de jardin & espaces verts"
        TERRACE_PERGOLA_POOLHOUSE = "terrace_pergola_poolhouse", "Terrasse, pergola, pool house"
        POOL_BUILDER = "pool_builder", "Pisciniste"
        FACADE_FENCING_GATES = "facade_fencing_gates", "Façade, clôture & portails"
        OUTDOOR_LIGHTING = "outdoor_lighting", "Éclairage extérieur"
        # 4. Mobilier, matériaux & décoration
        CUSTOM_STANDARD_FURNITURE = "custom_standard_furniture", "Mobilier sur-mesure & standard"
        LIGHTING_FIXTURES = "lighting_fixtures", "Luminaires"
        FABRICS_CURTAINS_LINENS = "fabrics_curtains_linens", "Tissus, rideaux, linge de maison"
        DECOR_ART_OBJECTS = "decor_art_objects", "Objets déco & art"
        MATERIAL_SUPPLIERS = "material_suppliers", "Fournisseurs de matériaux (bois, pierre, carrelage, peinture)"
        # 5. Exécution & services complémentaires
        GENERAL_CONTRACTOR = "general_contractor", "Entreprise générale / Maître d'œuvre"
        MOVING_INSTALLATION = "moving_installation", "Déménagement & Installation"
        POST_CONSTRUCTION_CLEANING = "post_construction_cleaning", "Nettoyage fin de chantier"
        INTERIOR_PHOTOGRAPHER = "interior_photographer", "Photographe d'intérieur"

    name = models.CharField(max_length=200)
    category = models.CharField(max_length=30, choices=Category.choices)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=30, blank=True)
    address = models.CharField(max_length=300, blank=True)
    city = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    price_range = models.CharField(max_length=100, blank=True, help_text="Ex: 50 000 - 150 000 XAF")
    identity_number = models.CharField(
        max_length=50, blank=True, help_text="Numéro de pièce d'identité ou d'immatriculation du prestataire"
    )
    photo = models.ImageField(upload_to="providers/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    discount_percent = models.PositiveSmallIntegerField(default=0, validators=[MaxValueValidator(90)])
    discount_label = models.CharField(max_length=100, blank=True, help_text="Ex: Offre de rentrée")
    discount_valid_until = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category", "name"]

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"

    def is_currently_available(self):
        from apps.bookings.models import Booking

        now = timezone.now()
        return not self.bookings.filter(
            status__in=[Booking.Status.PENDING, Booking.Status.CONFIRMED],
            start_datetime__lte=now,
            end_datetime__gte=now,
        ).exists()

    def has_active_discount(self):
        if self.discount_percent <= 0:
            return False
        if self.discount_valid_until and self.discount_valid_until < timezone.now().date():
            return False
        return True

    def average_rating(self):
        from django.db.models import Avg

        return self.reviews.aggregate(avg=Avg("rating"))["avg"]

    def review_count(self):
        return self.reviews.count()
