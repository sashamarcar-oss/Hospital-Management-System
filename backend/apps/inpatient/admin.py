from django.contrib import admin

from apps.inpatient.models import Admission, Bed, Discharge, NursingNote, Room, Ward

admin.site.register(Ward)
admin.site.register(Room)
admin.site.register(Bed)
admin.site.register(Admission)
admin.site.register(Discharge)
admin.site.register(NursingNote)
