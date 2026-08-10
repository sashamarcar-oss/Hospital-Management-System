from rest_framework.permissions import BasePermission, SAFE_METHODS


class HasPermission(BasePermission):
    """Grant access only if the user's role carries the given permission code."""

    code = None
    write_code = None

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        if self.code is None:
            return True
        target = self.write_code if (request.method not in SAFE_METHODS and self.write_code) else self.code
        return user.has_permission_code(target)


class HasRole(BasePermission):
    """Grant access only to users in one of the given role codes."""

    roles = []

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return user.in_roles(*self.roles)


class IsPatientAccountOwner(BasePermission):
    """Patients may only access their own records."""

    patient_field = "patient"

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.in_roles("super_admin", "admin", "doctor", "nurse", "receptionist",
                         "lab_technician", "pharmacist", "accountant"):
            return True
        if user.in_roles("patient") and not user.is_patient_account:
            return False
        patient = getattr(obj, self.patient_field, None)
        if patient is None:
            patient = getattr(obj, "patient", None)
        if patient is None:
            return True
        linked = getattr(user, "patient_account", None)
        return bool(linked and linked.id == patient.id)
