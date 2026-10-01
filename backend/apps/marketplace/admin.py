from django.contrib import admin

from .models import MarketplaceListing, MarketplaceOrder

admin.site.register(MarketplaceListing)
admin.site.register(MarketplaceOrder)
