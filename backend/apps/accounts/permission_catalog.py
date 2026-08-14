"""Central permission catalog.

Permission codes use the form <module>.<action>.
Roles reference these codes; the seed command materialises them in the DB.
"""

MODULES = [
    "dashboard",
    "patients",
    "appointments",
    "queue",
    "consultations",
    "vitals",
    "laboratory",
    "radiology",
    "pharmacy",
    "inventory",
    "admissions",
    "discharge",
    "emergency",
    "billing",
    "payments",
    "insurance",
    "staff",
    "shifts",
    "departments",
    "reports",
    "settings",
    "audit",
    "documents",
    "notifications",
]

ACTIONS = ["view", "create", "update", "delete"]

EXTRA_PERMISSIONS = {
    "laboratory": ["process", "enter_results", "review"],
    "pharmacy": ["dispense", "adjust_stock"],
    "billing": ["receive_payment", "refund", "cancel_invoice"],
    "insurance": ["manage_claims"],
    "staff": ["manage_leave", "manage_attendance"],
    "appointments": ["checkin", "reschedule", "cancel"],
    "settings": ["manage_permissions", "manage_users"],
    "reports": ["export", "view_financial", "view_operational"],
    "patients": ["print_summary"],
    "consultations": ["prescribe", "request_lab", "request_imaging", "refer"],
    "admissions": ["assign_bed", "transfer", "discharge"],
    "emergency": ["assign"],
    "documents": ["upload", "download"],
}


def build_catalog():
    """Return a dict {module: {action_code: display_name}} for every permission."""
    catalog = {}
    for module in MODULES:
        actions = {"view": "View", "create": "Create", "update": "Update", "delete": "Delete"}
        for action in EXTRA_PERMISSIONS.get(module, []):
            actions[action] = f"{action.replace('_', ' ').title()} {module.title()}"
        catalog[module] = {f"{module}.{action}": name for action, name in actions.items()}
    return catalog


def flat_permission_codes():
    catalog = build_catalog()
    codes = []
    for module_actions in catalog.values():
        codes.extend(module_actions.keys())
    return codes


# Role -> permission codes. super_admin implicitly has everything.
ROLE_PERMISSIONS = {
    "admin": [
        "dashboard.view", "patients.view", "patients.create", "patients.update",
        "patients.delete", "patients.print_summary", "appointments.view",
        "appointments.create", "appointments.update", "appointments.delete",
        "appointments.checkin", "appointments.reschedule", "appointments.cancel",
        "queue.view", "consultations.view", "vitals.view", "laboratory.view",
        "radiology.view", "pharmacy.view", "inventory.view", "inventory.create",
        "inventory.update", "inventory.delete", "admissions.view", "admissions.create",
        "admissions.update", "admissions.assign_bed", "admissions.transfer", "admissions.discharge",
        "emergency.view", "emergency.create", "emergency.update", "billing.view", "billing.cancel_invoice", "payments.view",
        "insurance.view", "insurance.manage_claims", "staff.view", "staff.create",
        "staff.update", "shifts.view", "shifts.create", "shifts.update", "shifts.delete",
        "departments.view", "departments.create", "departments.update",
        "reports.view", "reports.view_financial", "reports.view_operational",
        "reports.export", "audit.view", "documents.view", "documents.download",
        "settings.manage_users", "settings.manage_permissions",
        "notifications.view",
    ],
    "receptionist": [
        "dashboard.view", "patients.view", "patients.create", "patients.update",
        "patients.print_summary", "appointments.view", "appointments.create",
        "appointments.update", "appointments.checkin", "appointments.reschedule",
        "appointments.cancel", "queue.view", "queue.create", "queue.update",
        "departments.view", "vitals.view", "admissions.view", "emergency.view", "emergency.create",
        "billing.view", "payments.view", "payments.create", "payments.receive_payment", "shifts.view",
        "documents.view", "documents.download", "notifications.view",
    ],
    "doctor": [
        "dashboard.view", "patients.view", "patients.print_summary", "appointments.view",
        "shifts.view",
        "appointments.update", "queue.view", "consultations.view", "consultations.create",
        "consultations.update", "consultations.prescribe", "consultations.request_lab",
        "consultations.request_imaging", "consultations.refer", "vitals.view",
        "vitals.create", "laboratory.view", "laboratory.review", "radiology.view",
        "radiology.create", "radiology.update", "admissions.view", "admissions.create",
        "admissions.discharge", "emergency.view", "emergency.create", "emergency.update", "documents.view",
        "documents.download", "reports.view", "notifications.view",
    ],
    "nurse": [
        "dashboard.view", "patients.view", "appointments.view", "vitals.view", "vitals.create",
        "shifts.view",
        "vitals.update", "queue.view", "admissions.view", "admissions.update",
        "admissions.assign_bed", "emergency.view", "emergency.update", "consultations.view",
        "laboratory.view", "pharmacy.view", "documents.view", "documents.download", "notifications.view",
    ],
    "lab_technician": [
        "dashboard.view", "patients.view", "appointments.view", "queue.view", "consultations.view", "vitals.view",
        "laboratory.view", "laboratory.create",
        "shifts.view",
        "laboratory.update", "laboratory.process", "laboratory.enter_results",
        "laboratory.review", "documents.view", "documents.download", "notifications.view",
    ],
    "pharmacist": [
        "dashboard.view", "patients.view", "consultations.view", "admissions.view", "pharmacy.view", "pharmacy.create",
        "shifts.view",
        "pharmacy.update", "pharmacy.delete", "pharmacy.dispense",
        "pharmacy.adjust_stock", "inventory.view", "inventory.update",
        "inventory.create", "documents.view", "documents.download", "notifications.view",
    ],
    "radiologist": [
        "dashboard.view", "patients.view", "appointments.view", "queue.view", "consultations.view",
        "radiology.view", "radiology.create", "radiology.update", "shifts.view",
        "documents.view", "documents.download", "notifications.view",
    ],
    "accountant": [
        "dashboard.view", "patients.view", "billing.view", "billing.create", "shifts.view",
        "billing.update", "billing.cancel_invoice", "payments.view",
        "payments.create", "payments.receive_payment", "payments.refund",
        "insurance.view", "insurance.create", "insurance.manage_claims",
        "reports.view", "reports.view_financial", "reports.export", "documents.view",
        "documents.download", "notifications.view",
    ],
    "hr": [
        "dashboard.view", "staff.view", "staff.create", "staff.update",
        "staff.delete", "staff.manage_leave", "staff.manage_attendance", "shifts.view",
        "shifts.create", "shifts.update", "shifts.delete",
        "departments.view", "departments.update", "settings.manage_permissions",
        "reports.view", "reports.view_operational", "documents.view", "documents.upload",
        "documents.download", "notifications.view",
    ],
    "patient": [
        "appointments.view", "appointments.create", "appointments.reschedule",
        "appointments.cancel", "consultations.view", "vitals.view", "laboratory.view",
        "pharmacy.view", "billing.view", "payments.view", "documents.view",
        "documents.download", "notifications.view",
    ],
}


def permissions_for_role(role_code):
    if role_code in ("super_admin", "admin"):
        return flat_permission_codes()
    return ROLE_PERMISSIONS.get(role_code, [])
