from django.contrib import admin

from .models import MarketplaceListing, MarketplaceOrder, SaleOrder

admin.site.register(MarketplaceListing)
admin.site.register(MarketplaceOrder)
admin.site.register(SaleOrder)
