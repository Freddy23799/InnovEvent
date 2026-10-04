"""Assistant progressif et réponses prudentes pour le chat d'administration.

Les demandes de projet sont reconstruites à partir de l'historique chiffré de
la conversation : aucune copie en clair des détails client n'est conservée.
Le bot ne confirme pas de disponibilité, prix personnalisé ou paiement.
"""

import re
import unicodedata


FAQ = [
    (("qui etes vous", "innovevent", "presentation", "votre entreprise", "votre equipe"),
     "InnovEvent accompagne les particuliers, entreprises et institutions dans l'organisation d'événements et la recherche de prestations. Notre équipe peut préciser les services adaptés à votre projet."),
    (("service", "prestation", "proposez", "faites vous", "activite", "domaine"),
     "La plateforme regroupe notamment l'organisation d'événements, les salles, les prestataires (traiteur, DJ, décoration, photo/vidéo), le matériel, les formations et la messagerie de suivi. Dites-moi ce que vous recherchez pour que je vous oriente."),
    (("salle", "lieu", "reception", "capacite", "visite guidee", "visiter"),
     "Pour une salle, indiquez la ville, la date, le nombre d'invités et le type d'événement. Vous pouvez consulter les salles du catalogue et demander une visite guidée. L'équipe confirmera la disponibilité et le tarif exacts."),
    (("reserver", "reservation", "booking", "bloquer une date"),
     "Pour demander une réservation, sélectionnez la prestation ou la salle, puis indiquez la date, les horaires et les détails de votre événement. La demande reste à confirmer par l'équipe ou le prestataire; un envoi de demande ne garantit pas à lui seul la disponibilité."),
    (("devis", "estimation", "cout", "combien", "budget", "tarif", "prix"),
     "Le tarif dépend du lieu, de la date, du nombre d'invités et des prestations choisies. Envoyez votre budget indicatif et vos besoins; l'administration pourra préparer ou vérifier un devis personnalisé."),
    (("paiement", "payer", "mobile money", "orange money", "mtn", "transaction", "facture"),
     "Les moyens de paiement disponibles sont indiqués au moment du règlement sur la plateforme. Ne partagez jamais votre code PIN ni un code de validation dans le chat. Pour vérifier un paiement précis, transmettez la référence de transaction à l'administration."),
    (("abonnement", "abonner", "souscrire", "marketplace premium", "formule"),
     "Les abonnements et leurs tarifs sont présentés dans la section Marketplace correspondante. Après souscription et validation, les fonctions incluses sont accessibles depuis votre espace. Pour une activation ou un paiement qui n'apparaît pas, l'administration vérifiera votre compte."),
    (("compte", "inscription", "creer mon compte", "enregistrer", "connexion", "connecter", "mot de passe"),
     "Vous pouvez créer un compte depuis la page d'inscription. Si vous avez oublié votre mot de passe, utilisez « Mot de passe oublié » sur la page de connexion. Ne communiquez pas votre mot de passe ici."),
    (("annuler", "annulation", "rembour", "retour argent", "modifier reservation"),
     "Les conditions d'annulation et de remboursement dépendent de la réservation et du paiement concernés. Envoyez le numéro de réservation ou la référence de paiement; un administrateur vérifiera les conditions applicables."),
    (("prestataire", "fournisseur", "traiteur", "dj", "photographe", "decoration", "musique", "animation"),
     "Le catalogue Marketplace permet de parcourir les prestataires et leurs offres. Précisez le service, la ville et la date recherchés; l'équipe peut vous aider à choisir et à contacter le bon prestataire."),
    (("materiel", "equipement", "chaise", "table", "sonorisation", "eclairage", "location"),
     "Le catalogue des équipements présente le matériel proposé. Pour vérifier une quantité, une période de location ou un tarif, envoyez les articles souhaités et les dates; l'équipe confirmera leur disponibilité."),
    (("formation", "cours", "apprendre", "certificat", "academy"),
     "Les formations disponibles, leurs dates, prérequis et tarifs sont présentés dans la rubrique Formation lorsqu'elles sont ouvertes aux inscriptions. Indiquez la formation qui vous intéresse et l'équipe vous donnera les prochaines modalités."),
    (("livraison", "livrer", "transport", "colis", "chauffeur"),
     "Pour une demande de transport ou de livraison, indiquez les adresses de départ et d'arrivée, la date, le type de colis et vos contraintes. L'administration pourra vous orienter vers le service adapté."),
    (("contact", "telephone", "whatsapp", "adresse", "joindre"),
     "Vous pouvez continuer ici dans la messagerie. Pour une visite ou un échange direct, l'équipe peut aussi être jointe sur WhatsApp au +237 6 73 00 39 93."),
]

HANDOFF_TERMS = (
    "parler a un humain", "parler a une personne", "parler a un conseiller",
    "parler a un agent", "parler a un administrateur", "parler a l'administration",
    "contacter l'administration", "contacter un administrateur", "un conseiller humain",
    "transfert humain", "parler au responsable", "appeler quelqu'un", "personne reelle",
)

CITY_NAMES = {
    "yaounde": "Yaoundé", "douala": "Douala", "bafoussam": "Bafoussam",
    "garoua": "Garoua", "maroua": "Maroua", "bertoua": "Bertoua",
    "ngaoundere": "Ngaoundéré", "ebolowa": "Ebolowa", "bamenda": "Bamenda",
    "limbe": "Limbé", "kribi": "Kribi", "buea": "Buea", "dschang": "Dschang",
    "foumban": "Foumban", "nkongsamba": "Nkongsamba", "edea": "Édéa",
}

MONTHS = "janvier|fevrier|mars|avril|mai|juin|juillet|aout|septembre|octobre|novembre|decembre"
EVENT_TYPES = {
    "mariage": "mariage", "anniversaire": "anniversaire", "bapteme": "baptême",
    "conference": "conférence", "seminaire": "séminaire", "gala": "gala",
    "cocktail": "cocktail", "concert": "concert", "reception": "réception",
    "team building": "team building", "lancement": "lancement de produit",
}

PROJECT_FLOWS = {
    "venue": (
        ("city", "Dans quelle ville cherchez-vous la salle ?"),
        ("date", "Pour quelle date souhaitez-vous la réserver ? Donnez le jour et le mois."),
        ("guests", "Combien d'invités prévoyez-vous ?"),
        ("event", "Quel type d'événement organisez-vous ?"),
    ),
    "event": (
        ("event", "Quel type d'événement souhaitez-vous organiser ?"),
        ("city", "Dans quelle ville aura-t-il lieu ?"),
        ("date", "À quelle date est-il prévu ? Donnez le jour et le mois."),
        ("guests", "Combien d'invités prévoyez-vous ?"),
    ),
    "provider": (
        ("service", "Quel service recherchez-vous (traiteur, DJ, décoration, photo…) ?"),
        ("city", "Dans quelle ville avez-vous besoin de ce service ?"),
        ("date", "Pour quelle date ? Donnez le jour et le mois."),
        ("guests", "Combien de personnes sont concernées, environ ?"),
    ),
    "equipment": (
        ("equipment", "Quel matériel recherchez-vous et en quelle quantité ?"),
        ("city", "Dans quelle ville souhaitez-vous le louer ?"),
        ("date", "Pour quelle date ou période ?"),
    ),
}


def _normalize(text):
    normalized = unicodedata.normalize("NFKD", text or "")
    return "".join(char for char in normalized if not unicodedata.combining(char)).lower()


def _detect_intent(text):
    normalized = _normalize(text)
    if any(term in normalized for term in ("equipement", "materiel", "chaise", "table", "sonorisation", "eclairage")):
        return "equipment"
    if any(term in normalized for term in ("traiteur", "dj", "photographe", "decoration", "prestataire", "fleuriste", "animateur")):
        return "provider"
    if any(term in normalized for term in ("salle", "lieu de reception", "visite guidee", "louer une salle", "reserver un lieu", "reserver", "reservation")):
        return "venue"
    if any(term in normalized for term in ("evenement", "mariage", "anniversaire", "conference", "seminaire", "gala", "bapteme", "cocktail", "concert", "team building")):
        return "event"
    return None


def _extract_details(text, last_question=""):
    normalized = _normalize(text)
    details = {}

    for key, label in CITY_NAMES.items():
        if key in normalized:
            details["city"] = label
            break
    if "city" not in details and "ville" in _normalize(last_question):
        candidate = text.strip(" .,!?:;")
        candidate_words = _normalize(candidate).split()
        question_words = {"quel", "quelle", "quels", "quelles", "combien", "comment", "prix", "tarif", "disponibilite", "salle", "reservation"}
        if (
            2 <= len(candidate) <= 60
            and len(candidate_words) <= 4
            and not any(char.isdigit() for char in candidate)
            and "?" not in text
            and not question_words.intersection(candidate_words)
        ):
            details["city"] = candidate[:1].upper() + candidate[1:]

    date_match = re.search(rf"\b([0-3]?\d\s+(?:{MONTHS})(?:\s+20\d{{2}})?|20\d{{2}}-\d{{2}}-\d{{2}}|[0-3]?\d/[01]?\d/(?:20)?\d{{2}})\b", normalized)
    if date_match:
        details["date"] = date_match.group(1)
    elif "date" in _normalize(last_question):
        candidate = text.strip(" .,!?:;")
        if len(candidate) <= 40 and any(char.isdigit() for char in candidate):
            details["date"] = candidate

    guests_match = re.search(r"\b(\d{1,5})\s*(?:personnes|invites|convives|participants)\b", normalized)
    if guests_match:
        details["guests"] = guests_match.group(1)
    elif any(word in _normalize(last_question) for word in ("combien", "invites", "personnes")):
        guests_match = re.search(r"\b(\d{1,5})\b", normalized)
        if guests_match:
            details["guests"] = guests_match.group(1)

    for key, label in EVENT_TYPES.items():
        if key in normalized:
            details["event"] = label
            break
    if "event" not in details and "type d'evenement" in _normalize(last_question):
        candidate = text.strip(" .,!?:;")
        if 3 <= len(candidate) <= 80:
            details["event"] = candidate

    if any(word in normalized for word in ("traiteur", "dj", "photographe", "decoration", "fleuriste", "animation")):
        details["service"] = text.strip(" .,!?:;")[:100]
    if any(word in normalized for word in ("chaise", "table", "sonorisation", "eclairage", "chapiteau", "tente", "materiel")):
        details["equipment"] = text.strip(" .,!?:;")[:120]
    return details


def _faq_answer(text):
    normalized = _normalize(text)
    best_answer = None
    best_score = 0
    for terms, answer in FAQ:
        score = sum(1 for term in terms if _normalize(term) in normalized)
        if score > best_score:
            best_answer, best_score = answer, score
    return best_answer


def answer_support_message(text, history=()):
    """Return (reply, handoff_required), using prior user messages as context."""
    normalized = _normalize(text)
    if normalized.strip(" !?. ,;:") in {"bonjour", "salut", "bonsoir", "hello", "merci", "merci beaucoup"}:
        return (
            "Bonjour ! Dites-moi ce dont vous avez besoin et je vous orienterai. Pour passer directement à un administrateur, demandez-le dans ce chat.",
            False,
        )
    if any(term in normalized for term in HANDOFF_TERMS):
        return (
            "Bien sûr. J'ai transmis votre demande à l'administration. Un administrateur pourra poursuivre cet échange ici.",
            True,
        )

    history = list(history or [])[-24:]
    user_history = [content for role, content in history if role == "user"]
    combined = " ".join([*user_history, text])
    last_question = next((content for role, content in reversed(history) if role == "assistant"), "")

    intent = _detect_intent(combined)
    if intent:
        details = {}
        previous_question = ""
        for role, content in history:
            if role == "assistant":
                previous_question = content
            elif role == "user":
                details.update(_extract_details(content, previous_question))
        details.update(_extract_details(text, last_question))
        fields = PROJECT_FLOWS[intent]
        missing = [(key, question) for key, question in fields if not details.get(key)]
        if missing:
            _, question = missing[0]
            unrelated_answer = _faq_answer(text) if len(text.split()) > 3 else None
            if unrelated_answer:
                return (f"{unrelated_answer}\n\nPour avancer sur votre demande, j'ai encore besoin de cette précision : {question}", False)
            return (f"D'accord, je vous accompagne pour cette demande. {question}", False)

        summary = ", ".join(f"{label} : {details[key]}" for key, label in (
            ("event", "événement"), ("service", "service"), ("equipment", "matériel"),
            ("city", "ville"), ("date", "date"), ("guests", "invités"),
        ) if key in details)
        return (
            f"Merci, j'ai les premières informations : {summary}. Je transmets votre demande à l'administration pour vérifier le catalogue, la disponibilité et le tarif. Un administrateur pourra continuer ici.",
            True,
        )

    best_answer = _faq_answer(text)
    if not best_answer:
        return (
            "Je n'ai pas de réponse suffisamment fiable à cette question. Je la transmets à l'administration, qui pourra vous répondre dans cette conversation. Vous pouvez ajouter la ville, la date et les détails utiles.",
            True,
        )

    return (
        f"{best_answer}\n\nSi vous avez une demande particulière, écrivez « parler à un administrateur » et l'équipe prendra le relais.",
        False,
    )
