from datetime import timedelta

from django.db.models import Count, Sum
from django.db.models.functions import TruncDate, TruncMonth
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Role
from apps.appointments.models import Appointment, Queue
from apps.billing.models import Invoice, Payment
from apps.clinical.models import Diagnosis, Prescription, VitalSigns
from apps.inpatient.models import Admission, Bed
from apps.laboratory.models import LabRequest
from apps.patients.models import Patient


class KPIsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = timezone.now().date()
        today_start = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))

        todays_revenue = (
            Payment.objects.filter(status=Payment.STATUS_COMPLETED, paid_at__gte=today_start)
            .aggregate(total=Sum("amount"))["total"]
            or 0
        )

        return Response({
            "total_patients": Patient.objects.count(),
            "today_appointments": Appointment.objects.filter(appointment_date=today).count(),
            "pending_appointments": Appointment.objects.filter(
                status__in=[Appointment.STATUS_SCHEDULED, Appointment.STATUS_CONFIRMED],
                appointment_date__gte=today,
            ).count(),
            "admitted_patients": Admission.objects.filter(status=Admission.STATUS_ADMITTED).count(),
            "available_beds": Bed.objects.filter(status=Bed.STATUS_AVAILABLE).count(),
            "doctors": Role.objects.get(code=Role.CODE_DOCTOR).users.count() if Role.objects.filter(code=Role.CODE_DOCTOR).exists() else 0,
            "nurses": Role.objects.get(code=Role.CODE_NURSE).users.count() if Role.objects.filter(code=Role.CODE_NURSE).exists() else 0,
            "pending_lab_tests": LabRequest.objects.filter(
                status__in=[LabRequest.STATUS_REQUESTED, LabRequest.STATUS_SAMPLE_COLLECTED,
                            LabRequest.STATUS_PROCESSING]
            ).count(),
            "pending_prescriptions": Prescription.objects.filter(
                status__in=["active", "partially_dispensed"]
            ).count(),
            "today_revenue": float(todays_revenue),
            "active_queue": Queue.objects.filter(
                status__in=[Queue.STATUS_WAITING, Queue.STATUS_IN_CONSULTATION]
            ).count(),
        })


class ChartsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = timezone.now().date()
        days_30 = today - timedelta(days=29)

        patient_registrations = (
            Patient.objects.filter(created_at__date__gte=days_30)
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(count=Count("id"))
            .order_by("day")
        )

        appointments_by_status = (
            Appointment.objects.values("status").annotate(count=Count("id"))
        )

        revenue_by_day = (
            Payment.objects.filter(status=Payment.STATUS_COMPLETED, paid_at__date__gte=days_30)
            .annotate(day=TruncDate("paid_at"))
            .values("day")
            .annotate(total=Sum("amount"))
            .order_by("day")
        )

        dept_performance = (
            Appointment.objects.values("department__name")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )

        demographics = (
            Patient.objects.values("gender").annotate(count=Count("id"))
        )

        common_diagnoses = (
            Diagnosis.objects.values("name").annotate(count=Count("id")).order_by("-count")[:10]
        )

        lab_activity = (
            LabRequest.objects.annotate(month=TruncMonth("requested_at"))
            .values("month")
            .annotate(count=Count("id"))
            .order_by("month")
        )

        def _fill_dates(rows, key="day"):
            by_day = {}
            for row in rows:
                day = row[key]
                by_day[str(day.date()) if hasattr(day, "date") else str(day)] = row["count"] if "count" in row else float(row["total"])
            filled = []
            cursor = days_30
            while cursor <= today:
                filled.append({"date": str(cursor), "value": by_day.get(str(cursor), 0)})
                cursor += timedelta(days=1)
            return filled

        return Response({
            "patient_registrations": _fill_dates(patient_registrations),
            "revenue": _fill_dates(revenue_by_day),
            "appointments_by_status": list(appointments_by_status),
            "department_performance": list(dept_performance),
            "patient_demographics": list(demographics),
            "common_diagnoses": list(common_diagnoses),
            "lab_activity": list(lab_activity),
        })


class ActivityFeedView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        limit = int(request.query_params.get("limit", 15))
        from apps.core.models import AuditLog

        events = AuditLog.objects.select_related("user").filter(
            action__in=["create", "payment", "dispense", "update", "upload"]
        )[:limit]
        feed = [
            {
                "id": e.id,
                "user": e.user.get_full_name() if e.user else "System",
                "action": e.action,
                "module": e.module,
                "record": e.record,
                "description": e.description,
                "timestamp": e.created_at.isoformat(),
            }
            for e in events
        ]
        return Response(feed)


class VitalSignsTrendView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        patient = request.query_params.get("patient")
        if not patient:
            return Response({"detail": "patient query param is required."}, status=400)
        from apps.clinical.serializers import VitalSignsSerializer

        qs = VitalSigns.objects.filter(patient_id=patient).order_by("recorded_at")
        return Response(VitalSignsSerializer(qs, many=True).data)
