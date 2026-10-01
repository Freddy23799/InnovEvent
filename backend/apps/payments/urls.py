from rest_framework.routers import DefaultRouter

from django.urls import path

from .views import KobWebhookView, MobileMoneyWebhookView, PayPalWebhookView, PaymentViewSet

router = DefaultRouter()
router.register("", PaymentViewSet, basename="payment")

urlpatterns = [
    path("webhooks/paypal/", PayPalWebhookView.as_view(), name="webhook-paypal"),
    path("webhooks/mobile-money/", MobileMoneyWebhookView.as_view(), name="webhook-mobile-money"),
    path("webhooks/kob/", KobWebhookView.as_view(), name="webhook-kob"),
] + router.urls
