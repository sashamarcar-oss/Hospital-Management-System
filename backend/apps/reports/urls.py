from django.urls import path

from apps.reports.views import (
    ExportView,
    FinancialReportView,
    InventoryReportView,
    MedicalReportView,
    PatientReportView,
)

urlpatterns = [
    path("patients/", PatientReportView.as_view(), name="report-patients"),
    path("medical/", MedicalReportView.as_view(), name="report-medical"),
    path("financial/", FinancialReportView.as_view(), name="report-financial"),
    path("inventory/", InventoryReportView.as_view(), name="report-inventory"),
    path("export/", ExportView.as_view(), name="report-export"),
]
