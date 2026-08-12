import type { LucideIcon } from "lucide-react";
import {
  LayoutDashboard,
  Users,
  CalendarDays,
  ListOrdered,
  Stethoscope,
  HeartPulse,
  FlaskConical,
  ScanLine,
  Pill,
  Boxes,
  BedDouble,
  Siren,
  Receipt,
  ShieldCheck,
  Package,
  UserRound,
  Building2,
  BarChart3,
  Bell,
  Settings,
  ScrollText,
  FileText,
  MessageSquare,
  CalendarClock,
} from "lucide-react";

export interface NavItem {
  label: string;
  to: string;
  icon: LucideIcon;
  permission?: string;
  anyPermission?: string[];
  end?: boolean;
}

export interface NavGroup {
  label: string;
  items: NavItem[];
}

export const NAV_GROUPS: NavGroup[] = [
  {
    label: "Overview",
    items: [{ label: "Dashboard", to: "/dashboard", icon: LayoutDashboard, permission: "dashboard.view", end: true }],
  },
  {
    label: "Clinical",
    items: [
      { label: "Queue", to: "/queue", icon: ListOrdered, permission: "queue.view" },
      { label: "Appointments", to: "/appointments", icon: CalendarDays, permission: "appointments.view" },
      { label: "Patients", to: "/patients", icon: Users, permission: "patients.view" },
      { label: "Consultations", to: "/consultations", icon: Stethoscope, permission: "consultations.view" },
      { label: "Vital Signs", to: "/vitals", icon: HeartPulse, permission: "vitals.view" },
    ],
  },
  {
    label: "Diagnostics",
    items: [
      { label: "Laboratory", to: "/laboratory", icon: FlaskConical, permission: "laboratory.view" },
      { label: "Radiology", to: "/radiology", icon: ScanLine, permission: "radiology.view" },
    ],
  },
  {
    label: "Pharmacy & Stock",
    items: [
      { label: "Pharmacy", to: "/pharmacy", icon: Pill, permission: "pharmacy.view" },
      { label: "Inventory", to: "/inventory", icon: Boxes, permission: "inventory.view" },
    ],
  },
  {
    label: "Inpatient",
    items: [
      { label: "Admissions", to: "/admissions", icon: BedDouble, permission: "admissions.view" },
      { label: "Emergency", to: "/emergency", icon: Siren, permission: "emergency.view" },
    ],
  },
  {
    label: "Finance",
    items: [
      { label: "Billing", to: "/billing", icon: Receipt, permission: "billing.view" },
      { label: "Insurance", to: "/insurance", icon: ShieldCheck, permission: "insurance.view" },
    ],
  },
  {
    label: "Administration",
    items: [
      { label: "Shift Management", to: "/shifts", icon: CalendarClock, anyPermission: ["staff.view", "dashboard.view"] },
      { label: "Messages", to: "/messages", icon: MessageSquare },
      { label: "Staff", to: "/staff", icon: UserRound, permission: "staff.view" },
      { label: "Departments", to: "/departments", icon: Building2, permission: "departments.view" },
      { label: "Reports", to: "/reports", icon: BarChart3, permission: "reports.view" },
      { label: "Documents", to: "/documents", icon: FileText, permission: "documents.view" },
      { label: "Notifications", to: "/notifications", icon: Bell, permission: "notifications.view" },
      {
        label: "Settings",
        to: "/settings",
        icon: Settings,
        anyPermission: ["settings.manage_users", "settings.manage_permissions", "audit.view"],
      },
      { label: "Audit Logs", to: "/settings/audit-logs", icon: ScrollText, permission: "audit.view" },
    ],
  },
];

export function getNavGroups(can: (code: string) => boolean, canAny: (codes: string[]) => boolean): NavGroup[] {
  return NAV_GROUPS.map((group) => ({
    ...group,
    items: group.items.filter(
      (item) =>
        (!item.permission || can(item.permission)) &&
        (!item.anyPermission || canAny(item.anyPermission))
    ),
  })).filter((group) => group.items.length > 0);
}
