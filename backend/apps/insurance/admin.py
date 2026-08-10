from django.contrib import admin

from apps.insurance.models import InsuranceClaim, InsurancePolicy, InsuranceProvider

admin.site.register(InsuranceProvider)
admin.site.register(InsurancePolicy)
admin.site.register(InsuranceClaim)
