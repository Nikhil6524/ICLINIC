import { useState, useCallback } from "react";
import { voiceService } from "../services/voiceService";
import type { AxiosError } from "axios";

export type CallStatus = "idle" | "calling" | "connected" | "ended" | "error" | "verifying";

export function useVoiceCall() {
  const [callStatus, setCallStatus] = useState<CallStatus>("idle");
  const [callSid, setCallSid] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const initiateCall = useCallback(async (phoneNumber?: string, sessionId?: string) => {
    setError(null);
    setCallStatus("calling");

    try {
      const { data, status } = await voiceService.initiateCall({
        phone_number: phoneNumber || "",
        session_id: sessionId,
      });

      // Handle verification required (Twilio trial account)
      if (status === 202 || data.error === "verification_required") {
        setCallStatus("verifying");
        setError(
          data.message ||
          `Phone verification required. Check your phone for a call from Twilio and enter the code.`
        );
        return;
      }

      if (data.success) {
        setCallSid(data.call_sid || null);
        setCallStatus("connected");
      } else {
        setCallStatus("error");
        setError("Failed to initiate call");
      }
    } catch (err) {
      const axiosErr = err as AxiosError<{ error: string; message?: string }>;
      const message =
        axiosErr.response?.data?.message ||
        axiosErr.response?.data?.error ||
        "Failed to initiate call";
      setError(message);
      setCallStatus("error");
    }
  }, []);

  const resetCall = useCallback(() => {
    setCallStatus("idle");
    setCallSid(null);
    setError(null);
  }, []);

  return {
    callStatus,
    callSid,
    error,
    initiateCall,
    resetCall,
  };
}
