"""Moteur central de résolution des fonctionnalités de marketplace (voir
MarketplaceFeature). Un seul point d'entrée — `resolve_features()` — décide,
pour un utilisateur et un marketplace donnés, ce qui doit être visible,
verrouillé ou accompagné d'un message d'abonnement. Toute nouvelle
fonctionnalité ajoutée en base (via l'admin) est automatiquement prise en
compte ici : aucune condition à coder à la main côté vue ou frontend."""

from django.utils import timezone

from .models import MarketplaceFeature, MarketplaceSubscription


def _active_subscription(user, marketplace_type):
    if not user.is_authenticated:
        return None
    return (
        MarketplaceSubscription.objects.filter(
            user=user, marketplace_type=marketplace_type, expires_at__gt=timezone.now()
        )
        .select_related("tier")
        .first()
    )


def resolve_features(user, marketplace_type):
    """Retourne la liste des fonctionnalités du marketplace donné, résolues pour
    CET utilisateur : `visible` (à afficher ou non), `locked` (affichée mais
    action désactivée) et `upsell_message` (motif à afficher le cas échéant).
    Une fonctionnalité à l'état « Masqué » est totalement absente du résultat,
    sauf pour un administrateur (qui doit pouvoir la retrouver pour la
    réactiver) — elle n'est alors jamais interactive côté public."""

    is_admin = bool(user.is_authenticated and user.is_admin_role)
    is_authenticated = bool(user.is_authenticated)
    subscription = _active_subscription(user, marketplace_type)
    is_subscriber = subscription is not None
    user_tier_level = subscription.tier.level if (subscription and subscription.tier) else (0 if is_subscriber else None)

    features = MarketplaceFeature.objects.filter(marketplace_type=marketplace_type).select_related("min_tier")

    resolved = []
    for feature in features:
        # Masqué = absent de l'interface pour tout le monde, y compris
        # l'administration : elle la retrouve et la réactive via le panneau de
        # gestion dédié (liste complète, indépendante de cette résolution).
        if feature.state == MarketplaceFeature.State.HIDDEN:
            continue

        if is_admin:
            visible, locked, upsell = True, False, ""
        else:
            meets_visibility = {
                MarketplaceFeature.Visibility.EVERYONE: True,
                MarketplaceFeature.Visibility.AUTHENTICATED: is_authenticated,
                MarketplaceFeature.Visibility.NON_SUBSCRIBER: is_authenticated and not is_subscriber,
                MarketplaceFeature.Visibility.SUBSCRIBER: is_subscriber,
                MarketplaceFeature.Visibility.ADMIN: False,
            }.get(feature.visibility, False)

            meets_tier = True
            if feature.min_tier_id:
                meets_tier = is_subscriber and user_tier_level is not None and user_tier_level >= feature.min_tier.level

            if feature.state == MarketplaceFeature.State.LOCKED:
                visible, locked = True, True
            elif feature.state == MarketplaceFeature.State.UPSELL:
                visible = True
                locked = not (meets_visibility and meets_tier)
            else:  # SHOWN
                visible = meets_visibility
                locked = visible and not meets_tier

            upsell = feature.upsell_message if locked else ""

        resolved.append({
            "key": feature.key,
            "label": feature.label,
            "description": feature.description,
            "visible": visible,
            "locked": locked,
            "upsell_message": upsell,
        })

    return resolved
