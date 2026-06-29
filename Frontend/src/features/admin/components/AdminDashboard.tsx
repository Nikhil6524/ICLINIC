import { useEffect, useState } from "react";
import { useAuth } from "../../auth/context/AuthContext";
import { adminService, type DoctorSchedule, type BookedSlot } from "../services/adminService";
import "./AdminDashboard.css";

type Modal = "none" | "add-doctor" | "block-time" | "slot-detail" | "book-appointment";

export function AdminDashboard() {
  const { user, logout } = useAuth();
  const [date, setDate] = useState(() => new Date().toISOString().split("T")[0]);
  const [schedule, setSchedule] = useState<DoctorSchedule[]>([]);
  const [loading, setLoading] = useState(true);

  // Modal state
  const [modal, setModal] = useState<Modal>("none");
  const [selectedSlot, setSelectedSlot] = useState<BookedSlot | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);

  // Add Doctor form
  const [docName, setDocName] = useState("");
  const [docSpec, setDocSpec] = useState("");
  const [docEmail, setDocEmail] = useState("");
  const [docPhone, setDocPhone] = useState("");
  const [docStart, setDocStart] = useState("09:00");
  const [docEnd, setDocEnd] = useState("17:00");
  const [departments, setDepartments] = useState<{ department_id: string; name: string }[]>([]);
  const [docDept, setDocDept] = useState("");

  // Block Time form
  const [blockDoctor, setBlockDoctor] = useState("");
  const [blockStart, setBlockStart] = useState("");
  const [blockEnd, setBlockEnd] = useState("");
  const [blockReason, setBlockReason] = useState("");

  // Book Appointment form
  const [bookDoctor, setBookDoctor] = useState("");
  const [bookPatientName, setBookPatientName] = useState("");
  const [bookPatientPhone, setBookPatientPhone] = useState("");
  const [bookType, setBookType] = useState("");
  const [bookTime, setBookTime] = useState("");
  const [appointmentTypes, setAppointmentTypes] = useState<{ appointment_type_id: string; name: string }[]>([]);

  const loadSchedule = (d: string) => {
    setLoading(true);
    adminService.getSchedule(d)
      .then((res) => setSchedule(res.data.doctors))
      .catch(() => setSchedule([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => { loadSchedule(date); }, [date]);

  useEffect(() => {
    adminService.getDepartments().then((res) => setDepartments(res.data)).catch(() => {});
    adminService.getAppointmentTypes().then((res) => setAppointmentTypes(res.data)).catch(() => {});
  }, []);

  // ─── Handlers ─────────────────────────────────────────────────────────────────

  const handleCancel = async (appointmentId: string) => {
    if (!confirm("Cancel this appointment?")) return;
    setActionLoading(true);
    try {
      await adminService.cancelAppointment(appointmentId);
      loadSchedule(date);
      setModal("none"); setSelectedSlot(null);
    } catch (e: any) { alert(e?.response?.data?.detail || "Failed to cancel"); }
    finally { setActionLoading(false); }
  };

  const handleAddDoctor = async () => {
    setModalError(null);
    if (!docName || !docSpec || !docEmail || !docDept) { setModalError("All required fields must be filled"); return; }
    setActionLoading(true);
    try {
      await adminService.addDoctor({ department_id: docDept, auth_user_id: "system", full_name: docName, specialization: docSpec, email: docEmail, phone: docPhone || undefined, working_start_time: docStart, working_end_time: docEnd });
      setModal("none"); resetDoctorForm(); loadSchedule(date);
    } catch (e: any) { setModalError(e?.response?.data?.detail || "Failed to add doctor"); }
    finally { setActionLoading(false); }
  };

  const handleBlockTime = async () => {
    setModalError(null);
    if (!blockDoctor || !blockStart || !blockEnd) { setModalError("All fields are required"); return; }
    if (blockStart >= blockEnd) { setModalError("End time must be after start time"); return; }
    setActionLoading(true);
    try {
      await adminService.blockDoctorTime({ doctor_id: blockDoctor, start_datetime: `${date}T${blockStart}:00`, end_datetime: `${date}T${blockEnd}:00`, reason: blockReason || undefined });
      setModal("none"); setBlockDoctor(""); setBlockStart(""); setBlockEnd(""); setBlockReason(""); loadSchedule(date);
    } catch (e: any) { setModalError(e?.response?.data?.detail || "Failed to block time"); }
    finally { setActionLoading(false); }
  };

  const handleBookAppointment = async () => {
    setModalError(null);
    if (!bookDoctor || !bookPatientName || !bookPatientPhone || !bookType || !bookTime) { setModalError("All fields are required"); return; }
    setActionLoading(true);
    try {
      // Split name into first/last
      const nameParts = bookPatientName.trim().split(/\s+/);
      const firstName = nameParts[0] || "";
      const lastName = nameParts.slice(1).join(" ") || firstName;

      await adminService.bookByFrontDesk({
        first_name: firstName,
        last_name: lastName,
        phone: bookPatientPhone,
        doctor_id: bookDoctor,
        appointment_type_id: bookType,
        start_datetime: `${date}T${bookTime}:00`,
      });
      setModal("none"); setBookDoctor(""); setBookPatientName(""); setBookPatientPhone(""); setBookType(""); setBookTime(""); loadSchedule(date);
    } catch (e: any) { setModalError(e?.response?.data?.detail || "Failed to book appointment"); }
    finally { setActionLoading(false); }
  };

  const resetDoctorForm = () => { setDocName(""); setDocSpec(""); setDocEmail(""); setDocPhone(""); setDocStart("09:00"); setDocEnd("17:00"); setDocDept(""); };
  const openSlotDetail = (slot: BookedSlot) => { setSelectedSlot(slot); setModal("slot-detail"); };
  const closeModal = () => { setModal("none"); setModalError(null); };

  // ─── Render ───────────────────────────────────────────────────────────────────

  return (
    <div className="admin">
      <header className="admin-header">
        <div className="admin-header-left">
          <span className="admin-logo">iClinic</span>
          <span className="admin-badge">Front Desk</span>
        </div>
        <div className="admin-header-right">
          <span className="admin-user">{user?.email}</span>
          <button className="btn-logout" onClick={logout}>Sign Out</button>
        </div>
      </header>

      {/* Stats bar */}
      <div className="admin-stats">
        <div className="admin-stat">
          <span className="admin-stat-value">{schedule.length}</span>
          <span className="admin-stat-label">Doctors</span>
        </div>
        <div className="admin-stat">
          <span className="admin-stat-value">{schedule.reduce((sum, d) => sum + d.booked_slots.filter(s => s.status === "BOOKED").length, 0)}</span>
          <span className="admin-stat-label">Booked Today</span>
        </div>
        <div className="admin-stat">
          <span className="admin-stat-value">{schedule.reduce((sum, d) => sum + d.unavailability.length, 0)}</span>
          <span className="admin-stat-label">Blocked</span>
        </div>
      </div>

      {/* Controls */}
      <div className="admin-controls">
        <div className="admin-controls-left">
          <h2>Schedule</h2>
          <div className="admin-date-picker">
            <button onClick={() => setDate(shiftDate(date, -1))} className="admin-date-btn">←</button>
            <input type="date" value={date} onChange={(e) => setDate(e.target.value)} className="admin-date-input" />
            <button onClick={() => setDate(shiftDate(date, 1))} className="admin-date-btn">→</button>
          </div>
        </div>
        <div className="admin-controls-right">
          <button className="admin-action-btn admin-action-btn--primary" onClick={() => setModal("book-appointment")}>
            + Book
          </button>
          <button className="admin-action-btn admin-action-btn--secondary" onClick={() => setModal("add-doctor")}>
            + Doctor
          </button>
          <button className="admin-action-btn" onClick={() => setModal("block-time")}>
            Block
          </button>
        </div>
      </div>

      {/* Legend */}
      <div className="gantt-legend">
        <span className="gantt-legend-item"><span className="gantt-legend-swatch gantt-legend--available"></span>Available</span>
        <span className="gantt-legend-item"><span className="gantt-legend-swatch gantt-legend--booked"></span>Booked</span>
        <span className="gantt-legend-item"><span className="gantt-legend-swatch gantt-legend--blocked"></span>Blocked</span>
      </div>

      {/* Gantt Chart */}
      {loading ? (
        <div className="admin-loading">Loading schedule...</div>
      ) : schedule.length === 0 ? (
        <div className="admin-empty">No doctors yet. Click "+ Doctor" to add one.</div>
      ) : (
        <div className="gantt-container">
          <div className="gantt-header">
            <div className="gantt-doctor-label">DOCTOR</div>
            <div className="gantt-timeline">
              {generateHourLabels(schedule).map((h) => (
                <span key={h} className="gantt-hour-label">{h}</span>
              ))}
            </div>
          </div>
          {schedule.map((doc) => (
            <GanttRow key={doc.doctor_id} doctor={doc} allSchedule={schedule} onSlotClick={openSlotDetail} />
          ))}
        </div>
      )}

      {/* ─── Modals ─────────────────────────────────────────────────────────────── */}
      {modal !== "none" && (
        <>
          <div className="admin-overlay" onClick={closeModal} />
          <div className="admin-modal">
            {/* Book Appointment */}
            {modal === "book-appointment" && (
              <>
                <h3>Book Appointment</h3>
                <p className="admin-modal-sub">Book for {formatDate(date)}</p>
                {modalError && <div className="admin-modal-error">{modalError}</div>}
                <div className="admin-modal-form">
                  <div className="admin-modal-row">
                    <Field label="Patient Name" value={bookPatientName} onChange={setBookPatientName} placeholder="John Smith" />
                    <Field label="Phone Number" value={bookPatientPhone} onChange={setBookPatientPhone} placeholder="+91 98765..." />
                  </div>
                  <div className="admin-modal-field">
                    <label>Doctor</label>
                    <select value={bookDoctor} onChange={(e) => setBookDoctor(e.target.value)}>
                      <option value="">Select doctor</option>
                      {schedule.map((d) => <option key={d.doctor_id} value={d.doctor_id}>{d.doctor_name} – {d.specialization}</option>)}
                    </select>
                  </div>
                  <div className="admin-modal-row">
                    <div className="admin-modal-field">
                      <label>Type</label>
                      <select value={bookType} onChange={(e) => setBookType(e.target.value)}>
                        <option value="">Select type</option>
                        {appointmentTypes.map((t) => <option key={t.appointment_type_id} value={t.appointment_type_id}>{t.name}</option>)}
                      </select>
                    </div>
                    <Field label="Time" value={bookTime} onChange={setBookTime} type="time" />
                  </div>
                  {bookTime && <p className="admin-modal-hint">Appointment at {to12h(bookTime)}</p>}
                </div>
                <div className="admin-modal-actions">
                  <button className="admin-modal-save" onClick={handleBookAppointment} disabled={actionLoading}>
                    {actionLoading ? "Booking..." : "Book & Send Confirmation"}
                  </button>
                  <button className="admin-modal-cancel" onClick={closeModal}>Cancel</button>
                </div>
              </>
            )}

            {/* Add Doctor */}
            {modal === "add-doctor" && (
              <>
                <h3>Add Doctor</h3>
                {modalError && <div className="admin-modal-error">{modalError}</div>}
                <div className="admin-modal-form">
                  <Field label="Full Name" value={docName} onChange={setDocName} placeholder="Dr. John Smith" />
                  <Field label="Specialization" value={docSpec} onChange={setDocSpec} placeholder="Cardiology" />
                  <div className="admin-modal-row">
                    <Field label="Email" value={docEmail} onChange={setDocEmail} placeholder="doctor@iclinic.com" type="email" />
                    <Field label="Phone" value={docPhone} onChange={setDocPhone} placeholder="+91..." />
                  </div>
                  <div className="admin-modal-row">
                    <Field label="Start Time" value={docStart} onChange={setDocStart} type="time" />
                    <Field label="End Time" value={docEnd} onChange={setDocEnd} type="time" />
                  </div>
                  {docStart && docEnd && <p className="admin-modal-hint">Working hours: {to12h(docStart)} – {to12h(docEnd)}</p>}
                  <div className="admin-modal-field">
                    <label>Department</label>
                    <select value={docDept} onChange={(e) => setDocDept(e.target.value)}>
                      <option value="">Select department</option>
                      {departments.map((d) => <option key={d.department_id} value={d.department_id}>{d.name}</option>)}
                    </select>
                  </div>
                </div>
                <div className="admin-modal-actions">
                  <button className="admin-modal-save" onClick={handleAddDoctor} disabled={actionLoading}>{actionLoading ? "Adding..." : "Add Doctor"}</button>
                  <button className="admin-modal-cancel" onClick={() => { closeModal(); resetDoctorForm(); }}>Cancel</button>
                </div>
              </>
            )}

            {/* Block Time */}
            {modal === "block-time" && (
              <>
                <h3>Block Doctor Time</h3>
                <p className="admin-modal-sub">Block time on {formatDate(date)}</p>
                {modalError && <div className="admin-modal-error">{modalError}</div>}
                <div className="admin-modal-form">
                  <div className="admin-modal-field">
                    <label>Doctor</label>
                    <select value={blockDoctor} onChange={(e) => setBlockDoctor(e.target.value)}>
                      <option value="">Select doctor</option>
                      {schedule.map((d) => <option key={d.doctor_id} value={d.doctor_id}>{d.doctor_name}</option>)}
                    </select>
                  </div>
                  <div className="admin-modal-row">
                    <Field label="From" value={blockStart} onChange={setBlockStart} type="time" />
                    <Field label="To" value={blockEnd} onChange={setBlockEnd} type="time" />
                  </div>
                  {blockStart && blockEnd && (
                    <p className="admin-modal-hint">
                      {to12h(blockStart)} → {to12h(blockEnd)}
                      {blockStart >= blockEnd && <span className="admin-modal-hint--error"> (End must be after start)</span>}
                    </p>
                  )}
                  <Field label="Reason (optional)" value={blockReason} onChange={setBlockReason} placeholder="e.g. Surgery, Meeting" />
                </div>
                <div className="admin-modal-actions">
                  <button className="admin-modal-save admin-modal-save--warn" onClick={handleBlockTime} disabled={actionLoading || !!(blockStart && blockEnd && blockStart >= blockEnd)}>
                    {actionLoading ? "Blocking..." : "Block Time"}
                  </button>
                  <button className="admin-modal-cancel" onClick={closeModal}>Cancel</button>
                </div>
              </>
            )}

            {/* Slot Detail */}
            {modal === "slot-detail" && selectedSlot && (
              <>
                <h3>Appointment Details</h3>
                <div className="admin-slot-rows">
                  <div><span>Patient</span> <strong>{selectedSlot.patient_name || "Unknown"}</strong></div>
                  <div><span>Time</span> <strong>{formatTime(selectedSlot.start)} – {formatTime(selectedSlot.end)}</strong></div>
                  <div><span>Status</span> <span className={`admin-slot-status admin-slot-status--${selectedSlot.status.toLowerCase()}`}>{selectedSlot.status}</span></div>
                </div>
                {selectedSlot.status === "BOOKED" && (
                  <button className="admin-modal-save admin-modal-save--danger" style={{ width: "100%", marginTop: 16 }} onClick={() => handleCancel(selectedSlot.appointment_id)} disabled={actionLoading}>
                    {actionLoading ? "Cancelling..." : "Cancel This Appointment"}
                  </button>
                )}
                <button className="admin-modal-cancel" style={{ width: "100%", marginTop: 8 }} onClick={closeModal}>Close</button>
              </>
            )}
          </div>
        </>
      )}
    </div>
  );
}

// ─── Sub-components ────────────────────────────────────────────────────────────

function Field({ label, value, onChange, placeholder = "", type = "text" }: {
  label: string; value: string; onChange: (v: string) => void; placeholder?: string; type?: string;
}) {
  return (
    <div className="admin-modal-field">
      <label>{label}</label>
      <input type={type} value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} />
    </div>
  );
}

function GanttRow({ doctor, allSchedule, onSlotClick }: {
  doctor: DoctorSchedule; allSchedule: DoctorSchedule[]; onSlotClick: (s: BookedSlot) => void;
}) {
  const { earliest, latest } = getTimeRange(allSchedule);
  const workStart = new Date(doctor.working_start).getTime();
  const workEnd = new Date(doctor.working_end).getTime();
  const toPercent = (time: number) => ((time - earliest) / (latest - earliest)) * 100;

  return (
    <div className="gantt-row">
      <div className="gantt-doctor-label">
        <span className="gantt-doctor-name">{doctor.doctor_name}</span>
        <span className="gantt-doctor-spec">{doctor.specialization}</span>
      </div>
      <div className="gantt-timeline">
        <div className="gantt-block gantt-block--available" style={{ left: `${toPercent(workStart)}%`, width: `${toPercent(workEnd) - toPercent(workStart)}%` }} />
        {doctor.unavailability.map((u, i) => {
          const s = new Date(u.start).getTime(), e = new Date(u.end).getTime();
          return <div key={`u-${i}`} className="gantt-block gantt-block--unavailable" style={{ left: `${toPercent(s)}%`, width: `${toPercent(e) - toPercent(s)}%` }} title={u.reason || "Blocked"} />;
        })}
        {doctor.booked_slots.map((slot) => {
          const s = new Date(slot.start).getTime(), e = new Date(slot.end).getTime();
          return (
            <div key={slot.appointment_id} className={`gantt-block gantt-block--booked ${slot.status === "CANCELLED" ? "gantt-block--cancelled" : ""}`}
              style={{ left: `${toPercent(s)}%`, width: `${toPercent(e) - toPercent(s)}%` }}
              title={`${slot.patient_name || "Patient"} · ${formatTime(slot.start)}`}
              onClick={() => onSlotClick(slot)}
            />
          );
        })}
      </div>
    </div>
  );
}

// ─── Helpers ───────────────────────────────────────────────────────────────────

function getTimeRange(schedule: DoctorSchedule[]) {
  let earliest = Infinity, latest = -Infinity;
  for (const doc of schedule) {
    const s = new Date(doc.working_start).getTime(), e = new Date(doc.working_end).getTime();
    if (s < earliest) earliest = s;
    if (e > latest) latest = e;
  }
  return { earliest, latest };
}

function generateHourLabels(schedule: DoctorSchedule[]): string[] {
  const { earliest, latest } = getTimeRange(schedule);
  const labels: string[] = [];
  let current = new Date(earliest);
  current.setMinutes(0, 0, 0);
  while (current.getTime() <= latest) {
    labels.push(current.toLocaleTimeString("en-US", { hour: "numeric", hour12: true }));
    current = new Date(current.getTime() + 3600000);
  }
  return labels;
}

function shiftDate(dateStr: string, days: number): string {
  const d = new Date(dateStr); d.setDate(d.getDate() + days); return d.toISOString().split("T")[0];
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
}

function formatDate(dateStr: string): string {
  return new Date(dateStr + "T00:00:00").toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });
}

function to12h(time24: string): string {
  const [h, m] = time24.split(":").map(Number);
  const suffix = h >= 12 ? "PM" : "AM";
  const hour12 = h === 0 ? 12 : h > 12 ? h - 12 : h;
  return `${hour12}:${m.toString().padStart(2, "0")} ${suffix}`;
}
