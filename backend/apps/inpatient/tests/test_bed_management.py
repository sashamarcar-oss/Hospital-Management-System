"""Tests for bed assignment, transfer, release, reservation and RBAC."""

from django.utils import timezone

from apps.core.models import AuditLog, Notification
from apps.inpatient.models import Admission, Bed, BedAssignment
from apps.inpatient.tests.base import InpatientBaseTestCase


class BedAssignmentTests(InpatientBaseTestCase):
    def test_assign_patient_to_bed_creates_assignment_and_marks_occupied(self):
        self._auth(self.nurse)
        resp = self._assign(self.admission1, self.bed, self.nurse)
        self.assertEqual(resp.status_code, 201, resp.content)
        self.bed.refresh_from_db()
        self.admission1.refresh_from_db()
        self.assertEqual(self.bed.status, Bed.STATUS_OCCUPIED)
        self.assertEqual(self.admission1.bed_id, self.bed.id)
        self.assertTrue(BedAssignment.objects.filter(
            admission=self.admission1, bed=self.bed, released_at__isnull=True
        ).exists())

    def test_assign_patient_to_bed_is_immutable_history(self):
        self._auth(self.nurse)
        self._assign(self.admission1, self.bed, self.nurse)
        self._assign(self.admission2, self.bed2, self.nurse)
        self.admission1.refresh_from_db()
        self.admission2.refresh_from_db()
        self.assertEqual(
            BedAssignment.objects.filter(admission=self.admission1).count(), 1
        )

    def test_cannot_double_book_same_bed(self):
        self._auth(self.nurse)
        self._assign(self.admission1, self.bed, self.nurse)
        resp = self._assign(self.admission2, self.bed, self.nurse)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("occupied or reserved", resp.data["detail"])

    def test_cannot_assign_bed_to_bed_already_in_maintenance(self):
        self._auth(self.nurse)
        self.bed.status = Bed.STATUS_MAINTENANCE
        self.bed.save()
        resp = self._assign(self.admission1, self.bed, self.nurse)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("maintenance", resp.data["detail"])

    def test_cannot_assign_bed_to_bed_in_cleaning(self):
        self._auth(self.nurse)
        self.bed.status = Bed.STATUS_CLEANING
        self.bed.save()
        resp = self._assign(self.admission1, self.bed, self.nurse)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("cleaning", resp.data["detail"])

    def test_cannot_assign_discharged_patient(self):
        self.admission1.status = Admission.STATUS_DISCHARGED
        self.admission1.save()
        self._auth(self.nurse)
        resp = self._assign(self.admission1, self.bed, self.nurse)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("discharged", resp.data["detail"])

    def test_cannot_assign_same_admission_twice(self):
        self._auth(self.nurse)
        self._assign(self.admission1, self.bed, self.nurse)
        resp = self._assign(self.admission1, self.bed2, self.nurse)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("active bed assignment", resp.data["detail"])

    def test_receptionist_can_assign_bed(self):
        self._auth(self.receptionist)
        resp = self._assign(self.admission1, self.bed, self.receptionist)
        self.assertEqual(resp.status_code, 201, resp.content)

    def test_unpermissioned_user_cannot_assign_bed(self):
        self._auth(self.lab)
        resp = self._assign(self.admission1, self.bed, self.lab)
        self.assertEqual(resp.status_code, 403)


class BedTransferTests(InpatientBaseTestCase):
    def test_transfer_releases_old_bed_and_assigns_new(self):
        self._auth(self.nurse)
        self._assign(self.admission1, self.bed, self.nurse)
        resp = self.client.post(
            f"/api/inpatient/admissions/{self.admission1.id}/transfer/",
            {"bed": self.bed2.id, "reason": "Room change"}, format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.bed.refresh_from_db()
        self.bed2.refresh_from_db()
        self.admission1.refresh_from_db()
        self.assertEqual(self.bed.status, Bed.STATUS_AVAILABLE)
        self.assertEqual(self.bed2.status, Bed.STATUS_OCCUPIED)
        self.assertEqual(self.admission1.bed_id, self.bed2.id)
        assignments = BedAssignment.objects.filter(admission=self.admission1).order_by("assigned_at")
        self.assertEqual(assignments.count(), 2)
        self.assertIsNotNone(assignments[0].released_at)
        self.assertIsNone(assignments[1].released_at)
        self.assertEqual(assignments[0].bed_id, self.bed.id)
        self.assertEqual(assignments[1].bed_id, self.bed2.id)

    def test_transfer_to_unavailable_bed_rejected(self):
        self._auth(self.nurse)
        self._assign(self.admission1, self.bed, self.nurse)
        self.bed2.status = Bed.STATUS_MAINTENANCE
        self.bed2.save()
        resp = self.client.post(
            f"/api/inpatient/admissions/{self.admission1.id}/transfer/",
            {"bed": self.bed2.id}, format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.bed.refresh_from_db()
        self.assertEqual(self.bed.status, Bed.STATUS_OCCUPIED)

    def test_transfer_of_unassigned_admission_rejected(self):
        self._auth(self.nurse)
        resp = self.client.post(
            f"/api/inpatient/admissions/{self.admission1.id}/transfer/",
            {"bed": self.bed2.id}, format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_transfer_requires_permission(self):
        self._auth(self.nurse)
        self._assign(self.admission1, self.bed, self.nurse)
        self._auth(self.lab)
        resp = self.client.post(
            f"/api/inpatient/admissions/{self.admission1.id}/transfer/",
            {"bed": self.bed2.id}, format="json",
        )
        self.assertEqual(resp.status_code, 403)


class BedReleaseTests(InpatientBaseTestCase):
    def test_release_bed_marks_available(self):
        self._auth(self.nurse)
        self._assign(self.admission1, self.bed, self.nurse)
        resp = self.client.post(
            f"/api/inpatient/beds/{self.bed.id}/release/",
            {"reason": "Discharged"}, format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.bed.refresh_from_db()
        self.assertEqual(self.bed.status, Bed.STATUS_AVAILABLE)
        assignment = BedAssignment.objects.get(admission=self.admission1, bed=self.bed)
        self.assertIsNotNone(assignment.released_at)
        self.assertEqual(assignment.release_reason, "Discharged")

    def test_release_bed_with_cleaning(self):
        self._auth(self.nurse)
        self._assign(self.admission1, self.bed, self.nurse)
        resp = self.client.post(
            f"/api/inpatient/beds/{self.bed.id}/release/",
            {"set_cleaning": True}, format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.bed.refresh_from_db()
        self.assertEqual(self.bed.status, Bed.STATUS_CLEANING)
        self.assertIsNotNone(self.bed.last_cleaned_at)

    def test_release_unoccupied_bed_rejected(self):
        self._auth(self.nurse)
        resp = self.client.post(
            f"/api/inpatient/beds/{self.bed.id}/release/", {}, format="json",
        )
        self.assertEqual(resp.status_code, 400)


class BedReservationTests(InpatientBaseTestCase):
    def test_reserve_bed_for_admission(self):
        self._auth(self.nurse)
        resp = self.client.post(
            f"/api/inpatient/beds/{self.bed.id}/reserve/",
            {"admission": self.admission1.id}, format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.bed.refresh_from_db()
        self.assertEqual(self.bed.status, Bed.STATUS_RESERVED)

    def test_fulfil_reservation_by_assigning_same_admission(self):
        self._auth(self.nurse)
        self.client.post(
            f"/api/inpatient/beds/{self.bed.id}/reserve/",
            {"admission": self.admission1.id}, format="json",
        )
        resp = self._assign(self.admission1, self.bed, self.nurse)
        self.assertEqual(resp.status_code, 201, resp.content)
        self.bed.refresh_from_db()
        self.assertEqual(self.bed.status, Bed.STATUS_OCCUPIED)
        active = BedAssignment.objects.filter(bed=self.bed, released_at__isnull=True)
        self.assertEqual(active.count(), 1)
        self.assertEqual(active.first().admission_id, self.admission1.id)

    def test_cannot_reserve_bed_for_another_admission_when_reserved(self):
        self._auth(self.nurse)
        self.client.post(
            f"/api/inpatient/beds/{self.bed.id}/reserve/",
            {"admission": self.admission1.id}, format="json",
        )
        resp = self.client.post(
            f"/api/inpatient/beds/{self.bed.id}/reserve/",
            {"admission": self.admission2.id}, format="json",
        )
        self.assertEqual(resp.status_code, 400)


class BedBoardTests(InpatientBaseTestCase):
    def test_board_groups_beds_by_ward(self):
        self._auth(self.nurse)
        self._assign(self.admission1, self.bed, self.nurse)
        resp = self.client.get("/api/inpatient/beds/board/")
        self.assertEqual(resp.status_code, 200)
        wards = {item["ward"]["id"]: item for item in resp.data}
        self.assertIn(self.ward.id, wards)
        self.assertIn(self.icu_ward.id, wards)
        beds = {b["id"] for item in wards.values() for b in item["beds"]}
        self.assertIn(self.bed.id, beds)


class BedAssignmentAuditTests(InpatientBaseTestCase):
    def test_assign_logs_audit(self):
        self._auth(self.nurse)
        self._assign(self.admission1, self.bed, self.nurse)
        self.assertTrue(AuditLog.objects.filter(
            module__startswith="inpatient"
        ).exists())

    def test_bed_assignment_notifies_assigned_nurse_only(self):
        self.admission1.assigned_nurse = self.nurse
        self.admission1.save()
        Notification.objects.all().delete()
        self._auth(self.nurse)
        self._assign(self.admission1, self.bed, self.nurse)
        notified = set(Notification.objects.filter(
            type="bed_assignment"
        ).values_list("recipient_id", flat=True))
        self.assertIn(self.nurse.id, notified)
        self.assertIn(self.doctor.id, notified)
        self.assertNotIn(self.other_nurse.id, notified)
        self.assertNotIn(self.icu_nurse.id, notified)
