import { useNavigate, useSearchParams } from "react-router-dom";
import { AppointmentBookingForm } from "@/features/appointments/appointment-booking-form";
import { PageHeader } from "@/components/common/page-header";
import { Card, CardContent } from "@/components/ui/card";

export function AppointmentBookingPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const patientId = searchParams.get("patient") ? Number(searchParams.get("patient")) : undefined;

  return (
    <div className="space-y-6">
      <PageHeader title="Book appointment" description="Schedule a new appointment for a patient." />
      <div className="mx-auto max-w-3xl">
        <Card>
          <CardContent className="pt-6">
            <AppointmentBookingForm
              initialPatientId={patientId}
              onSuccess={() => navigate("/appointments")}
              onCancel={() => navigate("/appointments")}
            />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
