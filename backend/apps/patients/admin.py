from django.contrib import admin

from apps.patients.models import EmergencyContact, Patient

admin.site.register(Patient)
admin.site.register(EmergencyContact)
