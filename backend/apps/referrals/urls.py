from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    CouponValidateView,
    MyReferralView,
    ReferralAdminViewSet,
    ReferralCampaignViewSet,
    ReferralConversionAdminViewSet,
    RewardCouponAdminViewSet,
)

router = DefaultRouter()
router.register("campaigns", ReferralCampaignViewSet, basename="referral-campaign")
router.register("admin/referrals", ReferralAdminViewSet, basename="referral-admin")
router.register("admin/coupons", RewardCouponAdminViewSet, basename="referral-coupon-admin")
router.register("admin/conversions", ReferralConversionAdminViewSet, basename="referral-conversion-admin")

urlpatterns = [
    path("me/", MyReferralView.as_view(), name="referral-me"),
    path("coupons/validate/", CouponValidateView.as_view(), name="referral-coupon-validate"),
] + router.urls
