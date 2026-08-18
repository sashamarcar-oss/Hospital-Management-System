"""Tests for ICU monitoring sheets, records, alerts, thresholds and fluid balance."""

from apps.core.models import Notification
from apps.inpatient.models import (
    FluidBalance,
    ICUMonitoringRecord,
    ICUMonitoringSheet,
    ICUThreshold,
)
from apps.inpatient.tests.base import InpatientBaseTestCase


class ICUSheetTests(InpatientBaseTestCase):
    def test_icu_nurse_creates_sheet(self):
        self._auth(self.icu_nurse)
        resp = self.client.post("/api/icu/sheets/", {
            "admission": self.admission1.id,
            "bed": self.icu_bed.id,
            "period": ICUMonitoringSheet.PERIOD_MORNING,
            "interval": ICUMonitoringSheet.INTERVAL_HOURLY,
            "doctor": self.doctor.id,
        }, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(ICUMonitoringSheet.objects.filter(
            admission=self.admission1, status=ICUMonitoringSheet.STATUS_ACTIVE
        ).count(), 1)

    def test_regular_nurse_cannot_create_icu_sheet(self):
        self._auth(self.nurse)
        resp = self.client.post("/api/icu/sheets/", {
            "admission": self.admission1.id,
        }, format="json")
        self.assertEqual(resp.status_code, 403)


class ICUAlertTests(InpatientBaseTestCase):
    def setUp(self):
        super().setUp()
        self._seed_thresholds()
        self.sheet = ICUMonitoringSheet.objects.create(
            admission=self.admission1, nurse=self.icu_nurse, doctor=self.doctor,
            period=ICUMonitoringSheet.PERIOD_MORNING,
        )

    def test_record_evaluates_critical_alert(self):
        self._auth(self.icu_nurse)
        resp = self.client.post("/api/icu/monitoring/", {
            "admission": self.admission1.id,
            "sheet": self.sheet.id,
            "heart_rate": 140,
            "blood_pressure": "90/60",
            "temperature": "38.6",
            "oxygen_saturation": 95,
            "gcs_eye": 3, "gcs_verbal": 4, "gcs_motor": 5,
        }, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertTrue(resp.data.get("alerts"))
        severities = {a["severity"] for a in resp.data["alerts"]}
        self.assertIn(ICUThreshold.SEVERITY_CRITICAL, severities)

    def test_critical_alert_notifies_assigned_staff(self):
        self.admission1.assigned_nurse = self.icu_nurse
        self.admission1.save()
        Notification.objects.all().delete()
        self._auth(self.icu_nurse)
        self.client.post("/api/icu/monitoring/", {
            "admission": self.admission1.id,
            "sheet": self.sheet.id,
            "heart_rate": 140,
        }, format="json")
        self.assertTrue(Notification.objects.filter(
            type="icu_alert",
            recipient__in=[self.doctor, self.icu_nurse],
        ).exists())
        alert = Notification.objects.filter(type="icu_alert").first()
        self.assertEqual(alert.priority, "urgent")

    def test_normal_values_produce_no_alerts(self):
        self._auth(self.icu_nurse)
        resp = self.client.post("/api/icu/monitoring/", {
            "admission": self.admission1.id,
            "sheet": self.sheet.id,
            "heart_rate": 72,
            "oxygen_saturation": 98,
        }, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertFalse(resp.data.get("alerts"))


class ICUThresholdTests(InpatientBaseTestCase):
    def test_configured_threshold_can_be_updated_by_admin(self):
        self._seed_thresholds()
        threshold = ICUThreshold.objects.get(parameter="heart_rate")
        self._auth(self.admin)
        resp = self.client.patch(
            f"/api/icu/thresholds/{threshold.id}/",
            {"max_alert": "110"}, format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        threshold.refresh_from_db()
        self.assertEqual(float(threshold.max_alert), 110.0)

    def test_threshold_update_blocked_for_icu_nurse(self):
        self._seed_thresholds()
        threshold = ICUThreshold.objects.get(parameter="heart_rate")
        self._auth(self.icu_nurse)
        resp = self.client.patch(
            f"/api/icu/thresholds/{threshold.id}/",
            {"max_alert": "110"}, format="json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_threshold_view_allowed_for_authorized_staff(self):
        self._seed_thresholds()
        self._auth(self.doctor)
        resp = self.client.get("/api/icu/thresholds/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data["results"]), 2)


class FluidBalanceTests(InpatientBaseTestCase):
    def test_create_fluid_balance_and_totals(self):
        self._auth(self.icu_nurse)
        resp = self.client.post("/api/icu/fluid-balance/", {
            "admission": self.admission1.id,
            "oral_intake_ml": 500,
            "iv_intake_ml": 1000,
            "urine_output_ml": 600,
            "drain_output_ml": 100,
        }, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        fb = FluidBalance.objects.get(pk=resp.data["id"])
        self.assertEqual(fb.total_intake_ml, 1500)
        self.assertEqual(fb.total_output_ml, 700)
        self.assertEqual(fb.net_balance_ml, 800)
        self.assertEqual(resp.data["total_intake_ml"], 1500)
        self.assertEqual(resp.data["net_balance_ml"], 800)

    def test_regular_nurse_cannot_create_fluid_balance(self):
        self._auth(self.nurse)
        resp = self.client.post("/api/icu/fluid-balance/", {
            "admission": self.admission1.id,
            "oral_intake_ml": 100,
        }, format="json")
        self.assertEqual(resp.status_code, 403)


class ICUScopingTests(InpatientBaseTestCase):
    def test_lab_technician_cannot_view_icu(self):
        ICUMonitoringRecord.objects.create(admission=self.admission1)
        self._auth(self.lab)
        resp = self.client.get("/api/icu/monitoring/")
        self.assertEqual(resp.status_code, 403)
