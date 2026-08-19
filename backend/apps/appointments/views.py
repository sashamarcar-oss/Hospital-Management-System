from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from apps.accounts.permissions import HasPermission
from apps.appointments.models import Appointment, Queue
from apps.appointments.serializers import AppointmentSerializer, QueueSerializer
from apps.core.models import AuditLog
from apps.core.services import audit_log, notify


class AppointmentViewSet(viewsets.ModelViewSet):
    queryset = Appointment.objects.select_related(
        "patient", "doctor", "department"
    ).all()
    serializer_class = AppointmentSerializer
    permission_classes = [HasPermission]
    code = "appointments.view"
    write_code = "appointments.update"
    create_code = "appointments.create"
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status", "priority", "appointment_date", "doctor", "patient", "department"]
    search_fields = [
        "patient__first_name", "patient__last_name", "patient__patient_number",
        "doctor__first_name", "doctor__last_name", "reason",
    ]
    ordering_fields = ["appointment_date", "start_time", "created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.in_roles("doctor"):
            return qs.filter(doctor=user)
        if user.in_roles("patient"):
            linked = getattr(user, "patient_account", None)
            return qs.filter(patient=linked) if linked else qs.none()
        return qs

    def _audit(self, request, action, appointment, description=""):
        audit_log(
            request.user, action, "appointments.appointment",
            record=str(appointment), object_id=appointment.id,
            request=request, description=description,
        )

    def perform_create(self, serializer):
        if self.request.user.in_roles("patient"):
            linked = getattr(self.request.user, "patient_account", None)
            if linked:
                serializer.validated_data["patient"] = linked
        appointment = serializer.save(created_by=self.request.user)
        self._audit(self.request, AuditLog.ACTION_CREATE, appointment)
        if self.request.user.in_roles("doctor", "receptionist", "admin"):
            try:
                notify(
                    appointment.doctor,
                    "New appointment",
                    f"{appointment.patient.full_name} is scheduled on {appointment.appointment_date} "
                    f"at {appointment.start_time:%H:%M}.",
                    notification_type="appointment",
                    link=f"/appointments",
                )
            except Exception:
                pass

    def perform_update(self, serializer):
        previous = {"status": serializer.instance.status}
        appointment = serializer.save(updated_by=self.request.user)
        self._audit(self.request, AuditLog.ACTION_UPDATE, appointment)

    def perform_destroy(self, instance):
        self._audit(self.request, AuditLog.ACTION_DELETE, instance, description="soft-deleted appointment")
        instance.soft_delete(self.request.user)

    @transaction.atomic
    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        appointment = self.get_object()
        previous = {"status": appointment.status}
        appointment.status = Appointment.STATUS_CONFIRMED
        appointment.save()
        self._audit(request, AuditLog.ACTION_UPDATE, appointment, "confirmed")
        if appointment.patient.user:
            try:
                notify(appointment.patient.user, "Appointment confirmed", f"Your appointment on {appointment.appointment_date} at {appointment.start_time:%H:%M} is confirmed.",
                       notification_type="appointment", link="/portal")
            except Exception:
                pass
        return Response(AppointmentSerializer(appointment).data)

    @transaction.atomic
    @action(detail=True, methods=["post"])
    def checkin(self, request, pk=None):
        """Check a patient in and generate a queue number for today's queue."""
        appointment = self.get_object()
        if appointment.status in (Appointment.STATUS_COMPLETED, Appointment.STATUS_CANCELLED, Appointment.STATUS_NO_SHOW):
            return Response({"detail": f"Cannot check in an appointment with status {appointment.status}."},
                            status=400)
        if appointment.status != Appointment.STATUS_CHECKED_IN:
            appointment.status = Appointment.STATUS_CHECKED_IN
            appointment.checked_in_at = timezone.now()
            appointment.save()
            queue = Queue.objects.create(
                patient=appointment.patient,
                appointment=appointment,
                department=appointment.department,
                doctor=appointment.doctor,
                priority=appointment.priority,
                checked_in_at=appointment.checked_in_at,
            )
            queue.queue_number = queue.generate_number()
            queue.save(update_fields=["queue_number"])
            self._audit(request, AuditLog.ACTION_CREATE, appointment, f"checked in, queue {queue.queue_number}")
            return Response({
                "detail": "Patient checked in.",
                "queue": QueueSerializer(queue).data,
                "appointment": AppointmentSerializer(appointment).data,
            })
        return Response(AppointmentSerializer(appointment).data)

    @transaction.atomic
    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        appointment = self.get_object()
        previous = {"status": appointment.status}
        appointment.status = Appointment.STATUS_COMPLETED
        appointment.completed_at = timezone.now()
        appointment.save()
        appointment.queue_entries.filter(status=Queue.STATUS_IN_CONSULTATION).update(status=Queue.STATUS_COMPLETED, completed_at=timezone.now())
        self._audit(request, AuditLog.ACTION_UPDATE, appointment, "completed")
        return Response(AppointmentSerializer(appointment).data)

    @transaction.atomic
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Cancel an appointment and remove it from any active queue."""
        appointment = self.get_object()
        previous = {"status": appointment.status}
        appointment.status = Appointment.STATUS_CANCELLED
        appointment.save()
        active = appointment.queue_entries.filter(
            status__in=[Queue.STATUS_WAITING, Queue.STATUS_IN_CONSULTATION]
        )
        active.update(status=Queue.STATUS_CANCELLED)
        self._audit(request, AuditLog.ACTION_UPDATE, appointment, "cancelled, removed from queue")
        if appointment.patient.user:
            try:
                notify(appointment.patient.user, "Appointment cancelled",
                       f"Your appointment on {appointment.appointment_date} was cancelled.",
                       notification_type="appointment", link="/portal")
            except Exception:
                pass
        return Response(AppointmentSerializer(appointment).data)

    @transaction.atomic
    @action(detail=True, methods=["post"])
    def noshow(self, request, pk=None):
        appointment = self.get_object()
        previous = {"status": appointment.status}
        appointment.status = Appointment.STATUS_NO_SHOW
        appointment.save()
        appointment.queue_entries.filter(status__in=[Queue.STATUS_WAITING, Queue.STATUS_IN_CONSULTATION]).update(status=Queue.STATUS_SKIPPED)
        self._audit(request, AuditLog.ACTION_UPDATE, appointment, "marked no-show")
        return Response(AppointmentSerializer(appointment).data)

    @transaction.atomic
    @action(detail=True, methods=["post"])
    def reschedule(self, request, pk=None):
        appointment = self.get_object()
        new_date = request.data.get("appointment_date")
        new_start = request.data.get("start_time")
        new_end = request.data.get("end_time")
        if new_date and new_start and new_end:
            appointment.appointment_date = new_date
            appointment.start_time = new_start
            appointment.end_time = new_end
            appointment.status = Appointment.STATUS_SCHEDULED
            appointment.save()
            appointment.queue_entries.filter(status=Queue.STATUS_WAITING).update(status=Queue.STATUS_SKIPPED)
        self._audit(request, AuditLog.ACTION_UPDATE, appointment, "rescheduled")
        return Response(AppointmentSerializer(appointment).data)

    @action(detail=False, methods=["get"])
    def calendar(self, request):
        """Appointments for the calendar view between start/end dates."""
        start = request.query_params.get("start")
        end = request.query_params.get("end")
        qs = self.get_queryset()
        if start:
            qs = qs.filter(appointment_date__gte=start)
        if end:
            qs = qs.filter(appointment_date__lte=end)
        data = []
        for appt in qs:
            data.append({
                "id": appt.id,
                "title": appt.patient.full_name,
                "start": f"{appt.appointment_date}T{appt.start_time}",
                "end": f"{appt.appointment_date}T{appt.end_time}",
                "status": appt.status,
                "priority": appt.priority,
                "patient": appt.patient.patient_number,
                "doctor": appt.doctor.get_full_name() or appt.doctor.username,
                "department": appt.department.name,
            })
        return Response(data)

    @action(detail=False, methods=["get"])
    def upcoming(self, request):
        """Today's and upcoming appointments."""
        qs = self.get_queryset().filter(
            appointment_date__gte=timezone.now().date(),
            status__in=[Appointment.STATUS_SCHEDULED, Appointment.STATUS_CONFIRMED, Appointment.STATUS_CHECKED_IN],
        ).order_by("appointment_date", "start_time")[:100]
        return Response(AppointmentSerializer(qs, many=True).data)


class QueueViewSet(viewsets.ModelViewSet):
    queryset = Queue.objects.select_related("patient", "department", "doctor").all()
    serializer_class = QueueSerializer
    permission_classes = [HasPermission]
    code = "queue.view"
    write_code = "queue.update"
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status", "department", "doctor", "priority", "patient"]
    ordering_fields = ["checked_in_at", "queue_number"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.in_roles("doctor"):
            return qs.filter(doctor=user)
        return qs

    @action(detail=False, methods=["get"])
    def active(self, request):
        """Current active queues, grouped per department."""
        qs = self.get_queryset().filter(
            status__in=[Queue.STATUS_WAITING, Queue.STATUS_IN_CONSULTATION]
        ).order_by("department_id", "-priority", "checked_in_at")
        return Response(QueueSerializer(qs, many=True).data)

    @action(detail=False, methods=["get"])
    def current(self, request):
        """Current patient in consultation for a doctor/department."""
        department = request.query_params.get("department")
        doctor = request.query_params.get("doctor")
        qs = self.get_queryset().filter(status=Queue.STATUS_IN_CONSULTATION)
        if department:
            qs = qs.filter(department_id=department)
        if doctor:
            qs = qs.filter(doctor_id=doctor)
        return Response(QueueSerializer(qs.first()).data if qs.exists() else None)

    @transaction.atomic
    @action(detail=True, methods=["post"])
    def call(self, request, pk=None):
        """Mark the patient as in consultation; demote any current consultation."""
        queue = self.get_object()
        Queue.objects.filter(
            doctor=queue.doctor, status=Queue.STATUS_IN_CONSULTATION
        ).exclude(id=queue.id).update(status=Queue.STATUS_WAITING)
        queue.status = Queue.STATUS_IN_CONSULTATION
        queue.called_at = timezone.now()
        queue.save()
        audit_log(request.user, AuditLog.ACTION_UPDATE, "appointments.queue",
                  record=queue.queue_number, object_id=queue.id, request=request,
                  description=f"called patient {queue.patient.full_name}")
        return Response(QueueSerializer(queue).data)

    @transaction.atomic
    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        queue = self.get_object()
        queue.status = Queue.STATUS_COMPLETED
        queue.completed_at = timezone.now()
        queue.save()
        if queue.appointment and queue.appointment.status == Appointment.STATUS_CHECKED_IN:
            queue.appointment.status = Appointment.STATUS_COMPLETED
            queue.appointment.completed_at = timezone.now()
            queue.appointment.save()
        audit_log(request.user, AuditLog.ACTION_UPDATE, "appointments.queue",
                  record=queue.queue_number, object_id=queue.id, request=request)
        return Response(QueueSerializer(queue).data)

    @transaction.atomic
    @action(detail=True, methods=["post"])
    def skip(self, request, pk=None):
        queue = self.get_object()
        queue.status = Queue.STATUS_SKIPPED
        queue.save()
        audit_log(request.user, AuditLog.ACTION_UPDATE, "appointments.queue",
                  record=queue.queue_number, object_id=queue.id, request=request)
        return Response(QueueSerializer(queue).data)

    def perform_create(self, serializer):
        queue = serializer.save()
        queue.queue_number = queue.generate_number()
        queue.save(update_fields=["queue_number"])
        audit_log(self.request.user, AuditLog.ACTION_CREATE, "appointments.queue",
                  record=queue.queue_number, object_id=queue.id, request=self.request)
