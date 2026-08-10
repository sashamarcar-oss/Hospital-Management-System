from django.contrib import admin

from apps.pharmacy.models import Medicine, MedicineBatch, MedicineCategory, MedicineStockMovement

admin.site.register(Medicine)
admin.site.register(MedicineBatch)
admin.site.register(MedicineCategory)
admin.site.register(MedicineStockMovement)
