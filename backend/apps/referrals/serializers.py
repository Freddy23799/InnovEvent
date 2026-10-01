from rest_framework import serializers

from .models import Referral, ReferralCampaign, ReferralCampaignTier, ReferralConversion, RewardCoupon


class ReferralCampaignTierSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReferralCampaignTier
        fields = ["id", "threshold_referrals", "discount_percent", "max_discount_amount", "label"]
        read_only_fields = ["id"]


class ReferralCampaignSerializer(serializers.ModelSerializer):
    tiers = ReferralCampaignTierSerializer(many=True, required=False)
    category_display = serializers.CharField(source="get_category_display", read_only=True, default=None)

    class Meta:
        model = ReferralCampaign
        fields = [
            "id", "name", "slug", "description", "terms_text", "active", "is_default",
            "category", "category_display", "providers", "professional_profiles", "services",
            "marketplace_type", "min_purchase_amount", "coupon_validity_days", "max_uses_per_coupon",
            "valid_from", "valid_until", "tiers", "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def create(self, validated_data):
        tiers_data = validated_data.pop("tiers", [])
        m2m_fields = {
            key: validated_data.pop(key)
            for key in ["providers", "professional_profiles", "services"]
            if key in validated_data
        }
        campaign = ReferralCampaign.objects.create(**validated_data)
        for field, value in m2m_fields.items():
            getattr(campaign, field).set(value)
        for tier_data in tiers_data:
            ReferralCampaignTier.objects.create(campaign=campaign, **tier_data)
        return campaign

    def update(self, instance, validated_data):
        tiers_data = validated_data.pop("tiers", None)
        m2m_fields = {
            key: validated_data.pop(key)
            for key in ["providers", "professional_profiles", "services"]
            if key in validated_data
        }
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        for field, value in m2m_fields.items():
            getattr(instance, field).set(value)
        if tiers_data is not None:
            instance.tiers.all().delete()
            for tier_data in tiers_data:
                ReferralCampaignTier.objects.create(campaign=instance, **tier_data)
        return instance


class RewardCouponSerializer(serializers.ModelSerializer):
    campaign_name = serializers.CharField(source="campaign.name", read_only=True)

    class Meta:
        model = RewardCoupon
        fields = [
            "id", "code", "campaign", "campaign_name", "status", "discount_percent",
            "max_discount_amount", "max_uses", "times_used", "expires_at", "created_at",
        ]
        read_only_fields = fields


class ReferralAdminSerializer(serializers.ModelSerializer):
    referrer_username = serializers.CharField(source="referrer.username", read_only=True)
    referred_username = serializers.CharField(source="referred_user.username", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Referral
        fields = [
            "id", "referrer", "referrer_username", "referred_user", "referred_username",
            "status", "status_display", "signup_ip", "is_flagged", "flag_reason",
            "created_at", "converted_at",
        ]
        read_only_fields = fields


class ReferralConversionAdminSerializer(serializers.ModelSerializer):
    referrer_username = serializers.CharField(source="referral.referrer.username", read_only=True)
    referred_username = serializers.CharField(source="referral.referred_user.username", read_only=True)
    payment_ref = serializers.CharField(source="payment.transaction_ref", read_only=True)

    class Meta:
        model = ReferralConversion
        fields = [
            "id", "referral", "referrer_username", "referred_username", "payment", "payment_ref",
            "is_first_qualifying", "category", "provider", "professional_profile", "marketplace_type",
            "amount", "is_reversed", "created_at",
        ]
        read_only_fields = fields


class CouponValidateSerializer(serializers.Serializer):
    coupon_code = serializers.CharField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    category = serializers.CharField(required=False, allow_blank=True, default="")
    provider_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    professional_profile_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    service_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    marketplace_type = serializers.CharField(required=False, allow_blank=True, default="")
