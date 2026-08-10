from django.contrib import admin

from apps.radiology.models import RadiologyReport, RadiologyRequest

admin.site.register(RadiologyRequest)
admin.site.register(RadiologyReport)
