from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.audit.views import HealthCheckView

api_v1_patterns = [
    path("auth/", include("apps.accounts.urls")),
    path("events/", include("apps.events.urls")),
    path("venues/", include("apps.venues.urls")),
    path("providers/", include("apps.providers.urls")),
    path("equipment/", include("apps.equipment.urls")),
    path("bookings/", include("apps.bookings.urls")),
    path("tickets/", include("apps.tickets.urls")),
    path("payments/", include("apps.payments.urls")),
    path("messaging/", include("apps.messaging.urls")),
    path("ai-assistant/", include("apps.ai_assistant.urls")),
    path("training/", include("apps.training.urls")),
    path("employees/", include("apps.employees.urls")),
    path("payroll/", include("apps.payroll.urls")),
    path("notifications/", include("apps.notifications.urls")),
    path("audit/", include("apps.audit.urls")),
    path("reviews/", include("apps.reviews.urls")),
    path("games/", include("apps.games.urls")),
    path("public/", include("apps.public.urls")),
    path("marketplace/", include("apps.marketplace.urls")),
    path("deliveries/", include("apps.deliveries.urls")),
    path("referrals/", include("apps.referrals.urls")),
    path("companies/", include("apps.companies.urls")),
    path("talents/", include("apps.talents.urls")),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", HealthCheckView.as_view(), name="healthcheck"),
    path("api/v1/", include(api_v1_patterns)),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
