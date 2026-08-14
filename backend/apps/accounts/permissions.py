from rest_framework.permissions import BasePermission, SAFE_METHODS


class HasPermission(BasePermission):
    """Grant access only if the user's role carries the given permission code."""

    code = None
    write_code = None
    create_code = None

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        # Viewsets carry their policy so the same permission class can be
        # reused throughout the API.  Reading only ``self.code`` previously
        # made those view-level policies silently ineffective.
        code = getattr(view, "code", self.code)
        write_code = getattr(view, "write_code", self.write_code)
        create_code = getattr(view, "create_code", self.create_code)
        delete_code = getattr(view, "delete_code", None)
        if code is None:
            return True
        action = getattr(view, "action", None)
        module = code.split(".", 1)[0]
        if request.method == "POST" and action == "create":
            target = create_code or f"{module}.create"
        elif request.method == "DELETE" and action == "destroy":
            target = delete_code or f"{module}.delete"
        elif request.method not in SAFE_METHODS:
            target = write_code or f"{module}.update"
        else:
            target = code
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
                         "lab_technician", "radiologist", "pharmacist", "accountant", "hr"):
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
