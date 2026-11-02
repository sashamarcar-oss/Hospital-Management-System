from datetime import date, time

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.appointments.models import Appointment, Queue
from apps.appointments.serializers import AppointmentSerializer
from apps.departments.models import Department
from apps.patients.models import Patient


class AppointmentWorkflowTests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_superuser(
            username="workflow-admin", email="workflow@example.test", password="pw"
        )
        self.department = Department.objects.create(name="General Medicine")
        self.patient = Patient.objects.create(
            first_name="Jane", last_name="Doe", date_of_birth=date(1990, 1, 1),
            gender="female",
        )
        self.appointment = Appointment.objects.create(
            patient=self.patient, doctor=self.user, department=self.department,
            appointment_date=date.today(), start_time=time(10), end_time=time(10, 30),
        )

    def test_overlapping_doctor_and_patient_booking_is_rejected(self):
        serializer = AppointmentSerializer(data={
            "patient": self.patient.pk,
            "doctor": self.user.pk,
            "department": self.department.pk,
            "appointment_date": self.appointment.appointment_date,
            "start_time": "10:15",
            "end_time": "10:45",
        })
        self.assertFalse(serializer.is_valid())
        self.assertTrue("doctor" in serializer.errors or "patient" in serializer.errors)

    def test_repeated_checkin_reuses_existing_queue_entry(self):
        self.client.force_authenticate(self.user)
        url = f"/api/appointments/{self.appointment.pk}/checkin/"

        first = self.client.post(url, {}, format="json", secure=True)
        second = self.client.post(url, {}, format="json", secure=True)

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(Queue.objects.filter(appointment=self.appointment).count(), 1)
        self.assertEqual(first.data["queue"]["id"], second.data["queue"]["id"])
