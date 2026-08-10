from django.urls import path

from apps.dashboard.views import (
    ActivityFeedView,
    ChartsView,
    KPIsView,
    VitalSignsTrendView,
)

urlpatterns = [
    path("kpis/", KPIsView.as_view(), name="dashboard-kpis"),
    path("charts/", ChartsView.as_view(), name="dashboard-charts"),
    path("activity/", ActivityFeedView.as_view(), name="dashboard-activity"),
    path("vitals-trend/", VitalSignsTrendView.as_view(), name="dashboard-vitals-trend"),
]
