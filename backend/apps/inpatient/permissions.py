"""Permission classes for the inpatient/nursing/ICU module.

Custom ``@action`` methods in this module enforce fine-grained permission
codes through ``require_permission`` inside the action body. The base
``HasPermission`` class, however, gates every POST on the viewset's
``write_code`` before the action body runs, which would block legitimate
actions for roles that hold the granular code but not the coarse one.

``InpatientActionPermission`` keeps the standard CRUD gating of
``HasPermission`` but lets custom actions through on view access alone so
the action-level ``require_permission`` checks become authoritative.
"""

from apps.accounts.permissions import HasPermission

CRUD_ACTIONS = {"create", "update", "partial_update", "destroy", "list", "retrieve"}


class InpatientActionPermission(HasPermission):
    """View-gate custom actions; delegate CRUD gating to HasPermission."""

    def has_permission(self, request, view):
        action = getattr(view, "action", None)
        if action and action not in CRUD_ACTIONS:
            user = request.user
            if not user or not user.is_authenticated:
                return False
            if user.is_superuser:
                return True
            code = getattr(view, "code", self.code)
            if code is None:
                return True
            return user.has_permission_code(code)
        return super().has_permission(request, view)
