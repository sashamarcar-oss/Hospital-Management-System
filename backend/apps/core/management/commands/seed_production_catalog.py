"""Seed production-safe master catalog data.

Populates ONLY reference/configuration data:
  - Medicine categories and medicines
  - Laboratory test catalog
  - Hospital wards, rooms, and beds
  - Billing charge types

Does NOT create patients, staff, appointments, prescriptions, invoices,
payments, or any transactional/demo data.

Usage:  python manage.py seed_production_catalog
Safe to run repeatedly (idempotent).
"""

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.billing.models import ChargeType
from apps.inpatient.models import Bed, Room, Ward
from apps.laboratory.models import LabTestCatalog
from apps.pharmacy.models import Medicine, MedicineCategory


# ---------------------------------------------------------------------------
# Catalog data
# ---------------------------------------------------------------------------

MEDICINE_CATEGORIES = [
    "Analgesics",
    "Antibiotics",
    "Antidiabetics",
    "Antihypertensives",
    "Gastrointestinal",
    "Respiratory",
    "Antihistamines",
    "Insulins",
]

MEDICINES = [
    {
        "name": "Paracetamol",
        "generic_name": "paracetamol",
        "brand_name": "Panadol",
        "category_name": "Analgesics",
        "manufacturer": "GlaxoSmithKline",
        "unit": "tablet",
        "strength": "500mg",
        "reorder_level": 100,
        "purchase_price": Decimal("1.50"),
        "selling_price": Decimal("3.00"),
        "requires_prescription": False,
    },
    {
        "name": "Amoxicillin",
        "generic_name": "amoxicillin",
        "brand_name": "Amoxil",
        "category_name": "Antibiotics",
        "manufacturer": "Biochem Pharma",
        "unit": "capsule",
        "strength": "250mg",
        "reorder_level": 60,
        "purchase_price": Decimal("2.00"),
        "selling_price": Decimal("4.50"),
        "requires_prescription": True,
    },
    {
        "name": "Ibuprofen",
        "generic_name": "ibuprofen",
        "brand_name": "Brufen",
        "category_name": "Analgesics",
        "manufacturer": "Abbott",
        "unit": "tablet",
        "strength": "400mg",
        "reorder_level": 80,
        "purchase_price": Decimal("1.75"),
        "selling_price": Decimal("3.50"),
        "requires_prescription": False,
    },
    {
        "name": "Metformin",
        "generic_name": "metformin",
        "brand_name": "Glucophage",
        "category_name": "Antidiabetics",
        "manufacturer": "Merck",
        "unit": "tablet",
        "strength": "500mg",
        "reorder_level": 50,
        "purchase_price": Decimal("1.20"),
        "selling_price": Decimal("2.80"),
        "requires_prescription": True,
    },
    {
        "name": "Amlodipine",
        "generic_name": "amlodipine",
        "brand_name": "Norvasc",
        "category_name": "Antihypertensives",
        "manufacturer": "Pfizer",
        "unit": "tablet",
        "strength": "5mg",
        "reorder_level": 50,
        "purchase_price": Decimal("2.10"),
        "selling_price": Decimal("4.20"),
        "requires_prescription": True,
    },
    {
        "name": "Omeprazole",
        "generic_name": "omeprazole",
        "brand_name": "Losec",
        "category_name": "Gastrointestinal",
        "manufacturer": "AstraZeneca",
        "unit": "capsule",
        "strength": "20mg",
        "reorder_level": 40,
        "purchase_price": Decimal("2.40"),
        "selling_price": Decimal("5.00"),
        "requires_prescription": False,
    },
    {
        "name": "Azithromycin",
        "generic_name": "azithromycin",
        "brand_name": "Zithromax",
        "category_name": "Antibiotics",
        "manufacturer": "Pfizer",
        "unit": "tablet",
        "strength": "500mg",
        "reorder_level": 30,
        "purchase_price": Decimal("5.50"),
        "selling_price": Decimal("9.00"),
        "requires_prescription": True,
    },
    {
        "name": "Salbutamol",
        "generic_name": "salbutamol",
        "brand_name": "Ventolin",
        "category_name": "Respiratory",
        "manufacturer": "GlaxoSmithKline",
        "unit": "inhaler",
        "strength": "100mcg",
        "reorder_level": 15,
        "purchase_price": Decimal("8.00"),
        "selling_price": Decimal("14.00"),
        "requires_prescription": True,
    },
    {
        "name": "Cetirizine",
        "generic_name": "cetirizine",
        "brand_name": "Zyrtec",
        "category_name": "Antihistamines",
        "manufacturer": "UCB Pharma",
        "unit": "tablet",
        "strength": "10mg",
        "reorder_level": 60,
        "purchase_price": Decimal("0.80"),
        "selling_price": Decimal("1.80"),
        "requires_prescription": False,
    },
    {
        "name": "Insulin Glargine",
        "generic_name": "insulin glargine",
        "brand_name": "Lantus",
        "category_name": "Insulins",
        "manufacturer": "Sanofi",
        "unit": "vial",
        "strength": "100IU/ml",
        "reorder_level": 10,
        "purchase_price": Decimal("25.00"),
        "selling_price": Decimal("40.00"),
        "requires_prescription": True,
    },
]

LAB_TESTS = [
    {
        "name": "Complete Blood Count",
        "category": "hematology",
        "sample_type": "blood",
        "normal_range": "WBC 4-11 x10^9/L, Hb 12-17 g/dL, Plt 150-400 x10^9/L",
        "units": "various",
        "price": Decimal("25.00"),
        "description": "Full haemoglobin, white cell, and platelet count.",
    },
    {
        "name": "Blood Glucose (Fasting)",
        "category": "biochemistry",
        "sample_type": "blood",
        "normal_range": "70-110 mg/dL",
        "units": "mg/dL",
        "price": Decimal("12.00"),
        "description": "Fasting blood glucose level.",
    },
    {
        "name": "Urinalysis",
        "category": "urinalysis",
        "sample_type": "urine",
        "normal_range": "Clear, pale yellow, pH 4.5-8.0",
        "units": "",
        "price": Decimal("15.00"),
        "description": "Physical, chemical, and microscopic urine examination.",
    },
    {
        "name": "Lipid Panel",
        "category": "biochemistry",
        "sample_type": "blood",
        "normal_range": "Total Chol <200 mg/dL, LDL <130 mg/dL, HDL >40 mg/dL",
        "units": "mg/dL",
        "price": Decimal("35.00"),
        "description": "Total cholesterol, LDL, HDL, and triglycerides.",
    },
    {
        "name": "Liver Function Test",
        "category": "biochemistry",
        "sample_type": "blood",
        "normal_range": "ALT 7-56 U/L, AST 10-40 U/L, Bilirubin 0.1-1.2 mg/dL",
        "units": "U/L",
        "price": Decimal("30.00"),
        "description": "ALT, AST, ALP, bilirubin, total protein, albumin.",
    },
    {
        "name": "Malaria Smear",
        "category": "microbiology",
        "sample_type": "blood",
        "normal_range": "Negative",
        "units": "",
        "price": Decimal("10.00"),
        "description": "Thick and thin blood film for malaria parasites.",
    },
    {
        "name": "Typhoid (Widal)",
        "category": "serology",
        "sample_type": "blood",
        "normal_range": "Negative (titre <1:80)",
        "units": "titre",
        "price": Decimal("14.00"),
        "description": "Widal agglutination test for Salmonella typhi.",
    },
    {
        "name": "Thyroid Panel (TSH, T3, T4)",
        "category": "immunology",
        "sample_type": "blood",
        "normal_range": "TSH 0.4-4.0 mIU/L, T3 80-200 ng/dL, T4 5-12 ug/dL",
        "units": "various",
        "price": Decimal("45.00"),
        "description": "Thyroid stimulating hormone, free T3 and T4.",
    },
    {
        "name": "Creatinine",
        "category": "biochemistry",
        "sample_type": "blood",
        "normal_range": "0.6-1.2 mg/dL",
        "units": "mg/dL",
        "price": Decimal("15.00"),
        "description": "Serum creatinine for renal function assessment.",
    },
    {
        "name": "HIV Rapid Test",
        "category": "serology",
        "sample_type": "blood",
        "normal_range": "Non-reactive",
        "units": "",
        "price": Decimal("8.00"),
        "description": "Rapid HIV 1/2 antibody screening test.",
    },
    {
        "name": "Blood Group & Crossmatch",
        "category": "hematology",
        "sample_type": "blood",
        "normal_range": "ABO/Rh determined",
        "units": "",
        "price": Decimal("20.00"),
        "description": "ABO and Rh blood grouping.",
    },
    {
        "name": "Pregnancy Test (hCG)",
        "category": "immunology",
        "sample_type": "urine",
        "normal_range": "Negative",
        "units": "",
        "price": Decimal("8.00"),
        "description": "Urine qualitative hCG pregnancy test.",
    },
    {
        "name": "HbA1c (Glycated Haemoglobin)",
        "category": "biochemistry",
        "sample_type": "blood",
        "normal_range": "<5.7%",
        "units": "%",
        "price": Decimal("40.00"),
        "description": "Glycated haemoglobin for diabetes monitoring.",
    },
    {
        "name": "Urea",
        "category": "biochemistry",
        "sample_type": "blood",
        "normal_range": "7-20 mg/dL",
        "units": "mg/dL",
        "price": Decimal("12.00"),
        "description": "Blood urea nitrogen for renal function.",
    },
    {
        "name": "Electrolytes (Na, K, Cl)",
        "category": "biochemistry",
        "sample_type": "blood",
        "normal_range": "Na 135-145, K 3.5-5.0, Cl 96-106",
        "units": "mmol/L",
        "price": Decimal("18.00"),
        "description": "Serum sodium, potassium, and chloride.",
    },
    {
        "name": "Stool Analysis",
        "category": "microbiology",
        "sample_type": "stool",
        "normal_range": "No ova, cysts, or occult blood",
        "units": "",
        "price": Decimal("12.00"),
        "description": "Macroscopic, microscopic, and occult blood examination.",
    },
    {
        "name": "ESR (Erythrocyte Sedimentation Rate)",
        "category": "hematology",
        "sample_type": "blood",
        "normal_range": "0-20 mm/hr (male), 0-30 mm/hr (female)",
        "units": "mm/hr",
        "price": Decimal("10.00"),
        "description": "Erythrocyte sedimentation rate for inflammation.",
    },
    {
        "name": "CRP (C-Reactive Protein)",
        "category": "immunology",
        "sample_type": "blood",
        "normal_range": "<10 mg/L",
        "units": "mg/L",
        "price": Decimal("22.00"),
        "description": "C-reactive protein for acute inflammation.",
    },
    {
        "name": "Hepatitis B Surface Antigen (HBsAg)",
        "category": "serology",
        "sample_type": "blood",
        "normal_range": "Non-reactive",
        "units": "",
        "price": Decimal("15.00"),
        "description": "Screening test for hepatitis B infection.",
    },
    {
        "name": "Microscopy & Culture (Urine)",
        "category": "microbiology",
        "sample_type": "urine",
        "normal_range": "No growth",
        "units": "CFU/mL",
        "price": Decimal("20.00"),
        "description": "Urine microscopy, sensitivity, and culture.",
    },
]

WARD_SPECS = [
    {
        "name": "General Ward",
        "code": "GEN",
        "ward_type": "general",
        "rooms": [
            {"number": "GW-01", "type": "general", "beds": ["GW-01-B01", "GW-01-B02", "GW-01-B03", "GW-01-B04"]},
            {"number": "GW-02", "type": "general", "beds": ["GW-02-B01", "GW-02-B02", "GW-02-B03", "GW-02-B04"]},
            {"number": "GW-03", "type": "general", "beds": ["GW-03-B01", "GW-03-B02", "GW-03-B03", "GW-03-B04"]},
        ],
    },
    {
        "name": "Private Ward",
        "code": "PVT",
        "ward_type": "private",
        "rooms": [
            {"number": "PR-01", "type": "private", "beds": ["PR-01-B01"]},
            {"number": "PR-02", "type": "private", "beds": ["PR-02-B01"]},
            {"number": "PR-03", "type": "private", "beds": ["PR-03-B01"]},
        ],
    },
    {
        "name": "ICU",
        "code": "ICU",
        "ward_type": "icu",
        "rooms": [
            {"number": "ICU-01", "type": "icu", "beds": ["ICU-01-B01"]},
            {"number": "ICU-02", "type": "icu", "beds": ["ICU-02-B01"]},
            {"number": "ICU-03", "type": "icu", "beds": ["ICU-03-B01"]},
        ],
    },
    {
        "name": "Maternity Ward",
        "code": "MAT",
        "ward_type": "maternity",
        "rooms": [
            {"number": "MAT-01", "type": "maternity", "beds": ["MAT-01-B01", "MAT-01-B02"]},
            {"number": "MAT-02", "type": "maternity", "beds": ["MAT-02-B01", "MAT-02-B02"]},
        ],
    },
    {
        "name": "Pediatric Ward",
        "code": "PED",
        "ward_type": "pediatrics",
        "rooms": [
            {"number": "PED-01", "type": "pediatrics", "beds": ["PED-01-B01", "PED-01-B02"]},
            {"number": "PED-02", "type": "pediatrics", "beds": ["PED-02-B01", "PED-02-B02"]},
        ],
    },
    {
        "name": "Surgical Ward",
        "code": "SUR",
        "ward_type": "surgical",
        "rooms": [
            {"number": "SW-01", "type": "surgical", "beds": ["SW-01-B01", "SW-01-B02", "SW-01-B03", "SW-01-B04"]},
            {"number": "SW-02", "type": "surgical", "beds": ["SW-02-B01", "SW-02-B02", "SW-02-B03", "SW-02-B04"]},
        ],
    },
    {
        "name": "Emergency Observation",
        "code": "EMR",
        "ward_type": "emergency",
        "rooms": [
            {"number": "EO-01", "type": "emergency", "beds": ["EO-01-B01", "EO-01-B02"]},
            {"number": "EO-02", "type": "emergency", "beds": ["EO-02-B01", "EO-02-B02"]},
        ],
    },
]

CHARGE_TYPES = [
    {"name": "General Consultation", "code": "consultation", "category": "consultation", "default_price": Decimal("25.00")},
    {"name": "Specialist Consultation", "code": "specialist_consultation", "category": "consultation", "default_price": Decimal("50.00")},
    {"name": "Emergency Consultation", "code": "emergency_consultation", "category": "consultation", "default_price": Decimal("60.00")},
    {"name": "General Ward (per day)", "code": "general_bed", "category": "bed", "default_price": Decimal("40.00")},
    {"name": "Private Room (per day)", "code": "private_bed", "category": "bed", "default_price": Decimal("120.00")},
    {"name": "ICU (per day)", "code": "icu_bed", "category": "bed", "default_price": Decimal("300.00")},
    {"name": "X-Ray", "code": "xray", "category": "imaging", "default_price": Decimal("55.00")},
    {"name": "Ultrasound", "code": "ultrasound", "category": "imaging", "default_price": Decimal("65.00")},
    {"name": "CT Scan", "code": "ct_scan", "category": "imaging", "default_price": Decimal("250.00")},
    {"name": "MRI", "code": "mri", "category": "imaging", "default_price": Decimal("400.00")},
    {"name": "Small Procedure", "code": "small_procedure", "category": "procedure", "default_price": Decimal("75.00")},
    {"name": "Major Surgery", "code": "major_surgery", "category": "procedure", "default_price": Decimal("1500.00")},
    {"name": "Dressing", "code": "dressing", "category": "procedure", "default_price": Decimal("15.00")},
]


class Command(BaseCommand):
    help = "Seed production-safe master catalog data (idempotent)."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Seeding production catalog..."))

        with transaction.atomic():
            stats = {
                "med_categories": self._seed_medicine_categories(),
                "medicines": self._seed_medicines(),
                "lab_tests": self._seed_lab_tests(),
                "wards": self._seed_wards(),
                "rooms": self._seed_rooms(),
                "beds": self._seed_beds(),
                "charge_types": self._seed_charge_types(),
            }

        self.stdout.write(self.style.SUCCESS("\nProduction catalog seeding completed.\n"))
        self.stdout.write(f"  Medicine categories: {stats['med_categories']}")
        self.stdout.write(f"  Medicines:          {stats['medicines']}")
        self.stdout.write(f"  Lab tests:          {stats['lab_tests']}")
        self.stdout.write(f"  Wards:              {stats['wards']}")
        self.stdout.write(f"  Rooms:              {stats['rooms']}")
        self.stdout.write(f"  Beds:               {stats['beds']}")
        self.stdout.write(f"  Charge types:       {stats['charge_types']}")
        self.stdout.write(self.style.SUCCESS("\nRadiology procedures are defined as model choices (no catalog table)."))
        self.stdout.write(self.style.SUCCESS("Done."))

    # ------------------------------------------------------------------
    # Medicine categories
    # ------------------------------------------------------------------
    def _seed_medicine_categories(self):
        created = 0
        existing = 0
        for name in MEDICINE_CATEGORIES:
            _, is_new = MedicineCategory.objects.get_or_create(name=name)
            if is_new:
                created += 1
            else:
                existing += 1
        return f"{created} created, {existing} existing"

    # ------------------------------------------------------------------
    # Medicines
    # ------------------------------------------------------------------
    def _seed_medicines(self):
        created = 0
        existing = 0
        for med in MEDICINES:
            category_name = med.pop("category_name")
            category, _ = MedicineCategory.objects.get_or_create(name=category_name)
            _, is_new = Medicine.objects.update_or_create(
                generic_name=med["generic_name"],
                defaults={
                    "name": med["name"],
                    "brand_name": med["brand_name"],
                    "category": category,
                    "manufacturer": med["manufacturer"],
                    "unit": med["unit"],
                    "strength": med["strength"],
                    "reorder_level": med["reorder_level"],
                    "purchase_price": med["purchase_price"],
                    "selling_price": med["selling_price"],
                    "requires_prescription": med["requires_prescription"],
                    "is_active": True,
                },
            )
            if is_new:
                created += 1
            else:
                existing += 1
        return f"{created} created, {existing} existing"

    # ------------------------------------------------------------------
    # Lab tests
    # ------------------------------------------------------------------
    def _seed_lab_tests(self):
        created = 0
        existing = 0
        for test in LAB_TESTS:
            _, is_new = LabTestCatalog.objects.update_or_create(
                name=test["name"],
                defaults={
                    "category": test["category"],
                    "sample_type": test["sample_type"],
                    "normal_range": test["normal_range"],
                    "units": test["units"],
                    "price": test["price"],
                    "description": test["description"],
                    "is_active": True,
                },
            )
            if is_new:
                created += 1
            else:
                existing += 1
        return f"{created} created, {existing} existing"

    # ------------------------------------------------------------------
    # Wards
    # ------------------------------------------------------------------
    def _seed_wards(self):
        created = 0
        existing = 0
        for spec in WARD_SPECS:
            _, is_new = Ward.objects.update_or_create(
                name=spec["name"],
                defaults={
                    "code": spec["code"],
                    "ward_type": spec["ward_type"],
                    "is_active": True,
                },
            )
            if is_new:
                created += 1
            else:
                existing += 1
        return f"{created} created, {existing} existing"

    # ------------------------------------------------------------------
    # Rooms
    # ------------------------------------------------------------------
    def _seed_rooms(self):
        created = 0
        existing = 0
        for spec in WARD_SPECS:
            ward, _ = Ward.objects.get_or_create(
                name=spec["name"],
                defaults={"code": spec["code"], "ward_type": spec["ward_type"], "is_active": True},
            )
            for room_spec in spec["rooms"]:
                _, is_new = Room.objects.update_or_create(
                    ward=ward,
                    room_number=room_spec["number"],
                    defaults={"room_type": room_spec["type"]},
                )
                if is_new:
                    created += 1
                else:
                    existing += 1
        return f"{created} created, {existing} existing"

    # ------------------------------------------------------------------
    # Beds
    # ------------------------------------------------------------------
    def _seed_beds(self):
        created = 0
        existing = 0
        for spec in WARD_SPECS:
            ward, _ = Ward.objects.get_or_create(
                name=spec["name"],
                defaults={"code": spec["code"], "ward_type": spec["ward_type"], "is_active": True},
            )
            for room_spec in spec["rooms"]:
                room, _ = Room.objects.get_or_create(
                    ward=ward,
                    room_number=room_spec["number"],
                    defaults={"room_type": room_spec["type"]},
                )
                for bed_number in room_spec["beds"]:
                    _, is_new = Bed.objects.update_or_create(
                        room=room,
                        bed_number=bed_number,
                        defaults={"status": Bed.STATUS_AVAILABLE},
                    )
                    if is_new:
                        created += 1
                    else:
                        existing += 1
        return f"{created} created, {existing} existing"

    # ------------------------------------------------------------------
    # Billing charge types
    # ------------------------------------------------------------------
    def _seed_charge_types(self):
        created = 0
        existing = 0
        for ct in CHARGE_TYPES:
            _, is_new = ChargeType.objects.update_or_create(
                code=ct["code"],
                defaults={
                    "name": ct["name"],
                    "category": ct["category"],
                    "default_price": ct["default_price"],
                    "is_active": True,
                },
            )
            if is_new:
                created += 1
            else:
                existing += 1
        return f"{created} created, {existing} existing"
