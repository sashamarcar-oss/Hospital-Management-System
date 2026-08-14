export interface Paginated<T> {
  count: number;
  page: number;
  page_size: number;
  total_pages: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface UserBrief {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  phone: string;
  role_code: string | null;
  role_name: string;
  profile_photo: string | null;
  is_active: boolean;
  is_patient_account: boolean;
}

export interface User extends UserBrief {
  role: number | null;
  permission_codes: string[];
  dashboard_path: string;
  department: number | null;
  password?: string;
  date_joined: string;
}

export interface Permission {
  id: number;
  code: string;
  name: string;
  module: string;
}

export interface Role {
  id: number;
  code: string;
  name: string;
  description: string;
  permissions: Permission[];
  permission_codes: string[];
  dashboard_path: string;
}

export interface Department {
  id: number;
  name: string;
  code: string;
  description: string;
  is_active: boolean;
  member_count: number;
  staff_count: number;
  created_at: string;
}

export interface Patient {
  id: number;
  patient_number: string;
  user: number | null;
  first_name: string;
  middle_name: string;
  last_name: string;
  full_name: string;
  date_of_birth: string;
  age: number;
  gender: string;
  national_id: string;
  phone: string;
  email: string;
  address: string;
  occupation: string;
  marital_status: string;
  blood_group: string;
  allergies: string;
  insurance_provider: string;
  insurance_number: string;
  next_of_kin_name: string;
  next_of_kin_phone: string;
  next_of_kin_relationship: string;
  profile_photo: string | null;
  is_active: boolean;
  emergency_contacts: EmergencyContact[];
  created_at: string;
}

export interface EmergencyContact {
  id?: number;
  name: string;
  phone: string;
  relationship: string;
  address: string;
}

export interface PatientSummary {
  id: number;
  patient_number: string;
  first_name: string;
  middle_name: string;
  last_name: string;
  full_name: string;
  date_of_birth: string;
  age: number;
  gender: string;
  phone: string;
  email: string;
  blood_group: string;
  allergies: string;
  insurance_provider: string;
  insurance_number: string;
}

export interface Appointment {
  id: number;
  patient: number;
  patient_details: PatientSummary;
  doctor: number | null;
  doctor_details: UserBrief | null;
  department: number | null;
  department_name: string;
  appointment_date: string;
  start_time: string;
  end_time: string;
  reason: string;
  priority: string;
  status: string;
  notes: string;
  display_time: string;
  queue_entry: { id: number; queue_number: string; status: string } | null;
  created_at: string;
}

export interface QueueEntry {
  id: number;
  patient: number;
  patient_details: PatientSummary;
  appointment: number | null;
  department: number;
  department_name: string;
  doctor: number | null;
  doctor_name: string;
  queue_number: string;
  status: string;
  priority: string;
  checked_in_at: string;
  called_at: string | null;
  completed_at: string | null;
  waiting_minutes: number | null;
}

export interface Consultation {
  id: number;
  patient: number;
  patient_details: PatientSummary;
  doctor: number;
  doctor_details: UserBrief;
  appointment: number | null;
  chief_complaint: string;
  history_of_presenting_illness: string;
  symptoms: string;
  physical_examination: string;
  clinical_notes: string;
  treatment_plan: string;
  procedures: string;
  follow_up_date: string | null;
  status: string;
  recorded_at: string;
  diagnoses: Diagnosis[];
  vital_signs: VitalSigns[];
  prescriptions: Prescription[];
}

export interface Diagnosis {
  id: number;
  consultation: number;
  icd_code: string;
  name: string;
  description: string;
  is_primary: boolean;
}

export interface VitalSigns {
  id: number;
  patient: number;
  consultation: number | null;
  temperature: string | null;
  blood_pressure_systolic: number | null;
  blood_pressure_diastolic: number | null;
  pulse: number | null;
  respiratory_rate: number | null;
  oxygen_saturation: number | null;
  weight: string | null;
  height: string | null;
  bmi: string | null;
  pain_score: number | null;
  notes: string;
  recorded_by: number | null;
  recorded_by_name: string;
  recorded_at: string;
}

export interface PrescriptionItem {
  id: number;
  prescription: number;
  medicine: number;
  medicine_name: string;
  dosage: string;
  frequency: string;
  duration: string;
  route: string;
  quantity: number;
  instructions: string;
  dispensed_quantity: number;
}

export interface Prescription {
  id: number;
  patient: number;
  patient_details: PatientSummary;
  doctor: number;
  doctor_details: UserBrief;
  consultation: number | null;
  status: string;
  notes: string;
  dispensed_by: number | null;
  dispensed_at: string | null;
  items: PrescriptionItem[];
  item_count: number;
  created_at: string;
}

export interface Referral {
  id: number;
  patient: number;
  patient_details: PatientSummary;
  from_doctor: number;
  from_doctor_name: string;
  to_doctor: number | null;
  to_doctor_name: string;
  to_department: number | null;
  department_name: string;
  reason: string;
  notes: string;
  status: string;
  created_at: string;
}

export interface LabTestCatalog {
  id: number;
  name: string;
  category: string;
  price: string;
  sample_type: string;
  normal_range: string;
  units: string;
  description: string;
  is_active: boolean;
}

export interface LabResult {
  id: number;
  request_item: number;
  test_name: string;
  test_category: string;
  sample_type: string;
  result: string;
  units: string;
  reference_range: string;
  comments: string;
  technician: number | null;
  technician_name: string;
  report_file: string | null;
  is_abnormal: boolean;
  completed_at: string;
}

export interface LabRequestItem {
  id: number;
  test: number;
  test_name: string;
  normal_range: string;
  units: string;
  price: string;
  status: string;
  result: LabResult | null;
}

export interface LabRequest {
  id: number;
  patient: number;
  patient_details: PatientSummary;
  doctor: number;
  doctor_details: UserBrief;
  consultation: number | null;
  priority: string;
  status: string;
  clinical_notes: string;
  requested_at: string;
  completed_at: string | null;
  items: LabRequestItem[];
  test_ids?: number[];
  test_count: number;
  total_price: string;
}

export interface RadiologyReport {
  id: number;
  request: number;
  findings: string;
  impression: string;
  conclusion: string;
  radiologist: number | null;
  radiologist_name: string;
  report_file: string | null;
  completed_at: string;
}

export interface RadiologyRequest {
  id: number;
  patient: number;
  patient_details: PatientSummary;
  doctor: number;
  doctor_details: UserBrief;
  consultation: number | null;
  procedure_type: string;
  body_part: string;
  clinical_indication: string;
  priority: string;
  status: string;
  requested_at: string;
  completed_at: string | null;
  report: RadiologyReport | null;
}

export interface MedicineCategory {
  id: number;
  name: string;
}

export interface MedicineBatch {
  id: number;
  medicine: number;
  batch_number: string;
  quantity: number;
  purchase_price: string;
  expiry_date: string | null;
  supplier: string;
  received_at: string;
}

export interface Medicine {
  id: number;
  name: string;
  generic_name: string;
  brand_name: string;
  category: number | null;
  category_name: string;
  manufacturer: string;
  unit: string;
  strength: string;
  reorder_level: number;
  purchase_price: string;
  selling_price: string;
  requires_prescription: boolean;
  is_active: boolean;
  total_stock: number;
  is_low_stock: boolean;
  earliest_expiry: string | null;
  batches: MedicineBatch[];
  created_at: string;
}

export interface MedicineStockMovement {
  id: number;
  medicine: number;
  medicine_name: string;
  batch: number | null;
  batch_number: string;
  movement_type: string;
  quantity: number;
  balance_after: number;
  reference: string;
  notes: string;
  performed_by: number | null;
  performed_by_name: string;
  created_at: string;
}

export interface Ward {
  id: number;
  name: string;
  code: string;
  ward_type: string;
  department: number | null;
  department_name: string;
  is_active: boolean;
  bed_count: number;
  available_beds: number;
}

export interface Room {
  id: number;
  ward: number;
  ward_name: string;
  room_number: string;
  room_type: string;
}

export interface Bed {
  id: number;
  room: number;
  room_name: string;
  ward_name: string;
  bed_number: string;
  status: string;
  current_patient: PatientSummary | null;
}

export interface Admission {
  id: number;
  patient: number;
  patient_details: PatientSummary;
  doctor: number | null;
  doctor_details: UserBrief | null;
  department: number | null;
  department_name: string;
  ward: number | null;
  ward_name: string;
  room: number | null;
  room_name: string;
  bed: number | null;
  bed_name: string;
  admission_date: string;
  admission_reason: string;
  diagnosis: string;
  notes: string;
  status: string;
  discharged_at: string | null;
}

export interface NursingNote {
  id: number;
  admission: number;
  nurse: number | null;
  nurse_name: string;
  note: string;
  shift: string;
  recorded_at: string;
}

export interface Discharge {
  id: number;
  admission: number;
  admission_details: Admission;
  patient: number;
  patient_details: PatientSummary;
  discharge_date: string;
  discharge_type: string;
  diagnosis_summary: string;
  treatment_summary: string;
  medication: string;
  outstanding_bills: string;
  follow_up_instructions: string;
  follow_up_date: string | null;
  doctor_notes: string;
  discharged_by: number | null;
  discharged_by_name: string;
}

export interface ChargeType {
  id: number;
  name: string;
  code: string;
  category: string;
  default_price: string;
  is_active: boolean;
}

export interface InvoiceItem {
  id: number;
  invoice: number;
  description: string;
  quantity: number;
  unit_price: string;
  line_total: string;
  charge_type: number | null;
  consultation: number | null;
  lab_request: number | null;
  imaging_request: number | null;
  admission: number | null;
  prescription_item: number | null;
}

export interface Payment {
  id: number;
  invoice: number;
  amount: string;
  method: string;
  status: string;
  reference: string;
  receipt_number: string;
  received_by: number | null;
  received_by_name: string;
  paid_at: string;
  notes: string;
  insurance_provider: string; policy_number: string; member_name: string; authorization_number: string;
  insurance_amount: string; patient_copay: string; mpesa_phone: string; mpesa_transaction_code: string;
}

export interface Invoice {
  id: number;
  patient: number;
  patient_details: PatientSummary;
  invoice_number: string;
  status: string;
  subtotal: string;
  discount: string;
  tax_rate: string;
  tax: string;
  total: string;
  amount_paid: string;
  balance: string;
  insurance_covered_amount: string;
  patient_copay_amount: string;
  due_date: string | null;
  insurance_claim: number | null;
  notes: string;
  issued_by: number | null;
  issued_by_name: string;
  issued_at: string;
  items: InvoiceItem[];
  payments: Payment[];
}

export interface InsuranceProvider {
  id: number;
  name: string;
  code: string;
  phone: string;
  email: string;
  address: string;
  is_active: boolean;
}

export interface InsurancePolicy {
  id: number;
  patient: number;
  patient_details: PatientSummary;
  provider: number;
  provider_name: string;
  policy_number: string;
  membership_number: string;
  coverage_type: string;
  coverage_limit: string;
  start_date: string;
  end_date: string | null;
  status: string;
}

export interface InsuranceClaim {
  id: number;
  policy: number;
  policy_details: InsurancePolicy;
  patient: number;
  patient_details: PatientSummary;
  invoice: number | null;
  invoice_number: string;
  claim_number: string;
  amount: string;
  status: string;
  approved_amount: string | null;
  rejected_amount: string | null;
  patient_contribution: string | null;
  submitted_date: string | null;
  approval_date: string | null;
  notes: string;
  created_at: string;
}

export interface Supplier {
  id: number;
  name: string;
  contact_person: string;
  phone: string;
  email: string;
  address: string;
  is_active: boolean;
}

export interface InventoryItem {
  id: number;
  name: string;
  category: string;
  sku: string;
  unit: string;
  quantity: number;
  reorder_level: number;
  purchase_price: string;
  selling_price: string;
  supplier: number | null;
  supplier_name: string;
  location: string;
  expiry_date: string | null;
  is_active: boolean;
  is_low_stock: boolean;
}

export interface PurchaseOrderItem {
  id: number;
  purchase_order: number;
  item: number;
  item_name: string;
  quantity: number;
  unit_price: string;
  received_quantity: number;
  line_total: string;
}

export interface PurchaseOrder {
  id: number;
  po_number: string;
  supplier: number;
  supplier_name: string;
  status: string;
  order_date: string;
  expected_date: string | null;
  notes: string;
  items: PurchaseOrderItem[];
  total_cost: string;
}

export interface StockMovement {
  id: number;
  item: number;
  item_name: string;
  movement_type: string;
  quantity: number;
  balance_after: number;
  reference: string;
  notes: string;
  performed_by: number | null;
  performed_by_name: string;
  created_at: string;
}

export interface Staff {
  id: number;
  user: number;
  user_details: UserBrief;
  employee_id: string;
  job_title: string;
  license_number: string;
  qualifications: string;
  date_joined: string;
  employment_status: string;
  salary: string | null;
  address: string;
  department: number | null;
}

export interface Shift {
  id: number;
  name: string;
  start_time: string;
  end_time: string;
  description: string;
}

export interface NurseShift {
  id: number; nurse: number; nurse_details: UserBrief; department: number | null; department_name: string;
  shift_date: string; start_time: string; end_time: string; shift_type: string; location: string;
  notes: string; status: string; effective_status: string;
}

export interface Message { id: number; conversation: number; sender: number; sender_details: UserBrief; content: string; created_at: string; is_read: boolean; is_deleted: boolean; }
export interface Conversation { id: number; participants: number[]; participants_details: UserBrief[]; created_at: string; updated_at: string; last_message: Message | null; unread_count: number; }

export interface Attendance {
  id: number;
  staff: number;
  staff_name: string;
  employee_id: string;
  date: string;
  check_in: string | null;
  check_out: string | null;
  status: string;
  notes: string;
}

export interface LeaveRequest {
  id: number;
  staff: number;
  staff_name: string;
  leave_type: string;
  start_date: string;
  end_date: string;
  reason: string;
  status: string;
  approved_by: number | null;
  approved_at: string | null;
  created_at: string;
}

export interface EmergencyVisit {
  id: number;
  patient: number;
  patient_details: PatientSummary;
  arrival_time: string;
  mode_of_arrival: string;
  priority: string;
  chief_complaint: string;
  triage_notes: string;
  triage_score: number | null;
  vitals_summary: Record<string, unknown> | null;
  assigned_doctor: number | null;
  assigned_doctor_details: UserBrief | null;
  status: string;
  treatment_notes: string;
  referral_notes: string;
  triaged_by: number | null;
  triaged_by_name: string;
  completed_at: string | null;
  waiting_minutes: number | null;
}

export interface AuditLog {
  id: number;
  user: number | null;
  user_name: string;
  action: string;
  module: string;
  record: string;
  object_id: number | null;
  ip_address: string | null;
  user_agent: string;
  previous_value: unknown;
  new_value: unknown;
  description: string;
  created_at: string;
}

export interface Notification {
  id: number;
  type: string;
  title: string;
  message: string;
  link: string;
  related_module: string;
  related_object_id: number | null;
  priority: "low" | "normal" | "high" | "urgent";
  is_read: boolean;
  created_at: string;
}

export interface Document {
  id: number;
  patient: number | null;
  patient_name: string;
  title: string;
  category: string;
  description: string;
  file: string;
  file_url: string;
  content_type: string;
  size_bytes: number;
  uploaded_by: number | null;
  uploaded_by_name: string;
  created_at: string;
}

export interface KPIs {
  total_patients: number;
  today_appointments: number;
  pending_appointments: number;
  admitted_patients: number;
  available_beds: number;
  doctors: number;
  nurses: number;
  pending_lab_tests: number;
  pending_prescriptions: number;
  today_revenue: string;
  active_queue: number;
}

export interface DashboardCharts {
  patient_registrations: { date: string; value: number }[];
  revenue: { date: string; value: number }[];
  appointments_by_status: { status: string; count: number }[];
  department_performance: { department__name: string; count: number }[];
  patient_demographics: { gender: string; count: number }[];
  common_diagnoses: { name: string; count: number }[];
  lab_activity: { month: string; count: number }[];
}

export interface ActivityItem {
  id: string;
  kind: "activity" | "notification";
  user: string;
  action: string;
  module: string;
  record: string;
  description: string;
  title: string;
  is_read: boolean;
  priority: "low" | "normal" | "high" | "urgent";
  timestamp: string;
}

export interface ReportPatients {
  new_patients: number;
  returning_patients: number;
  registrations_30d: { date: string; count: number }[];
  demographics: { gender: string; count: number }[];
  visits_30d: { date: string; count: number }[];
}

export interface ReportMedical {
  common_diagnoses: { name: string; count: number }[];
  laboratory_activity: { status: string; count: number }[];
  admissions_by_status: { status: string; count: number }[];
  total_discharges: number;
  treatments: { icd_code: string; name: string; count: number }[];
}

export interface ReportFinancial {
  daily_revenue_30d: { date: string; total: number }[];
  monthly_revenue: { month: string; total: number }[];
  total_revenue: number;
  outstanding: { total_outstanding: number };
  payment_methods: { method: string; total: number; count: number }[];
  insurance_claims: { status: string; total: number; count: number }[];
}

export interface ReportInventory {
  current_stock: { name: string; stock: number; reorder_level: number }[];
  low_stock_count: number;
  low_stock: { name: string; stock: number }[];
  expired: { medicine: string; batch: string; quantity: number; expiry_date: string }[];
  recent_movements: { medicine: string; type: string; quantity: number; date: string }[];
}
