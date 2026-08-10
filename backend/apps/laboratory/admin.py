from django.contrib import admin

from apps.laboratory.models import LabRequest, LabRequestItem, LabResult, LabTestCatalog

admin.site.register(LabTestCatalog)
admin.site.register(LabRequest)
admin.site.register(LabRequestItem)
admin.site.register(LabResult)
