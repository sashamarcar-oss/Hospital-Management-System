from datetime import date, time, timedelta

from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Permission, Role, User
from apps.scheduling.models import NurseShift


class ShiftAccessTests(APITestCase):
    def setUp(self):
        self.admin = self.user("admin", Role.CODE_ADMIN)
        self.doctor = self.user("doctor", Role.CODE_DOCTOR)
        self.other_doctor = self.user("other-doctor", Role.CODE_DOCTOR)
        self.nurse = self.user("nurse", Role.CODE_NURSE)
        self.other_nurse = self.user("other-nurse", Role.CODE_NURSE)
        shift_view, _ = Permission.objects.get_or_create(code="shifts.view", defaults={"name": "View", "module": "shifts"})
        for role in (self.doctor.role, self.nurse.role):
            role.permissions.add(shift_view)
        self.doctor_shift = self.shift_for(self.doctor)
        self.nurse_shift = self.shift_for(self.nurse)

    def user(self, username, role_code):
        role, _ = Role.objects.get_or_create(code=role_code, defaults={"name": role_code})
        return User.objects.create_user(username=username, password="test-password", role=role)

    def shift_for(self, user):
        return NurseShift.objects.create(
            nurse=user,
            shift_date=date.today() + timedelta(days=1),
            start_time=time(8),
            end_time=time(16),
        )

    def test_admin_can_manage_and_assign_any_active_staff_member(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post("/api/shifts/", {
            "nurse": self.doctor.id,
            "shift_date": str(date.today() + timedelta(days=2)),
            "start_time": "08:00",
            "end_time": "16:00",
            "shift_type": "morning",
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created_id = response.data["id"]
        self.assertEqual(self.client.patch(f"/api/shifts/{created_id}/", {"location": "Outpatient"}).status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.delete(f"/api/shifts/{created_id}/").status_code, status.HTTP_204_NO_CONTENT)

    def test_doctor_can_only_read_their_own_shifts_and_cannot_change_roster(self):
        self.client.force_authenticate(self.doctor)
        self.assertEqual(self.client.get("/api/shifts/").data["count"], 1)
        self.assertEqual(self.client.get(f"/api/shifts/{self.nurse_shift.id}/").status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.post("/api/shifts/", {}).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.patch(f"/api/shifts/{self.doctor_shift.id}/", {"location": "Emergency"}).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.delete(f"/api/shifts/{self.doctor_shift.id}/").status_code, status.HTTP_403_FORBIDDEN)

    def test_nurse_can_only_read_their_own_shifts_and_cannot_change_roster(self):
        self.client.force_authenticate(self.nurse)
        self.assertEqual(self.client.get("/api/shifts/").data["count"], 1)
        self.assertEqual(self.client.get(f"/api/shifts/{self.doctor_shift.id}/").status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.post("/api/shifts/", {}).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.patch(f"/api/shifts/{self.nurse_shift.id}/", {"location": "Ward A"}).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.delete(f"/api/shifts/{self.nurse_shift.id}/").status_code, status.HTTP_403_FORBIDDEN)
