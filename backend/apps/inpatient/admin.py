from django.contrib import admin

from apps.inpatient.models import (
    Admission,
    Bed,
    BedAssignment,
    Discharge,
    FluidBalance,
    ICUMonitoringRecord,
    ICUMonitoringSheet,
    ICUThreshold,
    NurseAssignment,
    NursingHandover,
    NursingNote,
    NursingNoteAmendment,
    Room,
    Ward,
)

admin.site.register(Ward)
admin.site.register(Room)
admin.site.register(Bed)
admin.site.register(Admission)
admin.site.register(BedAssignment)
admin.site.register(NurseAssignment)
admin.site.register(Discharge)
admin.site.register(NursingNote)
admin.site.register(NursingNoteAmendment)
admin.site.register(NursingHandover)
admin.site.register(ICUThreshold)
admin.site.register(ICUMonitoringSheet)
admin.site.register(ICUMonitoringRecord)
admin.site.register(FluidBalance)
