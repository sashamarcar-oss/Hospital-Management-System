from django.core.management.base import BaseCommand

from apps.laboratory.models import LabTestCatalog


LAB_TESTS = [
    ("Complete Blood Count", "hematology", "blood", "WBC 4-11 x10^9/L, Hb 12-17 g/dL", "test", "25.00"),
    ("Blood Glucose", "biochemistry", "blood", "70-110 mg/dL", "mg/dL", "12.00"),
    ("Urinalysis", "urinalysis", "urine", "", "", "15.00"),
    ("Lipid Panel", "biochemistry", "blood", "Chol <200 mg/dL", "mg/dL", "35.00"),
    ("Liver Function Test", "biochemistry", "blood", "", "", "30.00"),
    ("Malaria Smear", "microbiology", "blood", "Negative", "", "10.00"),
    ("Typhoid (Widal)", "serology", "blood", "Negative", "", "14.00"),
    ("Thyroid Panel", "immunology", "blood", "", "", "45.00"),
    ("Creatinine", "biochemistry", "blood", "0.6-1.2 mg/dL", "mg/dL", "15.00"),
    ("HIV Rapid Test", "serology", "blood", "Negative", "", "8.00"),
]


class Command(BaseCommand):
    help = "Create any missing default laboratory tests without altering existing tests."

    def handle(self, *args, **options):
        created = 0
        for name, category, sample_type, normal_range, units, price in LAB_TESTS:
            _, was_created = LabTestCatalog.objects.get_or_create(
                name=name,
                defaults={
                    "category": category,
                    "sample_type": sample_type,
                    "normal_range": normal_range,
                    "units": units,
                    "price": price,
                    "is_active": True,
                },
            )
            created += was_created

        self.stdout.write(
            self.style.SUCCESS(
                f"Lab catalog ready: {LabTestCatalog.objects.count()} tests total ({created} created)."
            )
        )
