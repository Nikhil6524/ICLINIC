import { useVoiceCall, type CallStatus } from "../hooks/useVoiceCall";

interface CallButtonProps {
  /** Current chat session ID to continue the conversation on the call */
  sessionId?: string | null;
}

export function CallButton({ sessionId }: CallButtonProps) {
  const { callStatus, error, initiateCall, resetCall } = useVoiceCall();

  const handleCallClick = () => {
    // Call directly — the backend auto-fetches the user's phone from their patient profile
    initiateCall(undefined, sessionId || undefined);
  };

  return (
    <>
      <button
        className={`call-btn ${callStatus !== "idle" ? `call-btn--${callStatus}` : ""}`}
        onClick={callStatus === "idle" ? handleCallClick : resetCall}
        title={getTitle(callStatus)}
        disabled={callStatus === "calling"}
      >
        {callStatus === "idle" && <PhoneIcon />}
        {callStatus === "calling" && <SpinnerIcon />}
        {callStatus === "connected" && <PhoneConnectedIcon />}
        {callStatus === "error" && <PhoneIcon />}
        {callStatus === "ended" && <PhoneIcon />}
      </button>

      {/* Status text shown below the button when active */}
      {callStatus !== "idle" && (
        <span className={`call-status-text call-status-text--${callStatus}`}>
          {callStatus === "calling" && "Calling..."}
          {callStatus === "connected" && "Call in progress"}
          {callStatus === "error" && (error || "Call failed")}
          {callStatus === "ended" && "Call ended"}
        </span>
      )}
    </>
  );
}

function getTitle(status: CallStatus): string {
  switch (status) {
    case "idle":
      return "Call AI Assistant";
    case "calling":
      return "Ringing...";
    case "connected":
      return "Click to end status";
    case "error":
      return "Click to retry";
    case "ended":
      return "Call again";
    default:
      return "Call";
  }
}

function PhoneIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z" />
    </svg>
  );
}

function PhoneConnectedIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z" />
      <path d="M14.05 2a9 9 0 0 1 8 7.94" />
      <path d="M14.05 6A5 5 0 0 1 18 10" />
    </svg>
  );
}

function SpinnerIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="call-spinner">
      <path d="M21 12a9 9 0 1 1-6.219-8.56" />
    </svg>
  );
}
