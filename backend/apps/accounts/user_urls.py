from rest_framework.routers import DefaultRouter

from apps.accounts.views_users import PermissionViewSet, RoleViewSet, UserViewSet

router = DefaultRouter()
# Specific prefixes registered before "" so they win over the <pk> pattern.
router.register("roles", RoleViewSet, basename="role")
router.register("permissions", PermissionViewSet, basename="permission")
router.register("", UserViewSet, basename="user")

urlpatterns = router.urls
