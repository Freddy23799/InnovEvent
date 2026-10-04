"""Réponses d'erreur API lisibles, sans exposer de détails internes."""

from rest_framework.views import exception_handler


FIELD_LABELS = {
    "username": "Identifiant",
    "email": "Adresse e-mail",
    "phone": "Téléphone",
    "password": "Mot de passe",
    "password_confirm": "Confirmation du mot de passe",
    "old_password": "Ancien mot de passe",
    "first_name": "Prénom",
    "last_name": "Nom",
    "title": "Titre",
    "business_name": "Nom de l'entreprise ou de l'activité",
    "raison_sociale": "Raison sociale",
    "activity": "Activité",
    "start_date": "Date de début",
    "end_date": "Date de fin",
    "sale_start": "Début de la vente",
    "sale_end": "Fin de la vente",
    "quantity": "Quantité",
    "quota": "Quota",
    "price": "Prix",
    "photo": "Photo",
    "image": "Image",
    "attachment": "Pièce jointe",
    "non_field_errors": "Demande",
}

STATUS_MESSAGES = {
    400: "Certaines informations sont manquantes ou incorrectes. Vérifiez les champs indiqués.",
    401: "Votre session a expiré ou vos identifiants sont incorrects. Connectez-vous à nouveau.",
    403: "Vous n'avez pas l'autorisation d'effectuer cette action.",
    404: "L'élément demandé est introuvable ou n'est plus disponible.",
    409: "Cette action n'est plus possible car les informations ont changé. Actualisez la page puis réessayez.",
    429: "Vous avez effectué trop de demandes. Patientez un instant avant de réessayer.",
    500: "Une erreur est survenue. Réessayez dans quelques instants. Si le problème persiste, contactez l'assistance.",
    502: "Le service demandé est temporairement indisponible. Réessayez dans quelques instants.",
    503: "Le service est temporairement indisponible. Réessayez dans quelques instants.",
}

TECHNICAL_MESSAGES = {
    "authentication credentials were not provided.": STATUS_MESSAGES[401],
    "given token not valid for any token type": STATUS_MESSAGES[401],
    "token is invalid or expired": STATUS_MESSAGES[401],
    "no active account found with the given credentials": "Adresse e-mail ou mot de passe incorrect.",
    "invalid token header. no credentials provided.": STATUS_MESSAGES[401],
    "a user with that username already exists.": "Cet identifiant est déjà utilisé. Choisissez-en un autre.",
    "not found.": STATUS_MESSAGES[404],
    "request was throttled.": STATUS_MESSAGES[429],
    "this field is required.": "Ce champ est obligatoire.",
    "this field may not be blank.": "Ce champ ne peut pas rester vide.",
    "this field may not be null.": "Ce champ doit être renseigné.",
    "enter a valid email address.": "Saisissez une adresse e-mail valide.",
    "a valid integer is required.": "Saisissez un nombre entier valide.",
    "a valid number is required.": "Saisissez un nombre valide.",
    "this field must be unique.": "Cette valeur est déjà utilisée. Choisissez-en une autre.",
    "this password is too common.": "Ce mot de passe est trop courant. Choisissez-en un moins prévisible.",
    "this password is entirely numeric.": "Le mot de passe doit aussi contenir des lettres ou des symboles.",
    "this password is too short. it must contain at least 10 characters.": "Le mot de passe doit contenir au moins 10 caractères.",
    "invalid page.": "Cette page n'existe pas.",
    "invalid token.": STATUS_MESSAGES[401],
    "you do not have permission to perform this action.": STATUS_MESSAGES[403],
    "method \"get\" not allowed.": "Cette action n'est pas disponible ici.",
    "method \"post\" not allowed.": "Cette action n'est pas disponible ici.",
}


def _humanize_field(field):
    if field in FIELD_LABELS:
        return FIELD_LABELS[field]
    return field.replace("_", " ").strip().capitalize()


def _friendly_message(message):
    normalized = message.lower()
    if normalized.startswith("request was throttled."):
        return STATUS_MESSAGES[429]
    if normalized.startswith("json parse error"):
        return "Les informations reçues sont illisibles. Vérifiez les champs puis réessayez."
    if normalized.startswith("method ") and " not allowed." in normalized:
        return "Cette action n'est pas disponible ici."
    if normalized.startswith("unsupported media type"):
        return "Ce format de fichier n'est pas pris en charge. Choisissez un autre fichier."
    return TECHNICAL_MESSAGES.get(normalized, message)


def _messages(value):
    """Aplati les erreurs DRF imbriquées en phrases, sans afficher de dictionnaire brut."""
    if isinstance(value, dict):
        result = []
        for field, field_value in value.items():
            if field in {"code", "status_code"}:
                continue
            field_messages = _messages(field_value)
            if field == "detail":
                result.extend(field_messages)
            elif field_messages:
                label = _humanize_field(str(field))
                result.extend(f"{label} : {message}" for message in field_messages)
        return result
    if isinstance(value, (list, tuple)):
        return [message for item in value for message in _messages(item)]
    if value is None:
        return []
    message = str(value).strip()
    if not message:
        return []
    return [_friendly_message(message)]


def _user_message(data, status_code):
    messages = _messages(data)
    if messages:
        # La validation générale vient avant les erreurs de champ ; conserver une
        # seule phrase permet d'éviter un pavé dans les alertes et notifications.
        return " ".join(dict.fromkeys(messages))
    return STATUS_MESSAGES.get(
        status_code,
        "Une erreur est survenue. Vérifiez votre demande puis réessayez.",
    )


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        # Laisser Django journaliser les erreurs serveur non gérées ; aucune trace
        # ou donnée technique ne doit être renvoyée aux visiteurs.
        return None

    original_data = response.data
    message = _user_message(original_data, response.status_code)
    response.data = {
        # Préserve les erreurs par champ pour les formulaires qui les affichent
        # près du champ concerné, tout en garantissant un `detail` toujours lisible.
        **(original_data if isinstance(original_data, dict) else {}),
        "detail": message,
        "message": message,
        "errors": original_data if isinstance(original_data, dict) else None,
        "status_code": response.status_code,
    }
    return response
