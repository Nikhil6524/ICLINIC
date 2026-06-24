from datetime import datetime

from control.tools.base_tool import BaseTool
from pydantic import BaseModel, Field


class RescheduleToolInput(BaseModel):
    appointment_id: str = Field(description="UUID of the appointment to reschedule")

    new_start_datetime: str = Field(
        description="New appointment start date and time in ISO format (YYYY-MM-DDTHH:MM:SS)"
    )


class RescheduleTool(BaseTool):
    name = "reschedule_tool"

    description = (
        "Reschedule an existing appointment to a new date/time. "
        "Validates that the new slot is available."
    )

    args_schema = RescheduleToolInput

    def __init__(self, appointment_service):
        self.appointment_service = appointment_service

    async def execute(
        self,
        appointment_id: str,
        new_start_datetime: str,
    ):
        from uuid import UUID

        try:
            new_start_dt = datetime.fromisoformat(new_start_datetime)
        except ValueError:
            return {
                "error": f"Invalid datetime format: {new_start_datetime}. Use ISO format."
            }

        try:
            apt_uuid = UUID(appointment_id)
        except ValueError:
            return {"error": f"Invalid appointment ID: {appointment_id}"}

        try:
            appointment = self.appointment_service.reschedule_appointment(
                appointment_id=apt_uuid,
                new_start_datetime=new_start_dt,
            )

            # Lock new slot in Redis (old slot freed automatically via DB)
            try:
                from src.data.clients.redis_client import SessionStore

                new_iso = new_start_dt.strftime("%Y-%m-%dT%H:%M:%S")
                store = SessionStore(f"reschedule-{apt_uuid}")
                store.lock_slot(str(appointment.doctor_id), new_iso)
            except Exception:
                pass

            return {
                "success": True,
                "appointment_id": str(appointment.appointment_id),
                "new_start_datetime": appointment.start_datetime.isoformat(),
                "new_end_datetime": appointment.end_datetime.isoformat(),
                "status": appointment.status,
                "message": "Appointment rescheduled successfully.",
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e.detail) if hasattr(e, "detail") else str(e),
            }
