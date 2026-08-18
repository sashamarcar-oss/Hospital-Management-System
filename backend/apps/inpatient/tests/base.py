"""Shared fixtures and helpers for inpatient/nursing/ICU tests."""

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import Permission, Role
from apps.departments.models import Department
from apps.inpatient.models import (
    Admission,
    Bed,
    BedAssignment,
    ICUMonitoringSheet,
    ICUThreshold,
    NurseAssignment,
    NursingNote,
    NursingHandover,
    Room,
    Ward,
)
from apps.patients.models import Patient

User = get_user_model()


def create_role(role_code, permissions=()):
    role, _ = Role.objects.get_or_create(code=role_code, defaults={"name": role_code})
    for code in permissions:
        module, action = code.split(".", 1)
        perm, _ = Permission.objects.get_or_create(
            code=code, defaults={"name": code, "module": module}
        )
        role.permissions.add(perm)
    return role


def create_user(username, role_code, permissions=(), **kwargs):
    role = create_role(role_code, permissions)
    user = User.objects.create_user(username=username, password="pw", **kwargs)
    user.role = role
    user.save()
    return user


class InpatientBaseTestCase(APITestCase):
    def setUp(self):
        self.department = Department.objects.create(name="General Medicine")
        self.ward = Ward.objects.create(
            name="Ward A", code="WA", ward_type=Ward.TYPE_GENERAL, department=self.department
        )
        self.room = Room.objects.create(ward=self.ward, room_number="101")
        self.bed = Bed.objects.create(room=self.room, bed_number="1", status=Bed.STATUS_AVAILABLE)
        self.bed2 = Bed.objects.create(room=self.room, bed_number="2", status=Bed.STATUS_AVAILABLE)
        self.icu_ward = Ward.objects.create(name="ICU", code="ICU", ward_type=Ward.TYPE_ICU)
        self.icu_room = Room.objects.create(ward=self.icu_ward, room_number="ICU-1")
        self.icu_bed = Bed.objects.create(room=self.icu_room, bed_number="1", status=Bed.STATUS_AVAILABLE)

        self.doctor = create_user(
            "dr", "doctor",
            permissions=["admissions.view", "admissions.create", "admissions.discharge",
                         "inpatient.view", "inpatient.view_timeline", "inpatient.transfer",
                         "vitals.view", "vitals.create", "nursing.view", "icu.view",
                         "icu.review", "patients.view"],
        )
        self.nurse = create_user(
            "nurse", "nurse",
            permissions=["admissions.view", "admissions.create", "admissions.update",
                         "admissions.assign_bed",
                         "inpatient.view", "inpatient.view_timeline", "inpatient.assign_bed",
                         "inpatient.transfer", "inpatient.release_bed", "inpatient.reserve_bed",
                         "nursing.view", "nursing.create", "nursing.submit", "nursing.amend",
                         "nursing.handover", "nursing.manage_fluid", "icu.view",
                         "vitals.view", "vitals.create", "vitals.update", "patients.view",
                         "notifications.view", "dashboard.view"],
        )
        self.icu_nurse = create_user(
            "icunurse", "icu_nurse",
            permissions=["admissions.view", "inpatient.view", "nursing.view", "nursing.create",
                         "nursing.submit", "nursing.amend", "nursing.handover",
                         "nursing.manage_fluid", "icu.view", "icu.create", "icu.update",
                         "icu.record_fluid", "icu.review", "vitals.view", "vitals.create",
                         "notifications.view"],
        )
        self.other_nurse = create_user(
            "nurse2", "nurse",
            permissions=["admissions.view", "inpatient.view", "nursing.view", "nursing.create",
                         "icu.view", "vitals.view", "notifications.view"],
        )
        self.receptionist = create_user(
            "reception", "receptionist",
            permissions=["admissions.view", "admissions.create", "inpatient.view",
                         "inpatient.assign_bed", "inpatient.transfer", "inpatient.release_bed",
                         "inpatient.reserve_bed", "vitals.view", "patients.view"],
        )
        self.lab = create_user(
            "labtech", "lab_technician",
            permissions=["laboratory.view", "vitals.view", "patients.view"],
        )
        self.admin = User.objects.create_superuser(username="super", password="pw", email="a@a.com")

        self.patient1 = self._make_patient("Jane", "Doe")
        self.patient2 = self._make_patient("John", "Smith")

        self.admission1 = Admission.objects.create(
            patient=self.patient1, doctor=self.doctor, department=self.department,
            admission_reason="Observation", status=Admission.STATUS_ADMITTED,
        )
        self.admission2 = Admission.objects.create(
            patient=self.patient2, doctor=self.doctor, department=self.department,
            admission_reason="Surgery", status=Admission.STATUS_ADMITTED,
        )

    def _make_patient(self, first, last):
        return Patient.objects.create(
            first_name=first,
            last_name=last,
            date_of_birth=timezone.now().date().replace(year=1990),
            gender="female",
            phone="0712000000",
        )

    def _auth(self, user):
        self.client.force_authenticate(user=user)
        return user

    def _assign(self, admission, bed, user):
        url = f"/api/inpatient/beds/{bed.id}/assign/"
        return self.client.post(url, {"admission": admission.id, "notes": "test"}, format="json")

    def _seed_thresholds(self):
        ICUThreshold.objects.get_or_create(
            parameter="heart_rate", defaults={"name": "HR", "min_alert": 60, "max_alert": 100,
                                              "min_critical": 40, "max_critical": 130},
        )
        ICUThreshold.objects.get_or_create(
            parameter="spo2", defaults={"name": "SpO2", "min_alert": 94, "max_alert": 100,
                                        "min_critical": 90, "max_critical": None},
        )
