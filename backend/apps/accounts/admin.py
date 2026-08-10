from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.accounts.models import Permission, Role, User


class UserAdmin(BaseUserAdmin):
    list_display = ["username", "email", "first_name", "last_name", "role_name", "is_active"]
    list_filter = ["role", "is_active"]
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Hospital Profile", {"fields": ("role", "phone", "department", "profile_photo", "is_patient_account")}),
    )


admin.site.register(User, UserAdmin)
admin.site.register(Role)
admin.site.register(Permission)
