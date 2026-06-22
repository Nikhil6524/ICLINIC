from datetime import datetime

from control.tools.base_tool import BaseTool
from pydantic import BaseModel, Field


class AvailabilityToolInput(BaseModel):
    specialty: str = Field(
        description="Medical specialty such as cardiology or dermatology"
    )

    date: str = Field(
        description="Appointment date. Use YYYY-MM-DD format, or 'today' or 'tomorrow'"
    )

    appointment_type: str = Field(
        default="",
        description=(
            "Type of appointment if patient specified one. "
            "Options: General Consultation (15 min), Follow Up (10 min), "
            "Specialist Consultation (30 min), New Patient (45 min). "
            "Leave empty to show all types."
        ),
    )


class AvailabilityTool(BaseTool):
    name = "availability_tool"

    description = (
        "Check doctor availability by specialty and date. "
        "Returns available time slots for doctors matching the specialty."
    )

    args_schema = AvailabilityToolInput

    def __init__(self, doctor_service, appointment_service):
        self.doctor_service = doctor_service
        self.appointment_service = appointment_service

    async def execute(
        self,
        specialty: str,
        date: str,
        appointment_type: str = "",
    ):
        from datetime import timedelta as _timedelta

        # Handle relative date strings
        today = datetime.now()
        date_lower = date.strip().lower()

        if date_lower in ("today", "now"):
            target_date = today
        elif date_lower == "tomorrow":
            target_date = today + _timedelta(days=1)
        else:
            # Try multiple date formats
            target_date = None
            for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y"):
                try:
                    target_date = datetime.strptime(date, fmt)
                    break
                except ValueError:
                    continue

            if target_date is None:
                return {
                    "error": (
                        f"Invalid date format: {date}. "
                        "Use YYYY-MM-DD, DD-MM-YYYY, or words like 'today'/'tomorrow'."
                    )
                }

        # Find doctors by specialty
        doctors = self.doctor_service.get_doctors_by_specialization(specialty)

        if not doctors:
            return {
                "specialty": specialty,
                "date": date,
                "available_slots": [],
                "message": f"No active doctors found for specialty: {specialty}",
            }

        # Find matching appointment type
        from src.data.repositories.appointment_type_repository import (
            AppointmentTypeRepository,
        )

        apt_type_repo = AppointmentTypeRepository(self.doctor_service.db)

        apt_type = None
        if appointment_type:
            apt_type = apt_type_repo.get_by_name(appointment_type)

        if not apt_type:
            # Default to General Consultation
            apt_type = apt_type_repo.get_by_name("General Consultation")

        if not apt_type:
            # Fall back to first active appointment type
            active_types = apt_type_repo.get_all_active()
            if not active_types:
                return {"error": "No appointment types configured in the system."}
            apt_type = active_types[0]

        # Get all available appointment types for the response
        all_types = apt_type_repo.get_all_active()
        appointment_types_info = [
            {
                "appointment_type_id": str(t.appointment_type_id),
                "name": t.name,
                "duration_minutes": t.default_duration_minutes,
            }
            for t in all_types
        ]

        # Gather doctor schedule info: working hours + unavailable slots
        # The LLM will determine valid times from this data
        doctors_schedule = []

        for doctor in doctors:
            # Get all unavailability blocks for the target date
            day_start = target_date.replace(
                hour=doctor.working_start_time.hour,
                minute=doctor.working_start_time.minute,
                second=0,
                microsecond=0,
            )
            day_end = target_date.replace(
                hour=doctor.working_end_time.hour,
                minute=doctor.working_end_time.minute,
                second=0,
                microsecond=0,
            )

            from src.data.repositories.doctor_unavailability_repository import (
                DoctorUnavailabilityRepository,
            )

            unavailability_repo = DoctorUnavailabilityRepository(self.doctor_service.db)
            unavailabilities = unavailability_repo.get_by_doctor_and_date_range(
                doctor.doctor_id, day_start, day_end
            )

            # Format blocked slots
            blocked_slots = []
            for u in unavailabilities:
                blocked_slots.append(
                    {
                        "start": u.start_datetime.strftime("%I:%M %p"),
                        "end": u.end_datetime.strftime("%I:%M %p"),
                        "reason": u.reason or "Unavailable",
                    }
                )

            doctors_schedule.append(
                {
                    "doctor_id": str(doctor.doctor_id),
                    "doctor_name": doctor.full_name,
                    "working_hours": f"{doctor.working_start_time.strftime('%I:%M %p')} - {doctor.working_end_time.strftime('%I:%M %p')}",
                    "unavailable_slots": blocked_slots,
                }
            )

        return {
            "specialty": specialty,
            "date": target_date.strftime("%A, %B %d, %Y"),
            "date_iso": target_date.strftime("%Y-%m-%d"),
            "appointment_type": apt_type.name,
            "appointment_type_id": str(apt_type.appointment_type_id),
            "duration_minutes": apt_type.default_duration_minutes,
            "available_appointment_types": appointment_types_info,
            "doctors_schedule": doctors_schedule,
            "instructions": (
                "Each doctor works during 'working_hours'. "
                "The 'unavailable_slots' list shows times they are BLOCKED (already booked or busy). "
                "The patient can book ANY time during working hours that does NOT overlap with an unavailable slot. "
                "Account for the appointment duration when proposing times. "
                "Suggest times that match the patient's preference (morning/afternoon/specific time)."
            ),
        }
