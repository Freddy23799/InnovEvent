"""Assistant de la messagerie d'administration : réponses courtes et précises.

Chaque message reçoit une réponse d'une ou deux phrases qui indique où agir
sur la plateforme. Le bot ne confirme jamais de disponibilité, prix
personnalisé ou paiement ; s'il ne sait pas répondre (ou si le client le
demande), il transmet la conversation à l'équipe, qui reprend la main ici.
"""

import re
import unicodedata

HANDOFF_REPLY = "Je transmets votre message à notre équipe 🙏 Un conseiller vous répond ici très vite."

# --- Échanges simples ---------------------------------------------------------
GREETINGS = ("bonjour", "bonsoir", "salut", "hello", "coucou", "bjr", "slt", "cc", "hi", "hey", "bonne journee a vous")
HOW_ARE_YOU = ("ca va", "cava", "comment allez vous", "comment vas tu", "comment ca va", "vous allez bien", "tu vas bien", "cv")
THANKS = ("merci", "mrc", "thanks", "thank you", "je vous remercie")
ACKS = ("ok", "okay", "oki", "d accord", "dac", "daccord", "super", "parfait", "tres bien", "cool", "bien recu", "entendu", "top", "genial")
GOODBYES = ("au revoir", "aurevoir", "bye", "a bientot", "bonne journee", "bonne soiree", "bonne nuit", "a plus", "a demain")

SMALL_TALK = (
    (GOODBYES, "Au revoir et à bientôt sur InnovEvent ! 👋"),
    (HOW_ARE_YOU, "Très bien, merci 😊 Que puis-je faire pour vous ?"),
    (THANKS, "Avec plaisir ! Autre chose ?"),
    (ACKS, "Parfait 👍 Je reste disponible si besoin."),
    (GREETINGS, "Bonjour 👋 Comment puis-je vous aider ?"),
)

HANDOFF_TERMS = (
    "parler a un humain", "parler a une personne", "parler a un conseiller", "parler a un agent",
    "parler a un administrateur", "parler a l administration", "contacter l administration",
    "contacter un administrateur", "un conseiller", "un humain", "une vraie personne", "personne reelle",
    "parler au responsable", "service client", "votre equipe",
)

# --- Sujets -------------------------------------------------------------------
# (identifiant, mots-clés, réponse). La réponse peut dépendre du type de compte
# ({"default": …, "partner": …}). Les sujets les plus précis passent en premier
# en cas d'égalité. `handoff=True` : la demande nécessite l'équipe.
TOPICS = [
    {
        "key": "problem", "handoff": True,
        "terms": ("probleme", "bug", "erreur", "ne marche pas", "marche pas", "fonctionne pas", "bloque", "plainte", "reclamation", "arnaque", "pas recu"),
        "answer": "Désolé pour ce souci 😕 Je transmets à notre équipe, un conseiller vous répond ici très vite.",
    },
    {
        "key": "cancel", "handoff": True,
        "terms": ("annuler", "annulation", "rembourse", "remboursement", "rembourser"),
        "answer": "Envoyez-nous le numéro de votre facture (FAC-…) ici : notre équipe s'occupe de l'annulation.",
    },
    {
        "key": "rental",
        "terms": ("louer", "location", "loue", "en location", "pour 2 jours", "par jour", "a la journee"),
        "answer": "Pour louer : Boutique › ajoutez vos produits › choisissez « Louer » puis vos dates. Le total et la facture se calculent automatiquement.",
    },
    {
        "key": "invoice",
        "terms": ("facture", "ma commande", "mes commandes", "commande", "recu", "pdf"),
        "answer": "Vos factures sont dans Boutique › Mes commandes, téléchargeables en PDF.",
    },
    {
        "key": "payment",
        "terms": ("payer", "paiement", "paye", "mobile money", "orange money", "momo", "mtn", "carte bancaire", "virement"),
        "answer": "Les commandes de la boutique se paient à la livraison ou plus tard. Ne partagez jamais votre code PIN dans le chat.",
    },
    {
        "key": "delivery",
        "terms": ("livraison", "livrer", "livre", "recuperer le materiel", "retour du materiel", "transport", "expedier"),
        "answer": "Indiquez l'adresse lors de la commande : notre équipe vous appelle pour organiser la livraison (et le retour en cas de location).",
    },
    {
        "key": "availability",
        "terms": ("disponible", "disponibilite", "en stock", "stock", "rupture", "reste combien"),
        "answer": "La disponibilité s'affiche sur chaque produit. En location, elle est vérifiée pour vos dates au moment de commander.",
    },
    {
        "key": "verification",
        "terms": ("verification", "verifie", "verifier mon compte", "certifier", "certifie", "certification", "cni", "carte d identite", "badge"),
        "answer": {
            "default": "Les prestataires sont vérifiés par notre équipe : cherchez le badge « Vérifié » sur leur fiche.",
            "partner": "Ajoutez la photo de votre CNI dans Accueil › Modifier : notre équipe vérifie votre profil et vous attribue le badge.",
        },
    },
    {
        "key": "talent",
        "terms": ("talent", "profil visible", "rendre visible", "visibilite", "portfolio", "mes realisations"),
        "answer": {
            "default": "Les profils de talents sont consultables dans « Talents » par les prestataires.",
            "partner": "Complétez « Mon profil talent » (infos + une réalisation), puis cliquez « Rendre visible ».",
        },
    },
    {
        "key": "quote",
        "terms": ("devis", "demande de prix", "estimation"),
        "answer": {
            "default": "Ouvrez la fiche du prestataire et cliquez « Demander un devis ». Sa réponse arrive dans « Mes demandes prestataires ».",
            "partner": "Les demandes de vos clients sont dans « Demandes de devis reçues » : répondez-y avec votre devis.",
        },
    },
    {
        "key": "publish",
        "terms": ("publier", "inscrire mon activite", "vendre mes services", "devenir prestataire", "mon profil prestataire", "mes services"),
        "answer": {
            "default": "Pour proposer vos services, créez un compte Prestataire : vous publierez ensuite votre profil dans le Marketplace.",
            "partner": "Depuis votre Accueil : choisissez votre marketplace, abonnez-vous, puis ajoutez vos services et réalisations.",
        },
    },
    {
        "key": "subscription",
        "terms": ("abonnement", "abonner", "abonne", "souscrire", "formule", "premium", "gratuit", "palier"),
        "answer": "La Boutique est gratuite. Prestataires, Décoration et Salles se débloquent par abonnement : Marketplace › S'abonner.",
    },
    {
        "key": "provider",
        "terms": ("dj", "traiteur", "photographe", "videaste", "decorateur", "decoratrice", "prestataire", "animateur", "fleuriste",
                  "maquilleuse", "coiffeuse", "wedding planner", "mc", "musicien", "orchestre", "securite", "hotesse"),
        "answer": "Marketplace › Marketplace des acteurs : choisissez votre type d'événement puis le métier, et demandez un devis.",
    },
    {
        "key": "venue",
        "terms": ("salle", "lieu de reception", "salle de fete", "visite", "capacite"),
        "answer": "Rendez-vous dans « Salles » : filtrez par ville et capacité, puis demandez une réservation ou une visite.",
    },
    {
        "key": "ticket",
        "terms": ("billet", "ticket", "qr", "qr code", "entree", "place pour"),
        "answer": {
            "default": "Achetez vos billets dans « Billets » : ils apparaissent ensuite dans « Mes billets » avec leur QR code.",
            "organizer": "Gérez vos billets dans « Billetterie » : types de billets, ventes et scan à l'entrée.",
        },
    },
    {
        "key": "event",
        "terms": ("organiser", "j organise", "mon evenement", "creer un evenement", "mariage", "anniversaire", "bapteme",
                  "conference", "seminaire", "gala", "soiree", "concert", "dot", "funerailles", "team building"),
        "answer": {
            "default": "Super ! Indiquez-nous la date, la ville et le nombre d'invités : notre équipe vous prépare une proposition.",
            "organizer": "Créez votre événement dans « Mes événements › Nouvel événement », puis suivez-le dans « Pilotage ».",
        },
        "handoff_roles": ("client", "participant", "employee", "partner", "default"),
    },
    {
        "key": "shop",
        "terms": ("boutique", "acheter", "achat", "verre", "assiette", "vaisselle", "couvert", "chaise", "table", "nappe",
                  "materiel", "equipement", "sonorisation", "eclairage", "tente", "decoration"),
        "answer": "Tout est dans la Boutique (gratuite) : ajoutez vos produits au panier, choisissez « Acheter » ou « Louer », et validez.",
    },
    {
        "key": "price",
        "terms": ("prix", "tarif", "combien", "cout", "coute", "budget", "cher"),
        "answer": "Les prix sont affichés sur chaque produit de la Boutique. Pour un prestataire ou une salle, demandez un devis depuis sa fiche.",
    },
    {
        "key": "password",
        "terms": ("mot de passe", "mdp", "connexion", "me connecter", "identifiant", "code oublie"),
        "answer": "Cliquez sur « Mot de passe oublié » à la connexion. Ne partagez jamais votre mot de passe ici.",
    },
    {
        "key": "account",
        "terms": ("mon compte", "mon profil", "modifier mes informations", "photo de profil", "changer mon email", "changer mon numero", "inscription", "creer un compte"),
        "answer": "Modifiez vos informations dans Menu › Profil.",
    },
    {
        "key": "training",
        "terms": ("formation", "former", "cours", "attestation", "certificat"),
        "answer": "Les formations ouvertes sont dans « Formations », vos attestations dans « Attestations & badges ».",
    },
    {
        "key": "referral",
        "terms": ("parrain", "parrainage", "code promo", "coupon", "reduction", "promotion"),
        "answer": "Menu › Parrainage : partagez votre lien et gagnez des réductions.",
    },
    {
        "key": "jobs",
        "terms": ("emploi", "travail", "recrutement", "recrutez", "candidature", "postuler", "rejoindre l equipe", "cv", "stage"),
        "answer": "Envoyez votre candidature depuis Menu › Rejoindre l'équipe.",
    },
    {
        "key": "contact",
        "terms": ("telephone", "whatsapp", "appeler", "numero", "contact", "adresse", "vos bureaux", "joindre"),
        "answer": "Écrivez-nous ici, ou sur WhatsApp au +237 6 73 00 39 93.",
    },
    {
        "key": "about",
        "terms": ("qui etes vous", "c est quoi innovevent", "innovevent", "que faites vous", "vos services"),
        "answer": "InnovEvent réunit tout pour vos événements : boutique (achat et location), prestataires, salles et billetterie.",
    },
]


def _normalize(text):
    normalized = unicodedata.normalize("NFKD", text or "")
    normalized = "".join(char for char in normalized if not unicodedata.combining(char)).lower()
    normalized = re.sub(r"[’'`]", " ", normalized)
    normalized = re.sub(r"[^a-z0-9 ]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def _has(term, text):
    """Mot-clé présent en début de mot ; les termes courts (dj, qr, cv…) doivent
    être des mots entiers, les autres acceptent pluriels et dérivés."""
    term = _normalize(term)
    suffix = r"\b" if len(term) < 4 else ""
    return re.search(rf"\b{re.escape(term)}{suffix}", text) is not None


def _small_talk(text):
    """Réponse à un message qui n'est qu'une formule (bonjour, merci, ok…)."""
    words = text.split()
    if not words or len(words) > 6:
        return None
    for terms, reply in SMALL_TALK:
        for term in terms:
            if text == term or (_has(term, text) and len(words) <= len(term.split()) + 3):
                # « merci bonne journée » : on garde la formule la plus pertinente (ordre de SMALL_TALK).
                return reply
    return None


def _strip_greeting(text):
    for term in sorted(GREETINGS, key=len, reverse=True):
        if text.startswith(term + " "):
            return text[len(term) + 1:].strip(), True
    return text, False


def _resolve(answer, role):
    if isinstance(answer, dict):
        return answer.get(role) or answer["default"]
    return answer


def _best_topic(text):
    # Un problème ou une annulation passe avant tout : c'est à l'équipe d'agir.
    for topic in TOPICS:
        if topic.get("handoff") and any(_has(term, text) for term in topic["terms"]):
            return topic
    best, best_score = None, 0
    for topic in TOPICS:
        score = sum(1 for term in topic["terms"] if _has(term, text))
        if score > best_score:
            best, best_score = topic, score
    return best


def answer_support_message(text, history=(), role=None):
    """Retourne (réponse, transmission_à_l_équipe)."""
    normalized = _normalize(text)
    role = role or "default"

    if any(_has(term, normalized) for term in HANDOFF_TERMS):
        return HANDOFF_REPLY, True

    small_talk = _small_talk(normalized)
    if small_talk:
        if small_talk.startswith("Bonjour") and normalized.startswith("bonsoir"):
            small_talk = small_talk.replace("Bonjour", "Bonsoir", 1)
        return small_talk, False

    content, greeted = _strip_greeting(normalized)
    topic = _best_topic(content)
    if topic is None:
        return HANDOFF_REPLY, True

    reply = _resolve(topic["answer"], role)
    handoff = topic.get("handoff", False) or role in topic.get("handoff_roles", ())
    if greeted:
        reply = f"{'Bonsoir' if normalized.startswith('bonsoir') else 'Bonjour'} 👋 {reply}"
    return reply, handoff
