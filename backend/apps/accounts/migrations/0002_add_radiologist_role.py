# Generated to preserve existing role records while allowing radiology staff.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="role",
            name="code",
            field=models.CharField(
                choices=[
                    ("super_admin", "Super Admin"),
                    ("admin", "Hospital Administrator"),
                    ("receptionist", "Receptionist"),
                    ("doctor", "Doctor"),
                    ("nurse", "Nurse"),
                    ("lab_technician", "Laboratory Technician"),
                    ("radiologist", "Radiologist / Radiology Technician"),
                    ("pharmacist", "Pharmacist"),
                    ("accountant", "Accountant / Cashier"),
                    ("hr", "HR / Staff Manager"),
                    ("patient", "Patient"),
                ],
                max_length=32,
                unique=True,
            ),
        ),
    ]
