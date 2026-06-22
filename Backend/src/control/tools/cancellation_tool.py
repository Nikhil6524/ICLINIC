from control.tools.base_tool import BaseTool
from pydantic import BaseModel, Field


class CancellationToolInput(BaseModel):
    appointment_id: str = Field(description="UUID of the appointment to cancel")


class CancellationTool(BaseTool):
    name = "cancellation_tool"

    description = "Cancel an existing appointment by appointment ID."

    args_schema = CancellationToolInput

    def __init__(self, appointment_service):
        self.appointment_service = appointment_service

    async def execute(self, appointment_id: str):
        from uuid import UUID

        try:
            apt_uuid = UUID(appointment_id)
        except ValueError:
            return {"error": f"Invalid appointment ID: {appointment_id}"}

        try:
            appointment = self.appointment_service.cancel_appointment(
                appointment_id=apt_uuid,
            )

            return {
                "success": True,
                "appointment_id": str(appointment.appointment_id),
                "status": appointment.status,
                "message": "Appointment cancelled successfully.",
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e.detail) if hasattr(e, "detail") else str(e),
            }
