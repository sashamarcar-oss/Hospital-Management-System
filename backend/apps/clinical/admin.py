from django.contrib import admin

from apps.clinical.models import (
    Consultation,
    Diagnosis,
    Prescription,
    PrescriptionItem,
    Referral,
    VitalSigns,
)

admin.site.register(Consultation)
admin.site.register(Diagnosis)
admin.site.register(VitalSigns)
admin.site.register(Prescription)
admin.site.register(PrescriptionItem)
admin.site.register(Referral)
