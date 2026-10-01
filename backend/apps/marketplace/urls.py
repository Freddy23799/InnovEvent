from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    CommissionSettingsViewSet,
    MarketplaceAnalyticsView,
    MarketplaceFeatureResolveView,
    MarketplaceFeatureViewSet,
    MarketplaceListingViewSet,
    MarketplaceOrderPaymentView,
    MarketplaceOrderViewSet,
    MarketplaceSubscriptionView,
    ProfessionalBlockedDateViewSet,
    ProfessionalBookingRequestViewSet,
    ProfessionalFavoriteViewSet,
    ProfessionalPortfolioItemViewSet,
    ProfessionalProfileViewSet,
    ProfessionalServiceViewSet,
    QuoteViewSet,
    SubscriptionPlanViewSet,
    SubscriptionTierViewSet,
)

router = DefaultRouter()
router.register("listings", MarketplaceListingViewSet, basename="marketplace-listings")
router.register("orders", MarketplaceOrderViewSet, basename="marketplace-orders")
router.register("profiles", ProfessionalProfileViewSet, basename="professional-profiles")
router.register("services", ProfessionalServiceViewSet, basename="professional-services")
router.register("portfolio-items", ProfessionalPortfolioItemViewSet, basename="professional-portfolio-items")
router.register("blocked-dates", ProfessionalBlockedDateViewSet, basename="professional-blocked-dates")
router.register("favorites", ProfessionalFavoriteViewSet, basename="professional-favorites")
router.register("booking-requests", ProfessionalBookingRequestViewSet, basename="professional-booking-requests")
router.register("quotes", QuoteViewSet, basename="professional-quotes")
router.register("tiers", SubscriptionTierViewSet, basename="marketplace-tiers")
router.register("plans", SubscriptionPlanViewSet, basename="marketplace-plans")
router.register("commissions", CommissionSettingsViewSet, basename="marketplace-commissions")
router.register("features", MarketplaceFeatureViewSet, basename="marketplace-features")

urlpatterns = [
    path("orders/pay/", MarketplaceOrderPaymentView.as_view(), name="marketplace-order-pay"),
    path("subscriptions/", MarketplaceSubscriptionView.as_view(), name="marketplace-subscriptions"),
    path("features/resolve/", MarketplaceFeatureResolveView.as_view(), name="marketplace-features-resolve"),
    path("analytics/", MarketplaceAnalyticsView.as_view(), name="marketplace-analytics"),
] + router.urls
