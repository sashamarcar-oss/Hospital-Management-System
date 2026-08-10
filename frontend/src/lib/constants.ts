export const ROLE_CODES = [
  "super_admin",
  "admin",
  "receptionist",
  "doctor",
  "nurse",
  "lab_technician",
  "pharmacist",
  "accountant",
  "hr",
  "patient",
] as const;

export type RoleCode = (typeof ROLE_CODES)[number];

export const ROLE_LABELS: Record<string, string> = {
  super_admin: "Super Admin",
  admin: "Hospital Administrator",
  receptionist: "Receptionist",
  doctor: "Doctor",
  nurse: "Nurse",
  lab_technician: "Laboratory Technician",
  pharmacist: "Pharmacist",
  accountant: "Accountant / Cashier",
  hr: "HR / Staff Manager",
  patient: "Patient",
};

export const GENDERS = ["male", "female", "other"] as const;
export const GENDER_LABELS: Record<string, string> = {
  male: "Male",
  female: "Female",
  other: "Other",
};

export const BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-", "unknown"] as const;

export const MARITAL_STATUSES = ["single", "married", "divorced", "widowed"] as const;
export const MARITAL_LABELS: Record<string, string> = {
  single: "Single",
  married: "Married",
  divorced: "Divorced",
  widowed: "Widowed",
};

export const APPOINTMENT_STATUSES = [
  "scheduled",
  "confirmed",
  "checked_in",
  "completed",
  "cancelled",
  "no_show",
] as const;

export const APPOINTMENT_STATUS_LABELS: Record<string, string> = {
  scheduled: "Scheduled",
  confirmed: "Confirmed",
  checked_in: "Checked In",
  completed: "Completed",
  cancelled: "Cancelled",
  no_show: "No-show",
};

export const APPOINTMENT_STATUS_VARIANTS: Record<string, "info" | "default" | "success" | "neutral" | "destructive" | "warning"> = {
  scheduled: "info",
  confirmed: "default",
  checked_in: "warning",
  completed: "success",
  cancelled: "destructive",
  no_show: "neutral",
};

export const PRIORITIES = ["routine", "urgent", "emergency", "high", "medium", "low", "stat"] as const;
export const PRIORITY_LABELS: Record<string, string> = {
  routine: "Routine",
  urgent: "Urgent",
  emergency: "Emergency",
  high: "High",
  medium: "Medium",
  low: "Low",
  stat: "STAT",
};
export const PRIORITY_VARIANTS: Record<string, "neutral" | "warning" | "danger" | "info" | "success"> = {
  routine: "neutral",
  urgent: "warning",
  emergency: "danger",
  high: "danger",
  medium: "warning",
  low: "info",
  stat: "danger",
};

export const QUEUE_STATUSES = ["waiting", "in_consultation", "completed", "cancelled", "skipped"] as const;
export const QUEUE_STATUS_LABELS: Record<string, string> = {
  waiting: "Waiting",
  in_consultation: "In Consultation",
  completed: "Completed",
  cancelled: "Cancelled",
  skipped: "Skipped",
};
export const QUEUE_STATUS_VARIANTS: Record<string, "neutral" | "warning" | "success" | "destructive"> = {
  waiting: "neutral",
  in_consultation: "warning",
  completed: "success",
  cancelled: "destructive",
  skipped: "destructive",
};

export const CONSULTATION_STATUSES = ["in_progress", "completed"] as const;
export const CONSULTATION_STATUS_LABELS: Record<string, string> = {
  in_progress: "In Progress",
  completed: "Completed",
};

export const PRESCRIPTION_STATUSES = ["active", "partially_dispensed", "dispensed", "completed", "cancelled"] as const;
export const PRESCRIPTION_STATUS_LABELS: Record<string, string> = {
  active: "Active",
  partially_dispensed: "Partially Dispensed",
  dispensed: "Dispensed",
  completed: "Completed",
  cancelled: "Cancelled",
};
export const PRESCRIPTION_STATUS_VARIANTS: Record<string, "info" | "warning" | "success" | "neutral" | "destructive"> = {
  active: "info",
  partially_dispensed: "warning",
  dispensed: "success",
  completed: "success",
  cancelled: "destructive",
};

export const LAB_CATEGORIES = ["hematology", "biochemistry", "microbiology", "urinalysis", "serology", "immunology", "pathology", "other"] as const;
export const LAB_CATEGORY_LABELS: Record<string, string> = {
  hematology: "Hematology",
  biochemistry: "Biochemistry",
  microbiology: "Microbiology",
  urinalysis: "Urinalysis",
  serology: "Serology",
  immunology: "Immunology",
  pathology: "Pathology",
  other: "Other",
};

export const LAB_REQUEST_STATUSES = ["requested", "sample_collected", "processing", "completed", "reviewed", "cancelled"] as const;
export const LAB_REQUEST_STATUS_LABELS: Record<string, string> = {
  requested: "Requested",
  sample_collected: "Sample Collected",
  processing: "Processing",
  completed: "Completed",
  reviewed: "Reviewed",
  cancelled: "Cancelled",
};
export const LAB_REQUEST_STATUS_VARIANTS: Record<string, "info" | "warning" | "success" | "destructive" | "neutral"> = {
  requested: "info",
  sample_collected: "neutral",
  processing: "warning",
  completed: "success",
  reviewed: "success",
  cancelled: "destructive",
};

export const RADIOLOGY_PROCEDURES = ["xray", "ultrasound", "ct_scan", "mri", "other"] as const;
export const RADIOLOGY_PROCEDURE_LABELS: Record<string, string> = {
  xray: "X-Ray",
  ultrasound: "Ultrasound",
  ct_scan: "CT Scan",
  mri: "MRI",
  other: "Other Imaging",
};

export const RADIOLOGY_STATUSES = ["requested", "queued", "in_progress", "completed", "reviewed", "cancelled"] as const;
export const RADIOLOGY_STATUS_LABELS: Record<string, string> = {
  requested: "Requested",
  queued: "Queued",
  in_progress: "In Progress",
  completed: "Completed",
  reviewed: "Reviewed",
  cancelled: "Cancelled",
};

export const WARD_TYPES = ["general", "private", "icu", "maternity", "pediatrics", "surgical", "emergency", "isolation"] as const;
export const WARD_TYPE_LABELS: Record<string, string> = {
  general: "General",
  private: "Private",
  icu: "ICU",
  maternity: "Maternity",
  pediatrics: "Pediatrics",
  surgical: "Surgical",
  emergency: "Emergency",
  isolation: "Isolation",
};

export const BED_STATUSES = ["available", "occupied", "reserved", "maintenance"] as const;
export const BED_STATUS_LABELS: Record<string, string> = {
  available: "Available",
  occupied: "Occupied",
  reserved: "Reserved",
  maintenance: "Maintenance",
};
export const BED_STATUS_VARIANTS: Record<string, "success" | "destructive" | "warning" | "neutral"> = {
  available: "success",
  occupied: "destructive",
  reserved: "warning",
  maintenance: "neutral",
};

export const ADMISSION_STATUSES = ["admitted", "transferred", "discharged"] as const;
export const ADMISSION_STATUS_LABELS: Record<string, string> = {
  admitted: "Admitted",
  transferred: "Transferred",
  discharged: "Discharged",
};
export const ADMISSION_STATUS_VARIANTS: Record<string, "default" | "warning" | "neutral"> = {
  admitted: "default",
  transferred: "warning",
  discharged: "neutral",
};

export const INVOICE_STATUSES = ["unpaid", "partially_paid", "paid", "overdue", "cancelled"] as const;
export const INVOICE_STATUS_LABELS: Record<string, string> = {
  unpaid: "Unpaid",
  partially_paid: "Partially Paid",
  paid: "Paid",
  overdue: "Overdue",
  cancelled: "Cancelled",
};
export const INVOICE_STATUS_VARIANTS: Record<string, "neutral" | "warning" | "success" | "danger" | "destructive"> = {
  unpaid: "neutral",
  partially_paid: "warning",
  paid: "success",
  overdue: "danger",
  cancelled: "destructive",
};

export const PAYMENT_METHODS = ["cash", "card", "bank", "mobile_money", "insurance"] as const;
export const PAYMENT_METHOD_LABELS: Record<string, string> = {
  cash: "Cash",
  card: "Card",
  bank: "Bank Transfer",
  mobile_money: "Mobile Money",
  insurance: "Insurance",
};

export const PAYMENT_STATUSES = ["pending", "completed", "failed", "refunded"] as const;
export const PAYMENT_STATUS_LABELS: Record<string, string> = {
  pending: "Pending",
  completed: "Completed",
  failed: "Failed",
  refunded: "Refunded",
};

export const CHARGE_CATEGORIES = ["consultation", "laboratory", "imaging", "medication", "procedure", "admission", "bed", "service"] as const;
export const CHARGE_CATEGORY_LABELS: Record<string, string> = {
  consultation: "Consultation",
  laboratory: "Laboratory",
  imaging: "Imaging",
  medication: "Medication",
  procedure: "Procedure",
  admission: "Admission",
  bed: "Bed",
  service: "Service",
};

export const CLAIM_STATUSES = ["draft", "submitted", "under_review", "approved", "partially_approved", "rejected", "paid"] as const;
export const CLAIM_STATUS_LABELS: Record<string, string> = {
  draft: "Draft",
  submitted: "Submitted",
  under_review: "Under Review",
  approved: "Approved",
  partially_approved: "Partially Approved",
  rejected: "Rejected",
  paid: "Paid",
};
export const CLAIM_STATUS_VARIANTS: Record<string, "neutral" | "info" | "warning" | "success" | "destructive"> = {
  draft: "neutral",
  submitted: "info",
  under_review: "warning",
  approved: "success",
  partially_approved: "warning",
  rejected: "destructive",
  paid: "success",
};

export const POLICY_STATUSES = ["active", "expired", "suspended", "cancelled"] as const;
export const POLICY_STATUS_LABELS: Record<string, string> = {
  active: "Active",
  expired: "Expired",
  suspended: "Suspended",
  cancelled: "Cancelled",
};

export const COVERAGE_TYPES = ["outpatient", "inpatient", "both"] as const;
export const COVERAGE_TYPE_LABELS: Record<string, string> = {
  outpatient: "Outpatient",
  inpatient: "Inpatient",
  both: "Both",
};

export const INVENTORY_CATEGORIES = ["medical_supplies", "consumables", "equipment", "ppe", "stationery", "other"] as const;
export const INVENTORY_CATEGORY_LABELS: Record<string, string> = {
  medical_supplies: "Medical Supplies",
  consumables: "Consumables",
  equipment: "Equipment",
  ppe: "PPE",
  stationery: "Stationery",
  other: "Other",
};

export const PO_STATUSES = ["draft", "ordered", "partially_received", "received", "cancelled"] as const;
export const PO_STATUS_LABELS: Record<string, string> = {
  draft: "Draft",
  ordered: "Ordered",
  partially_received: "Partially Received",
  received: "Received",
  cancelled: "Cancelled",
};

export const STAFF_STATUSES = ["active", "on_leave", "terminated", "inactive"] as const;
export const STAFF_STATUS_LABELS: Record<string, string> = {
  active: "Active",
  on_leave: "On Leave",
  terminated: "Terminated",
  inactive: "Inactive",
};
export const STAFF_STATUS_VARIANTS: Record<string, "success" | "warning" | "destructive" | "neutral"> = {
  active: "success",
  on_leave: "warning",
  terminated: "destructive",
  inactive: "neutral",
};

export const LEAVE_TYPES = ["annual", "sick", "unpaid", "maternity", "paternity", "other"] as const;
export const LEAVE_TYPE_LABELS: Record<string, string> = {
  annual: "Annual",
  sick: "Sick",
  unpaid: "Unpaid",
  maternity: "Maternity",
  paternity: "Paternity",
  other: "Other",
};

export const LEAVE_STATUSES = ["pending", "approved", "rejected"] as const;
export const LEAVE_STATUS_LABELS: Record<string, string> = {
  pending: "Pending",
  approved: "Approved",
  rejected: "Rejected",
};

export const ATTENDANCE_STATUSES = ["present", "absent", "late", "leave"] as const;
export const ATTENDANCE_STATUS_LABELS: Record<string, string> = {
  present: "Present",
  absent: "Absent",
  late: "Late",
  leave: "On Leave",
};

export const EMERGENCY_PRIORITIES = ["critical", "high", "medium", "low"] as const;
export const EMERGENCY_PRIORITY_LABELS: Record<string, string> = {
  critical: "Critical",
  high: "High",
  medium: "Medium",
  low: "Low",
};
export const EMERGENCY_PRIORITY_VARIANTS: Record<string, "danger" | "warning" | "neutral" | "info"> = {
  critical: "danger",
  high: "warning",
  medium: "neutral",
  low: "info",
};

export const EMERGENCY_STATUSES = ["triage", "waiting", "in_treatment", "admitted", "referred", "discharged"] as const;
export const EMERGENCY_STATUS_LABELS: Record<string, string> = {
  triage: "Triage",
  waiting: "Waiting",
  in_treatment: "In Treatment",
  admitted: "Admitted",
  referred: "Referred",
  discharged: "Discharged",
};

export const ARRIVAL_MODES = ["ambulance", "walk_in", "referred", "police", "other"] as const;
export const ARRIVAL_MODE_LABELS: Record<string, string> = {
  ambulance: "Ambulance",
  walk_in: "Walk-in",
  referred: "Referred",
  police: "Police",
  other: "Other",
};

export const DOCUMENT_CATEGORIES = ["medical_report", "lab_report", "imaging_report", "insurance", "identification", "discharge_summary", "referral", "other"] as const;
export const DOCUMENT_CATEGORY_LABELS: Record<string, string> = {
  medical_report: "Medical Report",
  lab_report: "Lab Report",
  imaging_report: "Imaging Report",
  insurance: "Insurance",
  identification: "Identification",
  discharge_summary: "Discharge Summary",
  referral: "Referral",
  other: "Other",
};

export const NOTIFICATION_TYPES = ["appointment", "lab_result", "prescription", "low_stock", "payment", "admission", "discharge", "balance", "general"] as const;
export const NOTIFICATION_TYPE_LABELS: Record<string, string> = {
  appointment: "Appointment",
  lab_result: "Lab Result",
  prescription: "Prescription",
  low_stock: "Low Stock",
  payment: "Payment",
  admission: "Admission",
  discharge: "Discharge",
  balance: "Outstanding Balance",
  general: "General",
};

export const MOVEMENT_TYPES = ["receive", "adjustment", "issue", "transfer", "expire", "dispense", "return"] as const;
export const MOVEMENT_TYPE_LABELS: Record<string, string> = {
  receive: "Received",
  adjustment: "Adjustment",
  issue: "Issued",
  transfer: "Transferred",
  expire: "Expired",
  dispense: "Dispensed",
  return: "Returned",
};

export const AUDIT_ACTIONS = ["create", "update", "delete", "view", "login", "logout", "dispense", "payment", "permission_change", "upload", "download", "other"] as const;
export const AUDIT_ACTION_LABELS: Record<string, string> = {
  create: "Created",
  update: "Updated",
  delete: "Deleted",
  view: "Viewed",
  login: "Login",
  logout: "Logout",
  dispense: "Dispensed",
  payment: "Payment",
  permission_change: "Permission Change",
  upload: "Upload",
  download: "Download",
  other: "Other",
};
