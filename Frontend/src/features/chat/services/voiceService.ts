import backendClient from "../../../lib/backendClient";

export interface InitiateCallPayload {
  phone_number: string;
  session_id?: string;
}

export interface InitiateCallResponse {
  success: boolean;
  call_sid: string;
  to: string;
}

export const voiceService = {
  initiateCall: (data: InitiateCallPayload) =>
    backendClient.post<InitiateCallResponse>("/voice/initiate", data),
};
