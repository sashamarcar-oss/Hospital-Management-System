import { Routes, Route, Navigate } from "react-router-dom";
import { ProtectedRoute, GuestRoute, RoleRoute } from "@/components/auth/guards";
import { AppLayout } from "@/components/layout/app-layout";
import { LoginPage } from "@/features/auth/login-page";
import { ForgotPasswordPage } from "@/features/auth/forgot-password-page";
import { ResetPasswordPage } from "@/features/auth/reset-password-page";
import { RegisterPage } from "@/features/auth/register-page";
import { ChangePasswordPage } from "@/features/auth/change-password-page";
import { ForbiddenPage, NotFoundPage } from "@/features/errors/error-pages";
import { DashboardPage } from "@/features/dashboard/dashboard-page";
import { PatientListPage } from "@/features/patients/patient-list-page";
import { PatientRegisterPage } from "@/features/patients/patient-register-page";
import { PatientProfilePage } from "@/features/patients/patient-profile-page";
import { AppointmentListPage } from "@/features/appointments/appointment-list-page";
import { AppointmentBookingPage } from "@/features/appointments/appointment-booking-page";
import { AppointmentCalendarPage } from "@/features/appointments/appointment-calendar-page";
import { QueuePage } from "@/features/queue/queue-page";
import { ConsultationListPage } from "@/features/consultations/consultation-list-page";
import { ConsultationDetailPage } from "@/features/consultations/consultation-detail-page";
import { ConsultationNewPage } from "@/features/consultations/consultation-new-page";
import { VitalsPage } from "@/features/vitals/vitals-page";
import { LaboratoryPage } from "@/features/laboratory/laboratory-page";
import { LaboratoryRequestsPage } from "@/features/laboratory/laboratory-requests-page";
import { LabResultsPage } from "@/features/laboratory/lab-results-page";
import { RadiologyPage } from "@/features/radiology/radiology-page";
import { PharmacyPage } from "@/features/pharmacy/pharmacy-page";
import { PharmacyDispensePage } from "@/features/pharmacy/pharmacy-dispense-page";
import { AdmissionsPage } from "@/features/admissions/admissions-page";
import { BedsPage } from "@/features/admissions/beds-page";
import { DischargePage } from "@/features/admissions/discharge-page";
import { BillingPage } from "@/features/billing/billing-page";
import { InvoiceDetailPage } from "@/features/billing/invoice-detail-page";
import { InsurancePage } from "@/features/insurance/insurance-page";
import { InventoryPage } from "@/features/inventory/inventory-page";
import { PurchaseOrdersPage } from "@/features/inventory/purchase-orders-page";
import { StaffPage } from "@/features/staff/staff-page";
import { StaffAttendancePage } from "@/features/staff/staff-attendance-page";
import { StaffLeavePage } from "@/features/staff/staff-leave-page";
import { DepartmentsPage } from "@/features/departments/departments-page";
import { EmergencyPage } from "@/features/emergency/emergency-page";
import { ReportsPage } from "@/features/reports/reports-page";
import { SettingsPage } from "@/features/settings/settings-page";
import { AuditLogsPage } from "@/features/settings/audit-logs-page";
import { NotificationsPage } from "@/features/notifications/notifications-page";
import { DocumentsPage } from "@/features/documents/documents-page";
import { PatientPortalPage } from "@/features/portal/patient-portal-page";
import { NurseShiftsPage } from "@/features/shifts/nurse-shifts-page";
import { ShiftManagementPage } from "@/features/shifts/shift-management-page";
import { MessagesPage } from "@/features/messages/messages-page";
import { useAuth } from "@/hooks/use-auth";

function ShiftsRoute() {
  const { can, canAny, hasRole } = useAuth();
  const canManage = hasRole("admin", "super_admin", "hr") || canAny(["shifts.create", "shifts.update", "shifts.delete"]);
  if (canManage) return <ShiftManagementPage />;
  return can("shifts.view") ? <Navigate to="/my-shifts" replace /> : <Navigate to="/403" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<GuestRoute><Navigate to="/login" replace /></GuestRoute>} />
      <Route path="/login" element={<GuestRoute><LoginPage /></GuestRoute>} />
      <Route path="/forgot-password" element={<GuestRoute><ForgotPasswordPage /></GuestRoute>} />
      <Route path="/reset-password" element={<GuestRoute><ResetPasswordPage /></GuestRoute>} />
      <Route path="/register" element={<GuestRoute><RegisterPage /></GuestRoute>} />
      <Route path="/403" element={<ForbiddenPage />} />
      <Route path="*" element={<NotFoundPage />} />

      <Route element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
        <Route path="/change-password" element={<ChangePasswordPage />} />
        <Route path="/dashboard" element={<RoleRoute permission="dashboard.view"><DashboardPage /></RoleRoute>} />
        <Route path="/patients" element={<RoleRoute permission="patients.view"><PatientListPage /></RoleRoute>} />
        <Route path="/patients/register" element={<RoleRoute permission="patients.create"><PatientRegisterPage /></RoleRoute>} />
        <Route path="/patients/:id" element={<RoleRoute permission="patients.view"><PatientProfilePage /></RoleRoute>} />
        <Route path="/appointments" element={<RoleRoute permission="appointments.view"><AppointmentListPage /></RoleRoute>} />
        <Route path="/appointments/new" element={<RoleRoute permission="appointments.create"><AppointmentBookingPage /></RoleRoute>} />
        <Route path="/appointments/calendar" element={<RoleRoute permission="appointments.view"><AppointmentCalendarPage /></RoleRoute>} />
        <Route path="/queue" element={<RoleRoute permission="queue.view"><QueuePage /></RoleRoute>} />
        <Route path="/consultations" element={<RoleRoute permission="consultations.view"><ConsultationListPage /></RoleRoute>} />
        <Route path="/consultations/new" element={<RoleRoute permission="consultations.create"><ConsultationNewPage /></RoleRoute>} />
        <Route path="/consultations/:id" element={<RoleRoute permission="consultations.view"><ConsultationDetailPage /></RoleRoute>} />
        <Route path="/vitals" element={<RoleRoute permission="vitals.view"><VitalsPage /></RoleRoute>} />
        <Route path="/laboratory" element={<RoleRoute permission="laboratory.view"><LaboratoryPage /></RoleRoute>} />
        <Route path="/laboratory/requests" element={<RoleRoute permission="laboratory.view"><LaboratoryRequestsPage /></RoleRoute>} />
        <Route path="/laboratory/results" element={<RoleRoute permission="laboratory.view"><LabResultsPage /></RoleRoute>} />
        <Route path="/radiology" element={<RoleRoute permission="radiology.view"><RadiologyPage /></RoleRoute>} />
        <Route path="/pharmacy" element={<RoleRoute permission="pharmacy.view"><PharmacyPage /></RoleRoute>} />
        <Route path="/pharmacy/dispense" element={<RoleRoute permission="pharmacy.dispense"><PharmacyDispensePage /></RoleRoute>} />
        <Route path="/admissions" element={<RoleRoute permission="admissions.view"><AdmissionsPage /></RoleRoute>} />
        <Route path="/admissions/beds" element={<RoleRoute permission="admissions.view"><BedsPage /></RoleRoute>} />
        <Route path="/admissions/discharges" element={<RoleRoute permission="discharge.view"><DischargePage /></RoleRoute>} />
        <Route path="/billing" element={<RoleRoute permission="billing.view"><BillingPage /></RoleRoute>} />
        <Route path="/billing/:id" element={<RoleRoute permission="billing.view"><InvoiceDetailPage /></RoleRoute>} />
        <Route path="/insurance" element={<RoleRoute permission="insurance.view"><InsurancePage /></RoleRoute>} />
        <Route path="/inventory" element={<RoleRoute permission="inventory.view"><InventoryPage /></RoleRoute>} />
        <Route path="/inventory/purchase-orders" element={<RoleRoute permission="inventory.view"><PurchaseOrdersPage /></RoleRoute>} />
        <Route path="/staff" element={<RoleRoute permission="staff.view"><StaffPage /></RoleRoute>} />
        <Route path="/staff/attendance" element={<RoleRoute permission="staff.view"><StaffAttendancePage /></RoleRoute>} />
        <Route path="/staff/leaves" element={<RoleRoute permission="staff.view"><StaffLeavePage /></RoleRoute>} />
        <Route path="/departments" element={<RoleRoute permission="departments.view"><DepartmentsPage /></RoleRoute>} />
        <Route path="/emergency" element={<RoleRoute permission="emergency.view"><EmergencyPage /></RoleRoute>} />
        <Route path="/reports" element={<RoleRoute permission="reports.view"><ReportsPage /></RoleRoute>} />
        <Route path="/settings" element={<RoleRoute anyPermission={["settings.manage_users", "settings.manage_permissions"]}><SettingsPage /></RoleRoute>} />
        <Route path="/settings/audit-logs" element={<RoleRoute permission="audit.view"><AuditLogsPage /></RoleRoute>} />
        <Route path="/notifications" element={<RoleRoute permission="notifications.view"><NotificationsPage /></RoleRoute>} />
        <Route path="/documents" element={<RoleRoute permission="documents.view"><DocumentsPage /></RoleRoute>} />
        <Route path="/portal" element={<RoleRoute permission="appointments.view"><PatientPortalPage /></RoleRoute>} />
        <Route path="/my-shifts" element={<RoleRoute permission="shifts.view"><NurseShiftsPage /></RoleRoute>} />
        <Route path="/shifts" element={<ShiftsRoute />} />
        <Route path="/messages" element={<MessagesPage />} />
      </Route>
    </Routes>
  );
}
