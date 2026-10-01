from email.mime.image import MIMEImage

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from apps.documents.company import LOGO_PATH

from .models import EmailLog, Notification, SmsLog
from .sms import SmsProviderError, get_sms_provider

_logo_bytes = None


def _get_logo_bytes():
    global _logo_bytes
    if _logo_bytes is None:
        try:
            with open(LOGO_PATH, "rb") as f:
                _logo_bytes = f.read()
        except OSError:
            _logo_bytes = False
    return _logo_bytes or None


def send_transactional_email(recipient_email, subject, template_name, context=None, attachments=None):
    context = context or {}
    html_body = render_to_string(f"emails/{template_name}.html", context)
    try:
        message = EmailMultiAlternatives(subject, html_body, settings.DEFAULT_FROM_EMAIL, [recipient_email])
        message.attach_alternative(html_body, "text/html")

        logo_bytes = _get_logo_bytes()
        if logo_bytes:
            logo_image = MIMEImage(logo_bytes)
            logo_image.add_header("Content-ID", "<logo>")
            logo_image.add_header("Content-Disposition", "inline", filename="logo.png")
            message.attach(logo_image)

        for filename, content, mimetype in attachments or []:
            message.attach(filename, content, mimetype)
        message.send(fail_silently=False)
        EmailLog.objects.create(recipient_email=recipient_email, subject=subject, template_name=template_name, status=EmailLog.Status.SENT)
    except Exception as exc:
        EmailLog.objects.create(
            recipient_email=recipient_email, subject=subject, template_name=template_name,
            status=EmailLog.Status.FAILED, error_message=str(exc),
        )


def send_ticket_confirmation_email(user, tickets):
    if not user.email:
        return
    from apps.tickets.pdf import build_ticket_pdf  # import différé : évite un cycle tickets <-> notifications

    event = tickets[0].ticket_type.event
    attachments = [
        (f"billet-{ticket.code}.pdf", build_ticket_pdf(ticket), "application/pdf") for ticket in tickets
    ]
    send_transactional_email(
        recipient_email=user.email,
        subject=f"InnovEvent-GS — Confirmation de votre billet pour {event.title}",
        template_name="ticket_confirmation",
        context={
            "user": user,
            "event": event,
            "tickets": tickets,
        },
        attachments=attachments,
    )


def send_event_invitation_email(participant):
    if not participant.email:
        return
    import re

    from apps.events.pdf import build_participant_invitation_pdf  # import différé : évite un cycle events <-> notifications

    safe_title = re.sub(r"[^\w\- ]", "", participant.event.title)[:40].strip() or "evenement"
    attachments = [
        (f"invitation-{safe_title}.pdf", build_participant_invitation_pdf(participant), "application/pdf")
    ]
    send_transactional_email(
        recipient_email=participant.email,
        subject=f"InnovEvent-GS — Vous êtes invité(e) à « {participant.event.title} »",
        template_name="event_invitation",
        context={
            "participant": participant,
            "event": participant.event,
        },
        attachments=attachments,
    )


def send_booking_receipt_email(user, booking):
    if not user.email:
        return
    send_transactional_email(
        recipient_email=user.email,
        subject=f"InnovEvent-GS — Confirmation de votre réservation pour {booking.event.title}",
        template_name="booking_receipt",
        context={"user": user, "booking": booking},
    )


def send_sms(phone, message):
    if not phone:
        return
    try:
        get_sms_provider().send(phone, message)
        SmsLog.objects.create(recipient_phone=phone, message=message, status=SmsLog.Status.SENT)
    except SmsProviderError as exc:
        SmsLog.objects.create(recipient_phone=phone, message=message, status=SmsLog.Status.FAILED, error_message=str(exc))


def _push_realtime(notification):
    """Pousse la notification en direct au navigateur connecté (WebSocket),
    en plus de la ligne créée en base — voir apps.notifications.consumers.
    Best-effort : une indisponibilité de Redis ne doit jamais faire échouer
    l'action métier à l'origine de la notification (réservation, paiement...)."""
    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer

        channel_layer = get_channel_layer()
        if channel_layer is None:
            return
        async_to_sync(channel_layer.group_send)(
            f"notifications_{notification.recipient_id}",
            {
                "type": "notification.push",
                "notification": {
                    "id": notification.id,
                    "title": notification.title,
                    "message": notification.message,
                    "link": notification.link,
                    "is_read": notification.is_read,
                    "created_at": notification.created_at.isoformat(),
                },
            },
        )
    except Exception:
        pass


def notify_user(user, title, message="", link="", send_email_too=False, send_sms_too=False):
    """Point d'entrée unique pour notifier un utilisateur : notification in-app
    systématique (poussée en temps réel si l'utilisateur est connecté), email
    et/ou SMS en complément selon le contexte d'appel."""
    notification = Notification.objects.create(recipient=user, title=title, message=message, link=link)
    _push_realtime(notification)
    if send_email_too and user.email:
        send_transactional_email(
            recipient_email=user.email,
            subject=f"InnovEvent-GS — {title}",
            template_name="generic_notification",
            context={"user": user, "title": title, "message": message},
        )
    if send_sms_too and user.phone:
        send_sms(user.phone, f"InnovEvent-GS : {title} — {message}"[:320])


def notify_booking_created(booking):
    if not booking.created_by:
        return
    notify_user(
        booking.created_by,
        title="Réservation en attente de paiement",
        message=f"Votre réservation pour « {booking.event.title} » ({booking.resource}) attend son règlement.",
        link="/bookings",
        send_email_too=True,
        send_sms_too=True,
    )


def send_reminder(user, custom_message=""):
    message = custom_message or "N'oubliez pas de finaliser votre réservation ou votre paiement en cours."
    notify_user(user, title="Rappel InnovEvent-GS", message=message, link="/bookings", send_email_too=True, send_sms_too=True)


BOOKING_STATUS_TITLES = {
    "confirmed": "Réservation confirmée",
    "cancelled": "Réservation annulée",
}


def notify_booking_status_changed(booking):
    """Prévient le client/organisateur à l'origine de la demande dès que sa
    réservation change de statut (confirmée ou annulée par l'administration,
    ou automatiquement après paiement)."""
    if not booking.created_by:
        return
    title = BOOKING_STATUS_TITLES.get(booking.status)
    if not title:
        return
    notify_user(
        booking.created_by,
        title=title,
        message=f"Votre réservation pour « {booking.event.title} » ({booking.resource}) est maintenant {booking.get_status_display().lower()}.",
        link="/bookings",
    )


def notify_professional_booking_request_created(booking_request):
    """Alerte le prestataire (qui doit y répondre par un devis) et l'administration
    (qui garde une visibilité complète) dès qu'un client soumet une demande de
    devis — aucune coordonnée n'est échangée directement sur la plateforme."""
    from apps.accounts.models import User

    client_name = booking_request.client.get_full_name() or booking_request.client.username
    message = f"{client_name} souhaite un devis pour « {booking_request.profile.business_name} »."
    notify_user(
        booking_request.profile.user,
        title="Nouvelle demande de devis",
        message=message,
        link="/app/dashboard",
    )
    for admin in User.objects.filter(role=User.Role.ADMIN):
        notify_user(
            admin,
            title="Nouvelle demande de devis",
            message=message,
            link="/app/premium-marketplace/booking-requests",
        )
    notify_user(
        booking_request.client,
        title="Demande envoyée",
        message=f"Votre demande de devis pour « {booking_request.profile.business_name} » a été transmise au prestataire.",
        link="/app/my-booking-requests",
    )


BOOKING_REQUEST_STATUS_TITLES = {
    "contacted": "Mise en relation effectuée",
    "confirmed": "Réservation confirmée",
    "declined": "Demande refusée",
    "cancelled": "Demande annulée",
    "completed": "Prestation marquée comme réalisée",
}


def notify_professional_booking_request_status_changed(booking_request):
    title = BOOKING_REQUEST_STATUS_TITLES.get(booking_request.status)
    if not title:
        return
    notify_user(
        booking_request.client,
        title=title,
        message=f"Votre demande pour « {booking_request.profile.business_name} » est maintenant : {booking_request.get_status_display().lower()}.",
        link="/app/my-booking-requests",
    )


def notify_booking_request_contacted(booking_request, conversation):
    """L'administration vient de valider la mise en relation sur cette demande
    (statut « Mise en relation effectuée ») : une conversation directe est
    ouverte entre le client et le prestataire — les deux en sont informés avec
    un lien direct vers cette messagerie, jamais de coordonnées personnelles
    échangées."""
    business_name = booking_request.profile.business_name
    client_name = booking_request.client.get_full_name() or booking_request.client.username
    link = f"/messaging?conversation={conversation.pk}"
    notify_user(
        booking_request.client,
        title="Mise en relation effectuée",
        message=f"L'administration vous a mis en relation avec {business_name} — vous pouvez maintenant échanger directement via la messagerie.",
        link=link,
        send_email_too=True,
    )
    notify_user(
        booking_request.profile.user,
        title="Mise en relation effectuée",
        message=f"L'administration vous a mis en relation avec {client_name} pour sa demande — vous pouvez maintenant échanger directement via la messagerie.",
        link=link,
        send_email_too=True,
    )


def notify_quote_sent(quote):
    """Le prestataire vient d'envoyer un devis structuré — le client en est
    informé, jamais par un contact direct mais via l'objet devis lui-même."""
    booking_request = quote.booking_request
    notify_user(
        booking_request.client,
        title="Nouveau devis reçu",
        message=f"{booking_request.profile.business_name} vous a envoyé un devis de {quote.total_amount:,.0f} {quote.currency}.".replace(",", " "),
        link="/app/my-booking-requests",
        send_email_too=True,
    )


def notify_quote_client_response(quote):
    """Le client a répondu au devis (accepté, refusé, ou demande de
    modification) — le prestataire en est informé pour agir en conséquence."""
    booking_request = quote.booking_request
    titles = {
        "accepted": "Devis accepté",
        "declined": "Devis refusé",
        "modification_requested": "Modification demandée sur un devis",
    }
    title = titles.get(quote.status)
    if not title:
        return
    notify_user(
        booking_request.profile.user,
        title=title,
        message=f"{booking_request.client.get_full_name() or booking_request.client.username} — devis pour « {booking_request.profile.business_name} ».",
        link="/app/dashboard",
    )


def notify_quote_paid(quote):
    """Paiement du devis confirmé — le prestataire est notifié que la
    prestation est désormais réservée et payée."""
    booking_request = quote.booking_request
    notify_user(
        booking_request.profile.user,
        title="Devis payé — réservation confirmée",
        message=f"Le paiement de {quote.total_amount:,.0f} {quote.currency} a été reçu pour « {booking_request.profile.business_name} ».".replace(",", " "),
        link="/app/dashboard",
        send_email_too=True,
    )
    notify_user(
        booking_request.client,
        title="Paiement confirmé",
        message=f"Votre paiement pour « {booking_request.profile.business_name} » est confirmé. La prestation est réservée.",
        link="/app/my-booking-requests",
        send_email_too=True,
    )


def notify_new_message(message):
    """Pousse une notification temps réel aux autres participants d'une
    conversation dès qu'un message est envoyé (remplace le simple polling
    pour la réactivité, tout en le laissant en filet de sécurité)."""
    conversation = message.conversation
    sender_name = message.sender.get_full_name() or message.sender.username
    if message.body:
        preview = message.body[:140]
    elif message.attachment_type == message.AttachmentType.IMAGE:
        preview = "📷 Photo"
    elif message.attachment:
        preview = f"📎 {message.attachment_name or 'Pièce jointe'}"
    else:
        preview = ""
    for recipient in conversation.participants.exclude(pk=message.sender_id):
        notify_user(
            recipient,
            title=f"Nouveau message de {sender_name}",
            message=preview,
            link="/messaging",
        )


DELIVERY_STATUS_TITLES = {
    "confirmed": "Livraison confirmée",
    "carrier_assigned": "Transporteur affecté à votre livraison",
    "collected": "Colis collecté",
    "in_transit": "Livraison en transit",
    "arrived": "Livraison arrivée à destination",
    "delivering": "Livraison en cours",
    "delivered": "Livraison réussie",
    "failed": "Échec de livraison",
    "postponed": "Livraison reportée",
    "cancelled": "Livraison annulée",
    "returning": "Retour en cours",
    "returned": "Livraison retournée",
}


def notify_delivery_status_changed(delivery):
    """Prévient le client à l'origine de la livraison à chaque changement de
    statut significatif — même principe que `notify_booking_status_changed`.
    SMS en complément (section 14) si le client n'a pas de compte (livraison
    indépendante) ou en plus de la notification in-app."""
    title = DELIVERY_STATUS_TITLES.get(delivery.status)
    if not title:
        return
    message = f"Votre livraison {delivery.reference} vers {delivery.destination_address} est maintenant « {delivery.get_status_display().lower()} »."
    if delivery.client:
        notify_user(
            delivery.client,
            title=title,
            message=message,
            link=f"/app/deliveries/{delivery.id}",
            send_sms_too=True,
        )
    elif delivery.client_phone:
        # Livraison indépendante (sans compte client) — le seul canal
        # possible pour prévenir le destinataire reste le SMS.
        send_sms(delivery.client_phone, f"InnovEvent-GS : {title} — {message}"[:320])


def notify_delivery_assigned(delivery):
    """Prévient le chauffeur qu'une nouvelle mission lui a été affectée
    (section 17 — notifications transporteur). Notification in-app si le
    chauffeur a un compte lié, SMS direct sinon (la plupart des chauffeurs
    n'ont pas de compte utilisateur — cf. décision d'architecture "aucun
    nouveau rôle"). Le transporteur reçoit toujours un SMS de confirmation."""
    mission_summary = f"Livraison {delivery.reference} : {delivery.pickup_address} → {delivery.destination_address}."
    if delivery.driver:
        if delivery.driver.user:
            notify_user(
                delivery.driver.user,
                title="Nouvelle mission de livraison",
                message=mission_summary,
                link="/app/my-deliveries",
                send_sms_too=True,
            )
        elif delivery.driver.phone:
            send_sms(delivery.driver.phone, f"InnovEvent-GS : nouvelle mission — {mission_summary}"[:320])
    if delivery.carrier and delivery.carrier.phone:
        send_sms(
            delivery.carrier.phone,
            f"InnovEvent-GS : livraison {delivery.reference} vous a été affectée ({delivery.destination_address})."[:320],
        )


JOB_APPLICATION_STATUS_TITLES = {
    "reviewed": "Candidature examinée",
    "accepted": "Candidature acceptée",
    "rejected": "Candidature refusée",
}


def notify_job_application_created(application):
    """Un client vient de soumettre sa candidature (avec CV) depuis son
    compte — même principe que `notify_professional_booking_request_created` :
    l'administration garde une visibilité complète sur toutes les nouvelles
    candidatures à examiner."""
    from apps.accounts.models import User

    message = f"{application.full_name} a postulé pour « {application.desired_position} »."
    for admin in User.objects.filter(role=User.Role.ADMIN):
        notify_user(
            admin,
            title="Nouvelle candidature reçue",
            message=message,
            link="/app/job-applications",
        )
    notify_user(
        application.applicant,
        title="Candidature envoyée",
        message=f"Votre candidature pour « {application.desired_position} » a été transmise à l'administration.",
        link="/app/my-job-applications",
    )


def notify_job_application_status_changed(application):
    title = JOB_APPLICATION_STATUS_TITLES.get(application.status)
    if not title:
        return
    notify_user(
        application.applicant,
        title=title,
        message=f"Votre candidature pour « {application.desired_position} » est maintenant : {application.get_status_display().lower()}.",
        link="/app/my-job-applications",
        send_email_too=True,
    )


def notify_referral_signup(referral):
    """Le parrain est prévenu dès l'inscription de son filleul — avant même
    toute transaction, purement informatif (la récompense, elle, n'arrive
    qu'après une transaction validée, voir `notify_referral_progress`)."""
    referred_name = referral.referred_user.get_full_name() or referral.referred_user.username
    notify_user(
        referral.referrer,
        title="Nouveau filleul inscrit",
        message=f"🎉 {referred_name} vient de s'inscrire grâce à votre invitation.",
        link="/app/referral",
    )


def notify_referral_progress(referral):
    """Le filleul vient d'effectuer sa première transaction validée — le
    parrain progresse dans son programme de parrainage."""
    from apps.referrals.models import Referral

    referred_name = referral.referred_user.get_full_name() or referral.referred_user.username
    active_count = Referral.objects.filter(referrer=referral.referrer, status=Referral.Status.CONVERTED).count()
    notify_user(
        referral.referrer,
        title="Votre filleul a effectué une transaction",
        message=f"✅ {referred_name} vient d'effectuer une réservation. Vous avez maintenant {active_count} filleul(s) actif(s).",
        link="/app/referral",
    )


def notify_reward_unlocked(coupon):
    label = coupon.tier.label or f"{coupon.discount_percent}% de réduction"
    notify_user(
        coupon.owner,
        title="Récompense débloquée",
        message=f"🎁 Félicitations ! Vous avez débloqué : {label} (code {coupon.code}).",
        link="/app/referral",
        send_email_too=True,
    )


def notify_reward_expiring_soon(coupon):
    notify_user(
        coupon.owner,
        title="Votre récompense expire bientôt",
        message=f"⏳ Votre récompense {coupon.code} expire dans 7 jours — pensez à l'utiliser lors de votre prochaine réservation.",
        link="/app/referral",
        send_email_too=True,
    )
