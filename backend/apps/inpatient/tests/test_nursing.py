"""Tests for nursing notes (lifecycle, amendments) and handovers."""

from apps.core.models import AuditLog, Notification
from apps.inpatient.models import (
    Admission,
    Bed,
    NurseAssignment,
    NursingHandover,
    NursingNote,
    NursingNoteAmendment,
)
from apps.inpatient.services import assign_nurse_to_admission
from apps.inpatient.tests.base import InpatientBaseTestCase


class NursingNoteLifecycleTests(InpatientBaseTestCase):
    def _create_note(self, **extra):
        data = {
            "admission": self.admission1.id,
            "shift_type": NursingNote.SHIFT_MORNING,
            "condition": "stable",
            "note": "Patient resting comfortably.",
            "observations": "Mild tachycardia.",
        }
        data.update(extra)
        return data

    def test_create_draft_note(self):
        self._auth(self.nurse)
        resp = self.client.post("/api/nursing/notes/", self._create_note(), format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        note = NursingNote.objects.get(pk=resp.data["id"])
        self.assertEqual(note.status, NursingNote.STATUS_DRAFT)
        self.assertEqual(note.nurse_id, self.nurse.id)

    def test_create_note_as_submitted(self):
        self._auth(self.nurse)
        resp = self.client.post(
            "/api/nursing/notes/",
            self._create_note(status=NursingNote.STATUS_SUBMITTED),
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        note = NursingNote.objects.get(pk=resp.data["id"])
        self.assertEqual(note.status, NursingNote.STATUS_SUBMITTED)
        self.assertIsNotNone(note.submitted_at)

    def test_submit_draft_note(self):
        self._auth(self.nurse)
        note = NursingNote.objects.create(
            admission=self.admission1, nurse=self.nurse, note="draft",
        )
        resp = self.client.post(f"/api/nursing/notes/{note.id}/submit/", {}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        note.refresh_from_db()
        self.assertEqual(note.status, NursingNote.STATUS_SUBMITTED)
        self.assertIsNotNone(note.submitted_at)

    def test_cannot_submit_twice(self):
        self._auth(self.nurse)
        note = NursingNote.objects.create(
            admission=self.admission1, nurse=self.nurse, note="draft",
            status=NursingNote.STATUS_SUBMITTED, submitted_at="2026-01-01T10:00:00Z",
        )
        resp = self.client.post(f"/api/nursing/notes/{note.id}/submit/", {}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_cannot_edit_submitted_note(self):
        self._auth(self.nurse)
        note = NursingNote.objects.create(
            admission=self.admission1, nurse=self.nurse, note="draft",
            status=NursingNote.STATUS_SUBMITTED,
        )
        resp = self.client.patch(
            f"/api/nursing/notes/{note.id}/", {"note": "edited"}, format="json"
        )
        self.assertEqual(resp.status_code, 403)
        note.refresh_from_db()
        self.assertEqual(note.note, "draft")

    def test_amend_preserves_original(self):
        self._auth(self.nurse)
        note = NursingNote.objects.create(
            admission=self.admission1, nurse=self.nurse, note="original",
            observations="obs1", status=NursingNote.STATUS_SUBMITTED,
        )
        resp = self.client.post(
            f"/api/nursing/notes/{note.id}/amend/",
            {"reason": "Correction to observations", "note": "corrected note",
             "observations": "obs2"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        amended = NursingNote.objects.get(pk=resp.data["id"])
        self.assertEqual(amended.status, NursingNote.STATUS_AMENDED)
        self.assertEqual(amended.note, "corrected note")
        self.assertEqual(amended.amended_from_id, note.id)
        self.assertEqual(amended.amendment_reason, "Correction to observations")
        original = NursingNote.objects.get(pk=note.id)
        self.assertEqual(original.note, "original")
        self.assertTrue(NursingNoteAmendment.objects.filter(note=amended).exists())

    def test_amend_requires_reason(self):
        self._auth(self.nurse)
        note = NursingNote.objects.create(
            admission=self.admission1, nurse=self.nurse, note="original",
            status=NursingNote.STATUS_SUBMITTED,
        )
        resp = self.client.post(
            f"/api/nursing/notes/{note.id}/amend/", {"note": "x"}, format="json"
        )
        self.assertEqual(resp.status_code, 400)

    def test_amend_draft_rejected(self):
        self._auth(self.nurse)
        note = NursingNote.objects.create(
            admission=self.admission1, nurse=self.nurse, note="draft",
        )
        resp = self.client.post(
            f"/api/nursing/notes/{note.id}/amend/",
            {"reason": "why", "note": "x"}, format="json"
        )
        self.assertEqual(resp.status_code, 400)

    def test_amend_audited(self):
        self._auth(self.nurse)
        note = NursingNote.objects.create(
            admission=self.admission1, nurse=self.nurse, note="original",
            status=NursingNote.STATUS_SUBMITTED,
        )
        self.client.post(
            f"/api/nursing/notes/{note.id}/amend/",
            {"reason": "fix", "observations": "new"}, format="json"
        )
        self.assertTrue(AuditLog.objects.filter(module__startswith="inpatient").exists())


class NursingNoteScopingTests(InpatientBaseTestCase):
    def test_nurse_sees_own_assignments_only(self):
        assign_nurse_to_admission(self.admission1, self.nurse, self.doctor)
        NursingNote.objects.create(admission=self.admission1, nurse=self.nurse, note="mine")
        NursingNote.objects.create(admission=self.admission2, nurse=self.other_nurse, note="not mine")
        self._auth(self.nurse)
        resp = self.client.get("/api/nursing/notes/")
        self.assertEqual(resp.status_code, 200)
        notes = resp.data["results"]
        self.assertEqual(len(notes), 1)
        self.assertEqual(notes[0]["admission"], self.admission1.id)

    def test_lab_technician_cannot_view_nursing_notes(self):
        NursingNote.objects.create(admission=self.admission1, nurse=self.nurse, note="x")
        self._auth(self.lab)
        resp = self.client.get("/api/nursing/notes/")
        self.assertEqual(resp.status_code, 403)


class NursingHandoverTests(InpatientBaseTestCase):
    def test_create_handover_notifies_incoming_nurse(self):
        assign_nurse_to_admission(self.admission1, self.nurse, self.doctor)
        Notification.objects.all().delete()
        self._auth(self.nurse)
        resp = self.client.post("/api/nursing/handovers/", {
            "admission": self.admission1.id,
            "shift_type": NursingNote.SHIFT_NIGHT,
            "condition": "stable",
            "incoming_nurse": self.other_nurse.id,
            "current_condition": "Stable, awaiting review.",
            "pending_tasks": "Renew oxygen tank.",
        }, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertTrue(Notification.objects.filter(
            recipient=self.other_nurse, type="handover"
        ).exists())

    def test_my_handovers_lists_incoming_only(self):
        handover = NursingHandover.objects.create(
            admission=self.admission1, nurse=self.nurse, incoming_nurse=self.icu_nurse,
            condition="stable",
        )
        NursingHandover.objects.create(
            admission=self.admission2, nurse=self.other_nurse, incoming_nurse=self.nurse,
            condition="stable",
        )
        self._auth(self.icu_nurse)
        resp = self.client.get("/api/nursing/handovers/my_handovers/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual([h["id"] for h in resp.data], [handover.id])


class NurseAssignmentTests(InpatientBaseTestCase):
    def test_assign_nurse_to_admission_via_api(self):
        self._auth(self.nurse)
        resp = self.client.post(
            f"/api/inpatient/admissions/{self.admission1.id}/assign_nurse/",
            {"nurse": self.other_nurse.id, "role": NurseAssignment.ROLE_PRIMARY},
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertTrue(NurseAssignment.objects.filter(
            admission=self.admission1, nurse=self.other_nurse, unassigned_at__isnull=True
        ).exists())

    def test_cannot_assign_same_nurse_twice_active(self):
        assign_nurse_to_admission(self.admission1, self.other_nurse, self.doctor)
        self._auth(self.nurse)
        resp = self.client.post(
            f"/api/inpatient/admissions/{self.admission1.id}/assign_nurse/",
            {"nurse": self.other_nurse.id}, format="json",
        )
        self.assertEqual(resp.status_code, 400)
