from rest_framework.routers import DefaultRouter

from .views import EquipmentViewSet, ExpenseViewSet, StockMovementViewSet

router = DefaultRouter()
router.register("stock-movements", StockMovementViewSet, basename="stock-movement")
router.register("expenses", ExpenseViewSet, basename="expense")
router.register("", EquipmentViewSet, basename="equipment")

urlpatterns = router.urls
