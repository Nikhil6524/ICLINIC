import { useEffect, useState } from "react";
import { useAuth } from "../../auth/context/AuthContext";
import {
  profileService,
  type PatientResponse,
  type UpdateProfilePayload,
} from "../../profile/services/profileService";
import { ChatWindow } from "../../chat/components/ChatWindow";
import { CallButton } from "../../chat/components/CallButton";
import { useWebSocketChat } from "../../../hooks/useWebSocketChat";
import "./Dashboard.css";

export function Dashboard() {
  const { user, logout } = useAuth();
  const [patient, setPatient] = useState<PatientResponse | null>(null);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);

  // Chat hook — embedded directly in dashboard
  const {
    messages,
    sendMessage,
    clearMessages,
    isConnected,
    isTyping,
    sessionId,
    reconnect,
  } = useWebSocketChat();

  // Edit form state
  const [editFirst, setEditFirst] = useState("");
  const [editLast, setEditLast] = useState("");
  const [editPhone, setEditPhone] = useState("");
  const [editDob, setEditDob] = useState("");
  const [editGender, setEditGender] = useState("");

  useEffect(() => {
    profileService
      .getMyProfile()
      .then((res) => setPatient(res.data))
      .catch(() => {});
  }, []);

  const firstName = patient?.first_name || user?.email?.split("@")[0] || "there";

  const startEditing = () => {
    setEditFirst(patient?.first_name || "");
    setEditLast(patient?.last_name || "");
    setEditPhone(patient?.phone || "");
    setEditDob(patient?.dob || "");
    setEditGender(patient?.gender || "");
    setEditError(null);
    setEditing(true);
  };

  const cancelEditing = () => {
    setEditing(false);
    setEditError(null);
  };

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
          <button className="btn-logout" onClick={logout}>Sign Out</button>
        </div>
      </header>

      {/* Main Grid: Chat on left, Profile on right */}
      <div className="dashboard-grid">
        {/* Left: Embedded Chat */}
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
                    <path d="M21 2v6h-6" />
                    <path d="M3 12a9 9 0 0 1 15-6.7L21 8" />
                    <path d="M3 22v-6h6" />
                    <path d="M21 12a9 9 0 0 1-15 6.7L3 16" />
                  </svg>
                </button>
              )}
              <button className="dashboard-chat-action-btn" onClick={clearMessages} title="Clear chat">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M3 6h18" />
                  <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                  <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
                </svg>
              </button>
            </div>
          </div>
          <div className="dashboard-chat-body">
            <ChatWindow
              messages={messages}
              isTyping={isTyping}
              isConnected={isConnected}
              onSendMessage={sendMessage}
            />
          </div>
        </div>

        {/* Right: Profile Panel */}
        <aside className="dashboard-sidebar">
          <div className="profile-panel">
            <div className="profile-panel-header">
              <div className="profile-panel-avatar">
                {(patient?.first_name?.[0] || user?.email?.[0] || "U").toUpperCase()}
              </div>
              <div className="profile-panel-identity">
                <h3>{patient ? `${patient.first_name} ${patient.last_name}` : user?.email}</h3>
                <span>{patient?.email || user?.email}</span>
              </div>
            </div>

            {!editing ? (
              <>
                <div className="profile-panel-rows">
                  <ProfileRow label="Phone" value={patient?.phone} />
                  <ProfileRow label="Date of Birth" value={patient?.dob} />
                  <ProfileRow label="Gender" value={patient?.gender} />
                  <ProfileRow label="Member since" value={patient?.created_at ? new Date(patient.created_at).toLocaleDateString("en-US", { month: "short", year: "numeric" }) : undefined} />
                </div>
                <button className="profile-edit-btn" onClick={startEditing}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                  </svg>
                  Edit Profile
                </button>
              </>
            ) : (
              <div className="profile-edit-form">
                {editError && <div className="profile-edit-error">{editError}</div>}
                <div className="profile-edit-row">
                  <label>First Name</label>
                  <input value={editFirst} onChange={(e) => setEditFirst(e.target.value)} />
                </div>
                <div className="profile-edit-row">
                  <label>Last Name</label>
                  <input value={editLast} onChange={(e) => setEditLast(e.target.value)} />
                </div>
                <div className="profile-edit-row">
                  <label>Phone</label>
                  <input value={editPhone} onChange={(e) => setEditPhone(e.target.value)} />
                </div>
                <div className="profile-edit-row">
                  <label>Date of Birth</label>
                  <input type="date" value={editDob} onChange={(e) => setEditDob(e.target.value)} />
                </div>
                <div className="profile-edit-row">
                  <label>Gender</label>
                  <select value={editGender} onChange={(e) => setEditGender(e.target.value)}>
                    <option value="">Not specified</option>
                    <option value="Male">Male</option>
                    <option value="Female">Female</option>
                    <option value="Other">Other</option>
                  </select>
                </div>
                <div className="profile-edit-actions">
                  <button className="profile-save-btn" onClick={saveProfile} disabled={saving}>
                    {saving ? "Saving..." : "Save"}
                  </button>
                  <button className="profile-cancel-btn" onClick={cancelEditing} disabled={saving}>
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}

function ProfileRow({ label, value }: { label: string; value?: string | null }) {
  return (
    <div className="profile-panel-row">
      <span className="profile-panel-label">{label}</span>
      <span className="profile-panel-value">{value || "—"}</span>
    </div>
  );
}
