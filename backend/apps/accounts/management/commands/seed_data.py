"""Seed the database with realistic development data.

Usage: python manage.py seed_data [--superuser-only] [--patients N]
"""

import random
from datetime import date, datetime, timedelta, time

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import Permission, Role, User
from apps.accounts.permission_catalog import build_catalog, permissions_for_role
from apps.appointments.models import Appointment, Queue
from apps.billing.models import ChargeType, Invoice, InvoiceItem, Payment
from apps.clinical.models import (
    Consultation,
    Diagnosis,
    Prescription,
    PrescriptionItem,
    VitalSigns,
)
from apps.core.models import Notification
from apps.departments.models import Department
from apps.emergency.models import EmergencyVisit
from apps.inpatient.models import Admission, Bed, Room, Ward
from apps.insurance.models import InsuranceClaim, InsurancePolicy, InsuranceProvider
from apps.inventory.models import InventoryItem, Supplier
from apps.laboratory.models import LabRequest, LabRequestItem, LabTestCatalog
from apps.patients.models import Patient
from apps.pharmacy.models import (
    Medicine,
    MedicineBatch,
    MedicineCategory,
    MedicineStockMovement,
)
from apps.radiology.models import RadiologyReport, RadiologyRequest
from apps.staff.models import Staff

RANDOM = random.Random(42)

FIRST_NAMES = ["Amara", "Oluwaseun", "Nneka", "Kwame", "Fatima", "Chinedu", "Aisha", "Yusuf",
               "Ibrahim", "Blessing", "Tunde", "Chioma", "Emeka", "Halima", "Segun", "Ngozi",
               "Kofi", "Adaeze", "Musa", "Ifeoma"]
LAST_NAMES = ["Okafor", "Balogun", "Eze", "Mensah", "Abdullahi", "Adeyemi", "Okonkwo", "Diallo",
              "Ibrahim", "Nwachukwu", "Bello", "Uche", "Owusu", "Adebayo", "Mohammed", "Adeleke"]

DEPARTMENT_NAMES = [
    ("Outpatient", "OPD"), ("Inpatient", "IPD"), ("Emergency", "ER"),
    ("Pediatrics", "PED"), ("Maternity", "MAT"), ("Surgery", "SUR"),
    ("Laboratory", "LAB"), ("Pharmacy", "PHM"), ("Radiology", "RAD"),
    ("Dental", "DEN"), ("Physiotherapy", "PHY"), ("Administration", "ADM"),
]

MEDICINES = [
    ("Paracetamol", "paracetamol", "500mg", "tablet", 10, 1.50, 3.00, 30),
    ("Amoxicillin", "amoxicillin", "250mg", "capsule", 8, 2.00, 4.50, 60),
    ("Ibuprofen", "ibuprofen", "400mg", "tablet", 12, 1.75, 3.50, 40),
    ("Metformin", "metformin", "500mg", "tablet", 15, 1.20, 2.80, 50),
    ("Amlodipine", "amlodipine", "5mg", "tablet", 15, 2.10, 4.20, 35),
    ("Omeprazole", "omeprazole", "20mg", "capsule", 20, 2.40, 5.00, 25),
    ("Azithromycin", "azithromycin", "500mg", "tablet", 10, 5.50, 9.00, 20),
    ("Salbutamol", "salbutamol", "100mcg", "inhaler", 5, 8.00, 14.00, 15),
    ("Cetirizine", "cetirizine", "10mg", "tablet", 20, 0.80, 1.80, 60),
    ("Insulin Glargine", "insulin glargine", "100IU/ml", "vial", 3, 25.00, 40.00, 10),
]

LAB_TESTS = [
    ("Complete Blood Count", "hematology", "blood", "WBC 4-11 x10^9/L, Hb 12-17 g/dL", "test", 25.00),
    ("Blood Glucose", "biochemistry", "blood", "70-110 mg/dL", "mg/dL", 12.00),
    ("Urinalysis", "urinalysis", "urine", "", "", 15.00),
    ("Lipid Panel", "biochemistry", "blood", "Chol <200 mg/dL", "mg/dL", 35.00),
    ("Liver Function Test", "biochemistry", "blood", "", "", 30.00),
    ("Malaria Smear", "microbiology", "blood", "Negative", "", 10.00),
    ("Typhoid (Widal)", "serology", "blood", "Negative", "", 14.00),
    ("Thyroid Panel", "immunology", "blood", "", "", 45.00),
    ("Creatinine", "biochemistry", "blood", "0.6-1.2 mg/dL", "mg/dL", 15.00),
    ("HIV Rapid Test", "serology", "blood", "Negative", "", 8.00),
]

CHARGE_TYPES = [
    ("General Consultation", "consultation", "consultation", 25.00),
    ("Specialist Consultation", "specialist_consultation", "consultation", 50.00),
    ("Emergency Consultation", "emergency_consultation", "consultation", 60.00),
    ("General Ward (per day)", "general_bed", "bed", 40.00),
    ("Private Room (per day)", "private_bed", "bed", 120.00),
    ("ICU (per day)", "icu_bed", "bed", 300.00),
    ("X-Ray", "xray", "imaging", 55.00),
    ("Ultrasound", "ultrasound", "imaging", 65.00),
    ("CT Scan", "ct_scan", "imaging", 250.00),
    ("MRI", "mri", "imaging", 400.00),
    ("Small Procedure", "small_procedure", "procedure", 75.00),
    ("Major Surgery", "major_surgery", "procedure", 1500.00),
    ("Dressing", "dressing", "procedure", 15.00),
]


def make_phone():
    return f"+23320{random.randint(1000000, 9999999)}"


class Command(BaseCommand):
    help = "Seed the database with realistic development data."

    def add_arguments(self, parser):
        parser.add_argument("--patients", type=int, default=15)
        parser.add_argument("--superuser-only", action="store_true")

    def handle(self, *args, **options):
        self.stdout.write("Seeding Hospital Management System data...")
        self._sync_permissions_and_roles()
        departments = self._create_departments()
        admin = self._create_admin()
        if options["superuser_only"]:
            self.stdout.write(self.style.SUCCESS("Superuser seeded. Done."))
            return

        staff_map = self._create_staff(departments)
        patients = self._create_patients(options["patients"])
        self._create_wards()
        self._create_pharmacy()
        self._create_lab_catalog()
        self._create_charge_types()
        self._create_inventory()
        self._create_insurance()
        self._create_clinical_data(patients, staff_map, departments)
        self._create_billing(patients, staff_map)
        self._create_notifications(staff_map, patients)
        self.stdout.write(self.style.SUCCESS(
            "Seed complete. Login: admin / %s" % settings.SEED_ADMIN_PASSWORD
        ))

    # ------------------------------------------------------------------
    def _sync_permissions_and_roles(self):
        catalog = build_catalog()
        for module, actions in catalog.items():
            for code, name in actions.items():
                Permission.objects.update_or_create(
                    code=code, defaults={"name": name, "module": module}
                )
        for code, name in Role.ROLE_CHOICES:
            role, _ = Role.objects.update_or_create(
                code=code, defaults={"name": name}
            )
            role.permissions.set(
                Permission.objects.filter(code__in=permissions_for_role(code))
            )
        self.stdout.write(f"Synced {Permission.objects.count()} permissions and {Role.objects.count()} roles.")

    def _create_departments(self):
        for name, code in DEPARTMENT_NAMES:
            Department.objects.update_or_create(name=name, defaults={"code": code})
        return list(Department.objects.all())

    def _create_admin(self):
        username = settings.SEED_ADMIN_USERNAME
        admin, created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": settings.SEED_ADMIN_EMAIL,
                "first_name": "System",
                "last_name": "Administrator",
                "is_superuser": True,
                "is_staff": True,
            },
        )
        if created:
            admin.set_password(settings.SEED_ADMIN_PASSWORD)
        admin.role = Role.objects.filter(code=Role.CODE_SUPER_ADMIN).first()
        admin.department = Department.objects.filter(name="Administration").first()
        admin.save()
        Staff.objects.update_or_create(
            user=admin,
            defaults={
                "employee_id": "EMP-0001",
                "job_title": "Chief Executive Officer",
                "date_joined": date.today() - timedelta(days=900),
            },
        )
        self.stdout.write(f"Admin user ready: {username}")
        return admin

    def _create_staff(self, departments):
        by_name = {d.name: d for d in departments}
        specs = [
            ("admin2", "Hospital", "Administrator", "admin", "Administration", "Hospital Administrator", "EMP-0002", 900),
            ("dr.adeyemi", "Adaeze", "Adeyemi", "doctor", "Outpatient", "General Practitioner", "EMP-0003", 700),
            ("dr.balogun", "Tunde", "Balogun", "doctor", "Pediatrics", "Pediatrician", "EMP-0004", 650),
            ("dr.okafor", "Emeka", "Okafor", "doctor", "Surgery", "General Surgeon", "EMP-0005", 800),
            ("nurse.eze", "Chioma", "Eze", "nurse", "Inpatient", "Registered Nurse", "EMP-0006", 500),
            ("nurse.mensah", "Kofi", "Mensah", "nurse", "Emergency", "Emergency Nurse", "EMP-0007", 520),
            ("reception.nneka", "Nneka", "Uche", "receptionist", "Outpatient", "Receptionist", "EMP-0008", 350),
            ("lab.kwame", "Kwame", "Owusu", "lab_technician", "Laboratory", "Lab Technician", "EMP-0009", 420),
            ("pharm.fatima", "Fatima", "Abdullahi", "pharmacist", "Pharmacy", "Pharmacist", "EMP-0010", 480),
            ("acct.blessing", "Blessing", "Adeleke", "accountant", "Administration", "Accountant", "EMP-0011", 450),
            ("hr.segun", "Segun", "Bello", "hr", "Administration", "HR Manager", "EMP-0012", 460),
            ("rad.ibrahim", "Ibrahim", "Diallo", "doctor", "Radiology", "Radiologist", "EMP-0013", 700),
        ]
        staff_map = {}
        role_map = {r.code: r for r in Role.objects.all()}
        for username, first, last, role_code, dept_name, title, emp_id, days in specs:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": first,
                    "last_name": last,
                    "email": f"{username}@hospital.local",
                    "phone": make_phone(),
                    "role": role_map.get(role_code),
                    "department": by_name.get(dept_name),
                },
            )
            if created:
                user.set_password("Password@123")
                user.save()
            staff, _ = Staff.objects.update_or_create(
                user=user,
                defaults={
                    "employee_id": emp_id,
                    "job_title": title,
                    "license_number": f"LIC-{random.randint(10000, 99999)}",
                    "qualifications": "BSc / MD",
                    "date_joined": date.today() - timedelta(days=days),
                },
            )
            staff_map[role_code] = staff_map.get(role_code, []) + [user]
        self.stdout.write(f"Seeded {User.objects.count()} users.")
        return staff_map

    def _create_patients(self, count):
        patients = []
        genders = ["male", "female", "male", "female"]
        blood = ["A+", "O+", "B+", "AB+", "O-", "A-"]
        for i in range(count):
            first = RANDOM.choice(FIRST_NAMES)
            last = RANDOM.choice(LAST_NAMES)
            dob = date.today() - timedelta(days=random.randint(730, 30000))
            gender = RANDOM.choice(genders)
            patient, created = Patient.objects.get_or_create(
                national_id=f"NID-{random.randint(10000000, 99999999)}",
                defaults={
                    "first_name": first,
                    "middle_name": "",
                    "last_name": last,
                    "date_of_birth": dob,
                    "gender": gender,
                    "phone": make_phone(),
                    "email": f"{first.lower()}.{last.lower()}@mail.local",
                    "address": f"{random.randint(1, 250)} Example Street, Accra",
                    "blood_group": RANDOM.choice(blood),
                    "allergies": random.choice(["", "", "", "Penicillin", "Aspirin", "Peanuts"]),
                    "occupation": random.choice(["Teacher", "Engineer", "Trader", "Student", "Retired", "Nurse"]),
                    "insurance_provider": random.choice(["NHIS", "Equity Health", "AXA Health", ""]),
                    "insurance_number": f"INS-{random.randint(100000, 999999)}" if random.random() > 0.4 else "",
                    "next_of_kin_name": RANDOM.choice(LAST_NAMES),
                    "next_of_kin_phone": make_phone(),
                    "next_of_kin_relationship": random.choice(["Spouse", "Parent", "Sibling"]),
                },
            )
            patients.append(patient)
        self.stdout.write(f"Seeded {len(patients)} patients.")
        return patients

    def _create_wards(self):
        ward_specs = [
            ("General Ward A", "general", 20), ("General Ward B", "general", 20),
            ("Private Suites", "private", 8), ("ICU", "icu", 6),
            ("Maternity Ward", "maternity", 12), ("Pediatrics Ward", "pediatrics", 12),
            ("Surgical Ward", "surgical", 15),
        ]
        for name, wtype, bed_count in ward_specs:
            ward, _ = Ward.objects.get_or_create(
                name=name, defaults={"ward_type": wtype, "code": name[:3].upper()}
            )
            if not ward.rooms.exists():
                room = Room.objects.create(ward=ward, room_number="R1", room_type=wtype)
                for i in range(1, bed_count + 1):
                    Bed.objects.create(room=room, bed_number=f"B{i}")
        self.stdout.write(f"Seeded {Ward.objects.count()} wards.")

    def _create_pharmacy(self):
        for name, generic, strength, unit, qty, purchase, selling, reorder in MEDICINES:
            category, _ = MedicineCategory.objects.get_or_create(name="General")
            medicine, _ = Medicine.objects.get_or_create(
                name=name,
                defaults={
                    "generic_name": generic,
                    "strength": strength,
                    "unit": unit,
                    "category": category,
                    "manufacturer": "MedPharma Ltd",
                    "reorder_level": reorder,
                    "purchase_price": purchase,
                    "selling_price": selling,
                },
            )
            if not medicine.batches.exists():
                batch = MedicineBatch.objects.create(
                    medicine=medicine,
                    batch_number=f"BATCH-{random.randint(1000, 9999)}",
                    quantity=qty,
                    purchase_price=purchase,
                    expiry_date=date.today() + timedelta(days=random.randint(180, 720)),
                    supplier="MedPharma Ltd",
                )
                MedicineStockMovement.objects.create(
                    medicine=medicine, batch=batch,
                    movement_type=MedicineStockMovement.MOVEMENT_RECEIVE,
                    quantity=qty, balance_after=qty, reference="seed",
                )
        self.stdout.write(f"Seeded {Medicine.objects.count()} medicines.")

    def _create_lab_catalog(self):
        for name, category, sample, normal, units, price in LAB_TESTS:
            LabTestCatalog.objects.get_or_create(
                name=name,
                defaults={"category": category, "sample_type": sample,
                          "normal_range": normal, "units": units, "price": price},
            )
        self.stdout.write(f"Seeded {LabTestCatalog.objects.count()} lab tests.")

    def _create_charge_types(self):
        for name, code, category, price in CHARGE_TYPES:
            ChargeType.objects.get_or_create(
                code=code, defaults={"name": name, "category": category, "default_price": price}
            )

    def _create_inventory(self):
        supplier, _ = Supplier.objects.get_or_create(name="Global Medical Supplies")
        items = [
            ("Surgical Gloves", "ppe", "box", 100, 5.00),
            ("Face Masks", "ppe", "box", 200, 3.00),
            ("Syringes (5ml)", "consumables", "box", 150, 4.00),
            ("IV Drip Sets", "consumables", "pack", 80, 6.50),
            ("Gauze Rolls", "consumables", "pack", 120, 2.50),
            ("Hand Sanitizer", "consumables", "bottle", 60, 3.75),
        ]
        for name, category, unit, qty, price in items:
            InventoryItem.objects.get_or_create(
                name=name,
                defaults={"category": category, "unit": unit, "quantity": qty,
                          "reorder_level": 20, "purchase_price": price, "selling_price": price * 1.5,
                          "supplier": supplier},
            )

    def _create_insurance(self):
        provider, _ = InsuranceProvider.objects.get_or_create(
            name="National Health Insurance", defaults={"code": "NHIS", "phone": "0302123456"}
        )
        for policy_provider in ["Equity Health", "AXA Health"]:
            InsuranceProvider.objects.get_or_create(name=policy_provider, defaults={"code": policy_provider[:4].upper()})
        patients = Patient.objects.filter(insurance_provider__in=["NHIS", "Equity Health", "AXA Health"])
        for patient in patients:
            p = InsuranceProvider.objects.filter(name=patient.insurance_provider).first()
            if p and not InsurancePolicy.objects.filter(patient=patient, provider=p).exists():
                InsurancePolicy.objects.create(
                    patient=patient, provider=p,
                    policy_number=f"POL-{random.randint(100000, 999999)}",
                    membership_number=f"MBR-{random.randint(100000, 999999)}",
                    coverage_type="both",
                    coverage_limit=random.choice([5000, 10000, 15000, 20000]),
                    start_date=date.today() - timedelta(days=random.randint(30, 300)),
                    end_date=date.today() + timedelta(days=random.randint(30, 300)),
                )
        self.stdout.write(f"Seeded {InsurancePolicy.objects.count()} insurance policies.")

    def _create_clinical_data(self, patients, staff_map, departments):
        doctors = staff_map.get("doctor", [])
        if not doctors:
            return
        by_name = {d.name: d for d in departments}
        # Appointments across the past and next few days
        for i, patient in enumerate(patients[:12]):
            doctor = doctors[i % len(doctors)]
            appt_date = date.today() + timedelta(days=(i % 7) - 3)
            start = time(9, (i * 20) % 60)
            end = time(start.hour, start.minute + 30) if start.minute + 30 < 60 else time(start.hour + 1, (start.minute + 30) % 60)
            appointment, created = Appointment.objects.get_or_create(
                patient=patient, doctor=doctor, appointment_date=appt_date,
                start_time=start,
                defaults={
                    "end_time": end,
                    "department": by_name.get("Outpatient"),
                    "reason": RANDOM.choice(["Routine check-up", "Fever and headache", "Follow-up", "Cough", "Abdominal pain"]),
                    "priority": RANDOM.choice(["routine", "routine", "routine", "urgent"]),
                    "status": RANDOM.choice(["confirmed", "completed", "scheduled", "checked_in", "no_show"]),
                },
            )
            if created and appointment.status == "checked_in":
                queue = Queue.objects.create(
                    patient=patient, appointment=appointment,
                    department=appointment.department, doctor=doctor,
                    priority=appointment.priority,
                )
                queue.queue_number = queue.generate_number()
                queue.save(update_fields=["queue_number"])

        # Consultations + vitals + diagnoses + prescriptions for some patients
        for i, patient in enumerate(patients[:8]):
            doctor = doctors[i % len(doctors)]
            consultation = Consultation.objects.create(
                patient=patient, doctor=doctor,
                chief_complaint=RANDOM.choice(["Fever for 3 days", "Persistent cough", "Headache", "Malaria symptoms", "High blood sugar"]),
                history_of_presenting_illness="Patient reports gradual onset of symptoms over the past few days.",
                symptoms=RANDOM.choice(["Fever, chills, malaise", "Cough, mild chest pain", "Nausea, dizziness"]),
                physical_examination="Vitals recorded. General condition fair.",
                clinical_notes="Plan: supportive care and medication.",
                treatment_plan="Rest, fluids, and prescribed medication. Review in 1 week.",
                status="completed",
                follow_up_date=date.today() + timedelta(days=7),
            )
            VitalSigns.objects.create(
                patient=patient, consultation=consultation,
                temperature=round(RANDOM.uniform(36.0, 39.5), 1),
                blood_pressure_systolic=RANDOM.randint(110, 160),
                blood_pressure_diastolic=RANDOM.randint(70, 100),
                pulse=RANDOM.randint(60, 100),
                respiratory_rate=RANDOM.randint(14, 22),
                oxygen_saturation=RANDOM.randint(94, 100),
                weight=round(RANDOM.uniform(45, 110), 1),
                height=round(RANDOM.uniform(150, 190), 1),
                pain_score=RANDOM.randint(0, 8),
                recorded_by=doctors[0],
            )
            Diagnosis.objects.create(
                consultation=consultation, patient=patient,
                icd_code=RANDOM.choice(["R50.9", "J11.1", "B54", "E11.9", "I10"]),
                name=RANDOM.choice(["Fever, unspecified", "Influenza", "Malaria", "Type 2 Diabetes", "Essential Hypertension"]),
                is_primary=True,
            )
            # Prescription
            medicines = list(Medicine.objects.all()[:5])
            if medicines:
                prescription = Prescription.objects.create(
                    patient=patient, doctor=doctor, consultation=consultation,
                    status=RANDOM.choice(["active", "dispensed", "active", "partially_dispensed"]),
                )
                for med in RANDOM.sample(medicines, min(2, len(medicines))):
                    item = PrescriptionItem.objects.create(
                        prescription=prescription, medicine=med,
                        dosage=med.strength, frequency="2 times daily",
                        duration="7 days", route="oral", quantity=14,
                        instructions="Take after meals.",
                    )
                    if prescription.status in ("dispensed", "partially_dispensed"):
                        qty = 14 if prescription.status == "dispensed" else 7
                        item.dispensed_quantity = qty
                        item.save(update_fields=["dispensed_quantity"])
                        self._deduct(med, qty, doctors[0])

        # Lab requests with results for a few patients
        tests = list(LabTestCatalog.objects.all())
        for i, patient in enumerate(patients[:6]):
            doctor = doctors[i % len(doctors)]
            lab_request = LabRequest.objects.create(
                patient=patient, doctor=doctor,
                priority="routine",
                status=RANDOM.choice(["completed", "processing", "requested"]),
            )
            for test in RANDOM.sample(tests, min(2, len(tests))):
                LabRequestItem.objects.create(lab_request=lab_request, test=test,
                                              status="completed" if lab_request.status == "completed" else "pending")

        # Radiology requests with reports for a couple of patients
        rad_doctor = staff_map.get("doctor", [])[-1] if staff_map.get("doctor") else None
        for i, patient in enumerate(patients[:3]):
            request = RadiologyRequest.objects.create(
                patient=patient, doctor=doctors[i % len(doctors)],
                procedure_type=RANDOM.choice(["xray", "ultrasound", "ct_scan"]),
                body_part=RANDOM.choice(["Chest", "Abdomen", "Right ankle"]),
                clinical_indication="Requested as part of diagnostic workup.",
                status="completed",
            )
            if rad_doctor:
                RadiologyReport.objects.create(
                    request=request, radiologist=rad_doctor,
                    findings="No significant abnormality detected.",
                    impression="Normal study.",
                    conclusion="No acute pathology.",
                )

        # Emergency visits
        for i, patient in enumerate(patients[:4]):
            EmergencyVisit.objects.create(
                patient=patient,
                priority=RANDOM.choice(["critical", "high", "medium", "low"]),
                chief_complaint=RANDOM.choice(["Chest pain", "Road traffic accident", "Severe abdominal pain", "Difficulty breathing"]),
                mode_of_arrival=RANDOM.choice(["ambulance", "walk_in", "ambulance"]),
                status=RANDOM.choice(["waiting", "in_treatment", "triage"]),
                triaged_by=doctors[0],
            )

        # Admissions
        beds = list(Bed.objects.all())
        for i, patient in enumerate(patients[:5]):
            if i >= len(beds):
                break
            bed = beds[i]
            ward = bed.room.ward
            admission = Admission.objects.create(
                patient=patient,
                doctor=doctors[i % len(doctors)],
                department=ward.department or by_name.get("Inpatient"),
                ward=ward, room=bed.room, bed=bed,
                admission_reason=RANDOM.choice(["Observation", "Surgical admission", "Severe dehydration"]),
                diagnosis=RANDOM.choice(["Pneumonia", "Appendicitis", "Hypertension crisis"]),
            )
            admission._sync_bed()
        self.stdout.write("Seeded clinical data.")

    def _deduct(self, medicine, quantity, user):
        remaining = quantity
        for batch in medicine.batches.order_by("expiry_date"):
            if remaining <= 0:
                break
            take = min(batch.quantity, remaining)
            batch.quantity -= take
            batch.save(update_fields=["quantity"])
            remaining -= take
            MedicineStockMovement.objects.create(
                medicine=medicine, batch=batch,
                movement_type=MedicineStockMovement.MOVEMENT_DISPENSE,
                quantity=-take, balance_after=medicine.total_stock,
                reference="seed", performed_by=user,
            )

    def _create_billing(self, patients, staff_map):
        accountant = (staff_map.get("accountant") or [None])[0]
        for i, patient in enumerate(patients[:10]):
            invoice, _ = Invoice.objects.get_or_create(
                patient=patient,
                defaults={"issued_by": accountant},
            )
            if not invoice.items.exists():
                InvoiceItem.objects.create(
                    invoice=invoice, description="General Consultation",
                    quantity=1, unit_price=25.00,
                )
                InvoiceItem.objects.create(
                    invoice=invoice, description="Complete Blood Count",
                    quantity=1, unit_price=25.00,
                )
                InvoiceItem.objects.create(
                    invoice=invoice, description="Paracetamol 500mg x14",
                    quantity=1, unit_price=3.00,
                )
                invoice.recalculate()
            if invoice.balance > 0 and i % 2 == 0:
                from decimal import Decimal

                pay_amount = invoice.total if i % 4 == 0 else invoice.total * Decimal("0.5")
                if pay_amount > 0:
                    payment = Payment.objects.create(
                        invoice=invoice, amount=round(pay_amount, 2),
                        method=RANDOM.choice(["cash", "card", "mobile_money"]),
                        received_by=accountant,
                    )
                    invoice.recalculate()
        self.stdout.write("Seeded billing data.")

    def _create_notifications(self, staff_map, patients):
        doctors = staff_map.get("doctor", [])
        for doctor in doctors[:3]:
            Notification.objects.get_or_create(
                recipient=doctor, type="appointment",
                title="New appointment",
                message=f"Patient {patients[0].full_name} has a new appointment.",
            )
        pharmacists = staff_map.get("pharmacist", [])
        for pharmacist in pharmacists:
            Notification.objects.get_or_create(
                recipient=pharmacist, type="low_stock",
                title="Low stock alert",
                message="Amlodipine and Salbutamol are at or below reorder level.",
            )
        self.stdout.write("Seeded notifications.")
