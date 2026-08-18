"""Tests for the admission workflow, vitals API, timeline, stats and role scoping."""

from django.utils import timezone

from apps.clinical.models import VitalSigns
from apps.core.models import Notification
from apps.inpatient.models import Admission, Bed, BedAssignment
from apps.inpatient.tests.base import InpatientBaseTestCase, create_user


class AdmissionWorkflowTests(InpatientBaseTestCase):
    def test_create_admission_with_bed_assigns_it(self):
        self._auth(self.nurse)
        resp = self.client.post("/api/inpatient/admissions/", {
            "patient": self.patient1.id,
            "doctor": self.doctor.id,
            "admission_reason": "Acute chest pain",
            "ward": self.ward.id,
            "bed": self.bed.id,
        }, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        admission = Admission.objects.get(pk=resp.data["id"])
        self.assertEqual(admission.bed_id, self.bed.id)
        self.bed.refresh_from_db()
        self.assertEqual(self.bed.status, Bed.STATUS_OCCUPIED)
        self.assertTrue(BedAssignment.objects.filter(
            admission=admission, released_at__isnull=True
        ).exists())

    def test_create_admission_with_busy_bed_rejected(self):
        self._auth(self.nurse)
        self._assign(self.admission1, self.bed, self.nurse)
        resp = self.client.post("/api/inpatient/admissions/", {
            "patient": self.patient2.id,
            "doctor": self.doctor.id,
            "admission_reason": "x",
            "bed": self.bed.id,
        }, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_admission_timeline_includes_events(self):
        self._auth(self.nurse)
        self._assign(self.admission1, self.bed, self.nurse)
        VitalSigns.objects.create(
            patient=self.patient1, admission=self.admission1, recorded_by=self.nurse,
            temperature=37.0, blood_pressure_systolic=120, blood_pressure_diastolic=80,
        )
        resp = self.client.get(f"/api/inpatient/admissions/{self.admission1.id}/timeline/")
        self.assertEqual(resp.status_code, 200, resp.content)
        types = {e["type"] for e in resp.data}
        self.assertIn("bed_assignment", types)
        self.assertIn("vitals", types)

    def test_patient_timeline_export_filtered_by_patient(self):
        self._auth(self.nurse)
        self._assign(self.admission1, self.bed, self.nurse)
        resp = self.client.get(f"/api/inpatient/timeline/?patient={self.patient1.id}")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(resp.data)


class VitalSignsAPITests(InpatientBaseTestCase):
    def test_record_vitals_for_admission(self):
        self._auth(self.nurse)
        resp = self.client.post("/api/vitals/", {
            "patient": self.patient1.id,
            "admission": self.admission1.id,
            "temperature": "38.1",
            "blood_pressure_systolic": 128,
            "blood_pressure_diastolic": 82,
            "pulse": 96,
            "oxygen_saturation": 97,
            "pain_score": 4,
        }, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertTrue(VitalSigns.objects.filter(admission=self.admission1).exists())

    def test_record_vitals_notifies_doctor(self):
        Notification.objects.all().delete()
        self._auth(self.nurse)
        self.client.post("/api/vitals/", {
            "patient": self.patient1.id,
            "admission": self.admission1.id,
            "pulse": 88,
        }, format="json")
        self.assertTrue(Notification.objects.filter(
            recipient=self.doctor, type="vitals"
        ).exists())

    def test_vitals_history_action(self):
        from apps.inpatient.services import assign_nurse_to_admission

        assign_nurse_to_admission(self.admission1, self.nurse, self.doctor)
        VitalSigns.objects.create(patient=self.patient1, admission=self.admission1,
                                  recorded_by=self.nurse, pulse=72)
        VitalSigns.objects.create(patient=self.patient1, admission=self.admission1,
                                  recorded_by=self.nurse, pulse=74)
        self._auth(self.nurse)
        resp = self.client.get(f"/api/vitals/history/?patient={self.patient1.id}")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(len(resp.data), 2)
        self.assertEqual(resp.data[0]["pulse"], 72)

    def test_vitals_export_csv_for_authorized_user(self):
        VitalSigns.objects.create(
            patient=self.patient1, admission=self.admission1, recorded_by=self.nurse,
            pulse=76,
        )
        self._auth(self.nurse)
        resp = self.client.get("/api/vitals/export/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/csv", resp["Content-Type"])
        self.assertIn(b"pulse", resp.content)

    def test_vitals_export_blocked_for_patient(self):
        patient_user = create_user(
            "portaluser", "patient",
            permissions=["vitals.view", "appointments.view", "notifications.view"],
        )
        self.patient1.user = patient_user
        self.patient1.save()
        patient_user.is_patient_account = True
        patient_user.save()
        VitalSigns.objects.create(patient=self.patient1, recorded_by=self.nurse, pulse=76)
        self._auth(patient_user)
        resp = self.client.get("/api/vitals/export/")
        self.assertEqual(resp.status_code, 403)


class StatsTests(InpatientBaseTestCase):
    def test_stats_endpoint_returns_dashboard_snapshot(self):
        self._auth(self.nurse)
        self._assign(self.admission1, self.bed, self.nurse)
        VitalSigns.objects.create(patient=self.patient1, admission=self.admission1,
                                  recorded_by=self.nurse, pulse=80)
        resp = self.client.get("/api/inpatient/stats/")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertIn("total_beds", resp.data)
        self.assertEqual(resp.data["occupied_beds"], 1)
        self.assertEqual(resp.data["available_beds"], 2)
        self.assertEqual(resp.data["admitted_patients"], 2)


class RoleScopingTests(InpatientBaseTestCase):
    def setUp(self):
        super().setUp()
        self.other_doctor = create_user(
            "dr2", "doctor",
            permissions=["admissions.view", "admissions.create", "admissions.discharge",
                         "inpatient.view", "inpatient.transfer", "vitals.view",
                         "vitals.create", "nursing.view", "icu.view", "patients.view"],
        )
        self.other_admission = Admission.objects.create(
            patient=self.patient2, doctor=self.other_doctor, admission_reason="Other",
        )

    def test_doctor_sees_only_own_admissions(self):
        self._auth(self.doctor)
        resp = self.client.get("/api/inpatient/admissions/")
        self.assertEqual(resp.status_code, 200)
        ids = {a["id"] for a in resp.data["results"]}
        self.assertIn(self.admission1.id, ids)
        self.assertNotIn(self.other_admission.id, ids)

    def test_doctor_sees_only_own_patient_vitals(self):
        VitalSigns.objects.create(patient=self.patient1, admission=self.admission1,
                                  recorded_by=self.nurse, pulse=70)
        VitalSigns.objects.create(patient=self.patient2, admission=self.other_admission,
                                  recorded_by=self.nurse, pulse=90)
        self._auth(self.doctor)
        resp = self.client.get("/api/vitals/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data["results"]), 1)
        self.assertEqual(resp.data["results"][0]["patient"], self.patient1.id)

    def test_nurse_sees_only_assigned_patients_vitals(self):
        from apps.inpatient.services import assign_nurse_to_admission

        assign_nurse_to_admission(self.admission1, self.nurse, self.doctor)
        VitalSigns.objects.create(patient=self.patient1, admission=self.admission1,
                                  recorded_by=self.nurse, pulse=70)
        VitalSigns.objects.create(patient=self.patient2, admission=self.other_admission,
                                  recorded_by=self.nurse, pulse=90)
        self._auth(self.nurse)
        resp = self.client.get("/api/vitals/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data["results"]), 1)
        self.assertEqual(resp.data["results"][0]["patient"], self.patient1.id)

    def test_patient_sees_only_own_vitals(self):
        patient_user = create_user(
            "portal2", "patient",
            permissions=["vitals.view", "appointments.view", "notifications.view"],
        )
        self.patient1.user = patient_user
        self.patient1.save()
        patient_user.is_patient_account = True
        patient_user.save()
        VitalSigns.objects.create(patient=self.patient1, recorded_by=self.nurse, pulse=70)
        VitalSigns.objects.create(patient=self.patient2, recorded_by=self.nurse, pulse=90)
        self._auth(patient_user)
        resp = self.client.get("/api/vitals/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data["results"]), 1)
        self.assertEqual(resp.data["results"][0]["patient"], self.patient1.id)

    def test_receptionist_can_view_beds_but_not_icu(self):
        self._auth(self.receptionist)
        resp = self.client.get("/api/inpatient/beds/")
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get("/api/icu/monitoring/")
        self.assertEqual(resp.status_code, 403)
