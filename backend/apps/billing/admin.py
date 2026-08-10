from django.contrib import admin

from apps.billing.models import ChargeType, Invoice, InvoiceItem, Payment

admin.site.register(ChargeType)
admin.site.register(Invoice)
admin.site.register(InvoiceItem)
admin.site.register(Payment)
