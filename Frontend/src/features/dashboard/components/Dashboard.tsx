import { useEffect, useState } from "react";
import { useAuth } from "../../auth/context/AuthContext";
import {
  profileService,
  type PatientResponse,
  type UpdateProfilePayload,
} from "../../profile/services/profileService";
import {
  appointmentService,
  type AppointmentItem,
} from "../services/appointmentService";
import { ChatWindow } from "../../chat/components/ChatWindow";
import { CallButton } from "../../chat/components/CallButton";
import { useWebSocketChat } from "../../../hooks/useWebSocketChat";
import "./Dashboard.css";

export function Dashboard() {
  const { user, logout } = useAuth();
  const [patient, setPatient] = useState<PatientResponse | null>(null);
  const [activeAppointments, setActiveAppointments] = useState<AppointmentItem[]>([]);
  const [historyAppointments, setHistoryAppointments] = useState<AppointmentItem[]>([]);

  // Settings panel state
  const [showSettings, setShowSettings] = useState(false);
  const [settingsTab, setSettingsTab] = useState<"profile" | "upcoming" | "history">("profile");
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);
  const [editFirst, setEditFirst] = useState("");
  const [editLast, setEditLast] = useState("");
  const [editPhone, setEditPhone] = useState("");
  const [editDob, setEditDob] = useState("");
  const [editGender, setEditGender] = useState("");

  // Chat
  const {
    messages,
    sendMessage,
    clearMessages,
    isConnected,
    isTyping,
    sessionId,
    reconnect,
  } = useWebSocketChat();

  useEffect(() => {
    profileService.getMyProfile().then((res) => setPatient(res.data)).catch(() => {});
    appointmentService.getMyAppointments().then((res) => {
      setActiveAppointments(res.data.active);
      setHistoryAppointments(res.data.history);
    }).catch(() => {});
  }, []);

  const firstName = patient?.first_name || user?.email?.split("@")[0] || "there";

  // Edit handlers
  const startEditing = () => {
    setEditFirst(patient?.first_name || "");
    setEditLast(patient?.last_name || "");
    setEditPhone(patient?.phone || "");
    setEditDob(patient?.dob || "");
    setEditGender(patient?.gender || "");
    setEditError(null);
    setEditing(true);
  };

  const cancelEditing = () => { setEditing(false); setEditError(null); };

  const saveProfile = async () => {
    setSaving(true);
    setEditError(null);
    try {
      const payload: UpdateProfilePayload = {};
      if (editFirst && editFirst !== patient?.first_name) payload.first_name = editFirst;
      if (editLast && editLast !== patient?.last_name) payload.last_name = editLast;
      if (editPhone && editPhone !== patient?.phone) payload.phone = editPhone;
      if (editDob !== (patient?.dob || "")) payload.dob = editDob || null;
      if (editGender !== (patient?.gender || "")) payload.gender = editGender || null;
      const res = await profileService.updateMyProfile(payload);
      setPatient(res.data);
      setEditing(false);
    } catch (err: any) {
      setEditError(err?.response?.data?.detail || "Failed to save changes");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="dashboard">
      {/* Header */}
      <header className="dashboard-header">
        <span className="dashboard-logo">iClinic</span>
        <div className="dashboard-header-right">
          <span className="dashboard-greeting-small">Hi, {firstName}</span>
          <button
            className="dashboard-settings-btn"
            onClick={() => setShowSettings(true)}
            title="Settings & Appointments"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="3" />
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
            </svg>
          </button>
          <button className="btn-logout" onClick={logout}>Sign Out</button>
        </div>
      </header>

      {/* Full-width Chat */}
      <div className="dashboard-chat">
        <div className="dashboard-chat-header">
          <div className="dashboard-chat-header-left">
            <div className="dashboard-chat-avatar">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 2a3 3 0 0 0-3 3v1a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
                <path d="M19 10H5a2 2 0 0 0-2 2v1a8 8 0 0 0 16 0v-1a2 2 0 0 0-2-2Z" />
                <path d="M12 18v4" />
              </svg>
            </div>
            <div>
              <h3 className="dashboard-chat-title">AI Assistant</h3>
              <span className={`dashboard-chat-status ${isConnected ? "online" : ""}`}>
                <span className="dashboard-chat-dot"></span>
                {isConnected ? "Online" : "Connecting..."}
              </span>
            </div>
          </div>
          <div className="dashboard-chat-actions">
            <CallButton sessionId={sessionId} />
            {!isConnected && (
              <button className="dashboard-chat-action-btn" onClick={reconnect} title="Reconnect">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 2v6h-6" /><path d="M3 12a9 9 0 0 1 15-6.7L21 8" />
                  <path d="M3 22v-6h6" /><path d="M21 12a9 9 0 0 1-15 6.7L3 16" />
                </svg>
              </button>
            )}
            <button className="dashboard-chat-action-btn" onClick={clearMessages} title="Clear chat">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M3 6h18" /><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
              </svg>
            </button>
          </div>
        </div>
        <div className="dashboard-chat-body">
          <ChatWindow messages={messages} isTyping={isTyping} isConnected={isConnected} onSendMessage={sendMessage} />
        </div>
      </div>

      {/* Settings Slide-over Panel */}
      {showSettings && (
        <>
          <div className="settings-backdrop" onClick={() => { setShowSettings(false); setEditing(false); }} />
          <div className="settings-panel">
            <div className="settings-panel-header">
              <h2>Settings</h2>
              <button className="settings-close-btn" onClick={() => { setShowSettings(false); setEditing(false); }}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M18 6L6 18" /><path d="M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Tabs */}
            <div className="settings-tabs">
              <button className={`settings-tab ${settingsTab === "profile" ? "active" : ""}`} onClick={() => setSettingsTab("profile")}>Profile</button>
              <button className={`settings-tab ${settingsTab === "upcoming" ? "active" : ""}`} onClick={() => setSettingsTab("upcoming")}>
                Upcoming{activeAppointments.length > 0 && ` (${activeAppointments.length})`}
              </button>
              <button className={`settings-tab ${settingsTab === "history" ? "active" : ""}`} onClick={() => setSettingsTab("history")}>History</button>
            </div>

            {/* Tab content */}
            <div className="settings-content">
              {settingsTab === "profile" && (
                <div className="settings-profile">
                  <div className="settings-profile-header">
                    <div className="settings-avatar">
                      {(patient?.first_name?.[0] || user?.email?.[0] || "U").toUpperCase()}
                    </div>
                    <div>
                      <p className="settings-name">{patient ? `${patient.first_name} ${patient.last_name}` : user?.email}</p>
                      <p className="settings-email">{patient?.email || user?.email}</p>
                    </div>
                  </div>

                  {!editing ? (
                    <>
                      <div className="settings-details">
                        <DetailRow label="Phone" value={patient?.phone} />
                        <DetailRow label="Date of Birth" value={patient?.dob} />
                        <DetailRow label="Gender" value={patient?.gender} />
                        <DetailRow label="Member since" value={patient?.created_at ? new Date(patient.created_at).toLocaleDateString("en-US", { month: "short", year: "numeric" }) : undefined} />
                      </div>
                      <button className="settings-edit-btn" onClick={startEditing}>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                          <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                        </svg>
                        Edit Profile
                      </button>
                    </>
                  ) : (
                    <div className="settings-edit-form">
                      {editError && <div className="settings-edit-error">{editError}</div>}
                      <EditField label="First Name" value={editFirst} onChange={setEditFirst} />
                      <EditField label="Last Name" value={editLast} onChange={setEditLast} />
                      <EditField label="Phone" value={editPhone} onChange={setEditPhone} />
                      <EditField label="Date of Birth" value={editDob} onChange={setEditDob} type="date" />
                      <div className="settings-field">
                        <label>Gender</label>
                        <select value={editGender} onChange={(e) => setEditGender(e.target.value)}>
                          <option value="">Not specified</option>
                          <option value="Male">Male</option>
                          <option value="Female">Female</option>
                          <option value="Other">Other</option>
                        </select>
                      </div>
                      <div className="settings-edit-actions">
                        <button className="settings-save-btn" onClick={saveProfile} disabled={saving}>{saving ? "Saving..." : "Save"}</button>
                        <button className="settings-cancel-btn" onClick={cancelEditing} disabled={saving}>Cancel</button>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {settingsTab === "upcoming" && (
                <div className="settings-appointments">
                  {activeAppointments.length === 0 ? (
                    <div className="settings-empty">No upcoming appointments</div>
                  ) : (
                    activeAppointments.map((apt) => <AppointmentCard key={apt.appointment_id} appointment={apt} />)
                  )}
                </div>
              )}

              {settingsTab === "history" && (
                <div className="settings-appointments">
                  {historyAppointments.length === 0 ? (
                    <div className="settings-empty">No past appointments</div>
                  ) : (
                    historyAppointments.map((apt) => <AppointmentCard key={apt.appointment_id} appointment={apt} />)
                  )}
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// ─── Sub-components ────────────────────────────────────────────────────────────

function DetailRow({ label, value }: { label: string; value?: string | null }) {
  return (
    <div className="settings-detail-row">
      <span className="settings-detail-label">{label}</span>
      <span className="settings-detail-value">{value || "—"}</span>
    </div>
  );
}

function EditField({ label, value, onChange, type = "text" }: { label: string; value: string; onChange: (v: string) => void; type?: string }) {
  return (
    <div className="settings-field">
      <label>{label}</label>
      <input type={type} value={value} onChange={(e) => onChange(e.target.value)} />
    </div>
  );
}

function AppointmentCard({ appointment }: { appointment: AppointmentItem }) {
  const date = new Date(appointment.start_datetime);
  const dateStr = date.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });
  const timeStr = date.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });

  const statusClass = appointment.status === "BOOKED" ? "status--booked"
    : appointment.status === "CANCELLED" ? "status--cancelled"
    : appointment.status === "COMPLETED" ? "status--completed"
    : "status--other";

  return (
    <div className="appointment-card">
      <div className="appointment-card-date">
        <span className="appointment-card-day">{dateStr}</span>
        <span className="appointment-card-time">{timeStr}</span>
      </div>
      <div className="appointment-card-info">
        <span className="appointment-card-doctor">{appointment.doctor_name || "Doctor"}</span>
        <span className="appointment-card-type">
          {appointment.appointment_type_name || "Consultation"}
          {appointment.doctor_specialization && ` · ${appointment.doctor_specialization}`}
        </span>
      </div>
      <span className={`appointment-card-status ${statusClass}`}>{appointment.status}</span>
    </div>
  );
}
