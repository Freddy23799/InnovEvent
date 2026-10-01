from datetime import timedelta
from decimal import Decimal

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.bookings.models import Booking
from apps.employees.models import Employee
from apps.equipment.models import Equipment, Expense as EquipmentExpense, StockMovement
from apps.events.models import Event, EventExpense, EventTask
from apps.games.models import Quiz, QuizAttempt
from apps.marketplace.models import (
    CommissionSettings,
    MarketplaceListing,
    MarketplaceOrder,
    ProfessionalBlockedDate,
    ProfessionalBookingRequest,
    ProfessionalFavorite,
    ProfessionalProfile,
    Quote,
    QuoteLineItem,
    RequestedEquipmentItem,
)
from apps.payments.models import Payment
from apps.payroll.models import Payslip
from apps.providers.models import Provider
from apps.public.models import LandingMedia, PackItem
from apps.reviews.models import ProviderReview
from apps.venues.models import Venue

DEFAULT_COMMISSION_PERCENT = Decimal("5.00")


class Command(BaseCommand):
    """Complète les données de démonstration existantes (seed_demo,
    seed_fictional_professionals, seed_partner_demo, seed_organizer_demo) pour
    que TOUTES les fonctionnalités de la plateforme aient du contenu fictif à
    afficher — packs avec composants, devis à tous les stades, favoris, avis,
    tâches/dépenses d'événement, mouvements de stock, fiches de paie... Ne
    touche à aucune donnée réelle : entièrement idempotent (get_or_create), et
    s'arrête proprement si les données de base attendues sont absentes."""

    help = "Complète les données fictives sur l'ensemble de la plateforme (packs, devis, avis, RH, stock...)."

    def handle(self, *args, **options):
        with transaction.atomic():
            self.seed_pack_items()
            self.seed_quotes()
            self.seed_favorites_and_blocked_dates()
            self.seed_provider_reviews()
            self.seed_event_tasks_and_expenses()
            self.seed_equipment_stock_and_expenses()
            self.seed_employees_and_payslips()
            self.seed_sale_marketplace()
            self.seed_extra_bookings()
            self.seed_marketplace_orders()
            self.seed_quiz_attempts()
            self.seed_badges_and_commissions()
            self.seed_extra_equipment()
            self.seed_complete_equipment_request()
            self.seed_extra_packs()
        self.stdout.write(self.style.SUCCESS("Données fictives complétées sur l'ensemble de la plateforme."))

    # ------------------------------------------------------------ packs (+)
    def seed_extra_packs(self):
        """Beaucoup plus de packs fictifs (« Nos packs » côté page publique),
        chacun avec ses composants — pour que la page d'accueil et le
        catalogue de packs aient un contenu riche et varié à présenter,
        au-delà des 3 packs de base (Essentiel/Confort/Prestige)."""
        existing_photo = LandingMedia.objects.filter(category="pack").exclude(image="").first()
        if not existing_photo or not existing_photo.image:
            self.stdout.write("  - Packs additionnels ignorés (aucune photo de pack existante à réutiliser).")
            return

        # Réutilise des photos déco/réalisations déjà en place plutôt que d'en
        # générer de fausses — de vraies photos d'événements, juste réparties
        # sur davantage de packs pour la variété visuelle de la page publique.
        photo_pool = list(
            LandingMedia.objects.filter(category__in=["pack", "deco", "realisation"]).exclude(image="").values_list("image", flat=True)
        )
        if not photo_pool:
            photo_pool = [existing_photo.image.name]

        def photo_for(index):
            name = photo_pool[index % len(photo_pool)]
            try:
                with existing_photo.image.storage.open(name, "rb") as f:
                    return ContentFile(f.read(), name=name.split("/")[-1])
            except FileNotFoundError:
                return None

        venues = list(Venue.objects.all())
        providers = list(Provider.objects.all())
        equipment = list(Equipment.objects.all())
        if not venues or not providers or not equipment:
            self.stdout.write("  - Packs additionnels ignorés (salles/prestataires/matériel manquants).")
            return

        PACKS = [
            {
                "label": "Pack Mariage Élégance", "tier": "haut", "budget_label": "3 500 000 FCFA",
                "caption": "Décoration florale premium, salle de réception haut de gamme, DJ et sonorisation, service traiteur complet, photographe professionnel",
                "items": [("venue", 0, False), ("provider", 0, False), ("provider", 1, False), ("equipment", 0, 4, True)],
            },
            {
                "label": "Pack Anniversaire Enfant Magique", "tier": "petit", "budget_label": "350 000 FCFA",
                "caption": "Décoration à thème, animation et jeux, gâteau et confiseries, chaises et tables",
                "items": [("venue", 1, False), ("provider", 2, False), ("equipment", 1, 20, False)],
            },
            {
                "label": "Pack Gala Corporate Prestige", "tier": "haut", "budget_label": "4 200 000 FCFA",
                "caption": "Salle de conférence équipée, traiteur gastronomique, sonorisation professionnelle, hôtesses d'accueil, décoration scénique",
                "items": [("venue", 2, False), ("provider", 3, False), ("provider", 0, True), ("equipment", 2, 1, False)],
            },
            {
                "label": "Pack Team Building Aventure", "tier": "moyen", "budget_label": "900 000 FCFA",
                "caption": "Salle polyvalente, animation team building, restauration légère, matériel audiovisuel",
                "items": [("venue", 3, False), ("provider", 4, False), ("equipment", 3, 1, True)],
            },
            {
                "label": "Pack Anniversaire Adulte Chic", "tier": "moyen", "budget_label": "1 100 000 FCFA",
                "caption": "Décoration élégante, DJ, service traiteur, mobilier premium",
                "items": [("venue", 4, False), ("provider", 5, False), ("provider", 1, False), ("equipment", 4, 10, False)],
            },
            {
                "label": "Pack Baptême Tendresse", "tier": "petit", "budget_label": "450 000 FCFA",
                "caption": "Décoration douce et florale, traiteur, chaises et tables, photographe",
                "items": [("venue", 5, False), ("provider", 2, False), ("equipment", 5, 15, False)],
            },
            {
                "label": "Pack Conférence Business", "tier": "moyen", "budget_label": "1 600 000 FCFA",
                "caption": "Salle de conférence, sonorisation et vidéoprojection, pause-café, hôtesses d'accueil",
                "items": [("venue", 6, False), ("provider", 3, False), ("equipment", 6, 1, False), ("equipment", 0, 2, True)],
            },
            {
                "label": "Pack Fiançailles Romance", "tier": "moyen", "budget_label": "1 300 000 FCFA",
                "caption": "Décoration romantique, traiteur, DJ, photographe",
                "items": [("venue", 7, False), ("provider", 0, False), ("provider", 5, False)],
            },
        ]

        packs_created = 0
        items_created = 0
        for order, spec in enumerate(PACKS, start=1):
            pack, was_created = LandingMedia.objects.get_or_create(
                category="pack", label=spec["label"],
                defaults={
                    "caption": spec["caption"], "tier": spec["tier"], "budget_label": spec["budget_label"],
                    "order": order, "is_active": True,
                },
            )
            if was_created:
                packs_created += 1
                photo_file = photo_for(order)
                if photo_file:
                    pack.image.save(photo_file.name, photo_file, save=True)

            for line in spec["items"]:
                resource_type, res_index = line[0], line[1]
                if resource_type == "equipment":
                    _, res_index, qty, optional = line
                    resource = equipment[res_index % len(equipment)]
                    kwargs = {"pack": pack, "resource_type": "equipment", "equipment": resource}
                    defaults = {"default_quantity": qty, "is_optional": optional, "order": 1}
                else:
                    _, res_index, optional = line
                    resource_list = venues if resource_type == "venue" else providers
                    resource = resource_list[res_index % len(resource_list)]
                    kwargs = {"pack": pack, "resource_type": resource_type, resource_type: resource}
                    defaults = {"default_quantity": 1, "is_optional": optional, "order": 1}
                _, item_created = PackItem.objects.get_or_create(**kwargs, defaults=defaults)
                items_created += int(item_created)

        self.stdout.write(f"  - {packs_created} pack(s) additionnel(s) créé(s), {items_created} composant(s) associé(s).")

    # ------------------------------------------------------------------ packs
    def seed_pack_items(self):
        packs = list(LandingMedia.objects.filter(category="pack").order_by("id"))
        venues = list(Venue.objects.all()[:6])
        providers = list(Provider.objects.all()[:6])
        equipment = list(Equipment.objects.all()[:4])
        if not packs or not venues or not providers or not equipment:
            self.stdout.write("  - Composants de pack ignorés (packs/salles/prestataires/matériel manquants).")
            return

        plan = [
            # (pack_index, [(resource_type, resource_obj, qty, optional)])
            (0, [("venue", venues[0], 1, False), ("provider", providers[0], 1, False), ("equipment", equipment[0], 2, True)]),
            (1, [("venue", venues[1 % len(venues)], 1, False), ("provider", providers[1 % len(providers)], 1, False),
                 ("provider", providers[2 % len(providers)], 1, True), ("equipment", equipment[1 % len(equipment)], 4, False)]),
            (2, [("venue", venues[2 % len(venues)], 1, False), ("provider", providers[3 % len(providers)], 1, False),
                 ("provider", providers[4 % len(providers)], 1, False), ("equipment", equipment[2 % len(equipment)], 6, False),
                 ("equipment", equipment[3 % len(equipment)], 2, True)]),
        ]
        created = 0
        for pack_index, items in plan:
            if pack_index >= len(packs):
                continue
            pack = packs[pack_index]
            for order, (resource_type, resource, qty, optional) in enumerate(items, start=1):
                kwargs = {"pack": pack, "resource_type": resource_type, resource_type: resource}
                _, was_created = PackItem.objects.get_or_create(
                    **kwargs,
                    defaults={"default_quantity": qty, "is_optional": optional, "order": order},
                )
                created += int(was_created)
        self.stdout.write(f"  - {created} composant(s) de pack créé(s).")

    # ----------------------------------------------------------------- devis
    def seed_quotes(self):
        try:
            client = User.objects.get(username="client_demo")
        except User.DoesNotExist:
            self.stdout.write("  - Devis ignorés (client_demo introuvable).")
            return

        profiles = {p.category: p for p in ProfessionalProfile.objects.all()}
        by_id = {p.id: p for p in ProfessionalProfile.objects.all()}
        event_date = timezone.now().date() + timedelta(days=60)
        created_requests = 0
        created_quotes = 0

        def make_request(profile, status, event_type, city):
            nonlocal created_requests
            req, was_created = ProfessionalBookingRequest.objects.get_or_create(
                profile=profile, client=client, event_type=event_type,
                defaults=dict(
                    event_date=event_date, location=f"{city}, Cameroun", city=city,
                    guest_count=150, budget_estimate=Decimal("500000"),
                    options_wanted="Décoration florale, éclairage d'ambiance",
                    contact_phone="+237 6 90 00 11 22", message="Bonjour, pourriez-vous me faire une proposition ?",
                    status=status,
                ),
            )
            created_requests += int(was_created)
            return req, was_created

        def make_quote(req, status, items, travel_fee=15000, discount=0, paid=False):
            nonlocal created_quotes
            if req.quotes.exists():
                return req.quotes.first()
            quote = Quote.objects.create(
                booking_request=req, travel_fee=travel_fee, additional_fees=0, discount=discount,
                currency="XAF", conditions="Acompte de 50% à la confirmation, solde le jour J.",
                cancellation_policy="Remboursable à 80% jusqu'à 7 jours avant l'événement.",
                valid_until=timezone.now().date() + timedelta(days=14),
                provider_note="Voici notre proposition pour votre événement.",
                status=status,
            )
            for order, (label, qty, unit_price) in enumerate(items, start=1):
                QuoteLineItem.objects.create(quote=quote, label=label, quantity=qty, unit_price=unit_price, order=order)
            created_quotes += 1
            if paid:
                total = quote.total_amount
                settings_row = CommissionSettings.objects.filter(marketplace_type=req.profile.marketplace_type).first()
                commission_percent = settings_row.commission_percent if settings_row else DEFAULT_COMMISSION_PERCENT
                commission_amount = (total * commission_percent / Decimal("100")).quantize(Decimal("0.01"))
                payment = Payment.objects.create(
                    user=client, amount=total, currency="XAF", provider="demo", status=Payment.Status.COMPLETED,
                    purpose="marketplace_quote", completed_at=timezone.now(),
                )
                quote.payment = payment
                quote.commission_percent = commission_percent
                quote.commission_amount = commission_amount
                quote.provider_payout = total - commission_amount
                quote.save(update_fields=["payment", "commission_percent", "commission_amount", "provider_payout"])
            return quote

        # 1) En attente de réponse — pas encore de devis (DJ Kalvin Mix)
        dj = by_id.get(8)
        if dj:
            make_request(dj, ProfessionalBookingRequest.Status.PENDING, "Anniversaire", "Douala")

        # 2) Devis envoyé, en attente du client (Aline Déco Events)
        deco = by_id.get(2)
        if deco:
            req, _ = make_request(deco, ProfessionalBookingRequest.Status.QUOTED, "Mariage", "Yaoundé")
            make_quote(req, Quote.Status.SENT, [
                ("Décoration de salle (arche florale + tables)", 1, 350000),
                ("Éclairage d'ambiance", 1, 120000),
            ])

        # 3) Devis accepté, paiement attendu (SoundWave Sonorisation)
        sound = by_id.get(9)
        if sound:
            req, _ = make_request(sound, ProfessionalBookingRequest.Status.ACCEPTED, "Séminaire d'entreprise", "Douala")
            make_quote(req, Quote.Status.ACCEPTED, [
                ("Sonorisation complète (salle 300 pers.)", 1, 250000),
                ("Technicien son", 1, 50000),
            ])

        # 4) Devis payé — réservation confirmée, avec commission figée (Saveurs d'Afrique Traiteur)
        traiteur = by_id.get(10)
        if traiteur:
            req, was_created = make_request(traiteur, ProfessionalBookingRequest.Status.CONFIRMED, "Gala annuel", "Yaoundé")
            make_quote(req, Quote.Status.ACCEPTED, [
                ("Menu gala (150 couverts)", 150, 8500),
                ("Service en salle", 1, 100000),
            ], paid=True)

        # 5) Devis refusé (Prestige Events Agency)
        agency = by_id.get(12)
        if agency:
            req, _ = make_request(agency, ProfessionalBookingRequest.Status.DECLINED, "Lancement de produit", "Douala")
            make_quote(req, Quote.Status.DECLINED, [("Coordination événementielle complète", 1, 600000)])

        self.stdout.write(f"  - {created_requests} demande(s) de devis, {created_quotes} devis créé(s).")

    # -------------------------------------------------- favoris / disponibilités
    def seed_favorites_and_blocked_dates(self):
        try:
            client = User.objects.get(username="client_demo")
        except User.DoesNotExist:
            self.stdout.write("  - Favoris ignorés (client_demo introuvable).")
            return
        by_id = {p.id: p for p in ProfessionalProfile.objects.all()}
        favorited = 0
        for pid in (8, 13, 7):
            profile = by_id.get(pid)
            if not profile:
                continue
            _, was_created = ProfessionalFavorite.objects.get_or_create(client=client, profile=profile)
            favorited += int(was_created)

        blocked = 0
        for pid, offset in ((8, 20), (2, 35)):
            profile = by_id.get(pid)
            if not profile:
                continue
            _, was_created = ProfessionalBlockedDate.objects.get_or_create(
                profile=profile, date=timezone.now().date() + timedelta(days=offset),
                defaults={"reason": "Déjà engagé sur un autre événement"},
            )
            blocked += int(was_created)
        self.stdout.write(f"  - {favorited} favori(s), {blocked} date(s) bloquée(s) créé(s).")

    # ------------------------------------------------------------------- avis
    def seed_provider_reviews(self):
        try:
            client = User.objects.get(username="client_demo")
        except User.DoesNotExist:
            return
        providers = list(Provider.objects.all()[:2])
        comments = [
            ("Prestation impeccable, très professionnel et ponctuel.", Decimal("5.0")),
            ("Très bon rapport qualité-prix, je recommande.", Decimal("4.5")),
        ]
        created = 0
        for provider, (comment, rating) in zip(providers, comments):
            _, was_created = ProviderReview.objects.get_or_create(
                provider=provider, author=client, defaults={"rating": rating, "comment": comment},
            )
            created += int(was_created)
        self.stdout.write(f"  - {created} avis prestataire créé(s).")

    # ---------------------------------------------------- tâches / dépenses événement
    def seed_event_tasks_and_expenses(self):
        try:
            staff = User.objects.get(username="employe_demo")
        except User.DoesNotExist:
            staff = None
        events = list(Event.objects.all())
        if not events:
            self.stdout.write("  - Tâches/dépenses ignorées (aucun événement).")
            return
        task_templates = [
            ("Confirmer la salle", EventTask.Status.DONE, EventTask.Priority.HIGH, -20),
            ("Valider le traiteur", EventTask.Status.IN_PROGRESS, EventTask.Priority.HIGH, -10),
            ("Envoyer les invitations", EventTask.Status.TODO, EventTask.Priority.MEDIUM, 5),
            ("Préparer la playlist musicale", EventTask.Status.TODO, EventTask.Priority.LOW, 10),
        ]
        expense_templates = [
            ("Acompte salle", EventExpense.Category.VENUE, Decimal("150000"), -15),
            ("Acompte traiteur", EventExpense.Category.PROVIDER, Decimal("200000"), -8),
        ]
        created_tasks = created_expenses = 0
        today = timezone.now().date()
        for event in events:
            for title, status, priority, day_offset in task_templates:
                _, was_created = EventTask.objects.get_or_create(
                    event=event, title=title,
                    defaults={"status": status, "priority": priority, "assignee": staff, "due_date": today + timedelta(days=day_offset)},
                )
                created_tasks += int(was_created)
            for label, category, amount, day_offset in expense_templates:
                _, was_created = EventExpense.objects.get_or_create(
                    event=event, label=label,
                    defaults={"category": category, "amount": amount, "date": today + timedelta(days=day_offset)},
                )
                created_expenses += int(was_created)
        self.stdout.write(f"  - {created_tasks} tâche(s) et {created_expenses} dépense(s) d'événement créées.")

    # -------------------------------------------------- stock / dépenses matériel
    def seed_equipment_stock_and_expenses(self):
        try:
            admin = User.objects.get(username="admin")
        except User.DoesNotExist:
            admin = None
        equipment_list = list(Equipment.objects.all())
        if not equipment_list:
            self.stdout.write("  - Mouvements de stock ignorés (aucun matériel).")
            return
        created_movements = created_expenses = 0
        for equipment in equipment_list[:3]:
            if not equipment.stock_movements.exists():
                StockMovement.objects.create(
                    equipment=equipment, movement_type=StockMovement.MovementType.IN,
                    reason=StockMovement.Reason.RESTOCK, quantity=5,
                    notes="Réapprovisionnement initial", recorded_by=admin,
                )
                created_movements += 1
        first_equipment = equipment_list[0]
        _, was_created = EquipmentExpense.objects.get_or_create(
            label="Achat de matériel complémentaire", equipment=first_equipment,
            defaults={"category": EquipmentExpense.Category.PURCHASE, "amount": Decimal("450000"), "recorded_by": admin},
        )
        created_expenses += int(was_created)
        _, was_created = EquipmentExpense.objects.get_or_create(
            label="Maintenance annuelle sonorisation", equipment=first_equipment,
            defaults={"category": EquipmentExpense.Category.MAINTENANCE, "amount": Decimal("60000"), "recorded_by": admin},
        )
        created_expenses += int(was_created)
        self.stdout.write(f"  - {created_movements} mouvement(s) de stock, {created_expenses} dépense(s) matériel créées.")

    # -------------------------------------------------------------- RH / paie
    def seed_employees_and_payslips(self):
        roster = [
            ("Junior", "Fotso", "Chargé de clientèle", "6 90 12 34 56"),
            ("Aïssatou", "Bello", "Régisseuse technique", "6 90 23 45 67"),
            ("Patrick", "Ateba", "Comptable", "6 90 34 56 78"),
            ("Chantal", "Mvondo", "Chauffeur logistique", "6 90 45 67 89"),
        ]
        today = timezone.now().date()
        created_employees = created_payslips = 0
        for first_name, last_name, position, contact in roster:
            employee, was_created = Employee.objects.get_or_create(
                first_name=first_name, last_name=last_name,
                defaults={"position": position, "contact": contact, "hire_date": today - timedelta(days=400)},
            )
            created_employees += int(was_created)
            for month_offset in (1, 0):
                target = today.replace(day=1) - timedelta(days=month_offset * 30)
                _, was_created = Payslip.objects.get_or_create(
                    employee=employee, period_month=target.month, period_year=target.year,
                    defaults={"base_salary": Decimal("250000"), "bonuses": Decimal("15000"), "allowances": Decimal("10000"), "deductions": Decimal("5000")},
                )
                created_payslips += int(was_created)
        self.stdout.write(f"  - {created_employees} employé(s), {created_payslips} fiche(s) de paie créées.")

    # --------------------------------------------------------- marketplace vente
    def seed_sale_marketplace(self):
        try:
            partner = User.objects.get(username="partenaire_demo")
        except User.DoesNotExist:
            self.stdout.write("  - Annonces de vente ignorées (partenaire_demo introuvable).")
            return
        listings = [
            ("Lot de 50 chaises Chiavari dorées", "Chaises en excellent état, idéales pour mariages et galas.", Decimal("750000")),
            ("Arche de mariage en fer forgé", "Arche décorative réutilisable, peinture blanche mate.", Decimal("180000")),
            ("Sonorisation d'occasion 500W", "Enceintes + caisson de basses, révisées récemment.", Decimal("320000")),
        ]
        created = 0
        for title, description, price in listings:
            _, was_created = MarketplaceListing.objects.get_or_create(
                title=title, created_by=partner,
                defaults={
                    "marketplace_type": MarketplaceListing.MarketplaceType.SALE, "description": description,
                    "price": price, "currency": "XAF", "is_active": True,
                },
            )
            created += int(was_created)
        self.stdout.write(f"  - {created} annonce(s) de vente créée(s).")

    # -------------------------------------------------------------- réservations
    def seed_extra_bookings(self):
        events = list(Event.objects.all())
        venues = list(Venue.objects.all()[:3])
        if not events or not venues:
            self.stdout.write("  - Réservations supplémentaires ignorées.")
            return
        event = events[0]
        created = 0
        start = timezone.now() + timedelta(days=30)
        for venue in venues[1:3]:
            if event.bookings.filter(resource_type=Booking.ResourceType.VENUE, venue=venue).exists():
                continue
            Booking.objects.create(
                event=event, resource_type=Booking.ResourceType.VENUE, venue=venue,
                start_datetime=start, end_datetime=start + timedelta(hours=6),
                status=Booking.Status.PENDING, created_by=event.organizer,
            )
            created += 1
        self.stdout.write(f"  - {created} réservation(s) supplémentaire(s) créée(s).")

    # ---------------------------------------------------- commandes marketplace vente
    def seed_marketplace_orders(self):
        try:
            client = User.objects.get(username="client_demo")
        except User.DoesNotExist:
            return
        listing = MarketplaceListing.objects.filter(
            marketplace_type=MarketplaceListing.MarketplaceType.SALE, title="Arche de mariage en fer forgé",
        ).first()
        if not listing or listing.orders.filter(buyer=client).exists():
            self.stdout.write("  - Commande marketplace vente ignorée.")
            return
        payment = Payment.objects.create(
            user=client, amount=listing.price, currency=listing.currency, provider="demo",
            status=Payment.Status.COMPLETED, purpose="marketplace_order", completed_at=timezone.now(),
        )
        MarketplaceOrder.objects.create(
            listing=listing, buyer=client, payment=payment, quantity=1, status=MarketplaceOrder.Status.PAID,
        )
        self.stdout.write("  - 1 commande marketplace vente créée.")

    # -------------------------------------------------------------------- quiz
    def seed_quiz_attempts(self):
        try:
            participant = User.objects.get(username="participant_demo")
        except User.DoesNotExist:
            return
        quiz = Quiz.objects.first()
        if not quiz or QuizAttempt.objects.filter(quiz=quiz, participant=participant).exists():
            self.stdout.write("  - Tentative de quiz ignorée.")
            return
        questions = list(quiz.questions.all())
        answers = {str(q.id): 0 for q in questions}
        QuizAttempt.objects.create(
            quiz=quiz, participant=participant, score=max(1, len(questions) - 1),
            total_questions=len(questions), answers=answers,
        )
        self.stdout.write("  - 1 tentative de quiz créée.")

    # --------------------------------------------- badges & taux de commission
    def seed_badges_and_commissions(self):
        by_id = {p.id: p for p in ProfessionalProfile.objects.all()}
        badge_plan = [
            (13, {"is_top": True}),  # Mariage Parfait Events — mieux noté (5★)
            (10, {"is_recommended": True}),  # Saveurs d'Afrique Traiteur — prestation confirmée et payée
            (2, {"is_recommended": True}),  # Aline Déco Events — profil vitrine
        ]
        updated = 0
        for profile_id, badges in badge_plan:
            profile = by_id.get(profile_id)
            if not profile:
                continue
            changed = False
            for field, value in badges.items():
                if getattr(profile, field) != value:
                    setattr(profile, field, value)
                    changed = True
            if changed:
                profile.save(update_fields=list(badges.keys()))
                updated += 1

        # Taux différenciés par marketplace plutôt qu'un 5% uniforme partout —
        # plus représentatif d'une vraie politique tarifaire.
        commission_plan = {"sale": Decimal("5.00"), "interior_design": Decimal("7.00"), "actors": Decimal("6.00")}
        commissions_updated = 0
        for marketplace_type, percent in commission_plan.items():
            settings_row = CommissionSettings.objects.filter(marketplace_type=marketplace_type).first()
            if settings_row and settings_row.commission_percent != percent:
                settings_row.commission_percent = percent
                settings_row.save(update_fields=["commission_percent"])
                commissions_updated += 1

        self.stdout.write(f"  - {updated} profil(s) mis en avant (badges), {commissions_updated} taux de commission ajusté(s).")

    # ------------------------------------------------ matériel événementiel
    def seed_extra_equipment(self):
        catalog = [
            ("Chaises Chiavari dorées", Equipment.Category.FURNITURE, 200, Decimal("1500")),
            ("Tables rondes (10 pers.)", Equipment.Category.FURNITURE, 25, Decimal("12000")),
            ("Service de couverts complet", Equipment.Category.OTHER, 300, Decimal("800")),
        ]
        created = 0
        for name, category, quantity_total, price_per_unit in catalog:
            _, was_created = Equipment.objects.get_or_create(
                name=name, defaults={"category": category, "quantity_total": quantity_total, "price_per_unit": price_per_unit, "is_active": True},
            )
            created += int(was_created)
        self.stdout.write(f"  - {created} matériel(s) supplémentaire(s) créé(s) (chaises, tables, couverts).")

    # ----------------------------------------- demande de devis avec matériel
    def seed_complete_equipment_request(self):
        try:
            client = User.objects.get(username="client_demo")
        except User.DoesNotExist:
            self.stdout.write("  - Demande complète ignorée (client_demo introuvable).")
            return
        profile = ProfessionalProfile.objects.filter(pk=12).first()  # Prestige Events Agency
        if not profile:
            self.stdout.write("  - Demande complète ignorée (profil introuvable).")
            return
        request_obj, was_created = ProfessionalBookingRequest.objects.get_or_create(
            profile=profile, client=client, event_type="Mariage complet",
            defaults=dict(
                event_date=timezone.now().date() + timedelta(days=75),
                location="Douala, PK14", city="Douala",
                guest_count=200, budget_estimate=Decimal("2500000"),
                options_wanted="Installation complète salle + réception",
                contact_phone="+237 6 90 00 11 22",
                message="Bonjour, je souhaite un devis complet pour mon mariage : voici le matériel dont j'aurai besoin, "
                        "en plus de votre prestation de coordination.",
                status=ProfessionalBookingRequest.Status.PENDING,
            ),
        )
        if not was_created:
            self.stdout.write("  - Demande complète déjà présente.")
            return

        wanted = [("Chaises Chiavari dorées", 200), ("Tables rondes (10 pers.)", 20), ("Vidéoprojecteur HD", 1), ("Service de couverts complet", 200)]
        added = 0
        for name, quantity in wanted:
            equipment = Equipment.objects.filter(name=name).first()
            if not equipment:
                continue
            RequestedEquipmentItem.objects.create(booking_request=request_obj, equipment=equipment, quantity=quantity)
            added += 1
        self.stdout.write(f"  - 1 demande de devis complète créée avec {added} matériel(s) souhaité(s).")
