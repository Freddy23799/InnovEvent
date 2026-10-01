from django.core.management.base import BaseCommand

from apps.events.models import Event
from apps.games.models import Quiz, QuizQuestion

COMPANY_QUESTIONS = [
    ("Que signifie le sigle « InnovEvent-GS » ?",
     ["Innovation Événementielle — Gestion & Services", "International Events Group Sud", "Innov Events Global Store", "Aucune des réponses"], 0),
    ("Quelles ressources peut-on réserver directement depuis la plateforme ?",
     ["Uniquement des salles", "Salles, prestataires (DJ, traiteur, décoration) et matériel", "Uniquement des billets", "Uniquement de la formation"], 1),
    ("Qui peut publier un événement public avec vente de billets ?",
     ["N'importe quel client", "Uniquement un organisateur ou l'administration", "Uniquement les participants", "Personne"], 1),
    ("Comment un client peut-il contacter l'administration depuis la plateforme ?",
     ["Uniquement par téléphone", "Via le bouton « Contacter l'administration » de la messagerie", "Ce n'est pas possible", "Par courrier postal"], 1),
    ("À quoi sert la « Gestion de stock » de la plateforme ?",
     ["Uniquement à consulter le matériel", "À suivre les entrées/sorties de matériel et les dépenses associées", "À gérer les salaires", "À réserver des salles"], 1),
]

EVENT_QUESTIONS = [
    ("Que reçoit-on automatiquement après un paiement de billet réussi ?",
     ["Rien de particulier", "Un billet avec QR code et une confirmation par email", "Un appel téléphonique", "Un courrier postal"], 1),
    ("Où retrouve-t-on ses billets achetés sur la plateforme ?",
     ["Dans « Mes billets »", "Dans « Paramètres »", "Nulle part, il faut les redemander", "Dans « Messagerie »"], 0),
    ("Que se passe-t-il quand un billet est scanné à l'entrée d'un événement ?",
     ["Rien", "Il passe au statut « Utilisé » et le titulaire reçoit une confirmation d'entrée", "Il est automatiquement remboursé", "Il redevient « en attente »"], 1),
    ("Sur la page « Billetterie », à quoi correspond le badge de prix affiché sur la photo ?",
     ["Le prix le plus cher disponible", "Le prix de départ (le moins cher des billets actifs)", "Le prix moyen", "Le prix de l'année dernière"], 1),
    ("Quel type de compte peut consulter les événements publics et acheter des billets ?",
     ["Uniquement les administrateurs", "Tout utilisateur authentifié de la plateforme", "Uniquement les organisateurs", "Personne"], 1),
]


class Command(BaseCommand):
    """Crée les deux jeux-questionnaires de démonstration (quiz entreprise et
    jeu événementiel) proposés aux participants. Idempotent."""

    help = "Seed des quiz de démonstration (entreprise + événementiel)."

    def handle(self, *args, **options):
        company_quiz, _ = Quiz.objects.get_or_create(
            title="Quiz InnovEvent-GS",
            category=Quiz.Category.COMPANY,
            defaults=dict(description="Testez vos connaissances sur la plateforme et ses services.", is_active=True),
        )
        self._sync_questions(company_quiz, COMPANY_QUESTIONS)

        event = Event.objects.filter(is_public=True).order_by("start_date").first()
        event_quiz, _ = Quiz.objects.get_or_create(
            title="Jeu événementiel — Spécial billetterie",
            category=Quiz.Category.EVENT,
            defaults=dict(
                description="Un quiz éclair sur le fonctionnement de la billetterie et des événements.",
                event=event, is_active=True,
            ),
        )
        self._sync_questions(event_quiz, EVENT_QUESTIONS)

        self.stdout.write(self.style.SUCCESS("Quiz de démonstration prêts :"))
        self.stdout.write(f"  - {company_quiz.title} ({company_quiz.question_count} questions)")
        self.stdout.write(f"  - {event_quiz.title} ({event_quiz.question_count} questions)")

    def _sync_questions(self, quiz, questions):
        if quiz.questions.exists():
            return
        for i, (text, choices, correct_index) in enumerate(questions):
            QuizQuestion.objects.create(quiz=quiz, text=text, choices=choices, correct_index=correct_index, order=i)
