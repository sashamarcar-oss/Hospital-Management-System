import csv
import io

from django.db.models import Count, Sum
from django.db.models.functions import TruncDate, TruncMonth
from django.http import HttpResponse
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import HasPermission
from apps.appointments.models import Appointment
from apps.billing.models import Invoice, Payment
from apps.clinical.models import Diagnosis
from apps.inpatient.models import Admission, Discharge
from apps.insurance.models import InsuranceClaim
from apps.laboratory.models import LabRequest
from apps.patients.models import Patient
from apps.pharmacy.models import Medicine, MedicineStockMovement


class ReportBaseView(APIView):
    permission_classes = [IsAuthenticated, HasPermission]
    code = "reports.view"

    def _filter_dates(self, request, field="created_at__date"):
        start = request.query_params.get("start")
        end = request.query_params.get("end")
        result = {}
        if start:
            result[f"{field}__gte"] = start
        if end:
            result[f"{field}__lte"] = end
        return result


class PatientReportView(ReportBaseView):
    def get(self, request):
        date_filter = self._filter_dates(request)
        new_patients = Patient.objects.filter(**date_filter).count()
        returning = Appointment.objects.filter(patient__isnull=False).values("patient").annotate(
            visits=Count("id")
        ).filter(visits__gt=1).count()

        today = timezone.now().date()
        days_30 = today - timezone.timedelta(days=29)
        registrations = (
            Patient.objects.filter(created_at__date__gte=days_30)
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(count=Count("id"))
            .order_by("day")
        )
        demographics = Patient.objects.values("gender").annotate(count=Count("id"))
        visits_by_day = (
            Appointment.objects.filter(appointment_date__gte=days_30)
            .values("appointment_date")
            .annotate(count=Count("id"))
            .order_by("appointment_date")
        )

        return Response({
            "new_patients": new_patients,
            "returning_patients": returning,
            "registrations_30d": [
                {"date": str(r["day"]), "count": r["count"]} for r in registrations
            ],
            "demographics": list(demographics),
            "visits_30d": [
                {"date": str(r["appointment_date"]), "count": r["count"]} for r in visits_by_day
            ],
        })


class MedicalReportView(ReportBaseView):
    def get(self, request):
        diagnoses = (
            Diagnosis.objects.values("name").annotate(count=Count("id")).order_by("-count")[:20]
        )
        labs = LabRequest.objects.values("status").annotate(count=Count("id"))
        admissions = Admission.objects.values("status").annotate(count=Count("id"))
        discharges = Discharge.objects.filter().count()
        treatments = (
            Diagnosis.objects.values("icd_code", "name").annotate(count=Count("id")).order_by("-count")[:20]
        )
        return Response({
            "common_diagnoses": list(diagnoses),
            "laboratory_activity": list(labs),
            "admissions_by_status": list(admissions),
            "total_discharges": discharges,
            "treatments": list(treatments),
        })


class FinancialReportView(ReportBaseView):
    def get(self, request):
        today = timezone.now().date()
        days_30 = today - timezone.timedelta(days=29)

        daily_revenue = (
            Payment.objects.filter(status=Payment.STATUS_COMPLETED, paid_at__date__gte=days_30)
            .annotate(day=TruncDate("paid_at"))
            .values("day")
            .annotate(total=Sum("amount"))
            .order_by("day")
        )
        monthly_revenue = (
            Payment.objects.filter(status=Payment.STATUS_COMPLETED)
            .annotate(month=TruncMonth("paid_at"))
            .values("month")
            .annotate(total=Sum("amount"))
            .order_by("month")
        )
        outstanding = Invoice.objects.filter(status__in=["unpaid", "partially_paid", "overdue"]).aggregate(
            total_outstanding=Sum("balance")
        )
        payment_methods = (
            Payment.objects.filter(status=Payment.STATUS_COMPLETED)
            .values("method")
            .annotate(total=Sum("amount"), count=Count("id"))
        )
        insurance_claims = InsuranceClaim.objects.values("status").annotate(
            total=Sum("approved_amount"), count=Count("id")
        )

        total_revenue = Payment.objects.filter(status=Payment.STATUS_COMPLETED).aggregate(
            total=Sum("amount")
        )["total"] or 0

        return Response({
            "daily_revenue_30d": [
                {"date": str(r["day"]), "total": float(r["total"])} for r in daily_revenue
            ],
            "monthly_revenue": [
                {"month": str(r["month"]), "total": float(r["total"])} for r in monthly_revenue
            ],
            "total_revenue": float(total_revenue),
            "outstanding": outstanding,
            "payment_methods": list(payment_methods),
            "insurance_claims": list(insurance_claims),
        })


class InventoryReportView(ReportBaseView):
    def get(self, request):
        medicines = [m for m in Medicine.objects.prefetch_related("batches").all()]
        low_stock = [m for m in medicines if m.is_low_stock]
        expired = [
            {"medicine": m.name, "batch": b.batch_number, "quantity": b.quantity, "expiry_date": str(b.expiry_date)}
            for m in medicines
            for b in m.batches.all()
            if b.expiry_date and b.expiry_date < timezone.now().date()
        ]
        current_stock = [{"name": m.name, "stock": m.total_stock, "reorder_level": m.reorder_level} for m in medicines]
        movements = MedicineStockMovement.objects.order_by("-created_at")[:100]
        return Response({
            "current_stock": current_stock,
            "low_stock_count": len(low_stock),
            "low_stock": [{"name": m.name, "stock": m.total_stock} for m in low_stock],
            "expired": expired,
            "recent_movements": [
                {"medicine": mv.medicine.name, "type": mv.movement_type, "quantity": mv.quantity,
                 "date": mv.created_at.isoformat()}
                for mv in movements
            ],
        })


class ExportView(ReportBaseView):
    """Export a report table as CSV."""

    def get(self, request):
        report = request.query_params.get("report")
        rows = []
        headers = []

        if report == "patients":
            headers = ["Patient Number", "Name", "Gender", "Phone", "Email", "Created At"]
            for p in Patient.objects.all():
                rows.append([p.patient_number, p.full_name, p.gender, p.phone, p.email, str(p.created_at.date())])
        elif report == "invoices":
            headers = ["Invoice Number", "Patient", "Total", "Paid", "Balance", "Status"]
            for inv in Invoice.objects.all():
                rows.append([inv.invoice_number, inv.patient.full_name, str(inv.total),
                             str(inv.amount_paid), str(inv.balance), inv.status])
        elif report == "payments":
            headers = ["Receipt", "Invoice", "Amount", "Method", "Date"]
            for pay in Payment.objects.all():
                rows.append([pay.receipt_number, pay.invoice.invoice_number, str(pay.amount),
                             pay.method, str(pay.paid_at.date())])
        elif report == "medicines":
            headers = ["Name", "Generic", "Stock", "Reorder Level", "Selling Price", "Expiry"]
            for m in Medicine.objects.all():
                rows.append([m.name, m.generic_name, m.total_stock, m.reorder_level,
                             str(m.selling_price), str(m.earliest_expiry or "")])
        else:
            return Response({"detail": "Unknown report. Choose patients, invoices, payments or medicines."}, status=400)

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(headers)
        writer.writerows(rows)
        response = HttpResponse(buffer.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{report}_report.csv"'
        return response
