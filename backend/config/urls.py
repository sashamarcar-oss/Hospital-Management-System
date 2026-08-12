"""URL configuration for the Hospital Management System."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/core/", include("apps.core.urls")),
    path("api/users/", include("apps.accounts.user_urls")),
    path("api/departments/", include("apps.departments.urls")),
    path("api/staff/", include("apps.staff.urls")),
    path("api/shifts/", include("apps.scheduling.urls")),
    path("api/messages/", include("apps.messaging.urls")),
    path("api/patients/", include("apps.patients.urls")),
    path("api/appointments/", include("apps.appointments.urls")),
    path("api/consultations/", include("apps.clinical.urls")),
    path("api/laboratory/", include("apps.laboratory.urls")),
    path("api/radiology/", include("apps.radiology.urls")),
    path("api/pharmacy/", include("apps.pharmacy.urls")),
    path("api/admissions/", include("apps.inpatient.urls")),
    path("api/billing/", include("apps.billing.urls")),
    path("api/insurance/", include("apps.insurance.urls")),
    path("api/inventory/", include("apps.inventory.urls")),
    path("api/emergency/", include("apps.emergency.urls")),
    path("api/reports/", include("apps.reports.urls")),
    path("api/dashboard/", include("apps.dashboard.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
