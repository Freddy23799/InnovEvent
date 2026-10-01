from rest_framework.routers import DefaultRouter

from .views import EmployeeViewSet, JobApplicationViewSet

router = DefaultRouter()
router.register("job-applications", JobApplicationViewSet, basename="job-application")
router.register("", EmployeeViewSet, basename="employee")

urlpatterns = router.urls
