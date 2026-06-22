from datetime import datetime
from uuid import UUID

from control.tools.base_tool import BaseTool
from pydantic import BaseModel, Field


class AppointmentToolInput(BaseModel):
    patient_id: str = Field(description="UUID of the patient booking the appointment")

    doctor_id: str = Field(description="UUID of the doctor for the appointment")

    appointment_type_id: str = Field(description="UUID of the appointment type")

    start_datetime: str = Field(
        description="Appointment start date and time in ISO format (YYYY-MM-DDTHH:MM:SS)"
    )

    booking_source: str = Field(
        default="AI_CHAT",
        description="Source of booking: AI_CHAT, AI_CALL, or FRONT_DESK",
    )


class AppointmentTool(BaseTool):
    name = "appointment_tool"

    description = (
        "Create and book an appointment for a patient with a doctor. "
        "Requires patient_id, doctor_id, appointment_type_id, and start_datetime. "
        "All IDs must be UUIDs."
    )

    args_schema = AppointmentToolInput

    def __init__(self, appointment_service):
        self.appointment_service = appointment_service

    def _resolve_doctor_id(self, doctor_id: str) -> UUID | None:
        """Try to resolve a doctor_id that might be a name instead of UUID."""
        from src.data.models.postgres.doctor import Doctor

        db = self.appointment_service.db
        found = (
            db.query(Doctor)
            .filter(Doctor.full_name.ilike(f"%{doctor_id}%"), Doctor.active == True)
            .first()
        )
        return found.doctor_id if found else None

    async def execute(
        self,
        patient_id: str,
        doctor_id: str,
        appointment_type_id: str,
        start_datetime: str,
        booking_source: str = "AI_CHAT",
    ):
        # Parse start datetime
        try:
            start_dt = datetime.fromisoformat(start_datetime)
        except ValueError:
            return {
                "error": f"Invalid datetime format: {start_datetime}. "
                "Use ISO format (YYYY-MM-DDTHH:MM:SS)."
            }

        # Parse patient UUID
        try:
            patient_uuid = UUID(patient_id)
        except ValueError:
            return {"error": f"Invalid patient UUID: {patient_id}"}

        # Parse doctor UUID (with fallback to name resolution)
        try:
            doctor_uuid = UUID(doctor_id)
        except ValueError:
            # LLM sometimes passes doctor name instead of UUID
            resolved = self._resolve_doctor_id(doctor_id)
            if resolved:
                doctor_uuid = resolved
            else:
                return {
                    "error": f"Invalid doctor_id: '{doctor_id}'. "
                    "Pass the doctor_id UUID, not the name."
                }

        # Parse appointment type UUID
        try:
            apt_type_uuid = UUID(appointment_type_id)
        except ValueError:
            return {"error": f"Invalid appointment_type UUID: {appointment_type_id}"}

        # Book the appointment
        try:
            appointment = self.appointment_service.book_appointment(
                patient_id=patient_uuid,
                doctor_id=doctor_uuid,
                appointment_type_id=apt_type_uuid,
                start_datetime=start_dt,
                booking_source=booking_source,
                created_by_actor_type="AI",
                created_by_actor_id=patient_uuid,
            )

            return {
                "success": True,
                "appointment_id": str(appointment.appointment_id),
                "patient_id": str(appointment.patient_id),
                "doctor_id": str(appointment.doctor_id),
                "start_datetime": appointment.start_datetime.isoformat(),
                "end_datetime": appointment.end_datetime.isoformat(),
                "status": appointment.status,
                "booking_source": appointment.booking_source,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e.detail) if hasattr(e, "detail") else str(e),
            }
