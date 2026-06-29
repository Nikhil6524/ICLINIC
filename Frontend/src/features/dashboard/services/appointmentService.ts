import backendClient from "../../../lib/backendClient";

export interface AppointmentItem {
  appointment_id: string;
  patient_id: string;
  doctor_id: string;
  appointment_type_id: string;
  start_datetime: string;
  end_datetime: string;
  status: string;
  booking_source: string;
  created_at: string;
  doctor_name: string | null;
  doctor_specialization: string | null;
  appointment_type_name: string | null;
}

export interface MyAppointmentsResponse {
  active: AppointmentItem[];
  history: AppointmentItem[];
}

export const appointmentService = {
  getMyAppointments: () =>
    backendClient.get<MyAppointmentsResponse>("/appointments/me"),
};
