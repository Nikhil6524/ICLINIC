import backendClient from "../../../lib/backendClient";

export interface CompleteProfilePayload {
  first_name: string;
  last_name: string;
  phone: string;
  dob?: string | null;
  gender?: string | null;
}

export interface UpdateProfilePayload {
  first_name?: string;
  last_name?: string;
  phone?: string;
  dob?: string | null;
  gender?: string | null;
}

export interface PatientResponse {
  patient_id: string;
  user_id: string | null;
  first_name: string;
  last_name: string;
  phone: string;
  email: string | null;
  dob: string | null;
  gender: string | null;
  created_at: string;
}

export const profileService = {
  completeProfile: (data: CompleteProfilePayload) =>
    backendClient.post<PatientResponse>("/patients/complete-profile", data),

  getMyProfile: () =>
    backendClient.get<PatientResponse>("/patients/me"),

  updateMyProfile: (data: UpdateProfilePayload) =>
    backendClient.put<PatientResponse>("/patients/me", data),
};
