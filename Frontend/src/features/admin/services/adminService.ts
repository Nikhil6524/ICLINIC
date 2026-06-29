import backendClient from "../../../lib/backendClient";

export interface BookedSlot {
  appointment_id: string;
  patient_id: string;
  start: string;
  end: string;
  status: string;
  patient_name: string | null;
}

export interface UnavailabilityBlock {
  start: string;
  end: string;
  reason: string | null;
}

export interface DoctorSchedule {
  doctor_id: string;
  doctor_name: string;
  specialization: string;
  working_start: string;
  working_end: string;
  booked_slots: BookedSlot[];
  unavailability: UnavailabilityBlock[];
}

export interface ScheduleResponse {
  date: string;
  doctors: DoctorSchedule[];
}

export interface DoctorItem {
  doctor_id: string;
  department_id: string;
  auth_user_id: string;
  full_name: string;
  specialization: string;
  email: string;
  phone: string | null;
  working_start_time: string;
  working_end_time: string;
  active: boolean;
  created_at: string;
}

export const adminService = {
  // Schedule
  getSchedule: (date: string) =>
    backendClient.get<ScheduleResponse>(`/appointments/admin/schedule?date=${date}`),

  // Appointments
  cancelAppointment: (appointmentId: string) =>
    backendClient.put(`/appointments/${appointmentId}/cancel`),

  rescheduleAppointment: (appointmentId: string, newStart: string) =>
    backendClient.put(`/appointments/${appointmentId}/reschedule`, { new_start_datetime: newStart }),

  bookAppointment: (data: {
    patient_id: string;
    doctor_id: string;
    appointment_type_id: string;
    start_datetime: string;
    booking_source: string;
  }) => backendClient.post("/appointments", data),

  bookByFrontDesk: (data: {
    first_name: string;
    last_name: string;
    phone: string;
    doctor_id: string;
    appointment_type_id: string;
    start_datetime: string;
  }) => backendClient.post("/appointments/frontdesk-book", data),

  // Doctors
  getDoctors: () => backendClient.get<DoctorItem[]>("/doctors"),

  addDoctor: (data: {
    department_id: string;
    auth_user_id: string;
    full_name: string;
    specialization: string;
    email: string;
    phone?: string;
    working_start_time: string;
    working_end_time: string;
  }) => backendClient.post("/doctors", data),

  // Doctor unavailability
  blockDoctorTime: (data: {
    doctor_id: string;
    start_datetime: string;
    end_datetime: string;
    reason?: string;
  }) => backendClient.post("/doctor-unavailability", data),

  // Departments
  getDepartments: () => backendClient.get("/departments"),

  // Patients & Appointment types
  getAppointmentTypes: () => backendClient.get("/appointment-types"),
};
